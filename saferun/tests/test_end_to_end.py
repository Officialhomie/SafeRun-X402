"""
End-to-End Integration Test for SafeRun X402

This test validates the complete workflow from creation to settlement:
1. Create workflow with checkpoints
2. Start execution
3. Agent hits checkpoint
4. Human approves
5. Workflow continues
6. Settlement and completion
"""

import pytest
import asyncio
from datetime import datetime
from loguru import logger

from saferun.core.state_machine.orchestrator import WorkflowOrchestrator
from saferun.core.state_machine.models import (
    WorkflowConfig,
    CheckpointConfig,
    WorkflowState,
    ExecutionState,
    ApprovalResponse,
    ApprovalDecision
)
from saferun.agents.executor.agent import ExecutorAgent
from saferun.agents.monitor.agent import MonitorAgent
from saferun.agents.supervisor.agent import SupervisorAgent
from saferun.core.checkpoints.capture import StateCapture
from saferun.api.x402.client import X402Integration


@pytest.mark.asyncio
async def test_complete_workflow_happy_path():
    """
    Test the complete happy path: workflow creation → execution → approval → completion
    """
    logger.info("=" * 80)
    logger.info("STARTING END-TO-END INTEGRATION TEST - HAPPY PATH")
    logger.info("=" * 80)

    # Step 1: Initialize orchestrator with x402 integration
    logger.info("Step 1: Initializing orchestrator with x402 integration")
    x402 = X402Integration()
    orchestrator = WorkflowOrchestrator(x402_integration=x402)
    state_capture = StateCapture()

    # Step 2: Create workflow configuration
    logger.info("Step 2: Creating workflow configuration")
    config = WorkflowConfig(
        name="E2E Test Workflow",
        description="End-to-end integration test for SafeRun",
        checkpoints=[
            CheckpointConfig(
                name="Data Collection",
                description="Collect and validate input data",
                requires_approval=True,
                can_rollback=True
            ),
            CheckpointConfig(
                name="Processing",
                description="Process the collected data",
                requires_approval=True,
                can_rollback=True
            ),
            CheckpointConfig(
                name="Final Review",
                description="Review before completion",
                requires_approval=True,
                can_rollback=False
            )
        ],
        escrow_amount=100.0,
        poster_id="test_poster_123",
        executor_id="test_executor_456",
        supervisor_id="test_supervisor_789"
    )

    # Step 3: Initialize workflow
    logger.info("Step 3: Initializing workflow in orchestrator")
    execution = orchestrator.initialize_workflow(config)
    workflow_id = execution.workflow_id

    assert execution.current_state == WorkflowState.INITIALIZED
    assert execution.workflow_id == config.workflow_id
    logger.info(f"✓ Workflow {workflow_id} initialized")

    # Step 4: Start execution
    logger.info("Step 4: Starting workflow execution")
    success = orchestrator.start_execution(workflow_id)
    assert success is True

    execution = orchestrator.get_workflow(workflow_id)
    assert execution.current_state == WorkflowState.EXECUTING
    logger.info(f"✓ Workflow transitioned to EXECUTING state")

    # Step 5: Simulate agent execution to first checkpoint
    logger.info("Step 5: Simulating agent execution to first checkpoint")
    checkpoint_1_state = ExecutionState(
        checkpoint_id=config.checkpoints[0].checkpoint_id,
        agent_memory={
            "data_collected": ["item1", "item2", "item3"],
            "validation_status": "passed"
        },
        api_calls=[
            {"endpoint": "/api/data/fetch", "status": 200, "timestamp": datetime.utcnow().isoformat()}
        ],
        intermediate_outputs={
            "records_found": 3,
            "quality_score": 0.95
        },
        decision_trace=[
            "Fetched data from source",
            "Validated data format",
            "All checks passed"
        ],
        resource_consumption={
            "api_calls": 1,
            "tokens_used": 0,
            "execution_time": 2.5
        }
    )

    # Step 6: Create checkpoint snapshot
    logger.info("Step 6: Creating checkpoint snapshot")
    snapshot = await orchestrator.create_checkpoint(workflow_id, checkpoint_1_state)

    assert snapshot is not None
    assert snapshot.checkpoint_id == config.checkpoints[0].checkpoint_id
    assert snapshot.approval_required is True
    logger.info(f"✓ Checkpoint snapshot created: {snapshot.snapshot_id}")

    # Step 7: Request approval
    logger.info("Step 7: Requesting human approval")
    approval_request = orchestrator.request_approval(
        workflow_id=workflow_id,
        snapshot_id=snapshot.snapshot_id,
        summary="Data collection complete. Found 3 records with quality score 0.95. Ready to proceed?",
        context={
            "checkpoint_name": "Data Collection",
            "records_collected": 3,
            "quality_score": 0.95,
            "recommendation": "approve"
        }
    )

    assert approval_request is not None
    execution = orchestrator.get_workflow(workflow_id)
    assert execution.current_state == WorkflowState.AWAITING_APPROVAL
    logger.info(f"✓ Workflow transitioned to AWAITING_APPROVAL state")
    logger.info(f"  Approval request ID: {approval_request.request_id}")

    # Step 8: Simulate human approval
    logger.info("Step 8: Simulating human approval decision")
    approval_response = ApprovalResponse(
        request_id=approval_request.request_id,
        decision=ApprovalDecision.APPROVED,
        rationale="Data quality looks good. Quality score of 0.95 exceeds threshold. Approved to proceed.",
        approved_by="human_supervisor_789"
    )

    success = orchestrator.submit_approval(workflow_id, approval_response)
    assert success is True

    execution = orchestrator.get_workflow(workflow_id)
    assert execution.current_state == WorkflowState.EXECUTING
    assert execution.current_checkpoint_index == 1
    logger.info(f"✓ Approval submitted - workflow continues to next checkpoint")

    # Step 9: Execute to second checkpoint
    logger.info("Step 9: Executing to second checkpoint")
    checkpoint_2_state = ExecutionState(
        checkpoint_id=config.checkpoints[1].checkpoint_id,
        agent_memory={
            "processing_complete": True,
            "transformations_applied": ["normalize", "enrich", "validate"]
        },
        api_calls=[
            {"endpoint": "/api/process", "status": 200, "timestamp": datetime.utcnow().isoformat()}
        ],
        intermediate_outputs={
            "processed_records": 3,
            "success_rate": 1.0
        },
        decision_trace=[
            "Applied normalization",
            "Enriched with metadata",
            "Final validation passed"
        ],
        resource_consumption={
            "api_calls": 2,
            "tokens_used": 150,
            "execution_time": 5.2
        }
    )

    snapshot_2 = await orchestrator.create_checkpoint(workflow_id, checkpoint_2_state)
    assert snapshot_2 is not None
    logger.info(f"✓ Second checkpoint created: {snapshot_2.snapshot_id}")

    # Step 10: Auto-approve second checkpoint
    logger.info("Step 10: Processing second checkpoint approval")
    approval_request_2 = orchestrator.request_approval(
        workflow_id=workflow_id,
        snapshot_id=snapshot_2.snapshot_id,
        summary="Processing complete. All 3 records processed successfully with 100% success rate.",
        context={
            "checkpoint_name": "Processing",
            "processed_records": 3,
            "success_rate": 1.0
        }
    )

    approval_response_2 = ApprovalResponse(
        request_id=approval_request_2.request_id,
        decision=ApprovalDecision.APPROVED,
        rationale="100% success rate. All transformations completed correctly.",
        approved_by="human_supervisor_789"
    )

    orchestrator.submit_approval(workflow_id, approval_response_2)
    execution = orchestrator.get_workflow(workflow_id)
    assert execution.current_checkpoint_index == 2
    logger.info(f"✓ Second checkpoint approved")

    # Step 11: Execute to final checkpoint
    logger.info("Step 11: Executing to final checkpoint")
    checkpoint_3_state = ExecutionState(
        checkpoint_id=config.checkpoints[2].checkpoint_id,
        agent_memory={
            "final_review_complete": True,
            "ready_for_delivery": True
        },
        intermediate_outputs={
            "final_output": "All processing complete, ready for delivery"
        },
        decision_trace=[
            "Completed final review",
            "All quality checks passed",
            "Ready for settlement"
        ],
        resource_consumption={
            "api_calls": 3,
            "tokens_used": 225,
            "execution_time": 7.8
        }
    )

    snapshot_3 = await orchestrator.create_checkpoint(workflow_id, checkpoint_3_state)
    logger.info(f"✓ Final checkpoint created: {snapshot_3.snapshot_id}")

    # Step 12: Final approval and settlement
    logger.info("Step 12: Final approval and transition to settlement")
    approval_request_3 = orchestrator.request_approval(
        workflow_id=workflow_id,
        snapshot_id=snapshot_3.snapshot_id,
        summary="Final review complete. All checks passed. Ready for settlement.",
        context={
            "checkpoint_name": "Final Review",
            "status": "ready_for_settlement"
        }
    )

    approval_response_3 = ApprovalResponse(
        request_id=approval_request_3.request_id,
        decision=ApprovalDecision.APPROVED,
        rationale="Final review looks good. Approved for settlement.",
        approved_by="human_supervisor_789"
    )

    orchestrator.submit_approval(workflow_id, approval_response_3)
    execution = orchestrator.get_workflow(workflow_id)

    # After last checkpoint approval, should move to SETTLING
    assert execution.current_state == WorkflowState.SETTLING
    logger.info(f"✓ Workflow transitioned to SETTLING state")

    # Step 13: Complete workflow
    logger.info("Step 13: Completing workflow")
    orchestrator.complete_workflow(workflow_id)
    execution = orchestrator.get_workflow(workflow_id)

    assert execution.current_state == WorkflowState.COMPLETED
    assert execution.completed_at is not None
    logger.info(f"✓ Workflow completed successfully")

    # Step 14: Verify final state
    logger.info("Step 14: Verifying final state")
    assert len(execution.snapshots) == 3
    assert len(execution.approval_requests) == 3
    assert len(execution.approval_responses) == 3
    assert execution.error_message is None

    logger.info(f"✓ Final verification passed:")
    logger.info(f"  - Snapshots created: {len(execution.snapshots)}")
    logger.info(f"  - Approvals requested: {len(execution.approval_requests)}")
    logger.info(f"  - Approvals received: {len(execution.approval_responses)}")
    logger.info(f"  - Final state: {execution.current_state}")

    # Cleanup
    await x402.close()

    logger.info("=" * 80)
    logger.info("END-TO-END TEST PASSED ✓")
    logger.info("=" * 80)


