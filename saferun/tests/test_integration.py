"""
End-to-End Integration Tests

Tests complete workflows from creation through approval to completion.
"""

import pytest
import asyncio
from datetime import datetime

from saferun.core.state_machine.orchestrator import WorkflowOrchestrator
from saferun.core.state_machine.models import (
    WorkflowConfig,
    CheckpointConfig,
    ExecutionState,
    ApprovalResponse,
    ApprovalDecision,
    WorkflowState
)
from saferun.core.checkpoints.capture import CheckpointManager
from saferun.agents.executor.agent import ExecutorAgent
from saferun.agents.monitor.agent import MonitorAgent
from saferun.agents.supervisor.agent import SupervisorAgent
from saferun.core.rollback.reconciliation import ReconciliationAgent


class TestCompleteWorkflow:
    """Test a complete workflow from start to finish"""

    def test_complete_approval_workflow(self):
        """Test workflow with approval and completion"""
        # Setup
        orchestrator = WorkflowOrchestrator()
        checkpoint_manager = CheckpointManager()

        # Create workflow config
        config = WorkflowConfig(
            name="Test Workflow",
            description="End-to-end test",
            checkpoints=[
                CheckpointConfig(
                    name="Review Step 1",
                    description="First checkpoint"
                ),
                CheckpointConfig(
                    name="Review Step 2",
                    description="Second checkpoint"
                )
            ],
            escrow_amount=100.0,
            poster_id="test_poster",
            executor_id="test_executor"
        )

        # Initialize workflow
        execution = orchestrator.initialize_workflow(config)
        workflow_id = execution.workflow_id

        # Verify initialization
        assert execution.current_state == WorkflowState.INITIALIZED
        assert execution.workflow_id == config.workflow_id

        # Start execution
        assert orchestrator.start_execution(workflow_id)
        execution = orchestrator.get_workflow(workflow_id)
        assert execution.current_state == WorkflowState.EXECUTING

        # Create first checkpoint
        exec_state_1 = ExecutionState(
            checkpoint_id=config.checkpoints[0].checkpoint_id,
            agent_memory={"step": 1, "data": "test_data_1"},
            api_calls=[{"call_id": "call_1", "status": "success"}],
            intermediate_outputs={"output_1": "result_1"}
        )

        checkpoint_1 = checkpoint_manager.create_checkpoint(
            checkpoint_id=config.checkpoints[0].checkpoint_id,
            agent_memory=exec_state_1.agent_memory,
            api_calls=exec_state_1.api_calls,
            intermediate_outputs=exec_state_1.intermediate_outputs
        )

        assert checkpoint_1 is not None
        assert checkpoint_1.checkpoint_id == config.checkpoints[0].checkpoint_id

        # Create checkpoint in orchestrator
        snapshot_1 = orchestrator.create_checkpoint(workflow_id, exec_state_1)
        assert snapshot_1 is not None

        # Request approval
        request_1 = orchestrator.request_approval(
            workflow_id,
            snapshot_1.snapshot_id,
            "Please review step 1",
            {"detail": "test"}
        )

        assert request_1 is not None
        execution = orchestrator.get_workflow(workflow_id)
        assert execution.current_state == WorkflowState.AWAITING_APPROVAL

        # Create supervisor
        supervisor = SupervisorAgent(supervisor_id="test_supervisor")
        approval_req_1 = supervisor.create_approval_request(
            workflow_id=workflow_id,
            checkpoint_id=config.checkpoints[0].checkpoint_id,
            snapshot_id=snapshot_1.snapshot_id,
            execution_state=exec_state_1
        )

        assert approval_req_1 is not None

        # Approve first checkpoint
        response_1 = supervisor.submit_decision(
            request_id=approval_req_1.request_id,
            decision=ApprovalDecision.APPROVED,
            rationale="Looks good, proceed",
            approved_by="test_supervisor"
        )

        assert response_1.decision == ApprovalDecision.APPROVED

        # Submit to orchestrator
        assert orchestrator.submit_approval(workflow_id, response_1)
        execution = orchestrator.get_workflow(workflow_id)
        assert execution.current_state == WorkflowState.EXECUTING
        assert execution.current_checkpoint_index == 1

        # Second checkpoint
        exec_state_2 = ExecutionState(
            checkpoint_id=config.checkpoints[1].checkpoint_id,
            agent_memory={"step": 2, "data": "test_data_2"},
            intermediate_outputs={"output_2": "result_2"}
        )

        snapshot_2 = orchestrator.create_checkpoint(workflow_id, exec_state_2)
        request_2 = orchestrator.request_approval(
            workflow_id,
            snapshot_2.snapshot_id,
            "Please review step 2",
            {}
        )

        approval_req_2 = supervisor.create_approval_request(
            workflow_id=workflow_id,
            checkpoint_id=config.checkpoints[1].checkpoint_id,
            snapshot_id=snapshot_2.snapshot_id,
            execution_state=exec_state_2
        )

        # Approve second checkpoint
        response_2 = supervisor.submit_decision(
            request_id=approval_req_2.request_id,
            decision=ApprovalDecision.APPROVED,
            rationale="Final approval",
            approved_by="test_supervisor"
        )

        assert orchestrator.submit_approval(workflow_id, response_2)
        execution = orchestrator.get_workflow(workflow_id)
        assert execution.current_state == WorkflowState.SETTLING

        # Complete workflow
        assert orchestrator.settle_workflow(workflow_id, {"completion": "100%"})
        assert orchestrator.complete_workflow(workflow_id)

        execution = orchestrator.get_workflow(workflow_id)
        assert execution.current_state == WorkflowState.COMPLETED
        assert execution.completed_at is not None
        assert len(execution.snapshots) == 2
        assert len(execution.approval_responses) == 2

    def test_workflow_with_modification(self):
        """Test workflow where human modifies the plan"""
        orchestrator = WorkflowOrchestrator()

        config = WorkflowConfig(
            name="Modification Test",
            description="Test modification flow",
            checkpoints=[
                CheckpointConfig(name="Review", description="Test")
            ],
            escrow_amount=50.0,
            poster_id="poster",
            executor_id="executor"
        )

        execution = orchestrator.initialize_workflow(config)
        workflow_id = execution.workflow_id
        orchestrator.start_execution(workflow_id)

        # Create checkpoint with initial data
        exec_state = ExecutionState(
            checkpoint_id=config.checkpoints[0].checkpoint_id,
            agent_memory={"value": 100},
            intermediate_outputs={"calculation": "10 * 10 = 100"}
        )

        snapshot = orchestrator.create_checkpoint(workflow_id, exec_state)
        request = orchestrator.request_approval(
            workflow_id,
            snapshot.snapshot_id,
            "Review calculation",
            {}
        )

        supervisor = SupervisorAgent(supervisor_id="supervisor")
        approval_req = supervisor.create_approval_request(
            workflow_id=workflow_id,
            checkpoint_id=config.checkpoints[0].checkpoint_id,
            snapshot_id=snapshot.snapshot_id,
            execution_state=exec_state
        )

        # Modify the value
        response = supervisor.submit_decision(
            request_id=approval_req.request_id,
            decision=ApprovalDecision.MODIFIED,
            rationale="Should be 10 pizzas not 100",
            approved_by="supervisor",
            modifications={"value": 10}
        )

        assert response.decision == ApprovalDecision.MODIFIED
        assert response.modifications == {"value": 10}

        assert orchestrator.submit_approval(workflow_id, response)
        execution = orchestrator.get_workflow(workflow_id)
        assert execution.current_state == WorkflowState.SETTLING

    def test_workflow_with_rejection_and_rollback(self):
        """Test workflow rejection triggers rollback"""
        orchestrator = WorkflowOrchestrator()

        config = WorkflowConfig(
            name="Rollback Test",
            description="Test rejection flow",
            checkpoints=[
                CheckpointConfig(
                    name="Review",
                    description="Test",
                    can_rollback=True
                )
            ],
            escrow_amount=50.0,
            poster_id="poster",
            executor_id="executor"
        )

        execution = orchestrator.initialize_workflow(config)
        workflow_id = execution.workflow_id
        orchestrator.start_execution(workflow_id)

        # Create checkpoint
        exec_state = ExecutionState(
            checkpoint_id=config.checkpoints[0].checkpoint_id,
            agent_memory={"action": "delete_database"},
            api_calls=[
                {"call_id": "call_1", "has_side_effects": True}
            ]
        )

        snapshot = orchestrator.create_checkpoint(workflow_id, exec_state)
        request = orchestrator.request_approval(
            workflow_id,
            snapshot.snapshot_id,
            "Review destructive action",
            {}
        )

        supervisor = SupervisorAgent(supervisor_id="supervisor")
        approval_req = supervisor.create_approval_request(
            workflow_id=workflow_id,
            checkpoint_id=config.checkpoints[0].checkpoint_id,
            snapshot_id=snapshot.snapshot_id,
            execution_state=exec_state
        )

        # Reject the dangerous action
        response = supervisor.submit_decision(
            request_id=approval_req.request_id,
            decision=ApprovalDecision.REJECTED,
            rationale="Dangerous action - rejecting",
            approved_by="supervisor"
        )

        assert orchestrator.submit_approval(workflow_id, response)
        execution = orchestrator.get_workflow(workflow_id)
        assert execution.current_state == WorkflowState.ROLLING_BACK

        # Complete rollback
        assert orchestrator.complete_rollback(workflow_id, success=True)
        execution = orchestrator.get_workflow(workflow_id)
        assert execution.current_state == WorkflowState.EXECUTING


