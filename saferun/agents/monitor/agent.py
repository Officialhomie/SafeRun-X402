"""
Monitor Agent

This agent watches execution, detects checkpoint conditions,
and triggers the approval workflow.
"""

from typing import Dict, Any, List, Callable, Optional
from datetime import datetime
from loguru import logger

from saferun.core.state_machine.models import ExecutionState, CheckpointConfig


class MonitorAgent:
    """
    Agent that monitors execution and triggers checkpoints.

    Responsibilities:
    - Watch for checkpoint conditions
    - Capture execution telemetry
    - Compare actual vs expected progress
    - Trigger approval workflow when needed
    """

    def __init__(self, monitor_id: str):
        self.monitor_id = monitor_id
        self.telemetry: List[Dict[str, Any]] = []
        self.checkpoint_triggers: Dict[str, Callable] = {}
        self.alert_callback: Optional[Callable] = None
        logger.info(f"MonitorAgent {monitor_id} initialized")

    def register_checkpoint_trigger(
        self,
        checkpoint_id: str,
        condition: Callable[[ExecutionState], bool]
    ):
        """
        Register a condition that triggers a checkpoint.

        Args:
            checkpoint_id: ID of checkpoint to trigger
            condition: Function that returns True when checkpoint should trigger
        """
        self.checkpoint_triggers[checkpoint_id] = condition
        logger.debug(f"Registered trigger for checkpoint {checkpoint_id}")

    def set_alert_callback(self, callback: Callable):
        """Set callback to call when alerts are triggered"""
        self.alert_callback = callback

    async def monitor_execution(
        self,
        execution_state: ExecutionState,
        checkpoint_config: CheckpointConfig
    ) -> Dict[str, Any]:
        """
        Monitor execution state and determine if checkpoint needed.

        Args:
            execution_state: Current execution state
            checkpoint_config: Configuration for this checkpoint

        Returns:
            Monitoring report with checkpoint decision
        """
        logger.debug(f"Monitoring execution for checkpoint {checkpoint_config.checkpoint_id}")

        # Capture telemetry
        telemetry_entry = self._capture_telemetry(execution_state)
        self.telemetry.append(telemetry_entry)

        # Check if checkpoint condition met
        should_checkpoint = False
        trigger_reason = None

        # Check registered triggers
        if checkpoint_config.checkpoint_id in self.checkpoint_triggers:
            condition = self.checkpoint_triggers[checkpoint_config.checkpoint_id]
            if condition(execution_state):
                should_checkpoint = True
                trigger_reason = "custom_condition"

        # Check for anomalies
        anomalies = self._detect_anomalies(execution_state)
        if anomalies:
            should_checkpoint = True
            trigger_reason = "anomaly_detected"

            if self.alert_callback:
                await self.alert_callback({
                    "type": "anomaly",
                    "checkpoint_id": checkpoint_config.checkpoint_id,
                    "anomalies": anomalies
                })

        # Check for timeout
        if self._check_timeout(execution_state, checkpoint_config):
            should_checkpoint = True
            trigger_reason = "timeout"

        report = {
            "monitor_id": self.monitor_id,
            "checkpoint_id": checkpoint_config.checkpoint_id,
            "timestamp": datetime.utcnow().isoformat(),
            "should_checkpoint": should_checkpoint,
            "trigger_reason": trigger_reason,
            "telemetry": telemetry_entry,
            "anomalies": anomalies,
            "recommendations": self._generate_recommendations(execution_state, anomalies)
        }

        logger.info(
            f"Monitoring complete: checkpoint={should_checkpoint}, "
            f"reason={trigger_reason}"
        )

        return report

    def _capture_telemetry(self, execution_state: ExecutionState) -> Dict[str, Any]:
        """Capture execution metrics"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "api_calls": len(execution_state.api_calls),
            "decisions": len(execution_state.decision_trace),
            "outputs": len(execution_state.intermediate_outputs),
            "resources": execution_state.resource_consumption.copy(),
            "memory_size": len(str(execution_state.agent_memory))
        }

    def _detect_anomalies(self, execution_state: ExecutionState) -> List[Dict[str, Any]]:
        """
        Detect anomalies in execution that might require human review.

        Examples:
        - Too many API calls
        - Resource consumption exceeding thresholds
        - Unexpected decision patterns
        """
        anomalies = []

        # Check API call volume
        if len(execution_state.api_calls) > 50:
            anomalies.append({
                "type": "high_api_volume",
                "severity": "warning",
                "details": f"{len(execution_state.api_calls)} API calls made"
            })

        # Check resource consumption
        tokens_used = execution_state.resource_consumption.get("tokens_used", 0)
        if tokens_used > 10000:
            anomalies.append({
                "type": "high_token_usage",
                "severity": "warning",
                "details": f"{tokens_used} tokens consumed"
            })

        # Check for errors in decision trace
        error_decisions = [
            d for d in execution_state.decision_trace
            if "error" in d.lower() or "failed" in d.lower()
        ]
        if error_decisions:
            anomalies.append({
                "type": "error_detected",
                "severity": "critical",
                "details": f"{len(error_decisions)} error decisions found"
            })

        return anomalies

    def _check_timeout(
        self,
        execution_state: ExecutionState,
        checkpoint_config: CheckpointConfig
    ) -> bool:
        """Check if checkpoint has timed out"""
        elapsed = (datetime.utcnow() - execution_state.timestamp).total_seconds()
        return elapsed > checkpoint_config.timeout_seconds

    def _generate_recommendations(
        self,
        execution_state: ExecutionState,
        anomalies: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate recommendations based on monitoring"""
        recommendations = []

        if anomalies:
            recommendations.append("Human review recommended due to detected anomalies")

        if len(execution_state.api_calls) > 30:
            recommendations.append("Consider breaking task into smaller steps")

        if not execution_state.intermediate_outputs:
            recommendations.append("No outputs generated yet, verify progress")

        return recommendations

    def compare_progress(
        self,
        actual_state: ExecutionState,
        expected_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare actual progress to expected progress.

        Args:
            actual_state: Current execution state
            expected_state: What we expected at this point

        Returns:
            Comparison report
        """
        logger.debug("Comparing actual vs expected progress")

        comparison = {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {}
        }

        # Compare API calls
        expected_calls = expected_state.get("api_calls", 0)
        actual_calls = len(actual_state.api_calls)
        comparison["metrics"]["api_calls"] = {
            "expected": expected_calls,
            "actual": actual_calls,
            "variance": actual_calls - expected_calls
        }

        # Compare outputs
        expected_outputs = expected_state.get("outputs", 0)
        actual_outputs = len(actual_state.intermediate_outputs)
        comparison["metrics"]["outputs"] = {
            "expected": expected_outputs,
            "actual": actual_outputs,
            "variance": actual_outputs - expected_outputs
        }

        # Determine if on track
        comparison["on_track"] = (
            abs(actual_calls - expected_calls) <= expected_calls * 0.2 and
            actual_outputs >= expected_outputs * 0.8
        )

        return comparison

    def get_telemetry_summary(self) -> Dict[str, Any]:
        """Get summary of all captured telemetry"""
        if not self.telemetry:
            return {"message": "No telemetry captured"}

        return {
            "monitor_id": self.monitor_id,
            "entries_count": len(self.telemetry),
            "latest": self.telemetry[-1] if self.telemetry else None,
            "total_api_calls": sum(t.get("api_calls", 0) for t in self.telemetry),
            "total_decisions": sum(t.get("decisions", 0) for t in self.telemetry)
        }
