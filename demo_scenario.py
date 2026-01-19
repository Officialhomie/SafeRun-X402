"""
Demo Scenario: Meeting Room Booking with SafeRun

This demonstrates the core value proposition:
- Agent books meeting room, orders catering, sends invites
- Without SafeRun: Agent orders 100 pizzas instead of 10 (disaster!)
- With SafeRun: Human reviews catering order before confirmation
"""

import asyncio
from loguru import logger

from saferun.core.state_machine.orchestrator import WorkflowOrchestrator
from saferun.core.state_machine.models import (
    WorkflowConfig,
    CheckpointConfig,
    ExecutionState,
    ApprovalResponse,
    ApprovalDecision
)
from saferun.api.x402.client import X402Integration
from saferun.agents.executor.agent import ExecutorAgent
from saferun.agents.monitor.agent import MonitorAgent
from saferun.agents.supervisor.agent import SupervisorAgent


async def demo_disaster_scenario():
    """Show what happens WITHOUT SafeRun"""
    print("\n" + "=" * 70)
    print("SCENARIO 1: WITHOUT SAFERUN (The Disaster)")
    print("=" * 70 + "\n")

    print("🤖 Agent: Booking meeting room...")
    await asyncio.sleep(1)
    print("✓ Agent: Room 401 booked for 10 people\n")

    print("🤖 Agent: Ordering catering...")
    await asyncio.sleep(1)
    print("⚠️  Agent: Ordered 100 pizzas (MISTAKE!)")
    print("💳 Agent: Payment confirmed: $1,200\n")

    print("🤖 Agent: Sending calendar invites...")
    await asyncio.sleep(1)
    print("✓ Agent: Invites sent\n")

    print("😱 Human: Wait... 100 PIZZAS?! We only needed 10!")
    print("😱 Human: It's already paid and confirmed...")
    print("😱 Human: *stares at 100 pizzas arriving*\n")

    print("💥 RESULT: Disaster! Money wasted, massive cleanup needed.")
    print("\n")


async def demo_supervised_scenario():
    """Show what happens WITH SafeRun"""
    print("\n" + "=" * 70)
    print("SCENARIO 2: WITH SAFERUN (The Success)")
    print("=" * 70 + "\n")

    # Initialize SafeRun components (real x402 integration required)
    x402 = X402Integration()
    orchestrator = WorkflowOrchestrator(x402_integration=x402)

    # Create workflow with checkpoints
    config = WorkflowConfig(
        name="Meeting Room Booking",
        description="Book room, order catering, send invites",
        checkpoints=[
            CheckpointConfig(
                name="Review Catering Order",
                description="Human reviews catering before confirmation",
                requires_approval=True
            )
        ],
        escrow_amount=100.0,
        poster_id="user_123",
        executor_id="agent_456"
    )

    execution = orchestrator.initialize_workflow(config)
    workflow_id = execution.workflow_id

    # Create agents
    executor = ExecutorAgent(agent_id="agent_456")
    supervisor = SupervisorAgent(supervisor_id="supervisor_789")

    print("🤖 Agent: Booking meeting room...")
    await asyncio.sleep(1)
    print("✓ Agent: Room 401 booked for 10 people\n")

    # Start execution
    orchestrator.start_execution(workflow_id)

    print("🤖 Agent: Planning catering order...")
    await asyncio.sleep(1)
    print("🤖 Agent: Reached checkpoint - catering order ready for review\n")

    # Create checkpoint
    execution_state = ExecutionState(
        checkpoint_id=config.checkpoints[0].checkpoint_id,
        agent_memory={
            "meeting_room": "Room 401",
            "attendees": 10,
            "catering_plan": {
                "pizzas": 100,  # The mistake!
                "drinks": 10,
                "estimated_cost": "$1,200"
            }
        },
        intermediate_outputs={
            "room_booked": True,
            "catering_planned": True
        },
        decision_trace=[
            "Booked Room 401",
            "Calculated catering: 10 attendees",
            "Decided to order 100 pizzas"  # Error in calculation
        ]
    )

    snapshot = await orchestrator.create_checkpoint(workflow_id, execution_state)

    # Request approval
    request = orchestrator.request_approval(
        workflow_id,
        snapshot.snapshot_id,
        "Review catering order before confirmation",
        {"catering": execution_state.agent_memory["catering_plan"]}
    )

    # Supervisor presents for approval
    approval_request = supervisor.create_approval_request(
        workflow_id=workflow_id,
        checkpoint_id=config.checkpoints[0].checkpoint_id,
        snapshot_id=snapshot.snapshot_id,
        execution_state=execution_state
    )

    display = supervisor.format_for_display(approval_request)

    print("👤 HUMAN REVIEW INTERFACE")
    print("-" * 70)
    print(f"📋 Summary: {display['summary']}")
    print("\n🍕 Catering Order:")
    print(f"   - Pizzas: 100")
    print(f"   - Drinks: 10")
    print(f"   - Cost: $1,200")
    print("\n⚠️  Alert: This seems like too many pizzas for 10 people!")
    print("\nDecision options:")
    print("  [1] ✓ Approve")
    print("  [2] ✎ Approve with modifications")
    print("  [3] ✗ Reject\n")

    # Human catches the error!
    print("👤 Human: Wait, 100 pizzas for 10 people? That's wrong!")
    print("👤 Human: I'll approve with modification - change to 10 pizzas\n")

    # Submit modified approval
    response = supervisor.submit_decision(
        request_id=approval_request.request_id,
        decision=ApprovalDecision.MODIFIED,
        rationale="Changed pizza count from 100 to 10 for 10 attendees",
        approved_by="user_123",
        modifications={
            "catering_plan": {
                "pizzas": 10,  # Corrected!
                "drinks": 10,
                "estimated_cost": "$120"
            }
        }
    )

    # Apply modifications and continue
    orchestrator.submit_approval(workflow_id, response)
    await x402.close()

    print("🤖 Agent: Modifications applied, continuing...")
    print("🤖 Agent: Ordering catering with corrected quantities...")
    await asyncio.sleep(1)
    print("✓ Agent: Ordered 10 pizzas - $120")
    print("💳 Agent: Payment confirmed\n")

    print("🤖 Agent: Sending calendar invites...")
    await asyncio.sleep(1)
    print("✓ Agent: Invites sent\n")

    # Complete workflow
    orchestrator.settle_workflow(workflow_id, {"completion": "100%"})
    orchestrator.complete_workflow(workflow_id)

    print("✅ RESULT: Success! Human caught error, workflow completed correctly.")
    print("💰 Saved: $1,080 (avoided ordering 90 extra pizzas)")
    print("\n")


