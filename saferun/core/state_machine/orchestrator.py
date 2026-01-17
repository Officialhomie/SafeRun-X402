from typing import Optional, Dict, Any
from loguru import logger
from .models import (
    WorkflowExecution, WorkflowState, WorkflowConfig,
    CheckpointSnapshot, ApprovalRequest, ApprovalResponse,
    ApprovalDecision, ExecutionState
)
from saferun.core.checkpoints.capture import StateCapture

class WorkflowOrchestrator:
    """
    Core orchestrator managing workflow state transitions.

    This is the heart of SafeRun - it ensures workflows move through
    states correctly and enforces all the rules about approvals,
    rollbacks, and settlement.
    """

    def __init__(self, x402_integration=None):
        self.active_workflows: Dict[str, WorkflowExecution] = {}
        self.x402_integration = x402_integration
        self.state_capture = StateCapture()
        logger.info("WorkflowOrchestrator initialized")

    def initialize_workflow(self, config: WorkflowConfig) -> WorkflowExecution:
        """
        Create a new workflow execution from config.

        This sets up the initial state, validates the configuration,
        and prepares for execution to begin.
        """
        execution = WorkflowExecution(
            workflow_id=config.workflow_id,
            config=config,
            current_state=WorkflowState.INITIALIZED,
        )

        self.active_workflows[config.workflow_id] = execution
        logger.info(f"Workflow {config.workflow_id} initialized")

        return execution

    def start_execution(self, workflow_id: str) -> bool:
        """Transition from INITIALIZED to EXECUTING"""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            logger.error(f"Workflow {workflow_id} not found")
            return False

        if workflow.current_state != WorkflowState.INITIALIZED:
            logger.error(f"Cannot start workflow in state {workflow.current_state}")
            return False

        workflow.current_state = WorkflowState.EXECUTING
        logger.info(f"Workflow {workflow_id} started execution")
        return True

    async def create_checkpoint(
        self,
        workflow_id: str,
        execution_state: ExecutionState
    ) -> Optional[CheckpointSnapshot]:
        """
        Capture execution state at a checkpoint.

        This creates an immutable snapshot of everything the agent
        has done so far, which enables rollback if approval is rejected.
        Also stores the checkpoint as an x402 artifact for persistence.
        """
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            logger.error(f"Workflow {workflow_id} not found")
            return None

        if workflow.current_state != WorkflowState.EXECUTING:
            logger.error(f"Cannot checkpoint workflow in state {workflow.current_state}")
            return None

        # Get current checkpoint config
        checkpoint_config = workflow.config.checkpoints[workflow.current_checkpoint_index]

        snapshot = CheckpointSnapshot(
            workflow_id=workflow_id,
            checkpoint_id=checkpoint_config.checkpoint_id,
            execution_state=execution_state,
            approval_required=checkpoint_config.requires_approval
        )

        # Store checkpoint as x402 artifact
        if self.x402_integration:
            try:
                # Serialize the execution state
                serialized_state = self.state_capture.serialize_state(execution_state)
                
                # Store as x402 artifact
                artifact_uri = await self.x402_integration.store_checkpoint_artifact(
                    checkpoint_id=snapshot.checkpoint_id,
                    checkpoint_data=serialized_state,
                    metadata={
                        "workflow_id": workflow_id,
                        "snapshot_id": snapshot.snapshot_id,
                        "checkpoint_name": checkpoint_config.name,
                        "approval_required": checkpoint_config.requires_approval
                    }
                )
                
                snapshot.artifact_uri = artifact_uri
                logger.info(f"Checkpoint {snapshot.snapshot_id} stored as x402 artifact: {artifact_uri}")
            except Exception as e:
                logger.error(f"Failed to store checkpoint as x402 artifact: {e}")
                # Continue without artifact storage - checkpoint still created locally

        workflow.snapshots.append(snapshot)
        logger.info(f"Checkpoint {snapshot.snapshot_id} created for workflow {workflow_id}")

        return snapshot

    def request_approval(
        self,
        workflow_id: str,
        snapshot_id: str,
        summary: str,
        context: Dict[str, Any]
    ) -> Optional[ApprovalRequest]:
        """
        Transition to AWAITING_APPROVAL and create approval request.

        This pauses execution and routes the decision to a human supervisor.
        """
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return None

        # Find the snapshot
        snapshot = next((s for s in workflow.snapshots if s.snapshot_id == snapshot_id), None)
        if not snapshot:
            logger.error(f"Snapshot {snapshot_id} not found")
            return None

        # Transition to awaiting approval
        workflow.current_state = WorkflowState.AWAITING_APPROVAL

        # Create approval request
        request = ApprovalRequest(
            workflow_id=workflow_id,
            checkpoint_id=snapshot.checkpoint_id,
            snapshot_id=snapshot_id,
            summary=summary,
            context=context
        )

        workflow.approval_requests.append(request)
        logger.info(f"Approval requested for workflow {workflow_id}")

        return request

    def submit_approval(
        self,
        workflow_id: str,
        response: ApprovalResponse
    ) -> bool:
        """
        Process human approval decision and transition accordingly.

        Approved -> continue execution
        Rejected -> rollback or fail
        Modified -> apply modifications and continue
        """
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return False

        if workflow.current_state != WorkflowState.AWAITING_APPROVAL:
            logger.error(f"Cannot process approval in state {workflow.current_state}")
            return False

        workflow.approval_responses.append(response)

        if response.decision == ApprovalDecision.APPROVED:
            # Move to next checkpoint or settle if done
            workflow.current_checkpoint_index += 1

            if workflow.current_checkpoint_index >= len(workflow.config.checkpoints):
                workflow.current_state = WorkflowState.SETTLING
                logger.info(f"Workflow {workflow_id} moving to settlement")
            else:
                workflow.current_state = WorkflowState.EXECUTING
                logger.info(f"Workflow {workflow_id} continuing execution")

            return True

        elif response.decision == ApprovalDecision.REJECTED:
            # Trigger rollback
            checkpoint_config = workflow.config.checkpoints[workflow.current_checkpoint_index]

            if checkpoint_config.can_rollback:
                workflow.current_state = WorkflowState.ROLLING_BACK
                logger.info(f"Workflow {workflow_id} rolling back")
            else:
                workflow.current_state = WorkflowState.FAILED
                workflow.error_message = "Approval rejected and rollback not permitted"
                logger.info(f"Workflow {workflow_id} failed")

            return True

        elif response.decision == ApprovalDecision.MODIFIED:
            # Apply modifications and continue
            workflow.current_state = WorkflowState.EXECUTING
            logger.info(f"Workflow {workflow_id} continuing with modifications")
            return True

        return False

    def complete_rollback(self, workflow_id: str, success: bool) -> bool:
        """Mark rollback as completed"""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return False

        if success:
            # Return to previous checkpoint
            workflow.current_checkpoint_index = max(0, workflow.current_checkpoint_index - 1)
            workflow.current_state = WorkflowState.EXECUTING
            logger.info(f"Workflow {workflow_id} rolled back successfully")
        else:
            workflow.current_state = WorkflowState.FAILED
            workflow.error_message = "Rollback failed"
            logger.error(f"Workflow {workflow_id} rollback failed")

        return True

    def settle_workflow(self, workflow_id: str, final_state: Dict[str, Any]) -> bool:
        """
        Transition to SETTLING and prepare for payment distribution.

        This calculates how much work was completed and prepares
        the x402 settlement based on completion percentage.
        """
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return False

        workflow.current_state = WorkflowState.SETTLING
        logger.info(f"Workflow {workflow_id} settling with state: {final_state}")

        return True

    def complete_workflow(self, workflow_id: str) -> bool:
        """Mark workflow as completed"""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return False

        from datetime import datetime
        workflow.current_state = WorkflowState.COMPLETED
        workflow.completed_at = datetime.utcnow()
        logger.info(f"Workflow {workflow_id} completed")

        return True

    def fail_workflow(self, workflow_id: str, error: str) -> bool:
        """Mark workflow as failed"""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return False

        from datetime import datetime
        workflow.current_state = WorkflowState.FAILED
        workflow.error_message = error
        workflow.completed_at = datetime.utcnow()
        logger.error(f"Workflow {workflow_id} failed: {error}")

        return True

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowExecution]:
        """Retrieve workflow execution state"""
        return self.active_workflows.get(workflow_id)