@pytest.mark.asyncio
class TestAgentIntegration:
    """Test agent components working together"""

    async def test_executor_with_monitor(self):
        """Test executor agent with monitor watching"""
        executor = ExecutorAgent(agent_id="test_executor")
        monitor = MonitorAgent(monitor_id="test_monitor")

        # Execute a simple task (without actual API calls for testing)
        executor.execution_context = {
            "task": "test",
            "status": "executing"
        }

        # Capture state
        state = executor.capture_current_state("checkpoint_1")

        # Monitor checks the state
        checkpoint_config = CheckpointConfig(
            checkpoint_id="checkpoint_1",
            name="Test",
            description="Test checkpoint"
        )

        report = await monitor.monitor_execution(state, checkpoint_config)

        assert report["checkpoint_id"] == "checkpoint_1"
        assert "should_checkpoint" in report
        assert "telemetry" in report

    async def test_full_agent_workflow(self):
        """Test all agents working together in a workflow"""
        orchestrator = WorkflowOrchestrator()
        executor = ExecutorAgent(agent_id="executor")
        monitor = MonitorAgent(monitor_id="monitor")
        supervisor = SupervisorAgent(supervisor_id="supervisor")

        # Create workflow
        config = WorkflowConfig(
            name="Full Agent Test",
            description="Test all agents",
            checkpoints=[
                CheckpointConfig(name="Review", description="Test")
            ],
            escrow_amount=100.0,
            poster_id="poster",
            executor_id="executor"
        )

        execution = orchestrator.initialize_workflow(config)
        workflow_id = execution.workflow_id
        orchestrator.start_execution(workflow_id)

        # Executor captures state
        executor.execution_context = {"test": "data"}
        executor.api_call_history = [{"call": "test"}]
        executor.decision_trace = ["Decision 1"]

        exec_state = executor.capture_current_state(
            config.checkpoints[0].checkpoint_id
        )

        # Monitor reviews
        checkpoint_config = config.checkpoints[0]
        monitor_report = await monitor.monitor_execution(
            exec_state,
            checkpoint_config
        )

        # Create checkpoint
        snapshot = orchestrator.create_checkpoint(workflow_id, exec_state)
        request = orchestrator.request_approval(
            workflow_id,
            snapshot.snapshot_id,
            "Review",
            {}
        )

        # Supervisor handles approval
        approval_req = supervisor.create_approval_request(
            workflow_id=workflow_id,
            checkpoint_id=config.checkpoints[0].checkpoint_id,
            snapshot_id=snapshot.snapshot_id,
            execution_state=exec_state,
            monitoring_report=monitor_report
        )

        display = supervisor.format_for_display(approval_req)

        assert "sections" in display
        assert display["request_id"] == approval_req.request_id

        # Approve
        response = supervisor.submit_decision(
            request_id=approval_req.request_id,
            decision=ApprovalDecision.APPROVED,
            rationale="All good",
            approved_by="supervisor"
        )

        assert orchestrator.submit_approval(workflow_id, response)

        # Verify stats
        stats = supervisor.get_approval_stats()
        assert stats["total_approvals"] == 1
        assert stats["decision_breakdown"]["approved"] == 1