async def demo_rollback_scenario():
    """Show rollback capability"""
    print("\n" + "=" * 70)
    print("SCENARIO 3: ROLLBACK DEMO")
    print("=" * 70 + "\n")

    x402 = X402Integration()
    orchestrator = WorkflowOrchestrator(x402_integration=x402)

    config = WorkflowConfig(
        name="Financial Transaction",
        description="Multi-step financial workflow",
        checkpoints=[
            CheckpointConfig(
                name="Review Transaction",
                description="Review before executing",
                requires_approval=True,
                can_rollback=True
            )
        ],
        escrow_amount=1000.0,
        poster_id="user_123",
        executor_id="agent_456"
    )

    execution = orchestrator.initialize_workflow(config)
    workflow_id = execution.workflow_id

    print("🤖 Agent: Preparing financial transaction...")
    await asyncio.sleep(1)
    print("🤖 Agent: Amount: $10,000 to Account XYZ\n")

    orchestrator.start_execution(workflow_id)

    # Create checkpoint
    execution_state = ExecutionState(
        checkpoint_id=config.checkpoints[0].checkpoint_id,
        agent_memory={
            "transaction": {
                "amount": 10000,
                "to_account": "XYZ",
                "from_account": "ABC"
            }
        },
        api_calls=[
            {
                "call_id": "call_1",
                "description": "Initiated transfer",
                "has_side_effects": True
            }
        ]
    )

    snapshot = await orchestrator.create_checkpoint(workflow_id, execution_state)

    request = orchestrator.request_approval(
        workflow_id,
        snapshot.snapshot_id,
        "Review $10,000 transaction",
        {"transaction": execution_state.agent_memory["transaction"]}
    )

    print("👤 HUMAN REVIEW")
    print("-" * 70)
    print("💰 Transaction: $10,000 to Account XYZ")
    print("\n⚠️  Alert: This account is flagged as suspicious!")
    print("\n👤 Human: This doesn't look right - REJECTING\n")

    supervisor = SupervisorAgent(supervisor_id="supervisor_789")
    approval_request = supervisor.create_approval_request(
        workflow_id=workflow_id,
        checkpoint_id=config.checkpoints[0].checkpoint_id,
        snapshot_id=snapshot.snapshot_id,
        execution_state=execution_state
    )

    # Human rejects
    response = supervisor.submit_decision(
        request_id=approval_request.request_id,
        decision=ApprovalDecision.REJECTED,
        rationale="Suspicious account - rejecting transaction",
        approved_by="user_123"
    )

    orchestrator.submit_approval(workflow_id, response)

    print("🔄 SafeRun: Approval rejected, initiating rollback...")
    await asyncio.sleep(1)
    print("🔄 SafeRun: Reversing transaction...")
    await asyncio.sleep(1)
    print("🔄 SafeRun: Restoring state to checkpoint...")
    await asyncio.sleep(1)

    orchestrator.complete_rollback(workflow_id, success=True)
    await x402.close()

    print("✓ SafeRun: Rollback complete - no money transferred\n")

    print("✅ RESULT: Transaction prevented, state rolled back safely.")
    print("🛡️  Disaster averted through supervised execution!\n")


async def main():
    """Run all demo scenarios"""
    print("\n")
    print("=" * 70)
    print("           SafeRun X402 - Supervised Agent Execution Demo")
    print("=" * 70)

    # Run scenarios
    await demo_disaster_scenario()
    await demo_supervised_scenario()
    await demo_rollback_scenario()

    print("=" * 70)
    print("Demo complete! SafeRun enables safe agent autonomy with human oversight.")
    print("=" * 70)
    print("\n")


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(lambda msg: None)  # Suppress logs for cleaner demo output

    # Run demo
    asyncio.run(main())
