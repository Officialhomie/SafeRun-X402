# 🛡️ SafeRun X402

**Supervised Agent Execution Protocol for x402**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

SafeRun enables AI agents to work autonomously until they hit critical decision points, then pauses for human approval before continuing. This solves the fundamental problem of agent deployment: agents are either fully autonomous (risky) or require constant babysitting (defeating the purpose of automation).

Built for the [x402 Hackathon](https://x402.io).

---

## 📋 Table of Contents

- [The Problem](#-the-problem)
- [The Solution](#-the-solution)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Usage Examples](#-usage-examples)
- [API Reference](#-api-reference)
- [Project Structure](#-project-structure)
- [x402 Integration](#-x402-integration)
- [Testing](#-testing)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 The Problem

Every company deploying AI agents hits the same wall:

- **Full Autonomy = Disasters**: Agents make expensive mistakes (ordering 100 pizzas instead of 10, sending wrong data to customers, making bad financial decisions)
- **Constant Supervision = No Value**: Babysitting agents defeats the purpose of automation
- **No Middle Ground**: Current tools don't support "supervised autonomy" - agents that work independently until they need human judgment

---

## 💡 The Solution

SafeRun provides **supervised autonomy** through:

1. **Stateful Checkpoints**: Capture complete agent state at decision points
2. **Human-in-the-Loop**: Pause for approval at critical moments with full context
3. **Saga Pattern Rollback**: Undo actions if approval is rejected
4. **x402 Integration**: Compose Jobs, Escrow, Artifacts, Identity, and Marketplace primitives
5. **Payment Intelligence**: Pro-rated payments based on work completed

---

## ✨ Key Features

### 1. Complete State Capture
At every checkpoint, SafeRun captures:
- Agent memory and context
- API calls made
- Intermediate outputs
- Decision reasoning trace
- Resource consumption

This enables true rollback, not just cancellation.

### 2. Intelligent Monitoring
The Monitor Agent detects:
- Anomalies in execution (high API usage, errors)
- Progress vs. expected timeline
- Resource consumption thresholds
- Custom checkpoint conditions

### 3. Human-Friendly Approval UI
The Supervisor Agent presents:
- Clear summary of what happened
- Recent actions and decisions
- Outputs generated
- Alerts and recommendations
- Three decision options: Approve, Modify, Reject

### 4. Saga Pattern Rollback
When approval is rejected:
- Execute compensating transactions (undo API calls)
- Restore state from checkpoint
- Calculate partial payment
- Clean up resources

### 5. x402 Integration
Compose all five primitives:
- **Jobs**: Main workflow + approval sub-jobs
- **Escrow**: Funds locked at start, released at milestones
- **Artifacts**: Checkpoint state stored immutably
- **Identity**: Role-based access (poster/executor/supervisor)
- **Marketplace**: Find and rate supervisors

---

## 🏗️ Architecture

### State Machine

Workflows transition through these states:

```
INITIALIZED → EXECUTING → AWAITING_APPROVAL → EXECUTING → SETTLING → COMPLETED
                             ↓
                      ROLLING_BACK → EXECUTING
```

### Four Agent Types

1. **Executor Agent**: Performs actual work, emits checkpoint signals
2. **Monitor Agent**: Watches for anomalies and checkpoint conditions
3. **Supervisor Agent**: Presents checkpoints to humans for approval
4. **Reconciliation Agent**: Handles rollback and cleanup

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                    SafeRun X402                         │
│            Supervised Execution Platform                │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
   ┌─────────┐      ┌─────────┐      ┌─────────┐
   │   API   │      │  Core   │      │ Agents  │
   │  Layer  │      │ Engine  │      │ System  │
   └─────────┘      └─────────┘      └─────────┘
        │                 │                 │
        ▼                 ▼                 ▼
   ┌─────────┐      ┌─────────┐      ┌─────────┐
   │FastAPI  │      │  State  │      │Executor │
   │Server   │◄────►│ Machine │◄────►│ Agent   │
   │         │      │         │      │         │
   │REST API │      │Workflow │      │Monitor  │
   │         │      │Orchestr-│      │ Agent   │
   │WebUI    │      │ator     │      │         │
   └─────────┘      └─────────┘      │Supervis-│
        │                 │           │or Agent │
        │                 │           │         │
        │                 │           │Reconcil-│
        │                 │           │ation    │
        │                 │           └─────────┘
        │                 │
        ▼                 ▼
   ┌─────────────────────────────────┐
   │         x402 Platform          │
   ├─────────────────────────────────┤
   │ • Jobs (workflow execution)     │
   │ • Escrow (payment management)   │
   │ • Artifacts (state storage)     │
   │ • Identity (role management)    │
   │ • Marketplace (supervisor pool) │
   └─────────────────────────────────┘
```

---

## 📦 Installation

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Git

### Step 1: Clone the Repository

```bash
git clone https://github.com/Officialhomie/SafeRun-X402.git
cd SafeRun-X402
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your API keys (optional for demo)
# X402_API_KEY=your_x402_key_here
# ANTHROPIC_API_KEY=your_anthropic_key_here
# OPENAI_API_KEY=your_openai_key_here
```

**Note**: The demo works without API keys! Real x402 integration is mocked for development.

### Step 5: Run Setup Script (Optional)

```bash
chmod +x setup.sh
./setup.sh
```

---

## 🚀 Quick Start

### Run the Demo

The fastest way to see SafeRun in action:

```bash
# Using the run script
./run_demo.sh

# Or manually
source venv/bin/activate
python demo_scenario.py
```

This runs three scenarios:
1. **Disaster Scenario**: What happens without SafeRun (100 pizzas ordered!)
2. **Success Scenario**: SafeRun catches the error, human approves with correction
3. **Rollback Scenario**: Rejection triggers compensating transactions

### Run the API Server

Start the FastAPI server:

```bash
# Using the run script
./run_server.sh

# Or manually
source venv/bin/activate
python -m saferun.api.server

# Or with uvicorn directly
uvicorn saferun.api.server:app --reload
```

Then visit:
- **Main UI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (Interactive Swagger UI)
- **ReDoc**: http://localhost:8000/redoc

---

## 📚 Usage Examples

### Creating a Supervised Workflow

```python
from saferun.core.state_machine.orchestrator import WorkflowOrchestrator
from saferun.core.state_machine.models import WorkflowConfig, CheckpointConfig

orchestrator = WorkflowOrchestrator()

# Define workflow with checkpoints
config = WorkflowConfig(
    name="Data Processing Pipeline",
    description="Process customer data with approval gates",
    checkpoints=[
        CheckpointConfig(
            name="Review Data Selection",
            description="Ensure correct data is selected",
            requires_approval=True
        ),
        CheckpointConfig(
            name="Review Transformations",
            description="Validate data transformations",
            requires_approval=True
        )
    ],
    escrow_amount=100.0,
    poster_id="user_123",
    executor_id="agent_456"
)

# Initialize and start
execution = orchestrator.initialize_workflow(config)
orchestrator.start_execution(config.workflow_id)
```

### Creating Checkpoints

```python
from saferun.agents.executor.agent import ExecutorAgent

executor = ExecutorAgent(agent_id="agent_456")

# Agent executes work
result = await executor.execute_task(
    task_description="Process customer data",
    task_parameters={"dataset": "customers_2024"}
)

# Capture state at checkpoint
execution_state = executor.capture_current_state("review_data")
snapshot = orchestrator.create_checkpoint(workflow_id, execution_state)
```

### Requesting Approval

```python
from saferun.agents.supervisor.agent import SupervisorAgent

supervisor = SupervisorAgent(supervisor_id="supervisor_789")

# Create approval request
approval_request = supervisor.create_approval_request(
    workflow_id=workflow_id,
    checkpoint_id=checkpoint_id,
    snapshot_id=snapshot.snapshot_id,
    execution_state=execution_state
)

# Format for human review
display = supervisor.format_for_display(approval_request)
# Present display to human...
```

### Submitting Approval

```python
from saferun.core.state_machine.models import ApprovalDecision

# Human makes decision
response = supervisor.submit_decision(
    request_id=approval_request.request_id,
    decision=ApprovalDecision.APPROVED,
    rationale="Data selection looks correct",
    approved_by="user_123"
)

# Route to orchestrator
orchestrator.submit_approval(workflow_id, response)
```

---

## 🔌 API Reference

### Create Workflow

```bash
POST /api/workflows
Content-Type: application/json

{
  "name": "My Workflow",
  "description": "Description here",
  "checkpoint_names": ["Review Step 1", "Review Step 2"],
  "escrow_amount": 100.0,
  "poster_id": "user_123",
  "executor_id": "agent_456"
}
```

**Response:**
```json
{
  "workflow_id": "wf_abc123",
  "status": "initialized",
  "message": "Workflow created successfully"
}
```

### Get Workflow Status

```bash
GET /api/workflows/{workflow_id}
```

**Response:**
```json
{
  "workflow_id": "wf_abc123",
  "name": "My Workflow",
  "current_state": "executing",
  "current_checkpoint_index": 1,
  "started_at": "2024-01-17T10:00:00Z"
}
```

### Get Pending Approvals

```bash
GET /api/approvals/pending
```

**Response:**
```json
{
  "pending_approvals": [
    {
      "request_id": "req_123",
      "workflow_id": "wf_abc123",
      "summary": "Review data selection",
      "created_at": "2024-01-17T10:05:00Z"
    }
  ]
}
```

### Submit Approval

```bash
POST /api/approvals/submit
Content-Type: application/json

{
  "request_id": "req_123",
  "decision": "APPROVED",
  "rationale": "Looks good",
  "approved_by": "user_123",
  "modifications": null
}
```

### Get System Statistics

```bash
GET /api/stats
```

**Response:**
```json
{
  "total_workflows": 42,
  "active_workflows": 5,
  "pending_approvals": 2,
  "completed_workflows": 35
}
```

### Health Check

```bash
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

## 📁 Project Structure

```
SafeRun-X402/
├── saferun/                    # Main package
│   ├── __init__.py
│   ├── config.py               # Configuration management
│   ├── core/                   # Core infrastructure
│   │   ├── __init__.py
│   │   ├── state_machine/      # Workflow orchestration
│   │   │   ├── __init__.py
│   │   │   ├── models.py       # Pydantic models
│   │   │   └── orchestrator.py # State machine
│   │   ├── checkpoints/        # Checkpoint capture
│   │   │   ├── __init__.py
│   │   │   └── capture.py      # State serialization
│   │   └── rollback/           # Rollback mechanism
│   │       ├── __init__.py
│   │       └── reconciliation.py # Compensating transactions
│   ├── agents/                 # Four agent types
│   │   ├── __init__.py
│   │   ├── executor/           # Executor agent
│   │   │   ├── __init__.py
│   │   │   └── agent.py
│   │   ├── monitor/            # Monitor agent
│   │   │   ├── __init__.py
│   │   │   └── agent.py
│   │   └── supervisor/         # Supervisor agent
│   │       ├── __init__.py
│   │       └── agent.py
│   ├── api/                    # API layer
│   │   ├── __init__.py
│   │   ├── x402/               # x402 integration
│   │   │   ├── __init__.py
│   │   │   └── client.py       # x402 API client
│   │   └── server.py           # FastAPI application
│   ├── ui/                     # Frontend assets
│   │   └── __init__.py
│   └── tests/                  # Test suite
│       ├── __init__.py
│       └── test_state_machine.py
├── demo_scenario.py            # Demo scenarios
├── requirements.txt             # Python dependencies
├── .env.example                # Environment template
├── .gitignore                  # Git exclusions
├── setup.sh                    # Setup script
├── run_demo.sh                 # Demo runner
├── run_server.sh               # Server runner
└── README.md                   # This file
```

---

## 🔗 x402 Integration

SafeRun composes all five x402 primitives:

### Jobs
- Main workflow job created at initialization
- Approval sub-jobs created dynamically at checkpoints
- Settlement job handles final payment distribution

### Escrow
- Funds locked at workflow start
- Milestone-based releases tied to approvals
- Pro-rated partial payments on rejection
- Split payments between executor and supervisor

### Artifacts
- Checkpoint state stored as immutable artifacts
- Content-addressed storage (SHA-256)
- Full audit trail of all decisions
- Approval decisions stored with rationale

### Identity
- Three primary roles: Poster, Executor, Supervisor
- Role verification at each step
- Reputation tracking for supervisors
- Optional verifier role for disputes

### Marketplace
- Supervisor discovery by workflow type
- Filtering by reputation and availability
- Rating and review system
- Pricing models (per-approval, subscription)

---

## 🧪 Testing

### Run Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
pytest saferun/tests/ -v

# Run specific test file
pytest saferun/tests/test_state_machine.py -v

# Run with coverage
pytest --cov=saferun saferun/tests/
```

### Test Coverage

Current test coverage includes:
- ✅ Workflow initialization
- ✅ State transitions
- ✅ Checkpoint creation
- ✅ Approval flow
- ✅ Rollback logic

---

## 🎯 Use Cases

1. **Financial Workflows**: Approve transactions before execution
2. **Data Processing**: Review data selection and transformations
3. **Customer Communication**: Review messages before sending
4. **Infrastructure Changes**: Approve deployments and config changes
5. **Research Pipelines**: Verify intermediate results
6. **Multi-Agent Coordination**: Handoff approval between agent stages

---

## 🛠️ Development

### Adding a New Agent Type

1. Create directory in `saferun/agents/`
2. Implement agent class with required methods
3. Register in orchestrator
4. Add to API endpoints

### Adding a New Checkpoint Type

1. Define condition function
2. Register with MonitorAgent
3. Add UI rendering in SupervisorAgent
4. Update API models

### Extending x402 Integration

1. Add new primitive methods in `x402/client.py`
2. Update integration layer in `X402Integration`
3. Wire into orchestrator lifecycle

---

## 📊 Demo Scenarios

### Scenario 1: Meeting Room Booking (The Classic)

**Without SafeRun:**
- Agent orders 100 pizzas instead of 10
- $1,200 wasted
- 90 pizzas to dispose of

**With SafeRun:**
- Human reviews order at checkpoint
- Catches error, approves with modification
- Correct order placed
- $1,080 saved!

### Scenario 2: Financial Transaction

**Without SafeRun:**
- Agent sends $10,000 to suspicious account
- Money lost
- No recourse

**With SafeRun:**
- Human reviews transaction
- Rejects due to suspicious account
- Rollback executes
- Transaction reversed
- Disaster averted!

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Add tests for new functionality
4. Ensure all tests pass (`pytest`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Built for the x402 Hackathon. Special thanks to:
- The x402 team for creating the platform primitives
- The open-source community for excellent tools and libraries

---

## 📧 Contact

- **Repository**: [https://github.com/Officialhomie/SafeRun-X402](https://github.com/Officialhomie/SafeRun-X402)
- **Issues**: [GitHub Issues](https://github.com/Officialhomie/SafeRun-X402/issues)

---

**SafeRun**: Making agent autonomy safe, one checkpoint at a time. 🛡️