class TestCheckpointPersistence:
    """Test checkpoint capture and restoration"""

    def test_checkpoint_serialization(self):
        """Test checkpoint can be serialized and deserialized"""
        manager = CheckpointManager()

        # Create checkpoint
        checkpoint = manager.create_checkpoint(
            checkpoint_id="test_cp",
            agent_memory={"key": "value"},
            api_calls=[{"call_id": "1"}],
            intermediate_outputs={"output": "data"},
            decision_trace=["decision 1"],
            resource_consumption={"tokens": 100}
        )

        # Export
        serialized = manager.export_checkpoint("test_cp")
        assert serialized is not None

        # Import to new checkpoint
        assert manager.import_checkpoint("test_cp_copy", serialized)

        # Verify restored
        restored = manager.get_checkpoint("test_cp_copy")
        assert restored is not None
        assert restored.agent_memory == {"key": "value"}
        assert len(restored.api_calls) == 1
        assert restored.intermediate_outputs == {"output": "data"}

    def test_checkpoint_restoration(self):
        """Test agent can restore from checkpoint"""
        manager = CheckpointManager()
        executor = ExecutorAgent(agent_id="test")

        # Set initial state
        executor.execution_context = {"step": 1}
        executor.api_call_history = [{"call": 1}]
        executor.decision_trace = ["decision 1"]

        # Create checkpoint
        state = executor.capture_current_state("cp1")
        manager.create_checkpoint(
            checkpoint_id="cp1",
            agent_memory=state.agent_memory,
            api_calls=state.api_calls,
            decision_trace=state.decision_trace
        )

        # Modify state
        executor.execution_context = {"step": 2}
        executor.api_call_history.append({"call": 2})

        # Restore from checkpoint
        restored_state = manager.restore_checkpoint("cp1")
        assert restored_state is not None

        executor.restore_state(restored_state)

        # Verify restoration
        assert executor.execution_context == {"step": 1}
        assert len(executor.api_call_history) == 1


@pytest.mark.asyncio
class TestReconciliation:
    """Test rollback and reconciliation"""

    async def test_reconciliation_workflow(self):
        """Test complete reconciliation flow"""
        reconciliation_agent = ReconciliationAgent()

        # Create mock execution state
        exec_state = ExecutionState(
            checkpoint_id="test_cp",
            agent_memory={"task": "test"},
            api_calls=[
                {"call_id": "1", "has_side_effects": True},
                {"call_id": "2", "has_side_effects": False}
            ],
            resource_consumption={"tokens": 100, "api_calls": 2}
        )

        # Reconcile after rejection
        report = await reconciliation_agent.reconcile_workflow(
            workflow_id="test_wf",
            checkpoint_state=exec_state,
            rejection_reason="Test rejection"
        )

        assert "workflow_id" in report
        assert "partial_completion" in report
        assert "recommended_payment" in report
        assert "rollback_success" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