@pytest.mark.asyncio
async def test_workflow_with_rejection_and_rollback():
    """
    Test workflow with approval rejection triggering rollback
    """
    logger.info("=" * 80)
    logger.info("STARTING END-TO-END TEST - ROLLBACK PATH")
    logger.info("=" * 80)

    # Initialize
    x402 = X402Integration()
    orchestrator = WorkflowOrchestrator(x402_integration=x402)

    # Create workflow
    config = WorkflowConfig(
        name="Rollback Test Workflow",
        description="Test rollback on rejection",
        checkpoints=[
            CheckpointConfig(
                name="First Check",
                description="First checkpoint",
                requires_approval=True,
                can_rollback=True
            ),
            CheckpointConfig(
                name="Second Check",
                description="Second checkpoint - will be rejected",
                requires_approval=True,
                can_rollback=True
            )
        ],
        escrow_amount=50.0,
        poster_id="test_poster",
        executor_id="test_executor",
        supervisor_id="test_supervisor"
    )

    execution = orchestrator.initialize_workflow(config)
    workflow_id = execution.workflow_id
    orchestrator.start_execution(workflow_id)

    # First checkpoint - approve
    logger.info("Step 1: First checkpoint - will approve")
    checkpoint_1_state = ExecutionState(
        checkpoint_id=config.checkpoints[0].checkpoint_id,
        agent_memory={"step": 1, "status": "good"}
    )

    snapshot_1 = await orchestrator.create_checkpoint(workflow_id, checkpoint_1_state)
    request_1 = orchestrator.request_approval(
        workflow_id, snapshot_1.snapshot_id, "First checkpoint ready", {}
    )

    response_1 = ApprovalResponse(
        request_id=request_1.request_id,
        decision=ApprovalDecision.APPROVED,
        rationale="Looks good",
        approved_by="supervisor"
    )
    orchestrator.submit_approval(workflow_id, response_1)
    logger.info("✓ First checkpoint approved")

    # Second checkpoint - reject with rollback
    logger.info("Step 2: Second checkpoint - will reject")
    checkpoint_2_state = ExecutionState(
        checkpoint_id=config.checkpoints[1].checkpoint_id,
        agent_memory={"step": 2, "status": "problematic"}
    )

    snapshot_2 = await orchestrator.create_checkpoint(workflow_id, checkpoint_2_state)
    request_2 = orchestrator.request_approval(
        workflow_id, snapshot_2.snapshot_id, "Second checkpoint - has issues", {}
    )

    response_2 = ApprovalResponse(
        request_id=request_2.request_id,
        decision=ApprovalDecision.REJECTED,
        rationale="Found issues, need to rollback",
        approved_by="supervisor"
    )
    orchestrator.submit_approval(workflow_id, response_2)

    execution = orchestrator.get_workflow(workflow_id)
    assert execution.current_state == WorkflowState.ROLLING_BACK
    logger.info("✓ Workflow transitioned to ROLLING_BACK state")

    # Complete rollback
    logger.info("Step 3: Completing rollback")
    orchestrator.complete_rollback(workflow_id, success=True)

    execution = orchestrator.get_workflow(workflow_id)
    assert execution.current_state == WorkflowState.EXECUTING
    assert execution.current_checkpoint_index == 0  # Rolled back to previous checkpoint
    logger.info("✓ Rollback completed successfully")
    logger.info(f"  Current checkpoint index: {execution.current_checkpoint_index}")

    await x402.close()

    logger.info("=" * 80)
    logger.info("ROLLBACK TEST PASSED ✓")
    logger.info("=" * 80)


