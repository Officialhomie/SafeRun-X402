"""
Checkpoint Capture Mechanism

This module handles capturing complete agent execution state at checkpoints.
The captured state enables rollback if approval is rejected.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import hashlib
from loguru import logger

from saferun.core.state_machine.models import ExecutionState


class StateCapture:
    """
    Captures and serializes agent execution state.

    This is the foundation for rollback - we need to capture everything
    necessary to restore execution to a previous checkpoint.
    """

    def __init__(self):
        self.capture_history: List[Dict[str, Any]] = []

    def capture_state(
        self,
        checkpoint_id: str,
        agent_memory: Dict[str, Any],
        api_calls: List[Dict[str, Any]],
        intermediate_outputs: Dict[str, Any],
        decision_trace: List[str],
        resource_consumption: Dict[str, float]
    ) -> ExecutionState:
        """
        Capture complete execution state at a checkpoint.

        Args:
            checkpoint_id: ID of the checkpoint being captured
            agent_memory: Agent's internal memory/context
            api_calls: History of API calls made
            intermediate_outputs: Outputs produced so far
            decision_trace: Agent's decision reasoning
            resource_consumption: Resources used (tokens, API calls, etc.)

        Returns:
            ExecutionState object containing all captured state
        """
        logger.info(f"Capturing state for checkpoint {checkpoint_id}")

        execution_state = ExecutionState(
            checkpoint_id=checkpoint_id,
            timestamp=datetime.utcnow(),
            agent_memory=agent_memory,
            api_calls=api_calls,
            intermediate_outputs=intermediate_outputs,
            decision_trace=decision_trace,
            resource_consumption=resource_consumption
        )

        # Store in capture history
        self.capture_history.append({
            "checkpoint_id": checkpoint_id,
            "timestamp": execution_state.timestamp.isoformat(),
            "state": execution_state.model_dump()
        })

        logger.info(
            f"State captured: {len(api_calls)} API calls, "
            f"{len(decision_trace)} decisions, "
            f"{len(intermediate_outputs)} outputs"
        )

        return execution_state

    def serialize_state(self, execution_state: ExecutionState) -> str:
        """
        Serialize execution state to JSON string.

        This enables storage as x402 artifact.
        """
        try:
            state_dict = execution_state.model_dump()
            # Convert datetime to ISO format for JSON serialization
            state_dict["timestamp"] = state_dict["timestamp"].isoformat()
            serialized = json.dumps(state_dict, indent=2)
            logger.debug(f"Serialized state size: {len(serialized)} bytes")
            return serialized
        except Exception as e:
            logger.error(f"Failed to serialize state: {e}")
            raise

    def deserialize_state(self, serialized: str) -> ExecutionState:
        """
        Deserialize execution state from JSON string.

        Used when restoring from a checkpoint.
        """
        try:
            state_dict = json.loads(serialized)
            # Convert ISO format back to datetime
            state_dict["timestamp"] = datetime.fromisoformat(state_dict["timestamp"])
            return ExecutionState(**state_dict)
        except Exception as e:
            logger.error(f"Failed to deserialize state: {e}")
            raise

    def compute_state_hash(self, execution_state: ExecutionState) -> str:
        """
        Compute cryptographic hash of execution state.

        This provides immutable reference for the checkpoint artifact.
        """
        serialized = self.serialize_state(execution_state)
        hash_obj = hashlib.sha256(serialized.encode())
        return hash_obj.hexdigest()

    def compare_states(
        self,
        state1: ExecutionState,
        state2: ExecutionState
    ) -> Dict[str, Any]:
        """
        Compare two execution states and return differences.

        Useful for debugging and understanding what changed between checkpoints.
        """
        diff = {
            "memory_diff": self._dict_diff(state1.agent_memory, state2.agent_memory),
            "api_calls_added": len(state2.api_calls) - len(state1.api_calls),
            "outputs_diff": self._dict_diff(
                state1.intermediate_outputs,
                state2.intermediate_outputs
            ),
            "decisions_added": len(state2.decision_trace) - len(state1.decision_trace),
            "resource_diff": self._dict_diff(
                state1.resource_consumption,
                state2.resource_consumption
            )
        }
        return diff

    def _dict_diff(self, dict1: Dict, dict2: Dict) -> Dict[str, Any]:
        """Helper to compute difference between two dictionaries"""
        added = {k: v for k, v in dict2.items() if k not in dict1}
        removed = {k: v for k, v in dict1.items() if k not in dict2}
        changed = {
            k: {"old": dict1[k], "new": dict2[k]}
            for k in dict1
            if k in dict2 and dict1[k] != dict2[k]
        }
        return {"added": added, "removed": removed, "changed": changed}


class CheckpointManager:
    """
    Manages checkpoint lifecycle: create, store, retrieve, restore.

    This integrates with x402 artifacts for permanent storage.
    """

    def __init__(self):
        self.state_capture = StateCapture()
        self.checkpoints: Dict[str, ExecutionState] = {}
        logger.info("CheckpointManager initialized")

    def create_checkpoint(
        self,
        checkpoint_id: str,
        agent_memory: Dict[str, Any],
        api_calls: List[Dict[str, Any]] = None,
        intermediate_outputs: Dict[str, Any] = None,
        decision_trace: List[str] = None,
        resource_consumption: Dict[str, float] = None
    ) -> ExecutionState:
        """
        Create a new checkpoint by capturing current state.

        Args:
            checkpoint_id: Unique ID for this checkpoint
            agent_memory: Agent's current memory state
            api_calls: List of API calls made (optional)
            intermediate_outputs: Outputs produced so far (optional)
            decision_trace: Agent's decision history (optional)
            resource_consumption: Resources consumed (optional)

        Returns:
            ExecutionState containing captured state
        """
        execution_state = self.state_capture.capture_state(
            checkpoint_id=checkpoint_id,
            agent_memory=agent_memory,
            api_calls=api_calls or [],
            intermediate_outputs=intermediate_outputs or {},
            decision_trace=decision_trace or [],
            resource_consumption=resource_consumption or {}
        )

        # Store checkpoint locally
        self.checkpoints[checkpoint_id] = execution_state

        logger.info(f"Checkpoint {checkpoint_id} created and stored")

        return execution_state

    def get_checkpoint(self, checkpoint_id: str) -> Optional[ExecutionState]:
        """Retrieve a checkpoint by ID"""
        checkpoint = self.checkpoints.get(checkpoint_id)
        if checkpoint:
            logger.info(f"Retrieved checkpoint {checkpoint_id}")
        else:
            logger.warning(f"Checkpoint {checkpoint_id} not found")
        return checkpoint

    def restore_checkpoint(self, checkpoint_id: str) -> Optional[ExecutionState]:
        """
        Restore execution state from a checkpoint.

        This is used during rollback to return to a previous state.
        """
        checkpoint = self.get_checkpoint(checkpoint_id)
        if checkpoint:
            logger.info(f"Restoring from checkpoint {checkpoint_id}")
            return checkpoint
        return None

    def list_checkpoints(self) -> List[str]:
        """List all available checkpoint IDs"""
        return list(self.checkpoints.keys())

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint (cleanup)"""
        if checkpoint_id in self.checkpoints:
            del self.checkpoints[checkpoint_id]
            logger.info(f"Deleted checkpoint {checkpoint_id}")
            return True
        return False

    def export_checkpoint(self, checkpoint_id: str) -> Optional[str]:
        """
        Export checkpoint as JSON string for x402 artifact storage.

        Returns:
            Serialized checkpoint data, or None if not found
        """
        checkpoint = self.get_checkpoint(checkpoint_id)
        if checkpoint:
            return self.state_capture.serialize_state(checkpoint)
        return None

    def import_checkpoint(self, checkpoint_id: str, serialized: str) -> bool:
        """
        Import checkpoint from JSON string (e.g., from x402 artifact).

        Args:
            checkpoint_id: ID to assign to imported checkpoint
            serialized: JSON string containing checkpoint data

        Returns:
            True if import successful
        """
        try:
            execution_state = self.state_capture.deserialize_state(serialized)
            self.checkpoints[checkpoint_id] = execution_state
            logger.info(f"Imported checkpoint {checkpoint_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to import checkpoint {checkpoint_id}: {e}")
            return False

    async def load_checkpoint_from_artifact(
        self,
        artifact_uri: str,
        checkpoint_id: str,
        x402_client
    ) -> ExecutionState:
        """
        Load checkpoint from x402 artifact URI.

        Args:
            artifact_uri: x402 artifact URI
            checkpoint_id: ID to assign to loaded checkpoint
            x402_client: X402Client instance (optional)

        Returns:
            ExecutionState if successful, None otherwise
        """
        if not x402_client:
            raise ValueError("x402_client is required to load checkpoint from artifact")

        # Fetch artifact from x402
        artifact = await x402_client.get_artifact(artifact_uri)

        # Extract content
        content = artifact.get("content")
        if not content:
            raise ValueError(f"Artifact {artifact_uri} has no content")

        # Deserialize and store
        execution_state = self.state_capture.deserialize_state(content)
        self.checkpoints[checkpoint_id] = execution_state
        logger.info(f"Loaded checkpoint {checkpoint_id} from artifact {artifact_uri}")
        return execution_state
