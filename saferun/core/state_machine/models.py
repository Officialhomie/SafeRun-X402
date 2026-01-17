from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from uuid import uuid4

class WorkflowState(str, Enum):
    """Possible states a workflow can be in"""
    INITIALIZED = "initialized"
    EXECUTING = "executing"
    AWAITING_APPROVAL = "awaiting_approval"
    ROLLING_BACK = "rolling_back"
    SETTLING = "settling"
    COMPLETED = "completed"
    FAILED = "failed"

class ApprovalDecision(str, Enum):
    """Human approval decisions"""
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"

class CheckpointConfig(BaseModel):
    """Configuration for a single checkpoint"""
    checkpoint_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    requires_approval: bool = True
    timeout_seconds: int = 300
    can_rollback: bool = True

class WorkflowConfig(BaseModel):
    """Configuration for an entire workflow"""
    workflow_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    checkpoints: List[CheckpointConfig]
    escrow_amount: float
    poster_id: str
    executor_id: str
    supervisor_id: Optional[str] = None

class ExecutionState(BaseModel):
    """Captured state at a checkpoint"""
    checkpoint_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    agent_memory: Dict[str, Any] = {}
    api_calls: List[Dict[str, Any]] = []
    intermediate_outputs: Dict[str, Any] = {}
    decision_trace: List[str] = []
    resource_consumption: Dict[str, float] = {}

class CheckpointSnapshot(BaseModel):
    """Complete snapshot at a checkpoint"""
    snapshot_id: str = Field(default_factory=lambda: str(uuid4()))
    workflow_id: str
    checkpoint_id: str
    execution_state: ExecutionState
    approval_required: bool
    created_at: datetime = Field(default_factory=datetime.utcnow)
    artifact_uri: Optional[str] = None  # x402 artifact reference

class ApprovalRequest(BaseModel):
    """Request for human approval"""
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    workflow_id: str
    checkpoint_id: str
    snapshot_id: str
    summary: str  # Human-readable summary of what needs approval
    context: Dict[str, Any]  # Additional context for decision
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

class ApprovalResponse(BaseModel):
    """Human response to approval request"""
    request_id: str
    decision: ApprovalDecision
    rationale: str
    modifications: Optional[Dict[str, Any]] = None
    approved_by: str
    approved_at: datetime = Field(default_factory=datetime.utcnow)

class WorkflowExecution(BaseModel):
    """Complete workflow execution tracking"""
    workflow_id: str
    config: WorkflowConfig
    current_state: WorkflowState
    current_checkpoint_index: int = 0
    snapshots: List[CheckpointSnapshot] = []
    approval_requests: List[ApprovalRequest] = []
    approval_responses: List[ApprovalResponse] = []
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
