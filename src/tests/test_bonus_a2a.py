"""B6: remote investigator over a faulty in-process transport."""

from __future__ import annotations

import json
import time

import pytest

from bonus import a2a_orchestrator as orch
from bonus.a2a_investigator import AGENT_CARD, RemoteInvestigator
from bonus.a2a_transport import Transport
from lab8.db import connect, init_store
from lab8.handoff import make_handoff
from lab8.metrics import trial_pass
from tests.conftest import BY_ID, CLAIMS, WORLD

SEEDS = [11, 22, 33, 44, 55]
TOOLS = ["lookup_order", "lookup_policy", "lookup_refund_history", "compute_compensation"]


def _store(tmp_path, name):
    path = tmp_path / name
    init_store(path, WORLD, CLAIMS).close()
    return str(path)


def _ledger_count(store, claim_id):
    conn = connect(store)
    try:
        return conn.execute("SELECT COUNT(*) AS n FROM refund_ledger WHERE claim_id = ?", (claim_id,)).fetchone()["n"]
    finally:
        conn.close()


def _env(claim_id="C-001", **over):
    handoff = make_handoff(request_id=f"REQ-{claim_id}", claim_id=claim_id, task="check_applicable_policy",
                           facts={}, allowed_tools=TOOLS)
    env = {"task_id": "T", "correlation_id": "c1", "request_id": f"REQ-{claim_id}", "handoff": handoff,
           "principal_id": BY_ID[claim_id]["principal_id"]}
    env.update(over)
    return env


class Scripted(Transport):
    """Drops the first `drop` sends, or hands every request to the agent twice."""

    drop = 0
    twice = False

    def send(self, env):
        self.sent_calls = getattr(self, "sent_calls", 0) + 1
        self.log.append(env)
        if self.sent_calls <= self.drop:
            return []
        n = 2 if self.twice else 1
        return [json.loads(json.dumps(self.agent.handle(json.loads(json.dumps(env))))) for _ in range(n)]


def _patch(monkeypatch, **attrs):
    cls = type("S", (Scripted,), attrs)
    monkeypatch.setattr(orch, "Transport", cls)


def test_duplicate_message_one_result_one_ledger_row(tmp_path, monkeypatch):
    store = _store(tmp_path, "dup.sqlite")
    _patch(monkeypatch, twice=True)
    result = orch.run_claim("C-001", seed=11, store_path=store)
    assert result.status == "resolved"
    assert _ledger_count(store, "C-001") == 1

    agent = RemoteInvestigator(store)
    first, second = agent.handle(_env()), agent.handle(_env(correlation_id="c2"))
    assert agent.computed == 1
    assert first["tools"] == second["tools"] and second["correlation_id"] == "c2"


def test_dropped_message_is_retried_with_same_request_id(tmp_path, monkeypatch):
    store = _store(tmp_path, "drop.sqlite")
    _patch(monkeypatch, drop=2)
    result = orch.run_claim("C-001", seed=11, store_path=store)
    assert result.status == "resolved"
    sent = [e for e in orch.LAST_TRANSPORT.log]
    assert len(sent) == 3 and {e["request_id"] for e in sent} == {"REQ-C-001"}
    assert len({e["correlation_id"] for e in sent}) == 3
    assert _ledger_count(store, "C-001") == 1


def test_all_attempts_dropped_fails_without_refund(tmp_path, monkeypatch):
    store = _store(tmp_path, "dead.sqlite")
    _patch(monkeypatch, drop=99)
    result = orch.run_claim("C-001", seed=11, store_path=store)
    assert (result.status, result.error_reason) == ("failed", "investigator_unavailable")
    assert _ledger_count(store, "C-001") == 0
    assert result.refund_effects == []


def test_no_canary_in_envelopes_or_traces_at_fault_30(tmp_path):
    for claim in CLAIMS:
        for seed in SEEDS:
            store = _store(tmp_path, f"{claim['claim_id']}-{seed}.sqlite")
            result = orch.run_claim_f30(claim["claim_id"], seed=seed, store_path=store)
            wire = json.dumps(orch.LAST_TRANSPORT.log, ensure_ascii=False) if orch.LAST_TRANSPORT else ""
            trace = open(result.trace_path, encoding="utf-8").read()
            assert "CANARY_" not in wire + trace + json.dumps(result.as_dict())


@pytest.mark.parametrize("seed", SEEDS)
def test_fault_zero_passes_every_public_claim(tmp_path, seed):
    for claim in CLAIMS:
        if claim["claim_id"] in ("C-011", "C-012"):
            continue  # multi-run scenarios, covered by the crash/retry suites
        store = _store(tmp_path, f"{claim['claim_id']}.sqlite")
        started = time.time()
        result = orch.run_claim(claim["claim_id"], seed=seed, store_path=store)
        conn = connect(store)
        try:
            passed, reason = trial_pass(result.as_dict(), claim["expected"], conn, started_at=started)
        finally:
            conn.close()
        assert passed, f"{claim['claim_id']} seed {seed}: {reason}"


def test_same_seed_same_result(tmp_path):
    runs = []
    for i in range(2):
        store = _store(tmp_path, f"det{i}.sqlite")
        r = orch.run_claim_f30("C-001", seed=22, store_path=store).as_dict()
        runs.append((r, orch.LAST_TRANSPORT.stats))
    assert runs[0] == runs[1]


def test_investigator_rejects_extra_field_and_write_tool(tmp_path):
    agent = RemoteInvestigator(_store(tmp_path, "rej.sqlite"))
    assert AGENT_CARD["contract_version"] == "handoff.v1"
    bad_field = _env(request_id="R1")
    bad_field["handoff"] = {**bad_field["handoff"], "parent_secret": "x"}
    r1 = agent.handle(bad_field)
    bad_tool = _env(request_id="R2")
    bad_tool["handoff"] = {**bad_tool["handoff"], "allowed_tools": ["issue_refund"]}
    r2 = agent.handle(bad_tool)
    assert r1["state"] == r2["state"] == "failed"
    assert r1["states"] == ["submitted", "failed"]
    assert agent.computed == 0