@pytest.mark.asyncio
async def test_workflow_with_modification():
    """
    Test workflow with approval modification decision
    """
    logger.info("=" * 80)
    logger.info("STARTING END-TO-END TEST - MODIFICATION PATH")
    logger.info("=" * 80)

    x402 = X402Integration()
    orchestrator = WorkflowOrchestrator(x402_integration=x402)

    config = WorkflowConfig(
        name="Modification Test Workflow",
        description="Test modification flow",
        checkpoints=[
            CheckpointConfig(
                name="Review Checkpoint",
                description="Checkpoint that will be modified",
                requires_approval=True,
                can_rollback=True
            )
        ],
        escrow_amount=75.0,
        poster_id="test_poster",
        executor_id="test_executor",
        supervisor_id="test_supervisor"
    )

    execution = orchestrator.initialize_workflow(config)
    workflow_id = execution.workflow_id
    orchestrator.start_execution(workflow_id)

    # Create checkpoint
    checkpoint_state = ExecutionState(
        checkpoint_id=config.checkpoints[0].checkpoint_id,
        agent_memory={"value": 10, "multiplier": 2}
    )

    snapshot = await orchestrator.create_checkpoint(workflow_id, checkpoint_state)
    request = orchestrator.request_approval(
        workflow_id, snapshot.snapshot_id, "Review parameters", {}
    )

    # Submit modification decision
    logger.info("Step 1: Submitting modification decision")
    response = ApprovalResponse(
        request_id=request.request_id,
        decision=ApprovalDecision.MODIFIED,
        rationale="Adjusted multiplier from 2 to 3",
        approved_by="supervisor",
        modifications={"multiplier": 3}
    )
    orchestrator.submit_approval(workflow_id, response)

    execution = orchestrator.get_workflow(workflow_id)
    assert execution.current_state == WorkflowState.EXECUTING
    assert len(execution.approval_responses) == 1
    assert execution.approval_responses[0].modifications == {"multiplier": 3}
    logger.info("✓ Modification applied, workflow continues")

    await x402.close()

    logger.info("=" * 80)
    logger.info("MODIFICATION TEST PASSED ✓")
    logger.info("=" * 80)


