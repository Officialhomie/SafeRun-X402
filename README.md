# 🛡️ SafeRun X402

**Supervised Agent Execution Protocol for x402 Hackathon**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

SafeRun enables AI agents to work autonomously until they hit critical decision points, then pauses for human approval before continuing. This solves the fundamental problem of agent deployment: agents are either fully autonomous (risky) or require constant babysitting (defeating the purpose of automation).

**Built for the [x402 Hackathon](https://x402.io)** - Demonstrating how to compose all 5 x402 primitives into production-ready agent infrastructure.

---

## 📋 Table of Contents

- [The Problem](#-the-problem)
- [The Solution](#-the-solution)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
  - [Visual Architecture Diagrams](#visual-architecture-diagrams)
  - [State Machine](#state-machine-7-states)
  - [System Components](#system-components)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Integration Guide](#-integration-guide-for-builders)
  - [Minimal Integration](#minimal-integration-20-lines)
  - [Step-by-Step Integration](#step-by-step-integration)
  - [Advanced Patterns](#advanced-patterns)
  - [Production Deployment](#production-deployment)
  - [Real-World Examples](#real-world-integration-examples)
- [Usage Examples](#-usage-examples)
- [API Reference](#-api-reference)
- [Configuration Reference](#-configuration-reference)
- [x402 Integration Details](#-x402-integration-details)
- [Testing](#-testing)
- [Troubleshooting](#-troubleshooting)
- [Demo Scenarios](#-demo-scenarios)
- [Project Structure](#-project-structure)
- [Contributing](#-contributing)

---

## 🎯 The Problem

Every company deploying AI agents hits the same wall:

- **Full Autonomy = Disasters**: Agents make expensive mistakes
  - Ordering 100 pizzas instead of 10 ($1,200 wasted)
  - Sending wrong data to customers (reputation damage)
  - Making bad financial decisions (money lost)
  - Deploying broken code (downtime costs)

- **Constant Supervision = No Value**: Babysitting agents defeats automation
  - Human must watch every step
  - No productivity gain
  - Expensive human time wasted

- **No Middle Ground**: Current tools don't support "supervised autonomy"
  - Can't pause execution at critical points
  - Can't capture full state for review
  - Can't rollback on mistakes
  - No infrastructure for human-in-the-loop at scale

---

## 💡 The Solution

SafeRun provides **supervised autonomy** - agents work independently until they need human judgment.

### How It Works

**Traditional Agent:**
```
Your Agent → Does Everything → Hope Nothing Breaks ❌
```

**With SafeRun:**
```
Your Agent → Checkpoint 1 → [Human Reviews] → Continue ✅
           → Checkpoint 2 → [Human Reviews] → Continue ✅
           → Final Check → [Human Approves] → Settle & Complete ✅
```

### Core Innovation

1. **Stateful Checkpoints**: Capture complete agent state (memory, outputs, decisions, resource usage)
2. **Human-in-the-Loop**: Beautiful web UI for human review with full context
3. **Saga Pattern Rollback**: True rollback with compensating transactions (not just cancellation)
4. **x402 Integration**: Compose all 5 primitives (Jobs, Escrow, Artifacts, Identity, Marketplace)
5. **Payment Intelligence**: Pro-rated payments based on completion percentage

---

## ✨ Key Features

### 1. Complete State Capture

At every checkpoint, SafeRun captures:
- **Agent Memory**: Conversation history, facts learned, current context
- **API Calls**: All external API calls with payloads and responses
- **Intermediate Outputs**: Results produced so far
- **Decision Trace**: Step-by-step reasoning the agent followed
- **Resource Consumption**: Tokens used, API calls, execution time, cost

**Why this matters**: Enables true rollback (restore from checkpoint) not just cancellation.

### 2. Intelligent Monitoring

The Monitor Agent detects:
- Anomalies in execution (sudden spike in API usage, errors)
- Progress vs. expected timeline (agent stuck or going too fast)
- Resource consumption thresholds (approaching budget limits)
- Custom checkpoint conditions (confidence score < 80%, critical action)

### 3. Human-Friendly Approval UI

Beautiful web dashboard presents:
- Clear summary of what the agent wants to do
- Recent actions and decisions with context
- Outputs generated so far
- Alerts and recommendations
- **Three decision options**:
  - ✅ **Approve**: Continue as planned
  - ✎ **Modify**: Change parameters and continue
  - ✗ **Reject**: Rollback to previous checkpoint

### 4. Saga Pattern Rollback

When approval is rejected, SafeRun:
1. Executes compensating transactions (undo API calls)
2. Restores state from last approved checkpoint
3. Calculates partial payment based on work completed
4. Cleans up resources (cancels scheduled jobs, deletes temp data)

**Real rollback**, not just stopping the workflow.

### 5. x402 Integration (All 5 Primitives)

| Primitive | How SafeRun Uses It |
|-----------|---------------------|
| **Jobs** | Main workflow job + approval sub-jobs at each checkpoint |
| **Escrow** | Lock funds at start, release incrementally at milestones |
| **Artifacts** | Store checkpoint state immutably (enables rollback) |
| **Identity** | Verify poster, executor, and supervisor roles |
| **Marketplace** | Discover and rate human supervisors |

---

## 🏗️ Architecture

SafeRun implements the **Saga pattern** for agent workflows, enabling stateful checkpoints and compensating transactions.

### Visual Architecture Diagrams

#### Diagram 1: Workflow State Machine

This shows all possible states and transitions with x402 operations:

```mermaid
stateDiagram-v2
    [*] --> INITIALIZED: Create Workflow<br/>(x402: Lock Escrow)

    INITIALIZED --> EXECUTING: Start Execution<br/>(x402: Create Job)

    EXECUTING --> AWAITING_APPROVAL: Checkpoint Reached<br/>(x402: Create Approval Sub-Job,<br/>Store State as Artifact)

    AWAITING_APPROVAL --> EXECUTING: Approved<br/>(x402: Release Milestone Payment,<br/>Resume Execution Job)

    AWAITING_APPROVAL --> ROLLING_BACK: Rejected + Can Rollback<br/>(x402: Mark Job Status,<br/>Prepare Rollback)

    AWAITING_APPROVAL --> FAILED: Rejected + Cannot Rollback<br/>(x402: Settle Partial Payment)

    AWAITING_APPROVAL --> EXECUTING: Modified<br/>(x402: Store Modified State,<br/>Resume with Changes)

    ROLLING_BACK --> EXECUTING: Rollback Success<br/>(x402: Restore from Artifact,<br/>Resume at Previous Checkpoint)

    ROLLING_BACK --> FAILED: Rollback Failed<br/>(x402: Settle Failure Payment)

    EXECUTING --> SETTLING: All Checkpoints Complete<br/>(x402: Calculate Completion %)

    EXECUTING --> FAILED: Execution Error<br/>(x402: Settle Partial Payment)

    SETTLING --> COMPLETED: Settlement Success<br/>(x402: Split Payment,<br/>Finalize Job)

    SETTLING --> FAILED: Settlement Failed<br/>(x402: Handle Dispute)

    COMPLETED --> [*]
    FAILED --> [*]

    note right of AWAITING_APPROVAL
        Human supervisor reviews:
        - Execution context
        - Intermediate outputs
        - Decision trace
        - Resource consumption
    end note

    note right of ROLLING_BACK
        Saga pattern compensating
        transactions restore state
        to last approved checkpoint
    end note

    note right of SETTLING
        Payment distribution:
        - 90% to executor agent
        - 10% to human supervisor
        Based on completion %
    end note
```

**State Descriptions:**

| State | Purpose | x402 Operations |
|-------|---------|-----------------|
| **INITIALIZED** | Workflow created, escrow locked | Lock escrow funds |
| **EXECUTING** | Agent actively working | Update job status, log telemetry |
| **AWAITING_APPROVAL** | Paused for human review | Create approval sub-job, store checkpoint artifact |
| **ROLLING_BACK** | Undoing rejected work | Execute compensating transactions |
| **SETTLING** | Calculating payment distribution | Calculate splits, prepare settlement |
| **COMPLETED** | Workflow finished successfully | Release payment, mark job complete |
| **FAILED** | Workflow failed or rejected | Settle partial payment, close job |

#### Diagram 2: Multi-Party Coordination

This shows how different actors interact through x402:

```mermaid
sequenceDiagram
    participant Poster as Task Poster
    participant x402 as x402 Platform
    participant Exec as Agent Executor
    participant Super as Human Supervisor
    participant Orch as SafeRun Orchestrator

    Note over Poster,Orch: Workflow Initialization
    Poster->>x402: Create Supervised Job<br/>(workflow config, escrow amount)
    x402->>x402: Lock $100 in escrow
    x402->>Orch: Job created (job_id: j123)
    Orch->>Exec: Initialize ExecutorAgent
    Orch->>Super: Assign Supervisor

    Note over Poster,Orch: Execution Phase
    Orch->>Exec: Start task execution
    Exec->>Exec: Perform work<br/>(API calls, processing)
    Exec->>Exec: Track telemetry<br/>(tokens, time, decisions)

    Note over Poster,Orch: Checkpoint 1 - Data Collection
    Exec->>Orch: Emit checkpoint signal<br/>(execution state)
    Orch->>Orch: Capture execution state<br/>(memory, outputs, trace)
    Orch->>x402: Store checkpoint as artifact<br/>(serialized state)
    x402-->>Orch: artifact_uri: x402://artifacts/abc123
    Orch->>x402: Create approval sub-job<br/>(for supervisor)
    x402->>Super: Route approval request<br/>(with context)

    Note over Super: Human Reviews Context
    Super->>Super: Review execution state<br/>- Data collected: 3 records<br/>- Quality score: 0.95<br/>- Decision trace shown

    Super->>x402: Submit approval decision<br/>(APPROVED)
    x402->>Orch: Decision: APPROVED
    Orch->>x402: Release milestone payment<br/>($30 to executor)
    x402->>Exec: Payment released
    Orch->>Exec: Continue execution

    Note over Poster,Orch: Settlement Phase
    Orch->>x402: Calculate settlement<br/>(100% complete)
    x402->>x402: Split remaining escrow:<br/>$36 → executor<br/>$4 → supervisor
    x402->>Exec: Final payment received
    x402->>Super: Supervisor fee received
    x402->>Orch: Settlement complete
    Orch->>Poster: Workflow COMPLETED

    Note over Poster,Orch: Audit Trail
    Poster->>x402: Query job artifacts
    x402-->>Poster: Return all checkpoints,<br/>approvals, payments
```

#### Diagram 3: Checkpoint State Architecture

This shows what gets captured at each checkpoint:

```mermaid
graph TB
    subgraph "Checkpoint Snapshot"
        subgraph "Layer 1: Approval Interface (Human-Facing)"
            A1[Human-Readable Summary]
            A2["Specific Decision Needed<br/>(Approve / Reject / Modify)"]
            A3[Relevant Artifacts]
            A4[Recommendation + Confidence]
        end

        subgraph "Layer 2: Task State (Business Logic)"
            B1[Inputs Received]
            B2[Intermediate Outputs]
            B3[Planned Next Steps]
            B4[Confidence Scores]
            B5[Risk Assessment]
        end

        subgraph "Layer 3: Execution Context (Technical)"
            C1["Agent Memory<br/>(conversation history, facts learned)"]
            C2["API Call History<br/>(endpoints, payloads, responses)"]
            C3["Resource Consumption<br/>(tokens, API calls, time)"]
            C4["Decision Trace<br/>(reasoning steps taken)"]
        end

        subgraph "Storage Layer"
            D1[Serialization Engine]
            D2[Compression]
            D3[x402 Artifact Storage]
            D4[Immutable Hash Reference]
        end
    end

    A1 & A2 & A3 & A4 --> B1
    B1 & B2 & B3 & B4 & B5 --> C1
    C1 & C2 & C3 & C4 --> D1
    D1 --> D2
    D2 --> D3
    D3 --> D4

    D4 -.->|"artifact_uri<br/>x402://artifacts/hash"| Restore[Rollback Restoration]

    style A1 fill:#e1f5ff
    style A2 fill:#e1f5ff
    style A3 fill:#e1f5ff
    style A4 fill:#e1f5ff

    style B1 fill:#fff4e1
    style B2 fill:#fff4e1
    style B3 fill:#fff4e1
    style B4 fill:#fff4e1
    style B5 fill:#fff4e1

    style C1 fill:#f0f0f0
    style C2 fill:#f0f0f0
    style C3 fill:#f0f0f0
    style C4 fill:#f0f0f0

    style D3 fill:#e8f5e9
    style D4 fill:#e8f5e9
```

**Checkpoint Data Structure Example:**

```json
{
  "snapshot_id": "snap_abc123",
  "workflow_id": "wf_456",
  "checkpoint_id": "cp_data_collection",
  "timestamp": "2025-01-18T10:30:00Z",

  "execution_state": {
    "agent_memory": {
      "conversation_history": ["User asked to analyze data", "Agent fetched records"],
      "facts_learned": {"data_source": "customers_2024", "total_records": 1000},
      "current_context": "Completed data fetching, ready for analysis"
    },
    "api_calls": [
      {
        "timestamp": "2025-01-18T10:29:45Z",
        "endpoint": "/api/data/fetch",
        "method": "GET",
        "status": 200,
        "response_summary": "3 records found"
      }
    ],
    "intermediate_outputs": {
      "records_collected": 3,
      "quality_score": 0.95,
      "data_preview": ["record1", "record2", "record3"]
    },
    "decision_trace": [
      "Analyzed data source reliability",
      "Fetched records using validated API",
      "Applied quality filters",
      "All validation checks passed"
    ],
    "resource_consumption": {
      "api_calls": 1,
      "tokens_used": 0,
      "execution_time_seconds": 2.5,
      "estimated_cost_usd": 0.02
    }
  },

  "approval_interface": {
    "summary": "Data collection complete. Found 3 high-quality records.",
    "decision_needed": "Approve to proceed with processing?",
    "context": {
      "checkpoint_name": "Data Collection",
      "records_found": 3,
      "quality_score": 0.95
    },
    "recommendation": "approve",
    "confidence": 0.92
  },

  "artifact_uri": "x402://artifacts/sha256:abc123def456...",
  "compressed_size_bytes": 15420
}
```

### State Machine (7 States)

Workflows transition through these states:

```
INITIALIZED → EXECUTING → AWAITING_APPROVAL → EXECUTING → SETTLING → COMPLETED
                             ↓
                      ROLLING_BACK → EXECUTING
                             ↓
                          FAILED
```

**Key Innovation**: At each `AWAITING_APPROVAL` checkpoint, complete execution state is captured and stored as an x402 artifact, enabling true rollback (not just cancellation).

### Four Agent Types

1. **Executor Agent**: Performs actual work, emits checkpoint signals, uses Claude API for intelligent task execution
2. **Monitor Agent**: Watches for anomalies, tracks resource consumption, triggers checkpoints based on conditions
3. **Supervisor Agent**: Presents checkpoints to humans via web UI, collects approval decisions
4. **Reconciliation Agent**: Handles rollback with compensating transactions, cleans up resources

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
   │         │      │         │      │(Claude) │
   │REST API │      │Workflow │      │         │
   │         │      │Orchestr-│      │Monitor  │
   │WebUI    │      │ator     │      │ Agent   │
   └─────────┘      └─────────┘      │         │
        │                 │           │Supervis-│
        │                 │           │or Agent │
        │                 │           │         │
        │                 │           │Reconcil-│
        │                 │           │iation   │
        │                 │           └─────────┘
        │                 │
        ▼                 ▼
   ┌─────────────────────────────────┐
   │         x402 Platform           │
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

- Python 3.11 or 3.12 (recommended). Python 3.13 is not supported by pinned deps.
- pip (Python package manager)
- Git

### Quick Install

```bash
# Clone repository
git clone https://github.com/Officialhomie/SafeRun-X402.git
cd SafeRun-X402

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment (required)
cp .env.example .env
# Edit .env to add API keys:
# X402_API_KEY=your_x402_key
# X402_API_URL=https://<your-real-x402-api-base-url>
# ANTHROPIC_API_KEY=your_anthropic_key
```

---

## 🚀 Quick Start

### 3-Minute Demo

The fastest way to see SafeRun in action:

```bash
# Terminal 1: Start the API server with approval UI
python3 -m uvicorn saferun.api.server:app --reload

# Terminal 2: Run impressive demo scenarios
python3 demo_impressive.py
```

Then **open in your browser**:
- **Approval Dashboard**: http://localhost:8000/approvals
- **Main UI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

**What you'll see:**
1. Demo creates workflows with checkpoints
2. Approval dashboard shows pending reviews with full context
3. Click "Approve" to let agents continue
4. See real-time state transitions and metrics
5. Impressive ROI scenarios ($36K+ savings, incident prevention)

### Run Classic Demo Scenarios

```bash
# Three scenarios showing the problem and solution
python3 demo_scenario.py
```

This demonstrates:
1. **Disaster Scenario**: What happens without SafeRun (100 pizzas ordered!)
2. **Success Scenario**: SafeRun catches the error, human approves with correction
3. **Rollback Scenario**: Rejection triggers compensating transactions

---

## 🔧 Integration Guide for Builders

**Add supervised autonomy to any agent workflow in under 20 lines of code.**

This guide shows you how to wrap your existing agent workflows with SafeRun's supervised execution protocol.

### Minimal Integration (20 Lines)

Here's the absolute minimum code to add SafeRun to your existing workflow:

```python
from saferun.core.state_machine.orchestrator import WorkflowOrchestrator
from saferun.core.state_machine.models import WorkflowConfig, CheckpointConfig, ExecutionState
from saferun.api.x402.client import X402Integration

# 1. Initialize SafeRun
x402 = X402Integration()
orchestrator = WorkflowOrchestrator(x402_integration=x402)

# 2. Define your workflow with checkpoints
config = WorkflowConfig(
    name="My Agent Workflow",
    description="Describe what your agent does",
    checkpoints=[
        CheckpointConfig(
            name="Review Before Execution",
            description="Human reviews plan before agent executes",
            requires_approval=True
        )
    ],
    escrow_amount=100.0,
    poster_id="your_user_id",
    executor_id="your_agent_id"
)

# 3. Start workflow
execution = orchestrator.initialize_workflow(config)
orchestrator.start_execution(execution.workflow_id)

# 4. Your agent does work...
# (your existing agent code here)

# 5. Hit checkpoint - agent pauses
checkpoint_state = ExecutionState(
    checkpoint_id=config.checkpoints[0].checkpoint_id,
    agent_memory={"what": "your agent learned"},
    intermediate_outputs={"results": "so far"}
)

snapshot = await orchestrator.create_checkpoint(execution.workflow_id, checkpoint_state)

# 6. Request human approval
approval_request = orchestrator.request_approval(
    workflow_id=execution.workflow_id,
    snapshot_id=snapshot.snapshot_id,
    summary="Agent wants to do X. Approve?",
    context={"details": "for human review"}
)

# Workflow is now paused. Human reviews in approval UI at http://localhost:8000/approvals
# Once approved, your agent continues automatically!
```

That's it! Your agent now has supervised execution.

### Step-by-Step Integration

#### Step 1: Identify Checkpoint Locations

Look at your existing agent workflow and identify **critical decision points** where a human should review:

**Good Checkpoint Locations:**
- ✅ Before executing expensive operations (e.g., deploying code, making trades)
- ✅ After data collection, before processing (validate inputs)
- ✅ Before final delivery (quality check)
- ✅ When agent confidence is low (< 80%)
- ✅ Before irreversible actions (sending emails, posting content)

**Bad Checkpoint Locations:**
- ❌ Every single step (creates approval fatigue)
- ❌ Inside tight loops (performance killer)
- ❌ For trivial decisions (defeats automation purpose)

**Example:**

```python
# Your existing workflow
async def my_agent_workflow(task_description):
    # Step 1: Research
    research_data = await agent.research(task_description)
    # ⭐ CHECKPOINT: Review research before analysis

    # Step 2: Analysis
    analysis = await agent.analyze(research_data)
    # ⭐ CHECKPOINT: Review analysis before action

    # Step 3: Execute
    result = await agent.execute_plan(analysis)
    # ⭐ CHECKPOINT: Final review before delivery

    return result
```

#### Step 2: Wrap Your Agent

Create a wrapper that integrates with SafeRun:

```python
from saferun.agents.executor.agent import ExecutorAgent
from saferun.core.state_machine.models import ExecutionState

class MyWrappedAgent:
    def __init__(self, agent_id: str):
        self.executor = ExecutorAgent(agent_id=agent_id)
        self.my_existing_agent = MyExistingAgent()  # Your agent

    async def execute_with_supervision(self, task: str, checkpoint_callback: callable):
        """
        Execute your agent's task with SafeRun supervision.

        Args:
            task: The task to execute
            checkpoint_callback: Function to call at checkpoints
        """
        # Step 1: Research (your existing code)
        research_data = await self.my_existing_agent.research(task)

        # Checkpoint 1: Review research
        state_1 = ExecutionState(
            checkpoint_id="research_review",
            agent_memory={"task": task},
            intermediate_outputs={"research": research_data},
            decision_trace=["Completed research phase"]
        )
        await checkpoint_callback(state_1)

        # Step 2: Analysis (your existing code)
        analysis = await self.my_existing_agent.analyze(research_data)

        # Checkpoint 2: Review analysis
        state_2 = ExecutionState(
            checkpoint_id="analysis_review",
            agent_memory={"task": task, "research": research_data},
            intermediate_outputs={"analysis": analysis},
            decision_trace=["Completed research", "Analyzed data", "Generated plan"]
        )
        await checkpoint_callback(state_2)

        # Step 3: Execute (your existing code)
        result = await self.my_existing_agent.execute_plan(analysis)
        return result
```

#### Step 3: Configure Workflow

Define your checkpoints and escrow settings:

```python
from saferun.core.state_machine.models import WorkflowConfig, CheckpointConfig

def create_my_workflow_config(task_description: str, escrow_amount: float = 100.0) -> WorkflowConfig:
    """Create a SafeRun workflow config for your agent."""

    return WorkflowConfig(
        name=f"Agent Task: {task_description[:50]}",
        description=task_description,

        checkpoints=[
            CheckpointConfig(
                name="Research Review",
                description="Review research data before analysis",
                requires_approval=True,
                can_rollback=True,  # Can restart if rejected
                timeout_seconds=300  # 5 min for human to respond
            ),
            CheckpointConfig(
                name="Analysis Review",
                description="Review analysis before execution",
                requires_approval=True,
                can_rollback=True
            ),
            CheckpointConfig(
                name="Final Review",
                description="Final check before delivery",
                requires_approval=True,
                can_rollback=False  # Point of no return
            )
        ],

        escrow_amount=escrow_amount,
        poster_id="user_123",  # Who's paying
        executor_id="agent_456",  # Your agent
        supervisor_id="human_789"  # Who approves
    )
```

#### Step 4: Orchestrate Execution

Put it all together:

```python
import asyncio
from saferun.core.state_machine.orchestrator import WorkflowOrchestrator
from saferun.core.state_machine.models import WorkflowState
from saferun.api.x402.client import X402Integration

async def run_supervised_workflow(task_description: str):
    """Run your agent with full SafeRun supervision."""

    # Initialize SafeRun
    x402 = X402Integration()
    orchestrator = WorkflowOrchestrator(x402_integration=x402)

    # Create workflow config
    config = create_my_workflow_config(task_description)

    # Initialize workflow
    execution = orchestrator.initialize_workflow(config)
    workflow_id = execution.workflow_id
    orchestrator.start_execution(workflow_id)

    print(f"✓ Workflow {workflow_id} started")
    print(f"  View approvals at: http://localhost:8000/approvals")

    # Create checkpoint callback
    checkpoint_index = 0

    async def checkpoint_callback(state: ExecutionState):
        nonlocal checkpoint_index

        # Create checkpoint snapshot
        snapshot = await orchestrator.create_checkpoint(workflow_id, state)

        # Request approval
        approval_request = orchestrator.request_approval(
            workflow_id=workflow_id,
            snapshot_id=snapshot.snapshot_id,
            summary=f"Checkpoint {checkpoint_index + 1}: {config.checkpoints[checkpoint_index].name}",
            context=state.intermediate_outputs
        )

        print(f"⏸  Waiting for approval at checkpoint: {config.checkpoints[checkpoint_index].name}")

        # Wait for human approval
        while True:
            workflow = orchestrator.get_workflow(workflow_id)
            if workflow.current_state != WorkflowState.AWAITING_APPROVAL:
                break
            await asyncio.sleep(1)  # Poll every second

        workflow = orchestrator.get_workflow(workflow_id)

        if workflow.current_state == WorkflowState.EXECUTING:
            print(f"✓ Approved! Continuing...")
            checkpoint_index += 1
        elif workflow.current_state == WorkflowState.ROLLING_BACK:
            print(f"✗ Rejected! Rolling back...")
            raise Exception("Approval rejected - rollback initiated")

    # Execute your agent with supervision
    agent = MyWrappedAgent(agent_id="agent_456")

    try:
        result = await agent.execute_with_supervision(
            task=task_description,
            checkpoint_callback=checkpoint_callback
        )

        # Complete workflow
        orchestrator.settle_workflow(workflow_id, {"result": result})
        orchestrator.complete_workflow(workflow_id)

        print(f"✓ Workflow completed successfully!")
        return result

    except Exception as e:
        orchestrator.fail_workflow(workflow_id, str(e))
        print(f"✗ Workflow failed: {e}")
        raise

    finally:
        await x402.close()

# Run it!
if __name__ == "__main__":
    asyncio.run(run_supervised_workflow(
        "Research competitor pricing and suggest our pricing strategy"
    ))
```

#### Step 5: Start Approval UI

In a separate terminal:

```bash
# Start the SafeRun API server with approval UI
python3 -m uvicorn saferun.api.server:app --reload --port 8000

# Open approval dashboard
open http://localhost:8000/approvals
```

Now when your agent hits checkpoints, they'll appear in the dashboard for human review!

### Advanced Patterns

#### Pattern 1: Conditional Checkpoints

Only checkpoint when agent confidence is low:

```python
async def smart_checkpoint(state, confidence_score):
    """Only checkpoint if agent is uncertain."""

    if confidence_score < 0.8:  # Low confidence
        print(f"⚠️  Low confidence ({confidence_score}), requesting human review")
        await checkpoint_callback(state)
    else:
        print(f"✓ High confidence ({confidence_score}), auto-proceeding")
        # Skip checkpoint, continue automatically
```

#### Pattern 2: Dynamic Checkpoint Creation

Generate checkpoints based on task complexity:

```python
def create_adaptive_config(task_complexity: str) -> WorkflowConfig:
    """Adjust checkpoints based on task complexity."""

    if task_complexity == "simple":
        checkpoints = [
            CheckpointConfig(name="Final Review", description="Quick check")
        ]
    elif task_complexity == "medium":
        checkpoints = [
            CheckpointConfig(name="Mid-Point Review", description="Halfway check"),
            CheckpointConfig(name="Final Review", description="Final check")
        ]
    else:  # complex
        checkpoints = [
            CheckpointConfig(name="Planning Review", description="Review plan"),
            CheckpointConfig(name="Execution Review", description="Review execution"),
            CheckpointConfig(name="Quality Review", description="Quality check"),
            CheckpointConfig(name="Final Review", description="Final approval")
        ]

    return WorkflowConfig(
        name=f"{task_complexity.title()} Task",
        checkpoints=checkpoints,
        escrow_amount=50.0 if task_complexity == "simple" else 100.0,
        poster_id="user",
        executor_id="agent"
    )
```

#### Pattern 3: Multi-Agent Workflows

Coordinate multiple agents with shared checkpoints:

```python
async def multi_agent_workflow():
    """Run multiple agents with coordinated checkpoints."""

    orchestrator = WorkflowOrchestrator(x402_integration=X402Integration())

    config = WorkflowConfig(
        name="Multi-Agent Research Pipeline",
        checkpoints=[
            CheckpointConfig(name="Research Complete"),
            CheckpointConfig(name="Analysis Complete"),
            CheckpointConfig(name="Synthesis Complete")
        ],
        escrow_amount=150.0,
        poster_id="user",
        executor_id="multi_agent_system"
    )

    execution = orchestrator.initialize_workflow(config)
    workflow_id = execution.workflow_id
    orchestrator.start_execution(workflow_id)

    # Agent 1: Researcher
    research_agent = ExecutorAgent("researcher_1")
    research_data = await research_agent.execute_task("Gather competitor data", {})

    # Checkpoint 1
    await create_and_approve_checkpoint(orchestrator, workflow_id, research_data)

    # Agent 2: Analyst (uses output from Agent 1)
    analyst_agent = ExecutorAgent("analyst_2")
    analysis = await analyst_agent.execute_task(
        "Analyze research data",
        {"input": research_data}
    )

    # Checkpoint 2
    await create_and_approve_checkpoint(orchestrator, workflow_id, analysis)

    # Agent 3: Synthesizer (uses outputs from Agent 1 & 2)
    synthesis_agent = ExecutorAgent("synthesizer_3")
    final_report = await synthesis_agent.execute_task(
        "Create final report",
        {"research": research_data, "analysis": analysis}
    )

    # Final checkpoint
    await create_and_approve_checkpoint(orchestrator, workflow_id, final_report)

    return final_report
```

#### Pattern 4: Rollback with Compensation

Define compensating transactions for rollback:

```python
from saferun.core.rollback.reconciliation import ReconciliationAgent

async def workflow_with_rollback():
    """Workflow that can cleanly rollback on rejection."""

    reconciliation = ReconciliationAgent("reconciler_1")

    # Define compensating transactions
    compensation_actions = {
        "checkpoint_1": async_delete_created_records,
        "checkpoint_2": async_revert_config_changes,
        "checkpoint_3": async_cancel_scheduled_jobs
    }

    try:
        # ... workflow execution ...
        pass
    except ApprovalRejected as e:
        # Execute compensating transaction
        checkpoint_id = e.rejected_checkpoint_id
        await compensation_actions[checkpoint_id]()

        # Use SafeRun's reconciliation agent
        await reconciliation.reconcile_workflow(
            workflow_id=workflow_id,
            target_checkpoint=e.last_approved_checkpoint
        )
```

### Production Deployment

#### Environment Variables

```bash
# Required (SafeRun will fail fast if missing)
X402_API_KEY=your_x402_api_key
X402_API_URL=https://<your-real-x402-api-base-url>

# Required (ExecutorAgent uses Claude)
ANTHROPIC_API_KEY=your_anthropic_key

# Optional (for OpenAI-powered agents)
OPENAI_API_KEY=your_openai_key

# Application
DEBUG=false
DATABASE_URL=postgresql://user:pass@localhost/saferun
```

#### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY saferun/ ./saferun/

EXPOSE 8000

CMD ["uvicorn", "saferun.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build and run
docker build -t saferun-x402 .
docker run -p 8000:8000 --env-file .env saferun-x402
```

#### Kubernetes Deployment

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: saferun-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: saferun
  template:
    metadata:
      labels:
        app: saferun
    spec:
      containers:
      - name: saferun
        image: saferun-x402:latest
        ports:
        - containerPort: 8000
        env:
        - name: X402_API_KEY
          valueFrom:
            secretKeyRef:
              name: saferun-secrets
              key: x402-api-key
---
apiVersion: v1
kind: Service
metadata:
  name: saferun-service
spec:
  selector:
    app: saferun
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

#### Monitoring & Observability

```python
# Add to your workflow code
from loguru import logger
import prometheus_client as prom

# Metrics
checkpoint_counter = prom.Counter(
    'saferun_checkpoints_total',
    'Total checkpoints created'
)
approval_latency = prom.Histogram(
    'saferun_approval_latency_seconds',
    'Time waiting for approval'
)

# In your checkpoint code
checkpoint_counter.inc()

start_time = time.time()
await wait_for_approval()
approval_latency.observe(time.time() - start_time)

logger.info(
    "Checkpoint approved",
    workflow_id=workflow_id,
    checkpoint_name=checkpoint_name,
    latency_seconds=time.time() - start_time
)
```

### Real-World Integration Examples

#### Example 1: Wrap LangChain Agent

```python
from langchain.agents import initialize_agent, Tool
from langchain.llms import OpenAI
from saferun.core.state_machine.orchestrator import WorkflowOrchestrator
from saferun.core.state_machine.models import WorkflowConfig, CheckpointConfig, ExecutionState
from saferun.api.x402.client import X402Integration

class SafeRunLangChainWrapper:
    def __init__(self):
        self.llm = OpenAI(temperature=0)
        self.tools = [...]  # Your LangChain tools
        self.agent = initialize_agent(
            self.tools,
            self.llm,
            agent="zero-shot-react-description"
        )

        self.orchestrator = WorkflowOrchestrator(
            x402_integration=X402Integration()
        )

    async def run_with_supervision(self, query: str):
        """Run LangChain agent with SafeRun checkpoints."""

        # Initialize SafeRun workflow
        config = WorkflowConfig(
            name=f"LangChain: {query}",
            checkpoints=[
                CheckpointConfig(name="Review Plan"),
                CheckpointConfig(name="Review Execution")
            ],
            escrow_amount=10.0,
            poster_id="user",
            executor_id="langchain_agent"
        )

        execution = self.orchestrator.initialize_workflow(config)
        workflow_id = execution.workflow_id
        self.orchestrator.start_execution(workflow_id)

        # Run your LangChain agent
        result = self.agent.run(query)

        # Add checkpoint before final answer
        state = ExecutionState(
            checkpoint_id=config.checkpoints[0].checkpoint_id,
            intermediate_outputs={"answer": result}
        )

        snapshot = await self.orchestrator.create_checkpoint(workflow_id, state)

        # Request approval
        self.orchestrator.request_approval(
            workflow_id,
            snapshot.snapshot_id,
            f"Agent wants to respond with: {result}",
            {}
        )

        # Wait for approval...
        # (approval polling logic)

        return result
```

#### Example 2: Wrap AutoGPT

```python
from saferun.core.state_machine.orchestrator import WorkflowOrchestrator
from saferun.core.state_machine.models import WorkflowConfig, CheckpointConfig, ExecutionState

class SafeRunAutoGPTWrapper:
    """Wrap AutoGPT with SafeRun supervision."""

    async def run_autogpt_with_checkpoints(self, goal: str):
        orchestrator = WorkflowOrchestrator(x402_integration=X402Integration())

        config = WorkflowConfig(
            name=f"AutoGPT: {goal}",
            checkpoints=[
                CheckpointConfig(
                    name="Review After Each Action",
                    description="Human reviews each AutoGPT action"
                )
            ],
            escrow_amount=50.0,
            poster_id="user",
            executor_id="autogpt"
        )

        # Start workflow
        execution = orchestrator.initialize_workflow(config)
        workflow_id = execution.workflow_id
        orchestrator.start_execution(workflow_id)

        # Wrap AutoGPT's action execution
        original_execute = autogpt.execute_action

        async def supervised_execute(action):
            # Create checkpoint before action
            state = ExecutionState(
                checkpoint_id=config.checkpoints[0].checkpoint_id,
                intermediate_outputs={"planned_action": action}
            )

            snapshot = await orchestrator.create_checkpoint(workflow_id, state)

            # Request approval
            orchestrator.request_approval(
                workflow_id,
                snapshot.snapshot_id,
                f"AutoGPT wants to: {action}",
                {"action": action}
            )

            # Wait for approval
            await wait_for_approval(orchestrator, workflow_id)

            # Execute original action
            return original_execute(action)

        # Monkey-patch AutoGPT
        autogpt.execute_action = supervised_execute

        # Run AutoGPT normally
        result = await autogpt.run(goal)

        return result
```

---

## 📚 Usage Examples

### Creating a Supervised Workflow

```python
from saferun.core.state_machine.orchestrator import WorkflowOrchestrator
from saferun.core.state_machine.models import WorkflowConfig, CheckpointConfig
from saferun.api.x402.client import X402Integration

x402 = X402Integration()
orchestrator = WorkflowOrchestrator(x402_integration=x402)

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
from saferun.core.state_machine.models import ExecutionState

# Capture state at checkpoint
checkpoint_state = ExecutionState(
    checkpoint_id="review_data",
    agent_memory={"task": "data processing", "phase": "collection"},
    api_calls=[{"endpoint": "/api/data", "status": 200}],
    intermediate_outputs={"records_found": 100},
    decision_trace=["Fetched data", "Validated format"],
    resource_consumption={"api_calls": 1, "tokens_used": 0}
)

snapshot = await orchestrator.create_checkpoint(workflow_id, checkpoint_state)
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
    execution_state=checkpoint_state
)

# Format for human review
display = supervisor.format_for_display(approval_request)
# Present display to human in approval UI
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

### REST Endpoints

#### Create Workflow

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
  "x402_setup": {
    "job_id": "job_xyz",
    "escrow_id": "escrow_456"
  },
  "checkpoints": 2,
  "message": "Workflow created and ready to execute"
}
```

#### Get Workflow Status

```bash
GET /api/workflows/{workflow_id}
```

**Response:**
```json
{
  "workflow_id": "wf_abc123",
  "name": "My Workflow",
  "description": "Description here",
  "status": "executing",
  "current_checkpoint": 1,
  "total_checkpoints": 2,
  "snapshots": 1,
  "approval_requests": 1,
  "approval_responses": 0,
  "started_at": "2024-01-18T10:00:00Z",
  "completed_at": null,
  "error_message": null
}
```

#### List All Workflows

```bash
GET /api/workflows
```

**Response:**
```json
{
  "workflows": [
    {
      "workflow_id": "wf_abc123",
      "name": "My Workflow",
      "status": "executing",
      "current_checkpoint": 1,
      "total_checkpoints": 2,
      "started_at": "2024-01-18T10:00:00Z"
    }
  ],
  "total": 1
}
```

#### Get Pending Approvals

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
      "checkpoint_name": "Review Step 1",
      "summary": "Agent completed data collection. Found 100 records. Ready to proceed?",
      "context": {
        "records_found": 100,
        "quality_score": 0.95
      },
      "created_at": "2024-01-18T10:05:00Z"
    }
  ],
  "total": 1
}
```

#### Submit Approval Decision

```bash
POST /api/approvals/submit
Content-Type: application/json

{
  "request_id": "req_123",
  "decision": "APPROVED",
  "rationale": "Data looks good, quality score is high",
  "approved_by": "user_123",
  "modifications": null
}
```

**Response:**
```json
{
  "success": true,
  "decision": "APPROVED",
  "workflow_status": "executing",
  "message": "Approval APPROVED - workflow now executing"
}
```

**For Modifications:**
```bash
POST /api/approvals/submit
Content-Type: application/json

{
  "request_id": "req_123",
  "decision": "MODIFIED",
  "rationale": "Adjust threshold from 100 to 150",
  "approved_by": "user_123",
  "modifications": {
    "threshold": 150
  }
}
```

**For Rejection:**
```bash
POST /api/approvals/submit
Content-Type: application/json

{
  "request_id": "req_123",
  "decision": "REJECTED",
  "rationale": "Data quality too low, need to re-fetch",
  "approved_by": "user_123",
  "modifications": null
}
```

#### Get System Statistics

```bash
GET /api/stats
```

**Response:**
```json
{
  "total_workflows": 42,
  "workflow_states": {
    "executing": 5,
    "awaiting_approval": 2,
    "completed": 35
  },
  "total_approvals_processed": 120,
  "pending_approvals": 2,
  "active_executors": 5,
  "active_supervisors": 3
}
```

#### Health Check

```bash
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "SafeRun X402",
  "version": "1.0.0"
}
```

---

## ⚙️ Configuration Reference

### CheckpointConfig Options

```python
CheckpointConfig(
    name: str,                    # Display name for this checkpoint
    description: str,             # What's being reviewed
    requires_approval: bool,      # Default: True - pause for human
    can_rollback: bool,           # Default: True - allow undo
    timeout_seconds: int,         # Default: 300 - how long to wait
    checkpoint_id: str            # Auto-generated if not provided
)
```

**Example:**
```python
CheckpointConfig(
    name="Review Data Processing",
    description="Validate processed data before delivery",
    requires_approval=True,
    can_rollback=True,
    timeout_seconds=600  # 10 minutes
)
```

### WorkflowConfig Options

```python
WorkflowConfig(
    name: str,                           # Workflow display name
    description: str,                    # What this workflow does
    checkpoints: List[CheckpointConfig], # Your checkpoint list
    escrow_amount: float,                # x402 escrow (in dollars)
    poster_id: str,                      # User/org running workflow
    executor_id: str,                    # Agent performing work
    supervisor_id: str,                  # Optional: specific supervisor
    workflow_id: str                     # Auto-generated if not provided
)
```

**Example:**
```python
WorkflowConfig(
    name="Customer Data Pipeline",
    description="Process and validate customer data with human oversight",
    checkpoints=[
        CheckpointConfig(name="Data Collection Review"),
        CheckpointConfig(name="Processing Review"),
        CheckpointConfig(name="Final Quality Check")
    ],
    escrow_amount=150.0,
    poster_id="company_abc",
    executor_id="data_agent_001",
    supervisor_id="human_reviewer_xyz"
)
```

### ExecutionState Capture

```python
ExecutionState(
    checkpoint_id: str,           # Which checkpoint this is

    # What the agent has learned/remembered
    agent_memory: Dict[str, Any],

    # External API calls made
    api_calls: List[Dict[str, Any]],

    # Results produced so far
    intermediate_outputs: Dict[str, Any],

    # Agent's reasoning steps
    decision_trace: List[str],

    # Resource usage tracking
    resource_consumption: Dict[str, float]
)
```

**Example:**
```python
ExecutionState(
    checkpoint_id="data_review",
    agent_memory={
        "conversation": ["User requested data analysis", "Agent started collection"],
        "facts": {"data_source": "database_prod", "table": "customers"}
    },
    api_calls=[
        {
            "endpoint": "/api/data/query",
            "method": "POST",
            "status": 200,
            "timestamp": "2024-01-18T10:30:00Z",
            "payload": {"table": "customers", "limit": 1000}
        }
    ],
    intermediate_outputs={
        "records_found": 856,
        "quality_score": 0.92,
        "data_preview": ["record1", "record2", "record3"]
    },
    decision_trace=[
        "Analyzed user query",
        "Determined data source: production database",
        "Executed query with safety limits",
        "Validated data quality",
        "Quality score 0.92 exceeds threshold 0.80"
    ],
    resource_consumption={
        "api_calls": 1,
        "tokens_used": 245,
        "execution_time_seconds": 3.2,
        "estimated_cost_usd": 0.05
    }
)
```

---

## 🔗 x402 Integration Details

SafeRun composes **all 5 x402 primitives** to create supervised agent infrastructure:

### 1. Jobs Primitive

**How SafeRun Uses It:**
- Main workflow job created at initialization
- Approval sub-jobs created dynamically at each checkpoint
- Settlement job handles final payment distribution

**Implementation:**
```python
# Main job creation (in orchestrator)
job = await x402.create_job(
    job_type="supervised_workflow",
    job_data={"workflow_id": workflow_id, "config": workflow_config},
    escrow_amount=escrow_amount,
    executor_id=executor_id
)

# Approval sub-job (at checkpoints)
approval_job = await x402.create_approval_subjob(
    parent_job_id=job["job_id"],
    checkpoint_id=checkpoint_id,
    supervisor_id=supervisor_id,
    approval_data=checkpoint_data
)
```

### 2. Escrow Primitive

**How SafeRun Uses It:**
- Funds locked at workflow start
- Milestone-based releases tied to approvals
- Pro-rated partial payments on rejection
- Split payments between executor and supervisor

**Implementation:**
```python
# Lock escrow at start
escrow = await x402.lock_escrow(
    workflow_id=workflow_id,
    amount=escrow_amount,
    poster_id=poster_id,
    executor_id=executor_id
)

# Release milestone payment after approval
await x402.release_escrow(
    escrow_id=escrow["escrow_id"],
    amount=milestone_amount,
    recipient_id=executor_id,
    reason="checkpoint_approved"
)

# Split final payment
await x402.split_payment(
    escrow_id=escrow["escrow_id"],
    splits=[
        {"recipient_id": executor_id, "amount": 90.0, "reason": "execution"},
        {"recipient_id": supervisor_id, "amount": 10.0, "reason": "supervision"}
    ]
)
```

### 3. Artifacts Primitive

**How SafeRun Uses It:**
- Checkpoint state stored as immutable artifacts
- Content-addressed storage (SHA-256)
- Full audit trail of all decisions
- Approval decisions stored with rationale

**Implementation:**
```python
# Store checkpoint as artifact
serialized_state = json.dumps(execution_state.model_dump())
artifact = await x402.create_artifact(
    artifact_type="checkpoint_state",
    content=serialized_state,
    metadata={
        "workflow_id": workflow_id,
        "checkpoint_id": checkpoint_id,
        "snapshot_id": snapshot_id
    }
)

# artifact_uri: "x402://artifacts/sha256:abc123..."
snapshot.artifact_uri = artifact["uri"]

# Later: Retrieve for rollback
artifact_data = await x402.get_artifact(artifact_uri)
restored_state = json.loads(artifact_data["content"])
```

### 4. Identity Primitive

**How SafeRun Uses It:**
- Three primary roles: Poster, Executor, Supervisor
- Role verification at each step
- Reputation tracking for supervisors
- Optional verifier role for disputes

**Implementation:**
```python
# Verify executor identity
is_valid = await x402.verify_identity(
    user_id=executor_id,
    role="executor"
)

# Get supervisor profile
profile = await x402.get_user_profile(supervisor_id)
reputation_score = profile["reputation"]

# Track approval quality (affects reputation)
await x402.record_approval_quality(
    supervisor_id=supervisor_id,
    workflow_id=workflow_id,
    quality_score=0.95
)
```

### 5. Marketplace Primitive

**How SafeRun Uses It:**
- Supervisor discovery by workflow type
- Filtering by reputation and availability
- Rating and review system
- Pricing models (per-approval, subscription)

**Implementation:**
```python
# Find available supervisors
supervisors = await x402.find_supervisors(
    workflow_type="data_processing",
    min_reputation=0.8
)

# Request specific supervisor
await x402.request_supervisor(
    supervisor_id=supervisors[0]["supervisor_id"],
    workflow_id=workflow_id
)

# Rate supervisor after completion
await x402.rate_supervisor(
    supervisor_id=supervisor_id,
    workflow_id=workflow_id,
    rating=5,
    review="Quick and thorough review"
)
```

---

## 🧪 Testing

### Run Tests

```bash
# Run all tests
python3 -m pytest saferun/tests/ -v

# Run specific test file
python3 -m pytest saferun/tests/test_state_machine.py -v

# Run end-to-end integration test
python3 -m pytest saferun/tests/test_end_to_end.py -v -s

# Run with coverage
python3 -m pytest --cov=saferun saferun/tests/
```

### Test Coverage

Current test coverage includes:
- ✅ **Workflow initialization and state transitions**
  - All 7 states (INITIALIZED, EXECUTING, AWAITING_APPROVAL, etc.)
  - Valid and invalid state transitions

- ✅ **Checkpoint creation and artifact storage**
  - State serialization and deserialization
  - x402 artifact storage integration
  - Checkpoint metadata preservation

- ✅ **Approval flow (approve, reject, modify)**
  - Approval decision routing
  - State transitions based on decisions
  - Modification parameter passing

- ✅ **Rollback logic with state restoration**
  - Rollback triggers
  - State restoration from artifacts
  - Compensating transaction execution

- ✅ **End-to-end integration (full workflow lifecycle)**
  - Complete happy path (create → execute → approve → complete)
  - Rejection and rollback path
  - Modification path
  - Multi-checkpoint workflows

- ✅ **x402 integration layer**
  - All 5 primitives tested
  - Error handling and retry logic
  - Fail-fast behavior

### Test Files

1. **test_state_machine.py** - Unit tests for orchestrator
   - Workflow initialization
   - State transitions
   - Checkpoint creation
   - Approval handling

2. **test_integration.py** - Integration tests for multi-agent workflows
   - Multi-agent coordination
   - Checkpoint sharing between agents
   - Complex workflow patterns

3. **test_end_to_end.py** - Complete workflow tests
   - `test_complete_workflow_happy_path()` - Full workflow from start to finish
   - `test_workflow_with_rejection_and_rollback()` - Rejection triggers rollback
   - `test_workflow_with_modification()` - Modification decision handling
   - `test_checkpoint_artifact_storage()` - x402 artifact integration

---

## 🔧 Troubleshooting

### Common Issues

#### Issue: "X402_API_KEY is required"

**Solution:**
```bash
# Set environment variable
export X402_API_KEY=your_key_here

# Or add to .env file
echo "X402_API_KEY=your_key_here" >> .env
```

#### Issue: "Workflow stuck in AWAITING_APPROVAL"

**Solution:**
```bash
# Check approval UI is running
curl http://localhost:8000/api/approvals/pending

# Submit approval via API
curl -X POST http://localhost:8000/api/approvals/submit \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "req_123",
    "decision": "APPROVED",
    "rationale": "Looks good",
    "approved_by": "human_789"
  }'
```

#### Issue: "Checkpoint artifact storage failed"

**Solution:**
```bash
# Check x402 API is accessible
curl "$X402_API_URL/health"
```

#### Issue: "ModuleNotFoundError: No module named 'anthropic'"

**Solution:**
```bash
# Install missing dependency
pip install anthropic

# Or install all requirements
pip install -r requirements.txt
```

#### Issue: "Port 8000 already in use"

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use a different port
uvicorn saferun.api.server:app --port 8001
```

---

## 📊 Demo Scenarios

### Scenario 1: Meeting Room Booking (The Classic)

**The Problem:**
```
Agent Task: Book meeting room and order food for 10 people
```

**Without SafeRun:**
- Agent misinterprets "10 people" as "100 pizzas"
- Order is placed automatically
- **$1,200 wasted** (100 pizzas × $12)
- 90 pizzas to dispose of
- Team embarrassment

**With SafeRun:**
```
1. Agent plans order: "100 pizzas for $1,200"
2. Checkpoint: "Review food order before placing"
3. Human reviews: "Wait, that's 100 pizzas not 10!"
4. Human modifies: "Change to 10 pizzas"
5. Agent proceeds with corrected order
6. **$1,080 saved!**
```

### Scenario 2: Financial Trading

**The Problem:**
```
Agent Task: Execute trading strategy based on market analysis
```

**Without SafeRun:**
- Agent analyzes market, sees opportunity
- Executes trade: Buy 1000 shares at $50 = $50,000
- Market immediately drops 20%
- **$10,000 lost**

**With SafeRun:**
```
1. Agent analyzes market data
2. Agent plans trade: "Buy 1000 shares at $50"
3. Checkpoint: "Review trading decision"
4. Human reviews: Market looks volatile, reduce position
5. Human modifies: "Buy 500 shares instead"
6. Trade executed with reduced risk
7. Market drops 20% → Loss only $5,000 instead of $10,000
8. **$5,000 saved by human oversight**
```

### Scenario 3: Code Deployment

**The Problem:**
```
Agent Task: Deploy new feature to production
```

**Without SafeRun:**
- Agent builds and deploys code
- Deployment contains breaking change
- Production goes down for 2 hours
- **$50,000+ in lost revenue and recovery costs**

**With SafeRun:**
```
1. Agent builds code and runs tests
2. Checkpoint: "Review deployment plan"
3. Human reviews: Notices missing database migration
4. Human rejects: "Add migration before deploying"
5. Agent rolls back, adds migration
6. Second checkpoint: "Review updated deployment"
7. Human approves
8. Deployment succeeds without incident
9. **$50,000+ disaster prevented**
```

### ROI Summary

| Scenario | Without SafeRun | With SafeRun | Savings |
|----------|----------------|--------------|---------|
| **Pizza Disaster** | $1,200 wasted | $120 spent | **$1,080** |
| **Bad Trade** | $10,000 lost | $5,000 lost | **$5,000** |
| **Failed Deployment** | $50,000+ lost | $0 lost | **$50,000+** |
| **Total** | **$61,200+** | **$5,120** | **$56,080+** |

**Return on Investment: 1,095% (10.95x)**

Run these scenarios yourself:
```bash
python3 demo_impressive.py
```

---

## 📁 Project Structure

```
SafeRun-X402/
├── saferun/                    # Main package
│   ├── __init__.py
│   ├── config.py               # Configuration management
│   │
│   ├── core/                   # Core infrastructure
│   │   ├── __init__.py
│   │   ├── state_machine/      # Workflow orchestration
│   │   │   ├── __init__.py
│   │   │   ├── models.py       # Pydantic models (7 states, checkpoints)
│   │   │   └── orchestrator.py # State machine (278 lines)
│   │   ├── checkpoints/        # Checkpoint capture
│   │   │   ├── __init__.py
│   │   │   └── capture.py      # State serialization
│   │   └── rollback/           # Rollback mechanism
│   │       ├── __init__.py
│   │       └── reconciliation.py # Compensating transactions
│   │
│   ├── agents/                 # Four agent types
│   │   ├── __init__.py
│   │   ├── executor/           # Executor agent
│   │   │   ├── __init__.py
│   │   │   └── agent.py        # Claude API integration
│   │   ├── monitor/            # Monitor agent
│   │   │   ├── __init__.py
│   │   │   └── agent.py        # Telemetry tracking
│   │   ├── supervisor/         # Supervisor agent
│   │   │   ├── __init__.py
│   │   │   └── agent.py        # Human approval interface
│   │   └── reconciliation/     # Reconciliation agent
│   │       ├── __init__.py
│   │       └── agent.py        # Rollback logic
│   │
│   ├── api/                    # API layer
│   │   ├── __init__.py
│   │   ├── x402/               # x402 integration
│   │   │   ├── __init__.py
│   │   │   └── client.py       # x402 API client (709 lines)
│   │   │                       # - All 5 primitives
│   │   │                       # - Retry logic with exponential backoff
│   │   │                       # - Real HTTP calls using httpx
│   │   └── server.py           # FastAPI application (462 lines)
│   │                           # - 10 REST endpoints
│   │                           # - Approval dashboard
│   │
│   ├── ui/                     # Frontend assets
│   │   ├── __init__.py
│   │   └── templates/
│   │       └── approvals.html  # Beautiful approval UI (465 lines)
│   │
│   └── tests/                  # Test suite
│       ├── __init__.py
│       ├── test_state_machine.py    # Unit tests
│       ├── test_integration.py      # Multi-agent tests (447 lines)
│       └── test_end_to_end.py       # Full workflow tests (486 lines)
│
├── demo_scenario.py            # Classic demo (pizza disaster)
├── demo_impressive.py          # Impressive demos (financial, deploy, legal)
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
├── .gitignore                  # Git exclusions
└── README.md                   # This file
```

**Code Statistics:**
- **25 Python files**
- **3,852 lines of code**
- **85%+ test coverage**
- **Production-ready quality**

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Add tests for new functionality
4. Ensure all tests pass (`python3 -m pytest saferun/tests/ -v`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

**Development Guidelines:**
- Follow existing code style (Black formatter, type hints)
- Write tests for all new features
- Update README if adding new functionality
- Keep functions focused and under 50 lines
- Add docstrings to all public functions

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Built for the **x402 Hackathon**. Special thanks to:
- The x402 team for creating the platform primitives that make this possible
- The open-source community for excellent tools and libraries (FastAPI, Pydantic, httpx)
- Anthropic for Claude API that powers intelligent agent execution

---

## 📧 Contact & Support

- **Repository**: [https://github.com/Officialhomie/SafeRun-X402](https://github.com/Officialhomie/SafeRun-X402)
- **Issues**: [GitHub Issues](https://github.com/Officialhomie/SafeRun-X402/issues)
- **Discord**: Join our community for help and discussions
- **Email**: For security issues, contact the maintainers directly

---

## 🚀 What's Next?

After completing this hackathon, SafeRun will evolve into:

1. **Production Platform**: Full deployment on x402 mainnet with real escrow and payments
2. **Agent Marketplace**: Discover and hire pre-vetted human supervisors by specialty
3. **Enterprise Features**: Team management, advanced analytics, custom workflows
4. **Framework Integrations**: Official plugins for LangChain, AutoGPT, CrewAI, etc.
5. **Mobile App**: Review and approve checkpoints on the go

**Join us in making agent autonomy safe!**

---

**SafeRun X402**: Making agent autonomy safe, one checkpoint at a time. 🛡️

**Built with ❤️ for the x402 Hackathon**
