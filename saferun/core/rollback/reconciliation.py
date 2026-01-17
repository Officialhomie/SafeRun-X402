"""
Rollback and Reconciliation Mechanism

This module handles rolling back agent actions when approval is rejected.
It implements compensating transactions and state restoration.
"""

from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from loguru import logger

from saferun.core.state_machine.models import ExecutionState


class CompensatingTransaction:
    """
    Represents a compensating transaction that undoes an action.

    This is the Saga pattern in action - for every action, we define
    how to undo it.
    """

    def __init__(
        self,
        transaction_id: str,
        action_type: str,
        action_data: Dict[str, Any],
        rollback_func: Optional[Callable] = None
    ):
        self.transaction_id = transaction_id
        self.action_type = action_type
        self.action_data = action_data
        self.rollback_func = rollback_func
        self.executed = False
        self.success = False

    async def execute(self) -> bool:
        """
        Execute the compensating transaction.

        Returns:
            True if rollback successful, False otherwise
        """
        if self.executed:
            logger.warning(f"Transaction {self.transaction_id} already executed")
            return self.success

        try:
            logger.info(f"Executing compensating transaction {self.transaction_id}")

            if self.rollback_func:
                await self.rollback_func(self.action_data)
            else:
                # Default no-op for idempotent operations
                logger.info(f"No rollback function for {self.action_type}, skipping")

            self.success = True
            self.executed = True
            logger.info(f"Transaction {self.transaction_id} completed successfully")
            return True

        except Exception as e:
            logger.error(f"Transaction {self.transaction_id} failed: {e}")
            self.executed = True
            self.success = False
            return False


class RollbackManager:
    """
    Manages rollback operations when approval is rejected.

    This handles:
    1. Restoring state from checkpoint
    2. Executing compensating transactions
    3. Cleaning up partial work
    """

    def __init__(self):
        self.rollback_history: List[Dict[str, Any]] = []
        self.compensating_transactions: Dict[str, CompensatingTransaction] = {}
        logger.info("RollbackManager initialized")

    def register_action(
        self,
        action_id: str,
        action_type: str,
        action_data: Dict[str, Any],
        rollback_func: Optional[Callable] = None
    ):
        """
        Register an action that might need to be rolled back.

        This should be called before executing any action that has side effects.

        Args:
            action_id: Unique ID for this action
            action_type: Type of action (e.g., "api_call", "file_write")
            action_data: Data needed to roll back the action
            rollback_func: Optional async function to execute for rollback
        """
        transaction = CompensatingTransaction(
            transaction_id=action_id,
            action_type=action_type,
            action_data=action_data,
            rollback_func=rollback_func
        )

        self.compensating_transactions[action_id] = transaction
        logger.debug(f"Registered rollback for action {action_id} ({action_type})")

    async def execute_rollback(
        self,
        checkpoint_state: ExecutionState,
        actions_to_rollback: List[str]
    ) -> bool:
        """
        Execute rollback to a checkpoint.

        This:
        1. Executes compensating transactions in reverse order
        2. Restores state from checkpoint
        3. Cleans up resources

        Args:
            checkpoint_state: State to restore to
            actions_to_rollback: List of action IDs to roll back

        Returns:
            True if rollback successful
        """
        logger.info(f"Starting rollback to checkpoint {checkpoint_state.checkpoint_id}")

        rollback_record = {
            "checkpoint_id": checkpoint_state.checkpoint_id,
            "timestamp": datetime.utcnow().isoformat(),
            "actions_count": len(actions_to_rollback),
            "success": False,
            "failures": []
        }

        # Execute compensating transactions in reverse order
        # (undo most recent actions first)
        all_successful = True
        for action_id in reversed(actions_to_rollback):
            transaction = self.compensating_transactions.get(action_id)

            if not transaction:
                logger.warning(f"No transaction found for action {action_id}")
                continue

            success = await transaction.execute()
            if not success:
                all_successful = False
                rollback_record["failures"].append(action_id)
                logger.error(f"Failed to roll back action {action_id}")

        # State restoration (restore agent memory, outputs, etc.)
        logger.info("Restoring state from checkpoint")
        # This would integrate with the agent to restore its internal state
        # For now, we just log it

        rollback_record["success"] = all_successful
        self.rollback_history.append(rollback_record)

        if all_successful:
            logger.info(f"Rollback completed successfully for {len(actions_to_rollback)} actions")
        else:
            logger.error(f"Rollback completed with {len(rollback_record['failures'])} failures")

        return all_successful

    async def partial_rollback(
        self,
        checkpoint_state: ExecutionState,
        action_types: List[str]
    ) -> bool:
        """
        Roll back only specific types of actions.

        Useful when you want to undo some actions but keep others.
        """
        logger.info(f"Executing partial rollback for types: {action_types}")

        actions_to_rollback = [
            action_id
            for action_id, transaction in self.compensating_transactions.items()
            if transaction.action_type in action_types
        ]

        return await self.execute_rollback(checkpoint_state, actions_to_rollback)

    def get_rollback_history(self) -> List[Dict[str, Any]]:
        """Get history of all rollback operations"""
        return self.rollback_history

    def clear_transactions(self):
        """Clear all registered transactions (e.g., after successful completion)"""
        count = len(self.compensating_transactions)
        self.compensating_transactions.clear()
        logger.info(f"Cleared {count} compensating transactions")


