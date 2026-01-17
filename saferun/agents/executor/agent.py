"""
Executor Agent

This agent performs the actual task work, emits checkpoint signals,
and maintains execution context.
"""

from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from loguru import logger

from saferun.core.state_machine.models import ExecutionState


class ExecutorAgent:
    """
    Agent that executes the actual workflow tasks.

    Responsibilities:
    - Perform task work
    - Emit checkpoint signals when reaching decision points
    - Maintain execution context
    - Consume approval responses
    """

    def __init__(self, agent_id: str, agent_config: Optional[Dict[str, Any]] = None):
        self.agent_id = agent_id
        self.config = agent_config or {}
        self.execution_context: Dict[str, Any] = {}
        self.api_call_history: List[Dict[str, Any]] = []
        self.decision_trace: List[str] = []
        self.intermediate_outputs: Dict[str, Any] = {}
        self.resource_consumption: Dict[str, float] = {
            "api_calls": 0,
            "tokens_used": 0,
            "execution_time": 0
        }
        self.checkpoint_callback: Optional[Callable] = None
        logger.info(f"ExecutorAgent {agent_id} initialized")

    def set_checkpoint_callback(self, callback: Callable):
        """
        Set callback function to call when checkpoint is reached.

        The callback should handle pausing execution and requesting approval.
        """
        self.checkpoint_callback = callback

    async def execute_task(
        self,
        task_description: str,
        task_parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a task with supervised checkpoints.

        Args:
            task_description: What task to perform
            task_parameters: Task configuration and inputs

        Returns:
            Task execution results
        """
        logger.info(f"ExecutorAgent {self.agent_id} starting task: {task_description}")

        self.execution_context = {
            "task": task_description,
            "parameters": task_parameters,
            "started_at": datetime.utcnow().isoformat(),
            "status": "executing"
        }

        try:
            # Execute the task logic
            # In a real implementation, this would call the actual AI agent
            result = await self._execute_with_checkpoints(task_description, task_parameters)

            self.execution_context["status"] = "completed"
            self.execution_context["completed_at"] = datetime.utcnow().isoformat()

            logger.info(f"Task completed successfully: {task_description}")
            return result

        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            self.execution_context["status"] = "failed"
            self.execution_context["error"] = str(e)
            raise

    async def _execute_with_checkpoints(
        self,
        task_description: str,
        task_parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Internal method that executes task and triggers checkpoints.

        This is where the actual work happens, with checkpoint signals
        emitted at decision points.
        """
        # Example execution flow
        # In real implementation, this would integrate with Claude/OpenAI

        # Step 1: Plan the task
        self._log_decision("Planning task execution")
        plan = self._plan_task(task_description, task_parameters)
        self.intermediate_outputs["plan"] = plan

        # Checkpoint: Review plan before proceeding
        if self.checkpoint_callback and self._should_checkpoint("plan_review"):
            checkpoint_state = self.capture_current_state("plan_review")
            approval = await self.checkpoint_callback(
                checkpoint_id="plan_review",
                state=checkpoint_state,
                summary=f"Review execution plan: {plan.get('summary', 'No summary')}"
            )

            if not approval.get("approved"):
                raise Exception("Plan not approved")

        # Step 2: Execute the plan
        self._log_decision("Executing planned steps")
        results = []

        for step in plan.get("steps", []):
            self._log_decision(f"Executing step: {step['description']}")

            # Simulate API call
            api_result = await self._make_api_call(step)
            results.append(api_result)

            # Checkpoint: Review step result if critical
            if step.get("critical") and self.checkpoint_callback:
                checkpoint_state = self.capture_current_state(f"step_{step['id']}")
                approval = await self.checkpoint_callback(
                    checkpoint_id=f"step_{step['id']}",
                    state=checkpoint_state,
                    summary=f"Review step result: {step['description']}"
                )

                if not approval.get("approved"):
                    # Apply modifications if provided
                    if approval.get("modifications"):
                        step.update(approval["modifications"])

        self.intermediate_outputs["results"] = results

        # Step 3: Generate final output
        self._log_decision("Generating final output")
        final_output = self._generate_output(results)

        return final_output

    def _plan_task(
        self,
        task_description: str,
        task_parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create execution plan for the task"""
        # Mock implementation
        plan = {
            "summary": f"Execute {task_description}",
            "steps": [
                {
                    "id": 1,
                    "description": "Gather information",
                    "critical": False
                },
                {
                    "id": 2,
                    "description": "Process data",
                    "critical": True
                },
                {
                    "id": 3,
                    "description": "Generate output",
                    "critical": False
                }
            ]
        }
        return plan

    async def _make_api_call(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate making an API call"""
        call_record = {
            "call_id": f"call_{len(self.api_call_history)}",
            "timestamp": datetime.utcnow().isoformat(),
            "step_id": step["id"],
            "description": step["description"],
            "has_side_effects": step.get("critical", False),
            "result": {"status": "success", "data": f"Result for step {step['id']}"}
        }

        self.api_call_history.append(call_record)
        self.resource_consumption["api_calls"] += 1

        return call_record["result"]

    def _generate_output(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate final output from step results"""
        return {
            "status": "completed",
            "steps_completed": len(results),
            "results": results,
            "summary": "Task completed successfully"
        }

    def _should_checkpoint(self, checkpoint_type: str) -> bool:
        """Determine if a checkpoint should be created"""
        # Logic to determine when to checkpoint
        # Could be based on config, task complexity, etc.
        return True

    def _log_decision(self, decision: str):
        """Log agent decision for audit trail"""
        timestamp = datetime.utcnow().isoformat()
        self.decision_trace.append(f"[{timestamp}] {decision}")
        logger.debug(f"Decision: {decision}")

    def capture_current_state(self, checkpoint_id: str) -> ExecutionState:
        """
        Capture current execution state for checkpoint.

        This is called by the orchestrator when creating a checkpoint.
        """
        return ExecutionState(
            checkpoint_id=checkpoint_id,
            timestamp=datetime.utcnow(),
            agent_memory=self.execution_context.copy(),
            api_calls=self.api_call_history.copy(),
            intermediate_outputs=self.intermediate_outputs.copy(),
            decision_trace=self.decision_trace.copy(),
            resource_consumption=self.resource_consumption.copy()
        )

    def restore_state(self, execution_state: ExecutionState):
        """
        Restore execution state from a checkpoint.

        Used during rollback to return to previous state.
        """
        logger.info(f"Restoring state from checkpoint {execution_state.checkpoint_id}")

        self.execution_context = execution_state.agent_memory.copy()
        self.api_call_history = execution_state.api_calls.copy()
        self.intermediate_outputs = execution_state.intermediate_outputs.copy()
        self.decision_trace = execution_state.decision_trace.copy()
        self.resource_consumption = execution_state.resource_consumption.copy()

        logger.info("State restored successfully")

    def apply_modifications(self, modifications: Dict[str, Any]):
        """
        Apply modifications from approval response.

        When human approves with modifications, this updates the execution context.
        """
        logger.info(f"Applying modifications: {modifications}")

        for key, value in modifications.items():
            if key in self.execution_context:
                self.execution_context[key] = value
            elif key in self.intermediate_outputs:
                self.intermediate_outputs[key] = value

        logger.info("Modifications applied")

    def get_status(self) -> Dict[str, Any]:
        """Get current execution status"""
        return {
            "agent_id": self.agent_id,
            "context": self.execution_context,
            "api_calls_made": len(self.api_call_history),
            "decisions_made": len(self.decision_trace),
            "outputs_generated": len(self.intermediate_outputs),
            "resources_consumed": self.resource_consumption
        }
