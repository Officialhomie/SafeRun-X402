"""
Impressive Demo Scenarios for SafeRun X402

These scenarios showcase real-world complexity and demonstrate the value
of supervised agent execution in production environments.
"""

import asyncio
from loguru import logger
from datetime import datetime

from saferun.core.state_machine.orchestrator import WorkflowOrchestrator
from saferun.core.state_machine.models import (
    WorkflowConfig,
    CheckpointConfig,
    ExecutionState,
    ApprovalResponse,
    ApprovalDecision
)
from saferun.agents.executor.agent import ExecutorAgent
from saferun.agents.monitor.agent import MonitorAgent
from saferun.agents.supervisor.agent import SupervisorAgent


async def demo_financial_trade_execution():
    """
    Scenario: Automated Trading Agent

    Shows an agent about to execute a large trade, where human review
    catches a market condition the agent missed.
    """
    print("\n" + "=" * 80)
    print("SCENARIO: FINANCIAL TRADE EXECUTION")
    print("=" * 80 + "\n")

    print("📊 Context: Automated trading agent managing a $5M portfolio")
    print("🎯 Task: Execute trade based on market analysis\n")

    orchestrator = WorkflowOrchestrator()

    config = WorkflowConfig(
        name="Automated Trade Execution",
        description="AI agent analyzes market and executes trades",
        checkpoints=[
            CheckpointConfig(
                name="Review Trade Parameters",
                description="Human reviews trade before execution",
                requires_approval=True,
                can_rollback=True
            )
        ],
        escrow_amount=50000.0,  # 1% of portfolio
        poster_id="hedge_fund_xyz",
        executor_id="trading_agent_001"
    )

    execution = orchestrator.initialize_workflow(config)
    workflow_id = execution.workflow_id
    orchestrator.start_execution(workflow_id)

    print("🤖 Trading Agent: Analyzing market conditions...")
    await asyncio.sleep(1.5)
    print("✓ Analyzed 50 stocks, 200 technical indicators")
    print("✓ Sentiment analysis of 10,000 news articles")
    print("✓ Options flow data processed\n")

    print("🤖 Trading Agent: Generated trading strategy...")
    await asyncio.sleep(1)
    print("📈 Recommendation: SELL 10,000 shares of TECH-XYZ at market")
    print("   Reasoning: Detected bearish divergence + high put volume")
    print("   Expected P/L: +$125,000 (2.5% gain)\n")

    # Create checkpoint with realistic trading data
    execution_state = ExecutionState(
        checkpoint_id=config.checkpoints[0].checkpoint_id,
        agent_memory={
            "market_analysis": {
                "stock": "TECH-XYZ",
                "current_price": 150.25,
                "action": "SELL",
                "quantity": 10000,
                "expected_execution_price": 150.20,
                "estimated_pnl": 125000
            },
            "signals": {
                "technical": "BEARISH (RSI overbought, MACD bearish cross)",
                "sentiment": "NEGATIVE (news sentiment down 15%)",
                "options_flow": "BEARISH (put/call ratio 2.3:1)"
            },
            "risk_metrics": {
                "portfolio_impact": "2.5%",
                "var_95": "$180,000",
                "sharpe_impact": "+0.15"
            }
        },
        api_calls=[
            {"service": "Market Data API", "calls": 127},
            {"service": "News Sentiment API", "calls": 43},
            {"service": "Options Data API", "calls": 18}
        ],
        intermediate_outputs={
            "analysis_complete": True,
            "trade_plan_generated": True,
            "risk_check_passed": True
        },
        decision_trace=[
            "Loaded portfolio positions (15 stocks, $5M total)",
            "Analyzed TECH-XYZ technical indicators - BEARISH signal",
            "Checked news sentiment - NEGATIVE trend detected",
            "Reviewed options flow - High put volume (bearish)",
            "Calculated optimal position size: 10,000 shares",
            "Risk check: Within parameters (2.5% portfolio)",
            "Decision: SELL 10,000 shares at market"
        ],
        resource_consumption={
            "api_calls": 188,
            "data_processed_mb": 45.2,
            "analysis_time_sec": 12.3
        }
    )

    snapshot = orchestrator.create_checkpoint(workflow_id, execution_state)

    print("⏸️  SafeRun: Checkpoint reached - requesting human approval\n")

    request = orchestrator.request_approval(
        workflow_id,
        snapshot.snapshot_id,
        "Review trade execution before submitting to market",
        {
            "trade": execution_state.agent_memory["market_analysis"],
            "signals": execution_state.agent_memory["signals"]
        }
    )

    supervisor = SupervisorAgent(supervisor_id="portfolio_manager_alice")
    approval_request = supervisor.create_approval_request(
        workflow_id=workflow_id,
        checkpoint_id=config.checkpoints[0].checkpoint_id,
        snapshot_id=snapshot.snapshot_id,
        execution_state=execution_state
    )

    # Display to human
    print("┌" + "─" * 78 + "┐")
    print("│" + " " * 20 + "TRADE APPROVAL REQUIRED" + " " * 35 + "│")
    print("├" + "─" * 78 + "┤")
    print("│ Stock: TECH-XYZ" + " " * 63 + "│")
    print("│ Action: SELL 10,000 shares @ $150.20" + " " * 41 + "│")
    print("│ Expected P/L: +$125,000 (2.5% gain)" + " " * 43 + "│")
    print("│" + " " * 78 + "│")
    print("│ Agent Reasoning:" + " " * 61 + "│")
    print("│   • Bearish technical divergence (RSI + MACD)" + " " * 33 + "│")
    print("│   • Negative news sentiment (-15%)" + " " * 45 + "│")
    print("│   • High put volume (bearish options flow)" + " " * 37 + "│")
    print("│" + " " * 78 + "│")
    print("│ Risk Check: ✓ PASSED" + " " * 57 + "│")
    print("└" + "─" * 78 + "┘\n")

    await asyncio.sleep(2)

    print("👤 HUMAN PORTFOLIO MANAGER (Alice):")
    print("   'Wait... let me check something...'\n")

    await asyncio.sleep(1.5)

    print("👤 Alice: 'I see the bearish indicators, BUT...'")
    print("   'There's an earnings call scheduled in 2 hours'")
    print("   'If we sell now and earnings are positive, we'll miss the pop'")
    print("   'The agent didn't factor in the earnings calendar!'\n")

    await asyncio.sleep(1)

    print("👤 Alice Decision: MODIFY THE TRADE")
    print("   'Change to: SELL 5,000 shares (hedge 50%), hold 5,000 shares'")
    print("   'This way we're protected if earnings are bad, but can benefit if good'\n")

    # Human modifies the trade
    response = supervisor.submit_decision(
        request_id=approval_request.request_id,
        decision=ApprovalDecision.MODIFIED,
        rationale="Agent missed upcoming earnings call. Reduce position to hedge risk while maintaining upside exposure.",
        approved_by="portfolio_manager_alice",
        modifications={
            "market_analysis": {
                "stock": "TECH-XYZ",
                "current_price": 150.25,
                "action": "SELL",
                "quantity": 5000,  # Changed from 10,000
                "expected_execution_price": 150.20,
                "estimated_pnl": 62500,  # Half of original
                "strategy": "PARTIAL_HEDGE"
            }
        }
    )

    orchestrator.submit_approval(workflow_id, response)

    print("🤖 Trading Agent: Modifications received and applied")
    print("✓ Updated trade: SELL 5,000 shares (50% position)")
    print("✓ Executing modified trade...\n")

    await asyncio.sleep(1.5)

    print("💼 TRADE EXECUTED:")
    print("   Sold: 5,000 shares @ $150.18")
    print("   P/L: +$62,400")
    print("   Remaining position: 5,000 shares\n")

    await asyncio.sleep(1)

    print("📢 TWO HOURS LATER: Earnings announced - BEAT EXPECTATIONS!")
    print("📈 TECH-XYZ jumps to $157.50 (+4.8%)\n")

    await asyncio.sleep(1)

    print("💰 FINAL OUTCOME:")
    print("   Sold 5,000 @ $150.18: +$62,400")
    print("   Holding 5,000 @ $157.50: +$36,250 unrealized")
    print("   TOTAL GAIN: +$98,650\n")

    orchestrator.settle_workflow(workflow_id, {"completion": "100%"})
    orchestrator.complete_workflow(workflow_id)

    print("✅ RESULT: SUCCESS!")
    print("   If agent had sold all 10,000 shares: +$62,500 (missed $36,250 gain)")
    print("   With human supervision: +$98,650 total")
    print("   Human oversight added: +$36,150 (58% improvement!)")
    print("\n" + "🛡️  SafeRun prevented suboptimal execution and maximized returns" + "\n")


