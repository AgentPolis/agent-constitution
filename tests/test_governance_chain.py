"""Tests for GovernanceChain — hash-chained governance records."""

import json

import pytest

from constitution.governance_chain import (
    GovernanceChain,
    GovernanceRecord,
    VerifyResult,
    _genesis_hash,
)


class TestGovernanceRecord:
    def test_seal_sets_hash(self):
        r = GovernanceRecord(
            record_id="r1",
            chain_id="c1",
            event_type="assessment",
            timestamp="2026-04-14T00:00:00Z",
            payload={"score": 72},
            prev_hash="abc",
        )
        assert r.record_hash == ""
        r.seal()
        assert r.record_hash != ""
        assert len(r.record_hash) == 64  # SHA-256 hex

    def test_compute_hash_is_deterministic(self):
        r = GovernanceRecord(
            record_id="r1",
            chain_id="c1",
            event_type="assessment",
            timestamp="2026-04-14T00:00:00Z",
            payload={"score": 72},
            prev_hash="abc",
        )
        assert r.compute_hash() == r.compute_hash()

    def test_different_payload_different_hash(self):
        base = dict(
            record_id="r1",
            chain_id="c1",
            event_type="assessment",
            timestamp="2026-04-14T00:00:00Z",
            prev_hash="abc",
        )
        r1 = GovernanceRecord(**base, payload={"score": 72})
        r2 = GovernanceRecord(**base, payload={"score": 73})
        assert r1.compute_hash() != r2.compute_hash()

    def test_to_dict_roundtrip(self):
        r = GovernanceRecord(
            record_id="r1",
            chain_id="c1",
            event_type="verdict",
            timestamp="2026-04-14T00:00:00Z",
            payload={"verdict": "proceed"},
            prev_hash="abc",
        )
        r.seal()
        d = r.to_dict()
        r2 = GovernanceRecord.from_dict(d)
        assert r2.record_hash == r.record_hash
        assert r2.payload == r.payload

    def test_signature_field_preserved(self):
        r = GovernanceRecord(
            record_id="r1",
            chain_id="c1",
            event_type="verdict",
            timestamp="2026-04-14T00:00:00Z",
            payload={},
            prev_hash="abc",
            signature="future-ed25519-sig",
        )
        d = r.to_dict()
        assert d["signature"] == "future-ed25519-sig"
        r2 = GovernanceRecord.from_dict(d)
        assert r2.signature == "future-ed25519-sig"

    def test_signature_omitted_when_none(self):
        r = GovernanceRecord(
            record_id="r1",
            chain_id="c1",
            event_type="verdict",
            timestamp="2026-04-14T00:00:00Z",
            payload={},
            prev_hash="abc",
        )
        d = r.to_dict()
        assert "signature" not in d


class TestGovernanceChain:
    def test_empty_chain_verifies(self):
        chain = GovernanceChain()
        result = chain.verify()
        assert result.valid
        assert result.records_checked == 0

    def test_single_record_verifies(self):
        chain = GovernanceChain()
        chain.append("assessment", {"score": 72})
        result = chain.verify()
        assert result.valid
        assert result.records_checked == 1

    def test_multi_record_chain_verifies(self):
        chain = GovernanceChain()
        chain.append("assessment", {"score": 72})
        chain.append("challenge", {"challenges": ["c1", "c2", "c3"]})
        chain.append("defense", {"defenses": ["d1", "d2", "d3"]})
        chain.append("verdict", {"verdict": "proceed", "score_delta": 8})
        result = chain.verify()
        assert result.valid
        assert result.records_checked == 4

    def test_head_hash_updates(self):
        chain = GovernanceChain()
        h0 = chain.head_hash
        assert h0 == chain.genesis_hash
        chain.append("assessment", {"score": 72})
        h1 = chain.head_hash
        assert h1 != h0
        chain.append("verdict", {"verdict": "proceed"})
        h2 = chain.head_hash
        assert h2 != h1

    def test_prev_hash_links_correctly(self):
        chain = GovernanceChain()
        r1 = chain.append("assessment", {"score": 72})
        r2 = chain.append("verdict", {"verdict": "proceed"})
        assert r1.prev_hash == chain.genesis_hash
        assert r2.prev_hash == r1.record_hash