class ReconciliationAgent:
    """
    Agent responsible for cleanup and reconciliation.

    This is one of the four agent types in SafeRun architecture.
    It handles cleanup when things fail or get rejected.
    """

    def __init__(self):
        self.rollback_manager = RollbackManager()
        logger.info("ReconciliationAgent initialized")

    async def reconcile_workflow(
        self,
        workflow_id: str,
        checkpoint_state: ExecutionState,
        rejection_reason: str
    ) -> Dict[str, Any]:
        """
        Reconcile a workflow after rejection.

        This:
        1. Analyzes what needs to be cleaned up
        2. Executes rollback
        3. Calculates partial payment
        4. Generates reconciliation report

        Returns:
            Reconciliation report with cleanup status and payment calculation
        """
        logger.info(f"Reconciling workflow {workflow_id}")

        report = {
            "workflow_id": workflow_id,
            "checkpoint_id": checkpoint_state.checkpoint_id,
            "rejection_reason": rejection_reason,
            "timestamp": datetime.utcnow().isoformat(),
            "rollback_success": False,
            "partial_completion": 0.0,
            "recommended_payment": 0.0,
            "cleanup_actions": []
        }

        # Calculate partial completion based on checkpoint state
        report["partial_completion"] = self._calculate_completion(checkpoint_state)

        # Execute cleanup
        # In a real implementation, this would analyze the execution state
        # and determine which actions need rollback
        actions_to_rollback = self._identify_rollback_actions(checkpoint_state)

        rollback_success = await self.rollback_manager.execute_rollback(
            checkpoint_state,
            actions_to_rollback
        )

        report["rollback_success"] = rollback_success
        report["cleanup_actions"] = [
            {"action_id": aid, "status": "completed"}
            for aid in actions_to_rollback
        ]

        # Calculate recommended payment (pro-rated based on completion)
        # This integrates with x402 escrow for partial payment
        report["recommended_payment"] = self._calculate_partial_payment(
            checkpoint_state,
            report["partial_completion"]
        )

        logger.info(
            f"Reconciliation complete: {report['partial_completion']*100:.1f}% complete, "
            f"rollback {'successful' if rollback_success else 'failed'}"
        )

        return report

    def _calculate_completion(self, checkpoint_state: ExecutionState) -> float:
        """
        Calculate what percentage of work was completed.

        This looks at execution state to determine how far through
        the workflow we got.
        """
        # Simple heuristic based on available data
        # Real implementation would be more sophisticated
        factors = []

        if checkpoint_state.api_calls:
            factors.append(min(len(checkpoint_state.api_calls) / 10.0, 1.0))

        if checkpoint_state.intermediate_outputs:
            factors.append(min(len(checkpoint_state.intermediate_outputs) / 5.0, 1.0))

        if checkpoint_state.decision_trace:
            factors.append(min(len(checkpoint_state.decision_trace) / 10.0, 1.0))

        return sum(factors) / max(len(factors), 1) if factors else 0.0

    def _calculate_partial_payment(
        self,
        checkpoint_state: ExecutionState,
        completion_percentage: float
    ) -> float:
        """
        Calculate how much payment should be made for partial work.

        Considers:
        - How much work was completed
        - Resources consumed
        - Whether rollback was needed
        """
        # Base payment on completion percentage
        # Subtract rollback cost
        # This would integrate with actual escrow amounts
        base_payment = 100.0  # Placeholder
        partial_payment = base_payment * completion_percentage

        # Deduct rollback cost (resources used for cleanup)
        rollback_cost = sum(checkpoint_state.resource_consumption.values())
        adjusted_payment = max(0, partial_payment - rollback_cost)

        return adjusted_payment

    def _identify_rollback_actions(self, checkpoint_state: ExecutionState) -> List[str]:
        """
        Identify which actions need to be rolled back.

        Analyzes the checkpoint state to determine what cleanup is needed.
        """
        # In real implementation, this would look at:
        # - API calls that modified external state
        # - Files that were created
        # - Database changes
        # - etc.

        # For now, return action IDs based on API calls
        return [
            call.get("call_id", f"call_{i}")
            for i, call in enumerate(checkpoint_state.api_calls)
            if call.get("has_side_effects", False)
        ]
