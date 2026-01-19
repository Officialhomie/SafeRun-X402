"""
Executor Agent

This agent performs the actual task work, emits checkpoint signals,
and maintains execution context.
"""

from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from loguru import logger
import json

from saferun.core.state_machine.models import ExecutionState

# Try to import Anthropic, but don't fail if not available
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic library not available. Using mock execution.")
from saferun.config import settings


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
        
        # Initialize Claude API client - required for real execution
        if not settings.anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is required for ExecutorAgent. "
                "Please set it in your environment or config."
            )
        
        try:
            from anthropic import Anthropic
            self.claude_client = Anthropic(api_key=settings.anthropic_api_key)
            logger.info(f"ExecutorAgent {agent_id} initialized with Claude API")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Claude client: {e}") from e
        
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
        """Create execution plan for the task using Claude API"""
        if self.claude_client:
            try:
                # Use Claude to create an execution plan
                prompt = f"""You are an AI agent executor. Create a detailed execution plan for the following task.

Task Description: {task_description}
Task Parameters: {task_parameters}

Please create a structured plan with:
1. A brief summary of the approach
2. A list of steps to execute, each with:
   - An ID number
   - A clear description
   - Whether the step is critical (requires human approval)

Return your response as a JSON object with this structure:
{{
    "summary": "Brief summary of the execution approach",
    "steps": [
        {{
            "id": 1,
            "description": "Step description",
            "critical": true/false
        }}
    ]
}}"""

                response = self.claude_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=2000,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )
                
                # Parse the response
                content = response.content[0].text
                self.resource_consumption["tokens_used"] += response.usage.input_tokens + response.usage.output_tokens
                
                # Try to extract JSON from the response
                import json
                import re
                
                # Look for JSON in the response
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    plan = json.loads(json_match.group())
                    logger.info(f"Generated execution plan with {len(plan.get('steps', []))} steps")
                    return plan
                else:
                    # If JSON parsing fails, raise an error - we need structured response
                    raise ValueError(
                        f"Claude API response could not be parsed as JSON. "
                        f"Response: {content[:200]}"
                    )
                    
            except Exception as e:
                logger.error(f"Error calling Claude API for planning: {e}")
                raise RuntimeError(f"Failed to generate execution plan: {e}") from e

    async def _make_api_call(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a step using Claude API"""
        call_record = {
            "call_id": f"call_{len(self.api_call_history)}",
            "timestamp": datetime.utcnow().isoformat(),
            "step_id": step["id"],
            "description": step["description"],
            "has_side_effects": step.get("critical", False),
        }
        
        if self.claude_client:
            try:
                # Use Claude to execute the step
                prompt = f"""You are executing a workflow step. Here's the step to execute:

Step ID: {step['id']}
Description: {step['description']}
Critical: {step.get('critical', False)}

Current Context:
- Task: {self.execution_context.get('task', 'N/A')}
- Parameters: {self.execution_context.get('parameters', {})}
- Previous outputs: {list(self.intermediate_outputs.keys())}

Execute this step and provide:
1. A status (success, partial, or error)
2. The data or result produced
3. Any important notes or warnings

Return your response as a JSON object:
{{
    "status": "success|partial|error",
    "data": "The actual result or output",
    "notes": "Any important information"
}}"""

                response = self.claude_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=2000,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )
                
                content = response.content[0].text
                self.resource_consumption["tokens_used"] += response.usage.input_tokens + response.usage.output_tokens
                
                # Parse the response
                import json
                import re
                
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    call_record["result"] = result
                else:
                    # If JSON parsing fails, raise an error - we need structured response
                    raise ValueError(
                        f"Claude API response could not be parsed as JSON for step {step['id']}. "
                        f"Response: {content[:200]}"
                    )
                    
            except Exception as e:
                logger.error(f"Error calling Claude API for step execution: {e}")
                raise RuntimeError(f"Failed to execute step {step['id']}: {e}") from e

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
