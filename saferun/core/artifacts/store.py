"""
Local Artifact Store

x402 facilitator endpoints (e.g. pay.openfacilitator.io) do not provide
application-level artifact storage. SafeRun stores checkpoint artifacts locally
and references them by content-addressed URI.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
import hashlib
import json
from datetime import datetime

from loguru import logger


@dataclass(frozen=True)
class StoredArtifact:
    artifact_id: str
    uri: str
    content_hash: str
    size_bytes: int
    created_at: str
    metadata: Dict[str, Any]


class ArtifactStore:
    """
    Content-addressed artifact storage backed by the local filesystem.

    Files are written under:
      <base_dir>/<content_hash>.json
    """

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"ArtifactStore initialized at {self.base_dir}")

    def _hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def create(self, artifact_type: str, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        content_hash = self._hash(content)
        artifact_id = f"artifact_{content_hash[:16]}"
        uri = f"saferun://artifacts/{content_hash}"
        record = {
            "artifact_id": artifact_id,
            "uri": uri,
            "type": artifact_type,
            "content_hash": content_hash,
            "size_bytes": len(content.encode("utf-8")),
            "metadata": metadata,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "content": content,
        }

        path = self.base_dir / f"{content_hash}.json"
        # Overwrite is safe because content-addressed; identical content_hash means identical content.
        path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        logger.info(f"Artifact stored locally: {uri}")
        return {k: record[k] for k in ("artifact_id", "uri", "type", "content_hash", "size_bytes", "metadata", "created_at")}

    def get(self, artifact_uri: str) -> Dict[str, Any]:
        if not artifact_uri.startswith("saferun://artifacts/"):
            raise ValueError(f"Unsupported artifact URI: {artifact_uri}")
        content_hash = artifact_uri.split("/")[-1]
        path = self.base_dir / f"{content_hash}.json"
        if not path.exists():
            raise FileNotFoundError(f"Artifact not found: {artifact_uri}")
        record = json.loads(path.read_text(encoding="utf-8"))
        return record