async def demo_code_deployment_prevention():
    """
    Scenario: Automated Code Deployment

    Shows an agent about to deploy breaking changes, where human code
    review catches issues the automated tests missed.
    """
    print("\n" + "=" * 80)
    print("SCENARIO: AUTOMATED CODE DEPLOYMENT")
    print("=" * 80 + "\n")

    print("⚙️  Context: DevOps AI agent managing production deployments")
    print("🎯 Task: Deploy new microservice version to production\n")

    orchestrator = WorkflowOrchestrator()

    config = WorkflowConfig(
        name="Production Deployment",
        description="AI agent deploys code after automated testing",
        checkpoints=[
            CheckpointConfig(
                name="Review Deployment Changes",
                description="Human reviews diff before production push",
                requires_approval=True,
                can_rollback=True
            )
        ],
        escrow_amount=1000.0,
        poster_id="engineering_team",
        executor_id="devops_agent_002"
    )

    execution = orchestrator.initialize_workflow(config)
    workflow_id = execution.workflow_id
    orchestrator.start_execution(workflow_id)

    print("🤖 DevOps Agent: Running deployment checks...")
    await asyncio.sleep(1)
    print("✓ Unit tests: 487/487 PASSED")
    print("✓ Integration tests: 124/124 PASSED")
    print("✓ Code coverage: 89% (threshold: 80%)")
    print("✓ Security scan: No vulnerabilities")
    print("✓ Performance benchmarks: Within SLA\n")

    print("🤖 DevOps Agent: Preparing deployment...")
    await asyncio.sleep(1)
    print("📦 Building Docker image: api-service:v2.4.0")
    print("🔍 Diff detected: 23 files changed, +847 lines, -234 lines")
    print("🎯 Target: production-cluster-us-east\n")

    # Create checkpoint
    execution_state = ExecutionState(
        checkpoint_id=config.checkpoints[0].checkpoint_id,
        agent_memory={
            "deployment": {
                "service": "api-service",
                "version": "v2.4.0",
                "environment": "production",
                "cluster": "us-east",
                "instances": 12,
                "strategy": "rolling_update"
            },
            "changes": {
                "files_changed": 23,
                "lines_added": 847,
                "lines_removed": 234,
                "key_changes": [
                    "Updated database query optimization",
                    "Added new caching layer (Redis)",
                    "Refactored authentication middleware",
                    "Updated API rate limiting"
                ]
            },
            "test_results": {
                "unit_tests": "487/487 PASSED",
                "integration_tests": "124/124 PASSED",
                "coverage": "89%",
                "security_scan": "CLEAN",
                "performance": "WITHIN_SLA"
            }
        },
        decision_trace=[
            "Detected new commit on main branch: abc123",
            "Ran full test suite - ALL PASSED",
            "Built Docker image: api-service:v2.4.0",
            "Verified image security scan - CLEAN",
            "Generated deployment manifest",
            "Decision: READY FOR PRODUCTION DEPLOYMENT"
        ],
        intermediate_outputs={
            "docker_image": "registry.company.com/api-service:v2.4.0",
            "deployment_manifest": "k8s-manifests/production/api-service.yaml"
        },
        resource_consumption={
            "build_time_sec": 127,
            "test_time_sec": 89
        }
    )

    snapshot = orchestrator.create_checkpoint(workflow_id, execution_state)

    print("⏸️  SafeRun: Checkpoint reached - requesting deployment approval\n")

    request = orchestrator.request_approval(
        workflow_id,
        snapshot.snapshot_id,
        "Review code changes before production deployment",
        execution_state.agent_memory
    )

    supervisor = SupervisorAgent(supervisor_id="senior_engineer_bob")

    print("┌" + "─" * 78 + "┐")
    print("│" + " " * 23 + "DEPLOYMENT APPROVAL REQUIRED" + " " * 27 + "│")
    print("├" + "─" * 78 + "┤")
    print("│ Service: api-service v2.4.0 → production-cluster-us-east" + " " * 18 + "│")
    print("│ Changes: 23 files, +847/-234 lines" + " " * 43 + "│")
    print("│" + " " * 78 + "│")
    print("│ All Tests: ✓ PASSED" + " " * 57 + "│")
    print("│ Security: ✓ CLEAN" + " " * 59 + "│")
    print("│ Performance: ✓ WITHIN SLA" + " " * 51 + "│")
    print("│" + " " * 78 + "│")
    print("│ Key Changes:" + " " * 65 + "│")
    print("│   • Database query optimization" + " " * 47 + "│")
    print("│   • New Redis caching layer" + " " * 50 + "│")
    print("│   • Refactored auth middleware" + " " * 47 + "│")
    print("│   • Updated rate limiting" + " " * 53 + "│")
    print("└" + "─" * 78 + "┘\n")

    await asyncio.sleep(2)

    print("👤 SENIOR ENGINEER (Bob): 'Let me review the diff...'\n")
    await asyncio.sleep(2)

    print("👤 Bob: 'Wait a second...'")
    print("   Looking at the auth middleware refactor...")
    print("   Line 247: if (user.role == 'admin') {...}\n")

    await asyncio.sleep(1)

    print("👤 Bob: 'This looks wrong!'")
    print("   'The refactor changed == to === in JavaScript'")
    print("   'But JavaScript type coercion means this could break admin access!'")
    print("   'The tests passed because test users have role as string'")
    print("   'But production DB has some role as NUMBER for legacy reasons'\n")

    await asyncio.sleep(1)

    print("👤 Bob: '🚨 THIS WOULD LOCK OUT ALL ADMIN USERS IN PRODUCTION! 🚨'\n")

    await asyncio.sleep(1)

    print("👤 Bob Decision: REJECT DEPLOYMENT")
    print("   'Cannot deploy - critical auth bug that tests didn't catch'")
    print("   'Need to fix type handling in auth middleware first'\n")

    # Human rejects
    approval_request = supervisor.create_approval_request(
        workflow_id=workflow_id,
        checkpoint_id=config.checkpoints[0].checkpoint_id,
        snapshot_id=snapshot.snapshot_id,
        execution_state=execution_state
    )

    response = supervisor.submit_decision(
        request_id=approval_request.request_id,
        decision=ApprovalDecision.REJECTED,
        rationale="Critical auth bug detected in refactored middleware. Type coercion issue would lock out all admin users. Must fix before deployment.",
        approved_by="senior_engineer_bob"
    )

    orchestrator.submit_approval(workflow_id, response)

    print("🔄 SafeRun: Deployment REJECTED - initiating rollback...")
    await asyncio.sleep(1)
    print("✓ Deployment cancelled")
    print("✓ Docker image tagged as DO_NOT_DEPLOY")
    print("✓ Ticket created: FIX-AUTH-TYPE-BUG")
    print("✓ Team notified\n")

    orchestrator.complete_rollback(workflow_id, success=True)

    print("✅ RESULT: DISASTER AVERTED!")
    print("   What would have happened without human review:")
    print("     • All admin users locked out of production")
    print("     • Emergency rollback required")
    print("     • 30-60 min downtime")
    print("     • Customer impact: HIGH")
    print("     • Revenue loss: ~$50,000")
    print("\n   With SafeRun supervised execution:")
    print("     • Bug caught before deployment")
    print("     • Zero downtime")
    print("     • Zero customer impact")
    print("     • Saved: $50,000 + reputation damage")
    print("\n" + "🛡️  SafeRun prevented production incident through human code review" + "\n")


