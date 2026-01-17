"""
SafeRun X402 API Server

FastAPI application that provides REST API for supervised workflow execution.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from loguru import logger

from saferun.config import settings
from saferun.core.state_machine.orchestrator import WorkflowOrchestrator
from saferun.core.state_machine.models import (
    WorkflowConfig,
    CheckpointConfig,
    ApprovalDecision,
    ApprovalResponse,
    WorkflowState
)
from saferun.core.checkpoints.capture import CheckpointManager
from saferun.agents.executor.agent import ExecutorAgent
from saferun.agents.monitor.agent import MonitorAgent
from saferun.agents.supervisor.agent import SupervisorAgent
from saferun.api.x402.client import X402Integration

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Supervised Agent Execution Protocol for x402",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
orchestrator = WorkflowOrchestrator()
checkpoint_manager = CheckpointManager()
x402 = X402Integration()

# Active agents
active_executors: Dict[str, ExecutorAgent] = {}
active_monitors: Dict[str, MonitorAgent] = {}
active_supervisors: Dict[str, SupervisorAgent] = {}

# ==================== Pydantic Models ====================

class CreateWorkflowRequest(BaseModel):
    name: str
    description: str
    checkpoint_names: List[str]
    escrow_amount: float
    poster_id: str
    executor_id: str
    supervisor_id: Optional[str] = None

class ApprovalDecisionRequest(BaseModel):
    request_id: str
    decision: str  # "APPROVED", "REJECTED", "MODIFIED"
    rationale: str
    approved_by: str
    modifications: Optional[Dict[str, Any]] = None

# ==================== API Endpoints ====================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve main UI"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SafeRun X402 - Supervised Agent Execution</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px;
                border-radius: 10px;
                margin-bottom: 30px;
            }
            .header h1 {
                margin: 0;
                font-size: 36px;
            }
            .header p {
                margin: 10px 0 0 0;
                opacity: 0.9;
            }
            .card {
                background: white;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .card h2 {
                margin-top: 0;
                color: #333;
            }
            .endpoint {
                background: #f8f9fa;
                border-left: 4px solid #667eea;
                padding: 10px 15px;
                margin: 10px 0;
                font-family: monospace;
            }
            .method {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 3px;
                font-weight: bold;
                margin-right: 10px;
            }
            .get { background: #61affe; color: white; }
            .post { background: #49cc90; color: white; }
            .put { background: #fca130; color: white; }
            a {
                color: #667eea;
                text-decoration: none;
            }
            a:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🛡️ SafeRun X402</h1>
            <p>Supervised Agent Execution Protocol - Built for x402 Hackathon</p>
        </div>

        <div class="card">
            <h2>Welcome to SafeRun</h2>
            <p>SafeRun enables agents to work autonomously until they hit critical decision points,
            then pauses for human approval before continuing. This solves the problem of agents
            being either fully autonomous (risky) or requiring constant babysitting.</p>
        </div>

        <div class="card">
            <h2>Key Features</h2>
            <ul>
                <li><strong>Stateful Checkpointing:</strong> Complete state capture at decision points</li>
                <li><strong>Saga Pattern:</strong> Rollback with compensating transactions</li>
                <li><strong>x402 Integration:</strong> Jobs, Escrow, Artifacts, Identity, Marketplace</li>
                <li><strong>Human Oversight:</strong> Clear approval interfaces with context</li>
            </ul>
        </div>

        <div class="card">
            <h2>API Endpoints</h2>

            <div class="endpoint">
                <span class="method post">POST</span>
                <span>/api/workflows</span>
                <p>Create a new supervised workflow</p>
            </div>

            <div class="endpoint">
                <span class="method get">GET</span>
                <span>/api/workflows</span>
                <p>List all workflows</p>
            </div>

            <div class="endpoint">
                <span class="method get">GET</span>
                <span>/api/workflows/{workflow_id}</span>
                <p>Get workflow status</p>
            </div>

            <div class="endpoint">
                <span class="method get">GET</span>
                <span>/api/approvals/pending</span>
                <p>Get pending approval requests</p>
            </div>

            <div class="endpoint">
                <span class="method post">POST</span>
                <span>/api/approvals/submit</span>
                <p>Submit approval decision</p>
            </div>

            <div class="endpoint">
                <span class="method get">GET</span>
                <span>/api/health</span>
                <p>Health check</p>
            </div>
        </div>

        <div class="card">
            <h2>Documentation</h2>
            <p>
                <a href="/docs">📚 Interactive API Documentation (Swagger UI)</a><br>
                <a href="/redoc">📖 ReDoc Documentation</a>
            </p>
        </div>
    </body>
    </html>
    """

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": "1.0.0"
    }

