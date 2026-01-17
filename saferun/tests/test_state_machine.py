import pytest
from saferun.core.state_machine.models import (
    WorkflowConfig, CheckpointConfig, WorkflowState,
    ExecutionState, ApprovalResponse, ApprovalDecision
)
from saferun.core.state_machine.orchestrator import WorkflowOrchestrator

def test_workflow_initialization():
    """Test that workflows initialize correctly"""
    orchestrator = WorkflowOrchestrator()

    config = WorkflowConfig(
        name="Test Workflow",
        description="Testing state machine",
        checkpoints=[
            CheckpointConfig(
                name="First Checkpoint",
                description="Test checkpoint",
                requires_approval=True
            )
        ],
        escrow_amount=100.0,
        poster_id="poster_123",
        executor_id="executor_456"
    )

    execution = orchestrator.initialize_workflow(config)

    assert execution.current_state == WorkflowState.INITIALIZED
    assert execution.workflow_id == config.workflow_id
    assert len(execution.snapshots) == 0

def test_execution_flow():
    """Test basic execution flow through states"""
    orchestrator = WorkflowOrchestrator()

    config = WorkflowConfig(
        name="Test Workflow",
        description="Testing execution",
        checkpoints=[
            CheckpointConfig(
                name="Checkpoint 1",
                description="First checkpoint"
            )
        ],
        escrow_amount=100.0,
        poster_id="poster_123",
        executor_id="executor_456"
    )

    execution = orchestrator.initialize_workflow(config)
    workflow_id = execution.workflow_id

    # Start execution
    assert orchestrator.start_execution(workflow_id)
    execution = orchestrator.get_workflow(workflow_id)
    assert execution.current_state == WorkflowState.EXECUTING

    # Create checkpoint
    exec_state = ExecutionState(
        checkpoint_id=config.checkpoints[0].checkpoint_id,
        agent_memory={"key": "value"}
    )
    snapshot = orchestrator.create_checkpoint(workflow_id, exec_state)
    assert snapshot is not None

    # Request approval
    request = orchestrator.request_approval(
        workflow_id,
        snapshot.snapshot_id,
        "Please approve this work",
        {"detail": "test"}
    )
    assert request is not None
    execution = orchestrator.get_workflow(workflow_id)
    assert execution.current_state == WorkflowState.AWAITING_APPROVAL

def test_approval_flow():
    """Test approval decision handling"""
    orchestrator = WorkflowOrchestrator()

    config = WorkflowConfig(
        name="Approval Test",
        description="Testing approvals",
        checkpoints=[
            CheckpointConfig(name="CP1", description="First"),
            CheckpointConfig(name="CP2", description="Second")
        ],
        escrow_amount=100.0,
        poster_id="poster_123",
        executor_id="executor_456"
    )

    execution = orchestrator.initialize_workflow(config)
    workflow_id = execution.workflow_id

    orchestrator.start_execution(workflow_id)

    exec_state = ExecutionState(checkpoint_id=config.checkpoints[0].checkpoint_id)
    snapshot = orchestrator.create_checkpoint(workflow_id, exec_state)
    request = orchestrator.request_approval(
        workflow_id, snapshot.snapshot_id, "Test", {}
    )

    # Approve and verify it continues
    response = ApprovalResponse(
        request_id=request.request_id,
        decision=ApprovalDecision.APPROVED,
        rationale="Looks good",
        approved_by="supervisor_789"
    )

    assert orchestrator.submit_approval(workflow_id, response)
    execution = orchestrator.get_workflow(workflow_id)
    assert execution.current_state == WorkflowState.EXECUTING
    assert execution.current_checkpoint_index == 1

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
