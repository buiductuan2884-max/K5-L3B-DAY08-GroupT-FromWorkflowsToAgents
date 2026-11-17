"""Orchestrator that talks to a remote (A2A-style) investigator over a faulty transport.

Same business flow as lab8/shapes/orchestrator.py. Only this module writes (via the host gate).
Variants: run_claim (fault 0), run_claim_f10, run_claim_f30.
"""

from __future__ import annotations

from lab8 import durability
from lab8.db import connect
from lab8.handoff import make_handoff
from lab8.mock_llm import complete
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish, safe_dump
from lab8.shapes.orchestrator import INVESTIGATOR_TOOLS
from lab8.tools import get_claim_view, tool_cost
from lab8.trace import Trace

from bonus.a2a_investigator import RemoteInvestigator
from bonus.a2a_transport import Transport

MAX_ATTEMPTS = 3
LAST_TRANSPORT: Transport | None = None  # for tests and the report: envelopes of the last run


def _run(claim_id: str, *, seed: int, store_path: str, crash_at: str | None, fault_rate: float, shape: str) -> RunResult:
    global LAST_TRANSPORT
    conn = connect(store_path)
    try:
        budget = Budget()
        trace = Trace(make_run_id(shape, claim_id, seed))

        def done(status: str, amount: int = 0, reason: str | None = None) -> RunResult:
            complete(budget, seed=seed, purpose="draft", prompt=f"status={status} amount={amount}")
            trace.add("decision", {"status": status, "proposal_amount": amount, "reason": reason})
            return finish(conn, shape=shape, claim_id=claim_id, seed=seed, status=status,
                          proposal_amount=amount, budget=budget, trace=trace, error_reason=reason)

        budget.add_tool(tool_cost())
        claim = get_claim_view(conn, claim_id)
        if not claim["found"]:
            return done("failed", reason="unknown_claim")
        trace.add("claim", {"claim_id": claim_id, "has_order_id": bool(claim["order_id"])})
        if not (claim["order_id"] or "").strip():
            return done("needs_info", reason="missing_order_id")

        request_id = f"REQ-{claim_id}"
        handoff = make_handoff(request_id=request_id, claim_id=claim_id, task="check_applicable_policy",
                               facts={}, allowed_tools=INVESTIGATOR_TOOLS)
        trace.add("handoff", safe_dump(handoff))

        transport = LAST_TRANSPORT = Transport(
            RemoteInvestigator(store_path), fault_rate=fault_rate, seed=seed, claim_id=claim_id
        )
        reply, ignored, attempts, late = None, 0, 0, 0
        sent: set[str] = set()
        while reply is None and attempts < MAX_ATTEMPTS:
            attempts += 1
            corr = f"{request_id}:a{attempts}"
            sent.add(corr)
            env = {"task_id": f"TASK-{claim_id}", "correlation_id": corr, "request_id": request_id,
                   "handoff": handoff, "principal_id": claim["principal_id"]}
            for resp in transport.send(env):
                # Any attempt of this request is acceptable: the investigator is read-only and
                # idempotent by request_id, so a late reply carries the same result.
                if reply is None and resp.get("request_id") == request_id and resp.get("correlation_id") in sent:
                    reply = resp
                    late += resp.get("correlation_id") != corr
                else:
                    ignored += 1  # duplicate, or a reply after one was already accepted
        trace.add("a2a", {
            "attempts": attempts, "retries": attempts - 1, "ignored": ignored, "late_reply_accepted": late,
            "messages_sent": transport.stats["sent"], "messages_delivered": transport.stats["delivered"],
            "bytes": transport.stats["bytes_req"] + transport.stats["bytes_resp"],
            "faults": {k: transport.stats[k] for k in ("drop", "duplicate", "delay", "reorder")},
            "delay_ms": transport.stats["delay_ms"], "leaks": transport.stats["leaks"],
            "task_states": (reply or {}).get("states"),
        })
        if reply is None:
            return done("failed", reason="investigator_unavailable")
        if reply["state"] != "completed":
            return done("failed", reason="investigator_rejected")

        # Fold the remote work into our Budget (counted once, from the accepted reply).
        remote = reply["budget"]
        budget.tool_calls += remote["tool_calls"]
        budget.steps += remote["tool_calls"]
        budget.cost_estimate += remote["cost_estimate"]

        tools = reply["tools"]
        order_view = tools.get("lookup_order") or {}
        trace.add("investigator", {
            "order_visible": bool(order_view.get("visible")),
            "order_reason": order_view.get("reason"),
            "refunded_vnd": (tools.get("lookup_refund_history") or {}).get("refunded_vnd"),
            "policy_count": len((tools.get("lookup_policy") or {}).get("policies") or []),
        })
        if not order_view.get("visible"):
            return done("escalated", reason=order_view.get("reason"))

        quote = tools.get("compute_compensation") or {}
        proposal = int(quote.get("amount_vnd") or 0)
        trace.add("quote", {"amount_vnd": proposal, "reason": quote.get("reason"), "clause_ids": quote.get("clause_ids")})
        if proposal <= 0:
            return done("denied", reason=quote.get("reason"))

        try:
            outcome = durability.issue_refund(conn, claim_id, proposal, crash_at=crash_at)
        except durability.InjectedCrash:
            trace.add("crash", {"at": crash_at})
            trace.write()
            raise
        trace.add("issue_refund", {"ok": outcome["ok"], "reason": outcome["reason"]})
        if not outcome["ok"]:
            return done("failed" if outcome["conflict"] else "denied", proposal, outcome["reason"])
        return done("resolved", proposal)
    finally:
        conn.close()


def run_claim(claim_id: str, *, seed: int, store_path: str, crash_at: str | None = None) -> RunResult:
    return _run(claim_id, seed=seed, store_path=store_path, crash_at=crash_at, fault_rate=0.0, shape="orchestrator_a2a")


def run_claim_f10(claim_id: str, *, seed: int, store_path: str, crash_at: str | None = None) -> RunResult:
    return _run(claim_id, seed=seed, store_path=store_path, crash_at=crash_at, fault_rate=0.1, shape="orchestrator_a2a_f10")


def run_claim_f30(claim_id: str, *, seed: int, store_path: str, crash_at: str | None = None) -> RunResult:
    return _run(claim_id, seed=seed, store_path=store_path, crash_at=crash_at, fault_rate=0.3, shape="orchestrator_a2a_f30")
