"""
x402 Integration Client

This module handles integration with all five x402 primitives:
1. Jobs - workflow execution units
2. Escrow - payment locking and distribution
3. Artifacts - immutable state storage
4. Identity - role management (poster, executor, supervisor)
5. Marketplace - supervisor discovery
"""

from typing import Dict, Any, List, Optional, Callable
from loguru import logger
import httpx
import asyncio
from functools import wraps

from saferun.config import settings


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator to retry async functions on failure.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay after each retry
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except (httpx.HTTPError, httpx.TimeoutException) as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {current_delay}s..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"{func.__name__} failed after {max_retries + 1} attempts")
                except Exception as e:
                    # Don't retry on non-HTTP errors
                    logger.error(f"{func.__name__} failed with non-retryable error: {e}")
                    raise
            
            # If we exhausted retries, raise the last exception
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


class X402Client:
    """
    Client for interacting with x402 platform.

    This composes the five x402 primitives to create the supervised
    execution infrastructure.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.x402_api_key
        self.base_url = settings.x402_api_url
        
        if not self.api_key:
            raise ValueError("X402_API_KEY is required. Please set it in your environment or config.")
        if not self.base_url or self.base_url == "https://api.x402.io":
            raise ValueError("X402_API_URL must be set to a valid x402 API endpoint.")
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30.0
        )
        logger.info(f"X402Client initialized with API: {self.base_url}")

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    # ==================== Jobs ====================

    @retry_on_failure(max_retries=3, delay=1.0)
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
            response = await self.client.post(
                "/jobs",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Job created: {result.get('job_id')}")
            return result
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error creating job: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"HTTP error creating job: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to create job: {e}")
            raise

    @retry_on_failure(max_retries=2, delay=0.5)
    @retry_on_failure(max_retries=2, delay=0.5)
    async def get_job(self, job_id: str) -> Dict[str, Any]:
        """Retrieve job details"""
        logger.debug(f"Fetching job {job_id}")

        try:
            response = await self.client.get(f"/jobs/{job_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching job: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching job: {e}")
            raise

    @retry_on_failure(max_retries=2, delay=0.5)
    async def update_job_status(
        self,
        job_id: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update job status (executing, completed, failed, etc.)"""
        logger.info(f"Updating job {job_id} status to {status}")

        try:
            response = await self.client.patch(
                f"/jobs/{job_id}",
                json={"status": status, "metadata": metadata or {}}
            )
            response.raise_for_status()
            return True
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error updating job status: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"HTTP error updating job status: {e}")
            raise

    @retry_on_failure(max_retries=2, delay=0.5)
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

        try:
            response = await self.client.post(
                "/jobs/subjobs",
                json={
                    "parent_job_id": parent_job_id,
                    "checkpoint_id": checkpoint_id,
                    "supervisor_id": supervisor_id,
                    "type": "approval_request",
                    "data": approval_data
                }
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error creating approval sub-job: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"HTTP error creating approval sub-job: {e}")
            raise

    # ==================== Escrow ====================

    @retry_on_failure(max_retries=3, delay=1.0)
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

        payload = {
            "workflow_id": workflow_id,
            "amount": amount,
            "poster_id": poster_id,
            "executor_id": executor_id
        }

        try:
            response = await self.client.post(
                "/escrow/lock",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Escrow locked: {result.get('escrow_id')}")
            return result
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error locking escrow: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"HTTP error locking escrow: {e}")
            raise

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

        payload = {
            "escrow_id": escrow_id,
            "amount": amount,
            "recipient_id": recipient_id,
            "reason": reason
        }

        try:
            response = await self.client.post(
                "/escrow/release",
                json=payload
            )
            response.raise_for_status()
            return True
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error releasing escrow: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"HTTP error releasing escrow: {e}")
            raise

    @retry_on_failure(max_retries=3, delay=1.0)
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

        try:
            response = await self.client.post(
                "/escrow/split",
                json={
                    "escrow_id": escrow_id,
                    "splits": splits
                }
            )
            response.raise_for_status()
            return True
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error splitting payment: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"HTTP error splitting payment: {e}")
            raise

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

    @retry_on_failure(max_retries=3, delay=1.0)
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
        from datetime import datetime
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        payload = {
            "type": artifact_type,
            "content": content,
            "content_hash": content_hash,
            "metadata": metadata
        }

        try:
            response = await self.client.post(
                "/artifacts",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Artifact created: {result.get('artifact_id')}")
            return result
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error creating artifact: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"HTTP error creating artifact: {e}")
            raise

    @retry_on_failure(max_retries=2, delay=0.5)
    async def get_artifact(self, artifact_uri: str) -> Dict[str, Any]:
        """Retrieve artifact by URI"""
        logger.debug(f"Fetching artifact: {artifact_uri}")

        try:
            # Extract artifact ID from URI (format: x402://artifacts/{hash})
            artifact_id = artifact_uri.split("/")[-1] if "/" in artifact_uri else artifact_uri
            response = await self.client.get(f"/artifacts/{artifact_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching artifact: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching artifact: {e}")
            raise

    # ==================== Identity ====================

    @retry_on_failure(max_retries=2, delay=0.5)
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

        try:
            response = await self.client.post(
                "/identity/verify",
                json={
                    "user_id": user_id,
                    "role": role
                }
            )
            response.raise_for_status()
            result = response.json()
            return result.get("verified", False)
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error verifying identity: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"HTTP error verifying identity: {e}")
            raise

    @retry_on_failure(max_retries=2, delay=0.5)
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile information"""
        try:
            response = await self.client.get(f"/identity/users/{user_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching user profile: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching user profile: {e}")
            raise

    # ==================== Marketplace ====================

    @retry_on_failure(max_retries=2, delay=0.5)
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

        try:
            response = await self.client.get(
                "/marketplace/supervisors",
                params={
                    "workflow_type": workflow_type,
                    "min_reputation": min_reputation
                }
            )
            response.raise_for_status()
            result = response.json()
            return result.get("supervisors", [])
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error finding supervisors: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"HTTP error finding supervisors: {e}")
            raise

    @retry_on_failure(max_retries=2, delay=0.5)
    async def request_supervisor(
        self,
        supervisor_id: str,
        workflow_id: str
    ) -> bool:
        """Request a specific supervisor for a workflow"""
        logger.info(f"Requesting supervisor {supervisor_id} for workflow {workflow_id}")
        
        try:
            response = await self.client.post(
                "/marketplace/supervisors/request",
                json={
                    "supervisor_id": supervisor_id,
                    "workflow_id": workflow_id
                }
            )
            response.raise_for_status()
            return True
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error requesting supervisor: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"HTTP error requesting supervisor: {e}")
            raise


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