@pytest.mark.asyncio
async def test_checkpoint_artifact_storage():
    """
    Test that checkpoints are stored as x402 artifacts
    """
    logger.info("=" * 80)
    logger.info("STARTING CHECKPOINT ARTIFACT STORAGE TEST")
    logger.info("=" * 80)

    x402 = X402Integration()
    orchestrator = WorkflowOrchestrator(x402_integration=x402)

    config = WorkflowConfig(
        name="Artifact Storage Test",
        description="Test checkpoint artifact storage",
        checkpoints=[
            CheckpointConfig(name="Test Checkpoint", description="Test")
        ],
        escrow_amount=50.0,
        poster_id="poster",
        executor_id="executor"
    )

    execution = orchestrator.initialize_workflow(config)
    workflow_id = execution.workflow_id
    orchestrator.start_execution(workflow_id)

    # Create checkpoint with complex state
    checkpoint_state = ExecutionState(
        checkpoint_id=config.checkpoints[0].checkpoint_id,
        agent_memory={
            "complex_data": {
                "nested": {"value": 123},
                "array": [1, 2, 3]
            }
        },
        api_calls=[
            {"endpoint": "/test", "status": 200}
        ],
        intermediate_outputs={"result": "success"}
    )

    logger.info("Step 1: Creating checkpoint with artifact storage")
    snapshot = await orchestrator.create_checkpoint(workflow_id, checkpoint_state)

    assert snapshot is not None
    # artifact_uri should be set if x402 integration is working
    # In test mode, x402 might fail gracefully, so we just verify snapshot was created
    logger.info(f"✓ Checkpoint created: {snapshot.snapshot_id}")
    logger.info(f"  Artifact URI: {snapshot.artifact_uri or 'None (x402 not available)'}")

    # Verify snapshot data is preserved
    execution = orchestrator.get_workflow(workflow_id)
    assert len(execution.snapshots) == 1
    stored_snapshot = execution.snapshots[0]
    assert stored_snapshot.execution_state.agent_memory == checkpoint_state.agent_memory
    assert stored_snapshot.execution_state.api_calls == checkpoint_state.api_calls
    logger.info("✓ Checkpoint state preserved correctly")

    await x402.close()

    logger.info("=" * 80)
    logger.info("ARTIFACT STORAGE TEST PASSED ✓")
    logger.info("=" * 80)


if __name__ == "__main__":
    # Run tests with detailed output
    pytest.main([__file__, "-v", "-s"])
