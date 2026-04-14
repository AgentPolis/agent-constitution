"""Hash-chained governance records for tamper-evident decision trails.

Each debate produces a chain of GovernanceRecords:
  genesis(chain_id) → assessment → challenge → defense → verdict → [retrospective]

Every record hashes its content + the previous record's hash, forming a
tamper-evident chain. If any record is modified after the fact, verification
fails for every subsequent record.

Design choices:
- No replay verification: LLM outputs are non-deterministic, so replaying
  a debate will never reproduce the same challenges/defenses/verdict.
  The chain proves "this output was not altered after creation", not
  "this output was definitely produced by model X".
- Signature field is reserved but not yet implemented. Without signatures,
  an attacker with write access can recompute the entire chain. Signatures
  (Ed25519 or similar) would close that gap — planned for a future release.
- chain_root_hash in the artifact is designed to be pinned to an external
  system (git commit, CI artifact, S3 object tag) as a trust anchor.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _canonical_json(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _genesis_hash(chain_id: str) -> str:
    return _sha256(f"agent-constitution:genesis:{chain_id}")


@dataclass
class GovernanceRecord:
    """A single event in a governance hash chain."""

    record_id: str
    chain_id: str
    event_type: str  # assessment | challenge | defense | verdict | retrospective
    timestamp: str  # ISO 8601
    payload: dict[str, Any]
    prev_hash: str
    record_hash: str = ""
    signature: str | None = None  # reserved for future Ed25519 signing

    def compute_hash(self) -> str:
        content = _canonical_json(
            {
                "record_id": self.record_id,
                "chain_id": self.chain_id,
                "event_type": self.event_type,
                "timestamp": self.timestamp,
                "payload": self.payload,
                "prev_hash": self.prev_hash,
            }
        )
        return _sha256(content)

    def seal(self) -> None:
        """Compute and set the record hash. Call once after creation."""
        self.record_hash = self.compute_hash()

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "record_id": self.record_id,
            "chain_id": self.chain_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "prev_hash": self.prev_hash,
            "record_hash": self.record_hash,
        }
        if self.signature is not None:
            d["signature"] = self.signature
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GovernanceRecord:
        return cls(
            record_id=d["record_id"],
            chain_id=d["chain_id"],
            event_type=d["event_type"],
            timestamp=d["timestamp"],
            payload=d["payload"],
            prev_hash=d["prev_hash"],
            record_hash=d.get("record_hash", ""),
            signature=d.get("signature"),
        )


@dataclass
class VerifyResult:
    """Result of chain integrity verification."""

    valid: bool
    records_checked: int
    errors: list[str] = field(default_factory=list)


class GovernanceChain:
    """An append-only, hash-linked chain of governance records."""

    def __init__(self, chain_id: str | None = None):
        self.chain_id = chain_id or f"gc-{uuid.uuid4().hex[:12]}"
        self.records: list[GovernanceRecord] = []

    @property
    def genesis_hash(self) -> str:
        return _genesis_hash(self.chain_id)

    @property
    def head_hash(self) -> str:
        """Hash of the latest record, or genesis if chain is empty."""
        if self.records:
            return self.records[-1].record_hash
        return self.genesis_hash

    def append(self, event_type: str, payload: dict[str, Any]) -> GovernanceRecord:
        """Create, seal, and append a new record to the chain."""
        record = GovernanceRecord(
            record_id=f"gr-{uuid.uuid4().hex[:12]}",
            chain_id=self.chain_id,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            payload=payload,
            prev_hash=self.head_hash,
        )
        record.seal()
        self.records.append(record)
        return record

    def verify(self) -> VerifyResult:
        """Verify hash integrity of the entire chain."""
        if not self.records:
            return VerifyResult(valid=True, records_checked=0)

        errors: list[str] = []
        expected_prev = self.genesis_hash

        for i, record in enumerate(self.records):
            if record.prev_hash != expected_prev:
                errors.append(
                    f"Record {i} ({record.event_type}): prev_hash mismatch "
                    f"(expected {expected_prev[:16]}..., got {record.prev_hash[:16]}...)"
                )
            computed = record.compute_hash()
            if record.record_hash != computed:
                errors.append(
                    f"Record {i} ({record.event_type}): record_hash mismatch "
                    f"(expected {computed[:16]}..., got {record.record_hash[:16]}...)"
                )
            expected_prev = record.record_hash

        return VerifyResult(
            valid=len(errors) == 0,
            records_checked=len(self.records),
            errors=errors,
        )

    def to_artifact(self) -> dict[str, Any]:
        """Export chain as a portable, independently verifiable artifact.

        The ``chain_root_hash`` value can be pinned to an external system
        (git commit message, CI artifact, S3 tag) as a trust anchor.
        """
        result = self.verify()
        return {
            "artifact_version": "1.0",
            "chain_id": self.chain_id,
            "genesis_hash": self.genesis_hash,
            "chain_root_hash": self.head_hash,
            "integrity": result.valid,
            "records_checked": result.records_checked,
            "errors": result.errors,
            "records": [r.to_dict() for r in self.records],
        }

    @classmethod
    def verify_artifact(cls, artifact: dict[str, Any]) -> VerifyResult:
        """Verify a portable artifact without the runtime.

        Takes the JSON dict from ``to_artifact()`` and re-checks every
        hash in the chain. No GovernanceChain instance needed.
        """
        records_data = artifact.get("records", [])
        if not records_data:
            return VerifyResult(valid=True, records_checked=0)

        chain_id = artifact.get("chain_id", "")
        expected_prev = _genesis_hash(chain_id)
        errors: list[str] = []

        for i, rd in enumerate(records_data):
            if rd.get("prev_hash") != expected_prev:
                errors.append(
                    f"Record {i}: prev_hash mismatch "
                    f"(expected {expected_prev[:16]}..., got {rd.get('prev_hash', '')[:16]}...)"
                )
            content = _canonical_json(
                {
                    "record_id": rd["record_id"],
                    "chain_id": rd["chain_id"],
                    "event_type": rd["event_type"],
                    "timestamp": rd["timestamp"],
                    "payload": rd["payload"],
                    "prev_hash": rd["prev_hash"],
                }
            )
            computed = _sha256(content)
            if rd.get("record_hash") != computed:
                errors.append(
                    f"Record {i}: record_hash mismatch "
                    f"(expected {computed[:16]}..., got {rd.get('record_hash', '')[:16]}...)"
                )
            expected_prev = rd.get("record_hash", "")

        return VerifyResult(
            valid=len(errors) == 0,
            records_checked=len(records_data),
            errors=errors,
        )

    @classmethod
    def from_artifact(cls, artifact: dict[str, Any]) -> GovernanceChain:
        """Reconstruct a chain from a portable artifact."""
        chain = cls(chain_id=artifact["chain_id"])
        chain.records = [GovernanceRecord.from_dict(rd) for rd in artifact.get("records", [])]
        return chain

    def to_jsonl(self) -> str:
        """Serialize chain as newline-delimited JSON (one record per line)."""
        return "\n".join(json.dumps(r.to_dict(), ensure_ascii=False) for r in self.records)

    @classmethod
    def from_jsonl(cls, chain_id: str, data: str) -> GovernanceChain:
        """Deserialize from JSONL."""
        chain = cls(chain_id=chain_id)
        for line in data.strip().splitlines():
            if line.strip():
                chain.records.append(GovernanceRecord.from_dict(json.loads(line)))
        return chain