class TestTamperDetection:
    def test_modified_payload_detected(self):
        chain = GovernanceChain()
        chain.append("assessment", {"score": 72})
        chain.append("verdict", {"verdict": "proceed", "score_delta": 8})

        # Tamper: change score after the fact
        chain.records[0].payload["score"] = 99

        result = chain.verify()
        assert not result.valid
        assert len(result.errors) >= 1
        assert "record_hash mismatch" in result.errors[0]

    def test_modified_prev_hash_detected(self):
        chain = GovernanceChain()
        chain.append("assessment", {"score": 72})
        chain.append("verdict", {"verdict": "proceed"})

        # Tamper: break the link
        chain.records[1].prev_hash = "tampered"

        result = chain.verify()
        assert not result.valid

    def test_deleted_record_detected(self):
        chain = GovernanceChain()
        chain.append("assessment", {"score": 72})
        chain.append("challenge", {"challenges": ["c1"]})
        chain.append("verdict", {"verdict": "proceed"})

        # Tamper: remove middle record
        del chain.records[1]

        result = chain.verify()
        assert not result.valid

    def test_reordered_records_detected(self):
        chain = GovernanceChain()
        chain.append("assessment", {"score": 72})
        chain.append("challenge", {"challenges": ["c1"]})
        chain.append("verdict", {"verdict": "proceed"})

        # Tamper: swap records
        chain.records[1], chain.records[2] = chain.records[2], chain.records[1]

        result = chain.verify()
        assert not result.valid


class TestArtifactExport:
    def _make_chain(self) -> GovernanceChain:
        chain = GovernanceChain(chain_id="test-chain-001")
        chain.append("assessment", {"score": 72, "scenario": "deploy"})
        chain.append("challenge", {"challenges": ["no canary", "no rollback", "auth risk"]})
        chain.append("defense", {"defenses": ["canary planned", "rollback exists", "auth scoped"]})
        chain.append("verdict", {"verdict": "proceed_with_caution", "score_delta": -21})
        return chain

    def test_artifact_contains_required_fields(self):
        chain = self._make_chain()
        artifact = chain.to_artifact()
        assert artifact["artifact_version"] == "1.0"
        assert artifact["chain_id"] == "test-chain-001"
        assert artifact["integrity"] is True
        assert artifact["chain_root_hash"] == chain.head_hash
        assert len(artifact["records"]) == 4

    def test_artifact_is_json_serializable(self):
        chain = self._make_chain()
        artifact = chain.to_artifact()
        serialized = json.dumps(artifact)
        deserialized = json.loads(serialized)
        assert deserialized["chain_id"] == "test-chain-001"

    def test_verify_artifact_offline(self):
        chain = self._make_chain()
        artifact = chain.to_artifact()
        result = GovernanceChain.verify_artifact(artifact)
        assert result.valid
        assert result.records_checked == 4

    def test_verify_artifact_detects_tamper(self):
        chain = self._make_chain()
        artifact = chain.to_artifact()
        # Tamper with the exported artifact
        artifact["records"][0]["payload"]["score"] = 99
        result = GovernanceChain.verify_artifact(artifact)
        assert not result.valid

    def test_from_artifact_roundtrip(self):
        chain = self._make_chain()
        artifact = chain.to_artifact()
        restored = GovernanceChain.from_artifact(artifact)
        assert restored.chain_id == chain.chain_id
        assert len(restored.records) == len(chain.records)
        assert restored.verify().valid

    def test_chain_root_hash_is_pinnable(self):
        """chain_root_hash should be stable and usable as an external anchor."""
        chain = self._make_chain()
        artifact = chain.to_artifact()
        root = artifact["chain_root_hash"]
        assert len(root) == 64  # SHA-256 hex
        # Re-export produces same root
        assert chain.to_artifact()["chain_root_hash"] == root


class TestJsonlSerialization:
    def test_roundtrip(self):
        chain = GovernanceChain(chain_id="jsonl-test")
        chain.append("assessment", {"score": 72})
        chain.append("verdict", {"verdict": "proceed"})
        jsonl = chain.to_jsonl()
        restored = GovernanceChain.from_jsonl("jsonl-test", jsonl)
        assert len(restored.records) == 2
        assert restored.verify().valid


class TestGateHookChainIntegration:
    def test_debate_produces_chain(self):
        from constitution import BaseAgent, Constitution, GovernanceGateHook

        rules = Constitution.default()
        critic = BaseAgent(role="critic", goal="Challenge", constitution=rules)
        defender = BaseAgent(role="defender", goal="Defend", constitution=rules)
        judge = BaseAgent(role="judge", goal="Judge", constitution=rules)
        gate = GovernanceGateHook(
            challenger=critic, defender=defender, judge=judge
        )
        agent = BaseAgent(role="analyst", goal="Evaluate", constitution=rules, hooks=[gate])

        agent.run("Should we deploy the billing-auth hotfix?")

        if gate.last_result is not None:
            # Debate triggered — chain should exist
            assert gate.last_chain is not None
            assert len(gate.last_chain.records) >= 2  # at least assessment + verdict
            result = gate.last_chain.verify()
            assert result.valid
            # Artifact should be exportable
            artifact = gate.last_chain.to_artifact()
            assert artifact["integrity"] is True
            assert len(artifact["chain_root_hash"]) == 64