@app.post("/api/workflows")
async def create_workflow(request: CreateWorkflowRequest):
    """Create a new supervised workflow"""
    logger.info(f"Creating workflow: {request.name}")

    try:
        # Create checkpoint configs
        checkpoints = [
            CheckpointConfig(
                name=name,
                description=f"Checkpoint: {name}",
                requires_approval=True
            )
            for name in request.checkpoint_names
        ]

        # Create workflow config
        config = WorkflowConfig(
            name=request.name,
            description=request.description,
            checkpoints=checkpoints,
            escrow_amount=request.escrow_amount,
            poster_id=request.poster_id,
            executor_id=request.executor_id,
            supervisor_id=request.supervisor_id
        )

        # Initialize workflow in orchestrator
        execution = orchestrator.initialize_workflow(config)

        # Set up x402 integration
        x402_setup = await x402.setup_supervised_workflow(
            workflow_id=config.workflow_id,
            workflow_config={"name": request.name, "type": "supervised"},
            escrow_amount=request.escrow_amount,
            poster_id=request.poster_id,
            executor_id=request.executor_id,
            supervisor_id=request.supervisor_id
        )

        # Create agents
        executor = ExecutorAgent(agent_id=request.executor_id)
        monitor = MonitorAgent(monitor_id=f"monitor_{config.workflow_id}")
        supervisor = SupervisorAgent(supervisor_id=request.supervisor_id or "default_supervisor")

        active_executors[config.workflow_id] = executor
        active_monitors[config.workflow_id] = monitor
        active_supervisors[config.workflow_id] = supervisor

        # Start execution
        orchestrator.start_execution(config.workflow_id)

        return {
            "workflow_id": config.workflow_id,
            "status": execution.current_state,
            "x402_setup": x402_setup,
            "checkpoints": len(checkpoints),
            "message": "Workflow created and ready to execute"
        }

    except Exception as e:
        logger.error(f"Failed to create workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workflows")
async def list_workflows():
    """List all workflows"""
    workflows = []
    for workflow_id, execution in orchestrator.active_workflows.items():
        workflows.append({
            "workflow_id": workflow_id,
            "name": execution.config.name,
            "status": execution.current_state,
            "current_checkpoint": execution.current_checkpoint_index,
            "total_checkpoints": len(execution.config.checkpoints),
            "started_at": execution.started_at.isoformat()
        })

    return {"workflows": workflows, "total": len(workflows)}

@app.get("/api/workflows/{workflow_id}")
async def get_workflow_status(workflow_id: str):
    """Get detailed workflow status"""
    workflow = orchestrator.get_workflow(workflow_id)

    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return {
        "workflow_id": workflow_id,
        "name": workflow.config.name,
        "description": workflow.config.description,
        "status": workflow.current_state,
        "current_checkpoint": workflow.current_checkpoint_index,
        "total_checkpoints": len(workflow.config.checkpoints),
        "snapshots": len(workflow.snapshots),
        "approval_requests": len(workflow.approval_requests),
        "approval_responses": len(workflow.approval_responses),
        "started_at": workflow.started_at.isoformat(),
        "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
        "error_message": workflow.error_message
    }

@app.get("/api/approvals/pending")
async def get_pending_approvals():
    """Get all pending approval requests"""
    pending = []

    for workflow_id, supervisor in active_supervisors.items():
        for request in supervisor.get_pending_approvals():
            display = supervisor.format_for_display(request)
            pending.append(display)

    return {
        "pending_approvals": pending,
        "total": len(pending)
    }

@app.post("/api/approvals/submit")
async def submit_approval(request: ApprovalDecisionRequest):
    """Submit an approval decision"""
    logger.info(f"Submitting approval decision for request {request.request_id}")

    # Find which supervisor has this request
    supervisor = None
    workflow_id = None

    for wf_id, sup in active_supervisors.items():
        if request.request_id in sup.pending_approvals:
            supervisor = sup
            workflow_id = wf_id
            break

    if not supervisor:
        raise HTTPException(status_code=404, detail="Approval request not found")

    try:
        # Convert string decision to enum
        decision_enum = ApprovalDecision(request.decision.lower())

        # Submit decision to supervisor
        response = supervisor.submit_decision(
            request_id=request.request_id,
            decision=decision_enum,
            rationale=request.rationale,
            approved_by=request.approved_by,
            modifications=request.modifications
        )

        # Route to orchestrator
        orchestrator.submit_approval(workflow_id, response)

        # Get updated workflow status
        workflow = orchestrator.get_workflow(workflow_id)

        return {
            "success": True,
            "decision": request.decision,
            "workflow_status": workflow.current_state,
            "message": f"Approval {request.decision} - workflow now {workflow.current_state}"
        }

    except Exception as e:
        logger.error(f"Failed to submit approval: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_stats():
    """Get overall system statistics"""
    total_workflows = len(orchestrator.active_workflows)

    states = {}
    for execution in orchestrator.active_workflows.values():
        state = execution.current_state
        states[state] = states.get(state, 0) + 1

    total_approvals = sum(
        len(sup.approval_history)
        for sup in active_supervisors.values()
    )

    total_pending = sum(
        len(sup.pending_approvals)
        for sup in active_supervisors.values()
    )

    return {
        "total_workflows": total_workflows,
        "workflow_states": states,
        "total_approvals_processed": total_approvals,
        "pending_approvals": total_pending,
        "active_executors": len(active_executors),
        "active_supervisors": len(active_supervisors)
    }

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    await x402.close()
    logger.info("SafeRun API server shutting down")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
