"""
x402 Integration Client

This module handles integration with all five x402 primitives:
1. Jobs - workflow execution units
2. Escrow - payment locking and distribution
3. Artifacts - immutable state storage
4. Identity - role management (poster, executor, supervisor)
5. Marketplace - supervisor discovery
"""

from typing import Dict, Any, List, Optional
from loguru import logger
import httpx

from saferun.config import settings


class X402Client:
    """
    Client for interacting with x402 platform.

    This composes the five x402 primitives to create the supervised
    execution infrastructure.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.x402_api_key
        self.base_url = settings.x402_api_url
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        logger.info("X402Client initialized")

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    # ==================== Jobs ====================

    async def create_job(
        self,
        job_type: str,
        job_data: Dict[str, Any],
        escrow_amount: float,
        executor_id: str
    ) -> Dict[str, Any]:
        """
        Create a new job on x402.

        Args:
            job_type: Type of job (e.g., "supervised_workflow")
            job_data: Job configuration and parameters
            escrow_amount: Amount to lock in escrow
            executor_id: ID of the agent that will execute

        Returns:
            Job details including job_id
        """
        logger.info(f"Creating x402 job: {job_type}")

        payload = {
            "type": job_type,
            "data": job_data,
            "escrow": {
                "amount": escrow_amount,
                "executor_id": executor_id
            }
        }

        try:
            # Mock implementation - replace with actual x402 API call
            job_id = f"job_{hash(str(payload)) % 1000000}"
            result = {
                "job_id": job_id,
                "status": "created",
                "escrow_locked": True,
                **payload
            }

            logger.info(f"Job created: {job_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to create job: {e}")
            raise

    async def get_job(self, job_id: str) -> Dict[str, Any]:
        """Retrieve job details"""
        logger.debug(f"Fetching job {job_id}")

        # Mock implementation
        return {
            "job_id": job_id,
            "status": "active",
            "created_at": "2024-01-17T00:00:00Z"
        }

    async def update_job_status(
        self,
        job_id: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update job status (executing, completed, failed, etc.)"""
        logger.info(f"Updating job {job_id} status to {status}")

        # Mock implementation
        return True

    async def create_approval_subjob(
        self,
        parent_job_id: str,
        checkpoint_id: str,
        supervisor_id: str,
        approval_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a sub-job for approval.

        This is routed to the human supervisor.
        """
        logger.info(f"Creating approval sub-job for checkpoint {checkpoint_id}")

        subjob = {
            "subjob_id": f"approval_{checkpoint_id}",
            "parent_job_id": parent_job_id,
            "type": "approval_request",
            "supervisor_id": supervisor_id,
            "data": approval_data,
            "status": "pending"
        }

        return subjob

    # ==================== Escrow ====================

    async def lock_escrow(
        self,
        workflow_id: str,
        amount: float,
        poster_id: str,
        executor_id: str
    ) -> Dict[str, Any]:
        """
        Lock funds in escrow at workflow start.

        Args:
            workflow_id: Workflow identifier
            amount: Amount to lock
            poster_id: Who is posting the job
            executor_id: Who will execute

        Returns:
            Escrow details including escrow_id
        """
        logger.info(f"Locking escrow: {amount} for workflow {workflow_id}")

        escrow = {
            "escrow_id": f"escrow_{workflow_id}",
            "workflow_id": workflow_id,
            "amount": amount,
            "poster_id": poster_id,
            "executor_id": executor_id,
            "status": "locked",
            "released": 0.0
        }

        return escrow

    async def release_escrow(
        self,
        escrow_id: str,
        amount: float,
        recipient_id: str,
        reason: str
    ) -> bool:
        """
        Release funds from escrow (milestone payment).

        Args:
            escrow_id: Escrow to release from
            amount: Amount to release
            recipient_id: Who receives the funds
            reason: Reason for release (e.g., "checkpoint_approved")

        Returns:
            True if successful
        """
        logger.info(f"Releasing {amount} from escrow {escrow_id} to {recipient_id}")

        # Mock implementation
        return True

    async def split_payment(
        self,
        escrow_id: str,
        splits: List[Dict[str, Any]]
    ) -> bool:
        """
        Split payment between multiple parties.

        Example splits:
        [
            {"recipient_id": "executor_1", "amount": 80.0, "reason": "execution"},
            {"recipient_id": "supervisor_1", "amount": 20.0, "reason": "supervision"}
        ]
        """
        logger.info(f"Splitting payment from escrow {escrow_id} to {len(splits)} recipients")

        total = sum(split["amount"] for split in splits)
        logger.debug(f"Total split amount: {total}")

        # Mock implementation
        for split in splits:
            await self.release_escrow(
                escrow_id,
                split["amount"],
                split["recipient_id"],
                split["reason"]
            )

        return True

    async def calculate_settlement(
        self,
        workflow_id: str,
        completion_percentage: float,
        escrow_amount: float
    ) -> Dict[str, Any]:
        """
        Calculate how to settle payments based on completion.

        This is used for partial completion scenarios.
        """
        logger.info(
            f"Calculating settlement: {completion_percentage*100:.1f}% "
            f"complete of {escrow_amount}"
        )

        base_payment = escrow_amount * completion_percentage
        supervisor_fee = base_payment * 0.1  # 10% to supervisor
        executor_payment = base_payment * 0.9  # 90% to executor

        settlement = {
            "workflow_id": workflow_id,
            "completion_percentage": completion_percentage,
            "total_escrow": escrow_amount,
            "total_payout": base_payment,
            "splits": [
                {
                    "recipient_type": "executor",
                    "amount": executor_payment,
                    "reason": "partial_completion"
                },
                {
                    "recipient_type": "supervisor",
                    "amount": supervisor_fee,
                    "reason": "supervision_fee"
                }
            ]
        }

        return settlement

    # ==================== Artifacts ====================

    async def create_artifact(
        self,
        artifact_type: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create an immutable artifact (e.g., checkpoint state).

        Args:
            artifact_type: Type of artifact (e.g., "checkpoint_state")
            content: The actual content (serialized state)
            metadata: Additional metadata

        Returns:
            Artifact details including URI
        """
        logger.info(f"Creating artifact: {artifact_type}")

        import hashlib
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        artifact = {
            "artifact_id": f"artifact_{content_hash[:16]}",
            "uri": f"x402://artifacts/{content_hash}",
            "type": artifact_type,
            "content_hash": content_hash,
            "size_bytes": len(content),
            "metadata": metadata,
            "created_at": "2024-01-17T00:00:00Z"
        }

        logger.info(f"Artifact created: {artifact['artifact_id']}")
        return artifact

    async def get_artifact(self, artifact_uri: str) -> Dict[str, Any]:
        """Retrieve artifact by URI"""
        logger.debug(f"Fetching artifact: {artifact_uri}")

        # Mock implementation
        return {
            "uri": artifact_uri,
            "content": "{}",
            "metadata": {}
        }

    # ==================== Identity ====================

    async def verify_identity(
        self,
        user_id: str,
        role: str
    ) -> bool:
        """
        Verify user identity and role.

        Roles: poster, executor, supervisor, verifier
        """
        logger.debug(f"Verifying identity {user_id} for role {role}")

        # Mock implementation - always returns True
        return True

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile information"""
        return {
            "user_id": user_id,
            "reputation_score": 0.95,
            "verified": True
        }

    # ==================== Marketplace ====================

    async def find_supervisors(
        self,
        workflow_type: str,
        min_reputation: float = 0.8
    ) -> List[Dict[str, Any]]:
        """
        Find available supervisors in the marketplace.

        Args:
            workflow_type: Type of workflow needing supervision
            min_reputation: Minimum reputation score

        Returns:
            List of available supervisors
        """
        logger.info(f"Finding supervisors for {workflow_type}")

        # Mock implementation
        supervisors = [
            {
                "supervisor_id": "supervisor_1",
                "reputation": 0.95,
                "response_time_avg": 120,  # seconds
                "approval_quality": 0.92,
                "available": True
            },
            {
                "supervisor_id": "supervisor_2",
                "reputation": 0.88,
                "response_time_avg": 180,
                "approval_quality": 0.89,
                "available": True
            }
        ]

        return supervisors

    async def request_supervisor(
        self,
        supervisor_id: str,
        workflow_id: str
    ) -> bool:
        """Request a specific supervisor for a workflow"""
        logger.info(f"Requesting supervisor {supervisor_id} for workflow {workflow_id}")
        return True


class X402Integration:
    """
    High-level integration that composes x402 primitives for SafeRun.

    This provides the business logic layer on top of the raw x402 client.
    """

    def __init__(self):
        self.client = X402Client()
        logger.info("X402Integration initialized")

    async def setup_supervised_workflow(
        self,
        workflow_id: str,
        workflow_config: Dict[str, Any],
        escrow_amount: float,
        poster_id: str,
        executor_id: str,
        supervisor_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Set up a complete supervised workflow using x402 primitives.

        This:
        1. Creates the main job
        2. Locks escrow
        3. Assigns or finds supervisor
        4. Returns workflow handle

        Returns:
            Workflow setup details
        """
        logger.info(f"Setting up supervised workflow {workflow_id}")

        # Find supervisor if not provided
        if not supervisor_id:
            supervisors = await self.client.find_supervisors(
                workflow_type=workflow_config.get("type", "general")
            )
            if supervisors:
                supervisor_id = supervisors[0]["supervisor_id"]
            else:
                raise Exception("No supervisors available")

        # Create main job
        job = await self.client.create_job(
            job_type="supervised_workflow",
            job_data={
                "workflow_id": workflow_id,
                "config": workflow_config,
                "supervisor_id": supervisor_id
            },
            escrow_amount=escrow_amount,
            executor_id=executor_id
        )

        # Lock escrow
        escrow = await self.client.lock_escrow(
            workflow_id=workflow_id,
            amount=escrow_amount,
            poster_id=poster_id,
            executor_id=executor_id
        )

        setup = {
            "workflow_id": workflow_id,
            "job_id": job["job_id"],
            "escrow_id": escrow["escrow_id"],
            "supervisor_id": supervisor_id,
            "status": "ready"
        }

        logger.info(f"Supervised workflow setup complete: {workflow_id}")
        return setup

    async def store_checkpoint_artifact(
        self,
        checkpoint_id: str,
        checkpoint_data: str,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Store checkpoint state as x402 artifact.

        Returns:
            Artifact URI
        """
        artifact = await self.client.create_artifact(
            artifact_type="checkpoint_state",
            content=checkpoint_data,
            metadata={
                "checkpoint_id": checkpoint_id,
                **metadata
            }
        )

        return artifact["uri"]

    async def settle_workflow(
        self,
        workflow_id: str,
        escrow_id: str,
        escrow_amount: float,
        completion_percentage: float,
        executor_id: str,
        supervisor_id: str
    ) -> Dict[str, Any]:
        """
        Complete workflow settlement with payment distribution.

        Returns:
            Settlement details
        """
        logger.info(f"Settling workflow {workflow_id}")

        # Calculate settlement
        settlement = await self.client.calculate_settlement(
            workflow_id=workflow_id,
            completion_percentage=completion_percentage,
            escrow_amount=escrow_amount
        )

        # Execute payment splits
        splits = [
            {
                "recipient_id": executor_id,
                "amount": settlement["splits"][0]["amount"],
                "reason": "execution"
            },
            {
                "recipient_id": supervisor_id,
                "amount": settlement["splits"][1]["amount"],
                "reason": "supervision"
            }
        ]

        await self.client.split_payment(escrow_id, splits)

        logger.info(f"Workflow {workflow_id} settled successfully")
        return settlement

    async def close(self):
        """Close the client connection"""
        await self.client.close()
