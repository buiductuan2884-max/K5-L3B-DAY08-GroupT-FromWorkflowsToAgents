"""Shape C — orchestrator plus read-only investigators. Student work.

1. Build a handoff with `lab8.handoff.make_handoff`. Allowed tools are read-only.
   Never put parent_secret, raw headers, or the full claim row into facts.
2. `lab8.runtime.run_readonly_investigators` runs those tools.
3. The orchestrator quotes from the investigator's order view and calls
   `durability.issue_refund`. Investigators have no write registry.
   Pass the full quote; the host subtracts earlier refunds on the same order.
   `lookup_refund_history` is a read-only tool you may hand to an investigator.
4. Trace the sanitized handoff, not the parent context.

An LLM summary of the parent context is not a sanitizer. Use the allowlist.

Trace contract v1 (docs/contracts.md): return a trace_path to a JSON file written in this run,
{"run_id": <same run_id>, "events": [...]}, on every return path including early
ones. `lab8.trace.Trace` does this; your own tracer is fine if it matches.
"""

from __future__ import annotations

import sqlite3

from lab8 import durability
from lab8.db import connect
from lab8.handoff import make_handoff
from lab8.mock_llm import complete
from lab8.runtime import run_readonly_investigators
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish, safe_dump
from lab8.tools import get_claim_view, tool_cost
from lab8.trace import Trace

SHAPE = "orchestrator"

# Read-only tools for the investigator. lookup_order must come before
# compute_compensation because the runner feeds the order view into the quote.
INVESTIGATOR_TOOLS = [
    "lookup_order",
    "lookup_policy",
    "lookup_refund_history",
    "compute_compensation",
]


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    conn = connect(store_path)
    try:
        return _run(conn, claim_id, seed=seed, crash_at=crash_at)
    finally:
        conn.close()


def _run(conn: sqlite3.Connection, claim_id: str, *, seed: int, crash_at: str | None) -> RunResult:
    budget = Budget()
    trace = Trace(make_run_id(SHAPE, claim_id, seed))

    def done(status: str, amount: int = 0, reason: str | None = None) -> RunResult:
        # The model only drafts the reply text. Its prompt carries no claim data.
        complete(budget, seed=seed, purpose="draft", prompt=f"status={status} amount={amount}")
        trace.add("decision", {"status": status, "proposal_amount": amount, "reason": reason})
        return finish(
            conn,
            shape=SHAPE,
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=amount,
            budget=budget,
            trace=trace,
            error_reason=reason,
        )

    # 1. Orchestrator reads the claim view. Ticket text is never traced or used for money.
    budget.add_tool(tool_cost())
    claim = get_claim_view(conn, claim_id)
    if not claim["found"]:
        return done("failed", reason="unknown_claim")
    # Blank-only counts as missing. The id itself is not normalized: the host looks it up raw,
    # so a padded or lookalike id stays unknown and escalates.
    has_order_id = bool((claim["order_id"] or "").strip())
    trace.add("claim", {"claim_id": claim_id, "has_order_id": has_order_id})

    # 2. No usable order id on the claim row -> ask. Never take an order id from the ticket.
    if not has_order_id:
        return done("needs_info", reason="missing_order_id")

    # 3. Handoff: allowlist only, read-only tools. No parent secret, headers, or claim row.
    handoff = make_handoff(
        request_id=f"REQ-{claim_id}",
        claim_id=claim_id,
        task="check_applicable_policy",
        facts={},
        allowed_tools=INVESTIGATOR_TOOLS,
    )
    trace.add("handoff", safe_dump(handoff))

    # 4. Investigator runs the read tools. We trace a few chosen fields, not the raw result,
    #    because the raw result also holds the claim view with the ticket.
    investigated = run_readonly_investigators(conn, budget, handoff, principal_id=claim["principal_id"])
    tools = investigated["tools"]
    order_view = tools.get("lookup_order") or {}
    history = tools.get("lookup_refund_history") or {}
    trace.add(
        "investigator",
        {
            "order_visible": bool(order_view.get("visible")),
            "order_reason": order_view.get("reason"),
            "refunded_vnd": history.get("refunded_vnd"),
            "policy_count": len((tools.get("lookup_policy") or {}).get("policies") or []),
        },
    )
    if not order_view.get("visible"):
        return done("escalated", reason=order_view.get("reason"))

    # 5. Quote comes from code (compute_compensation), not from the model or the ticket.
    quote = tools.get("compute_compensation") or {}
    proposal = int(quote.get("amount_vnd") or 0)
    trace.add("quote", {"amount_vnd": proposal, "reason": quote.get("reason"), "clause_ids": quote.get("clause_ids")})
    if proposal <= 0:
        return done("denied", reason=quote.get("reason"))

    # 6. Full quote to the host gate. The host subtracts earlier refunds on the order.
    #    InjectedCrash must propagate so a resume can be tested.
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