async def demo_research_workflow_quality():
    """
    Scenario: AI Research Assistant

    Shows an agent conducting research where human domain expertise
    identifies better sources and catches factual errors.
    """
    print("\n" + "=" * 80)
    print("SCENARIO: AI RESEARCH ASSISTANT")
    print("=" * 80 + "\n")

    print("📚 Context: Legal AI assistant researching case law precedents")
    print("🎯 Task: Find relevant precedents for upcoming trial\n")

    orchestrator = WorkflowOrchestrator()

    config = WorkflowConfig(
        name="Legal Research",
        description="AI conducts legal research for litigation",
        checkpoints=[
            CheckpointConfig(
                name="Review Research Findings",
                description="Attorney reviews sources and conclusions",
                requires_approval=True
            )
        ],
        escrow_amount=500.0,
        poster_id="law_firm_johnson_associates",
        executor_id="legal_research_agent_003"
    )

    execution = orchestrator.initialize_workflow(config)
    workflow_id = execution.workflow_id
    orchestrator.start_execution(workflow_id)

    print("🤖 Research Agent: Analyzing case requirements...")
    await asyncio.sleep(1)
    print("✓ Issue: Contract dispute - material breach definition")
    print("✓ Jurisdiction: California state courts")
    print("✓ Searched: 847 cases, 234 relevant matches\n")

    print("🤖 Research Agent: Compiled precedents...")
    await asyncio.sleep(1.5)

    # Create checkpoint
    execution_state = ExecutionState(
        checkpoint_id=config.checkpoints[0].checkpoint_id,
        agent_memory={
            "research_topic": "Material breach in California contract law",
            "key_findings": [
                {
                    "case": "Smith v. Johnson (2018)",
                    "citation": "123 Cal.App.4th 456",
                    "relevance": "Defines material breach threshold",
                    "quote": "A material breach must substantially deprive the non-breaching party of expected benefits"
                },
                {
                    "case": "TechCorp v. StartupXYZ (2020)",
                    "citation": "145 Cal.App.5th 789",
                    "relevance": "Recent case on tech contracts",
                    "quote": "Delay in delivery constitutes material breach if time is of essence"
                },
                {
                    "case": "Anderson v. Wilson (2015)",
                    "citation": "201 Cal.App.4th 123",
                    "relevance": "Burden of proof standard",
                    "quote": "Plaintiff must demonstrate actual damages from breach"
                }
            ],
            "conclusion": "Strong precedent for material breach claim. Recommend proceeding with litigation based on TechCorp precedent."
        },
        decision_trace=[
            "Identified case issue: Material breach in contract dispute",
            "Searched California appellate databases",
            "Found 847 potentially relevant cases",
            "Filtered to 234 cases with material breach analysis",
            "Selected top 3 most relevant precedents",
            "Analyzed holdings and applicability",
            "Generated recommendation"
        ]
    )

    snapshot = orchestrator.create_checkpoint(workflow_id, execution_state)

    print("📋 RESEARCH SUMMARY:")
    print("   Found 3 strong precedents:")
    print("   1. Smith v. Johnson (2018) - Material breach definition")
    print("   2. TechCorp v. StartupXYZ (2020) - Tech contract delays")
    print("   3. Anderson v. Wilson (2015) - Burden of proof\n")

    print("⏸️  SafeRun: Checkpoint - requesting attorney review\n")

    await asyncio.sleep(2)

    print("👤 SENIOR ATTORNEY (Carol):")
    print("   'Let me verify these citations...'\n")

    await asyncio.sleep(2)

    print("👤 Carol: 'Hmm, something's off here...'")
    print("   'Smith v. Johnson (2018) - checking Westlaw...'")
    print("   'This case EXISTS but...'")
    print("   'It was OVERTURNED by the California Supreme Court in 2019!'")
    print("   'We absolutely CANNOT cite an overturned case!'\n")

    await asyncio.sleep(1)

    print("👤 Carol: 'And TechCorp v. StartupXYZ (2020)...'")
    print("   'This is a FEDERAL case, not California state law'")
    print("   'Different standards apply - could hurt our argument'\n")

    await asyncio.sleep(1)

    print("👤 Carol: 'Let me search for better precedents...'")
    await asyncio.sleep(1.5)
    print("   'Here: Martinez v. Brown (2021) - California Supreme Court'")
    print("   'This is binding precedent and directly on point'")
    print("   'Much stronger than what the AI found'\n")

    print("👤 Carol Decision: MODIFY RESEARCH")
    print("   'Remove overturned and federal cases'")
    print("   'Add Martinez v. Brown as primary precedent'")
    print("   'Keep Anderson v. Wilson - that one's solid'\n")

    supervisor = SupervisorAgent(supervisor_id="attorney_carol")
    approval_request = supervisor.create_approval_request(
        workflow_id=workflow_id,
        checkpoint_id=config.checkpoints[0].checkpoint_id,
        snapshot_id=snapshot.snapshot_id,
        execution_state=execution_state
    )

    response = supervisor.submit_decision(
        request_id=approval_request.request_id,
        decision=ApprovalDecision.MODIFIED,
        rationale="AI cited overturned case and federal case. Replaced with stronger California Supreme Court precedent (Martinez v. Brown 2021).",
        approved_by="attorney_carol",
        modifications={
            "key_findings": [
                {
                    "case": "Martinez v. Brown (2021)",
                    "citation": "11 Cal.5th 234",
                    "relevance": "California Supreme Court - Binding precedent on material breach",
                    "quote": "Material breach determined by substantial impairment of contract value"
                },
                {
                    "case": "Anderson v. Wilson (2015)",
                    "citation": "201 Cal.App.4th 123",
                    "relevance": "Burden of proof standard - still good law",
                    "quote": "Plaintiff must demonstrate actual damages from breach"
                }
            ]
        }
    )

    orchestrator.submit_approval(workflow_id, response)

    print("✅ FINAL RESEARCH (After Human Review):")
    print("   1. Martinez v. Brown (2021) - CA Supreme Court ⭐ PRIMARY")
    print("   2. Anderson v. Wilson (2015) - Still good law ✓\n")

    orchestrator.settle_workflow(workflow_id, {"completion": "100%"})
    orchestrator.complete_workflow(workflow_id)

    print("✅ RESULT: RESEARCH QUALITY DRAMATICALLY IMPROVED!")
    print("   Without human review:")
    print("     • Cited overturned case (malpractice risk)")
    print("     • Cited federal case (wrong jurisdiction)")
    print("     • Weak argument foundation")
    print("\n   With SafeRun supervised research:")
    print("     • Strong California Supreme Court precedent")
    print("     • Verified all citations current and applicable")
    print("     • Professional-grade legal work")
    print("\n" + "🛡️  SafeRun ensured research quality through expert human review" + "\n")


async def main():
    """Run all impressive demo scenarios"""
    print("\n")
    print("=" * 80)
    print("          SafeRun X402 - Real-World Supervised Execution Demos")
    print("=" * 80)

    await demo_financial_trade_execution()
    await asyncio.sleep(2)

    await demo_code_deployment_prevention()
    await asyncio.sleep(2)

    await demo_research_workflow_quality()

    print("\n" + "=" * 80)
    print("All demos complete!")
    print("\nKey Takeaway: SafeRun prevents disasters across multiple domains:")
    print("  • Financial: Optimized $36K additional returns (58% improvement)")
    print("  • Engineering: Prevented $50K+ loss from production incident")
    print("  • Legal: Prevented malpractice from citing overturned case")
    print("\n🛡️  Supervised autonomy: Agents work fast, humans ensure quality")
    print("=" * 80)
    print("\n")


if __name__ == "__main__":
    # Configure logging for clean output
    logger.remove()
    logger.add(lambda msg: None)

    # Run demos
    asyncio.run(main())
