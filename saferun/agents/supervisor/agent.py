"""
Supervisor Agent

This agent presents checkpoint state to humans for approval,
collects decisions, and routes them back to the orchestrator.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from saferun.core.state_machine.models import (
    ApprovalRequest,
    ApprovalResponse,
    ApprovalDecision,
    ExecutionState
)


class SupervisorAgent:
    """
    Agent that interfaces between the system and human supervisors.

    Responsibilities:
    - Present checkpoint state with clear context
    - Collect approval decisions with rationale
    - Route decisions back to orchestrator
    - Maintain approval audit trail
    """

    def __init__(self, supervisor_id: str):
        self.supervisor_id = supervisor_id
        self.pending_approvals: Dict[str, ApprovalRequest] = {}
        self.approval_history: List[ApprovalResponse] = []
        logger.info(f"SupervisorAgent {supervisor_id} initialized")

    def create_approval_request(
        self,
        workflow_id: str,
        checkpoint_id: str,
        snapshot_id: str,
        execution_state: ExecutionState,
        monitoring_report: Optional[Dict[str, Any]] = None
    ) -> ApprovalRequest:
        """
        Create an approval request for human review.

        This generates a human-readable summary and packages the context
        needed for decision-making.

        Args:
            workflow_id: Workflow being executed
            checkpoint_id: Checkpoint requiring approval
            snapshot_id: Snapshot ID for this checkpoint
            execution_state: Current execution state
            monitoring_report: Optional monitoring data

        Returns:
            ApprovalRequest ready to present to human
        """
        logger.info(f"Creating approval request for checkpoint {checkpoint_id}")

        # Generate human-readable summary
        summary = self._generate_summary(execution_state, monitoring_report)

        # Package context for decision
        context = self._package_context(execution_state, monitoring_report)

        request = ApprovalRequest(
            workflow_id=workflow_id,
            checkpoint_id=checkpoint_id,
            snapshot_id=snapshot_id,
            summary=summary,
            context=context
        )

        self.pending_approvals[request.request_id] = request

        logger.info(f"Approval request created: {request.request_id}")
        return request

    def _generate_summary(
        self,
        execution_state: ExecutionState,
        monitoring_report: Optional[Dict[str, Any]]
    ) -> str:
        """
        Generate human-readable summary of what needs approval.

        This is critical UX - humans need to quickly understand:
        1. What the agent did
        2. What decision is needed
        3. Why it requires approval
        """
        summary_parts = []

        # What was done
        summary_parts.append(
            f"Agent completed {len(execution_state.api_calls)} actions "
            f"with {len(execution_state.decision_trace)} decisions"
        )

        # Key outputs
        if execution_state.intermediate_outputs:
            outputs_summary = ", ".join(execution_state.intermediate_outputs.keys())
            summary_parts.append(f"Generated outputs: {outputs_summary}")

        # Anomalies/issues
        if monitoring_report and monitoring_report.get("anomalies"):
            anomaly_count = len(monitoring_report["anomalies"])
            summary_parts.append(f"⚠️ {anomaly_count} anomalies detected")

        # Resource usage
        resource_usage = execution_state.resource_consumption
        if resource_usage:
            summary_parts.append(
                f"Resources: {resource_usage.get('api_calls', 0)} API calls, "
                f"{resource_usage.get('tokens_used', 0)} tokens"
            )

        return " | ".join(summary_parts)

    def _package_context(
        self,
        execution_state: ExecutionState,
        monitoring_report: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Package all context needed for approval decision.

        This includes:
        - Recent decisions
        - Outputs produced
        - API calls made
        - Monitoring alerts
        - Recommendations
        """
        context = {
            "execution_summary": {
                "api_calls_count": len(execution_state.api_calls),
                "decisions_count": len(execution_state.decision_trace),
                "outputs_count": len(execution_state.intermediate_outputs),
                "timestamp": execution_state.timestamp.isoformat()
            },
            "recent_decisions": execution_state.decision_trace[-5:],  # Last 5
            "intermediate_outputs": execution_state.intermediate_outputs,
            "resource_consumption": execution_state.resource_consumption
        }

        # Add recent API calls with details
        context["recent_api_calls"] = [
            {
                "description": call.get("description", "Unknown"),
                "has_side_effects": call.get("has_side_effects", False),
                "timestamp": call.get("timestamp", "Unknown")
            }
            for call in execution_state.api_calls[-5:]  # Last 5
        ]

        # Add monitoring data if available
        if monitoring_report:
            context["monitoring"] = {
                "anomalies": monitoring_report.get("anomalies", []),
                "recommendations": monitoring_report.get("recommendations", []),
                "on_track": monitoring_report.get("on_track", True)
            }

        return context

    def format_for_display(self, request: ApprovalRequest) -> Dict[str, Any]:
        """
        Format approval request for human-friendly display.

        This would be used by the UI to render the approval interface.

        Returns:
            Display-ready data structure
        """
        display = {
            "request_id": request.request_id,
            "workflow_id": request.workflow_id,
            "checkpoint_id": request.checkpoint_id,
            "created_at": request.created_at.isoformat(),
            "summary": request.summary,
            "sections": []
        }

        # Section 1: Executive Summary
        display["sections"].append({
            "title": "Summary",
            "content": request.summary,
            "type": "text"
        })

        # Section 2: Recent Actions
        recent_calls = request.context.get("recent_api_calls", [])
        if recent_calls:
            display["sections"].append({
                "title": "Recent Actions",
                "content": recent_calls,
                "type": "list"
            })

        # Section 3: Outputs
        outputs = request.context.get("intermediate_outputs", {})
        if outputs:
            display["sections"].append({
                "title": "Outputs Generated",
                "content": outputs,
                "type": "json"
            })

        # Section 4: Alerts (if any)
        monitoring = request.context.get("monitoring", {})
        anomalies = monitoring.get("anomalies", [])
        if anomalies:
            display["sections"].append({
                "title": "⚠️ Alerts",
                "content": anomalies,
                "type": "alerts",
                "severity": "warning"
            })

        # Section 5: Recommendations
        recommendations = monitoring.get("recommendations", [])
        if recommendations:
            display["sections"].append({
                "title": "Recommendations",
                "content": recommendations,
                "type": "list"
            })

        # Section 6: Decision Options
        display["sections"].append({
            "title": "Decision Required",
            "content": {
                "options": [
                    {
                        "value": "APPROVED",
                        "label": "✓ Approve - Continue execution",
                        "color": "green"
                    },
                    {
                        "value": "MODIFIED",
                        "label": "✎ Approve with modifications",
                        "color": "yellow"
                    },
                    {
                        "value": "REJECTED",
                        "label": "✗ Reject - Rollback",
                        "color": "red"
                    }
                ]
            },
            "type": "decision"
        })

        return display

    def submit_decision(
        self,
        request_id: str,
        decision: ApprovalDecision,
        rationale: str,
        approved_by: str,
        modifications: Optional[Dict[str, Any]] = None
    ) -> ApprovalResponse:
        """
        Submit approval decision from human supervisor.

        Args:
            request_id: ID of the approval request
            decision: Approval decision (APPROVED/REJECTED/MODIFIED)
            rationale: Human explanation of decision
            approved_by: ID of human who made decision
            modifications: Optional modifications to apply

        Returns:
            ApprovalResponse to route back to orchestrator
        """
        logger.info(f"Submitting decision for request {request_id}: {decision}")

        # Validate request exists
        if request_id not in self.pending_approvals:
            raise ValueError(f"Request {request_id} not found")

        response = ApprovalResponse(
            request_id=request_id,
            decision=decision,
            rationale=rationale,
            modifications=modifications,
            approved_by=approved_by
        )

        # Move from pending to history
        del self.pending_approvals[request_id]
        self.approval_history.append(response)

        logger.info(
            f"Decision submitted: {decision} by {approved_by} - "
            f"{len(self.pending_approvals)} pending approvals remaining"
        )

        return response

    def get_pending_approvals(self) -> List[ApprovalRequest]:
        """Get all pending approval requests"""
        return list(self.pending_approvals.values())

    def get_approval_history(self) -> List[ApprovalResponse]:
        """Get history of all approval decisions"""
        return self.approval_history

    def get_approval_stats(self) -> Dict[str, Any]:
        """Get statistics about approvals"""
        total_approvals = len(self.approval_history)

        if total_approvals == 0:
            return {
                "supervisor_id": self.supervisor_id,
                "total_approvals": 0,
                "message": "No approvals processed yet"
            }

        decisions = [r.decision for r in self.approval_history]

        stats = {
            "supervisor_id": self.supervisor_id,
            "total_approvals": total_approvals,
            "pending": len(self.pending_approvals),
            "decision_breakdown": {
                "approved": decisions.count(ApprovalDecision.APPROVED),
                "rejected": decisions.count(ApprovalDecision.REJECTED),
                "modified": decisions.count(ApprovalDecision.MODIFIED)
            },
            "approval_rate": decisions.count(ApprovalDecision.APPROVED) / total_approvals,
            "average_response_time": self._calculate_avg_response_time()
        }

        return stats

    def _calculate_avg_response_time(self) -> float:
        """Calculate average time to respond to approvals"""
        # Mock implementation
        # In real system, would track request creation time vs response time
        return 120.0  # seconds
