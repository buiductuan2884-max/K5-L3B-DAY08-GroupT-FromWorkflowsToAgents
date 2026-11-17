"""Shape B — one ReAct agent. Student work.

Use `lab8.runtime.run_react` with max_steps=8. `decide` may pick a read tool.
It must not call `issue_refund`. After the loop, the host validates the quote
and is the only writer.

A decide() that trusts ticket text over the order row will fail hidden claims
where the customer overstates the delay or cites a superseded clause.

Per-order cap: an order may already have been refunded by an earlier claim.
The read tool `lookup_refund_history` shows how much. The host still enforces
the cap, so pass the full quote to `durability.issue_refund`, not a net amount.

Caps: stop at 8 steps. Count model calls in the Budget so cost stays comparable.

Trace contract v1 (docs/contracts.md): return a trace_path to a JSON file written in this run,
{"run_id": <same run_id>, "events": [...]}, on every return path including early
ones. `lab8.trace.Trace` does this; your own tracer is fine if it matches.
"""

from __future__ import annotations

# GroupT P2 — how this shape splits the work:
#
#   decide()  (the "model")  picks the next READ tool from what it has seen so far.
#                            One MockLLM call per step, so cost is counted. It may read
#                            the ticket, but nothing it reads from the ticket is used.
#   run_react (host runtime) runs the tool, caps the loop at 8 steps, rejects write tools.
#   _run()    (shape code)   after the loop, re-derives the outcome from the TOOL RESULTS
#                            (not from the model's "final"), and is the only caller of
#                            durability.issue_refund, with the full quote and crash_at.
#
# Everything lives in this file on purpose: the hidden grader copies only the three shape
# files from the group repo, so a helper module elsewhere would not exist there.

import json
import sqlite3
from typing import Any

from lab8 import durability
from lab8.db import connect
from lab8.mock_llm import complete
from lab8.runtime import run_react
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish
from lab8.trace import Trace

SHAPE = "single"
MAX_STEPS = 8


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
    # Agent memory. run_react only hands decide() the LAST tool result, so decide keeps
    # what it has learned here. The shape reads the same memory after the loop.
    mem: dict[str, Any] = {}
    steps = 0

    def done(status: str, amount: int = 0, reason: str | None = None) -> RunResult:
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

    def decide(seen: dict[str, Any]) -> dict[str, Any]:
        nonlocal steps
        steps += 1
        if seen.get("last_tool"):
            _remember(mem, seen["last_tool"], seen.get("last_result") or {}, trace)
        action = _next_action(claim_id, mem)
        complete(budget, seed=seed, purpose="react", prompt=_prompt(mem))
        trace.add("react_step", {"step": steps, "action": action.get("tool", "final")})
        return action

    # 1. Bounded ReAct loop: read tools only, at most 8 steps.
    #    No write happens in here, so InjectedCrash cannot come from this block; any
    #    error is turned into `failed` because run_claim must never raise.
    try:
        loop = run_react(
            conn,
            budget,
            observation={"claim_id": claim_id, "task": "refund_claim"},
            decide=decide,
            max_steps=MAX_STEPS,
        )
    except Exception as exc:  # noqa: BLE001 — contract: run_claim returns, never raises
        return done("failed", reason=f"react_error:{type(exc).__name__}")
    final = loop["final"] if isinstance(loop.get("final"), dict) else {}
    trace.add("react_stop", {"stopped": loop["stopped"], "steps": steps, "agent_status": final.get("status")})
    if loop["stopped"] != "final":
        return done("failed", reason="step_cap")

    # 2. Code decides from what the tools returned. The model's final is only logged.
    claim = mem.get("claim") or {}
    if not claim.get("found"):
        return done("failed", reason="unknown_claim")
    if not claim.get("order_id"):
        # Do not pull an order id out of the ticket text.
        return done("needs_info", reason="missing_order_id")
    order_view = mem.get("order_view") or {}
    if not order_view.get("visible"):
        return done("escalated", reason=order_view.get("reason") or "order_not_checked")
    quote = mem.get("quote")
    if quote is None:
        return done("failed", reason="quote_missing")
    proposal = int(quote["amount_vnd"])
    if proposal <= 0:
        return done("denied", reason=quote.get("reason"))

    # 3. Host gate with the FULL quote. The host checks the claim's own approval and
    #    subtracts earlier refunds on the order (T13, T14). Crash must propagate (T12).
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


def _next_action(claim_id: str, mem: dict[str, Any]) -> dict[str, Any]:
    """The agent's policy: which read tool next, or stop. Uses tool results only."""
    claim = mem.get("claim")
    if claim is None:
        return {"tool": "get_claim_view", "args": {"claim_id": claim_id}}
    if not claim["found"]:
        return {"final": {"status": "failed"}}
    if not claim["order_id"]:
        return {"final": {"status": "needs_info"}}
    order_view = mem.get("order_view")
    if order_view is None:
        # Order id and principal come from the claim row, never from the ticket.
        return {
            "tool": "lookup_order",
            "args": {"order_id": claim["order_id"], "principal_id": claim["principal_id"]},
        }
    if not order_view.get("visible"):
        return {"final": {"status": "escalated"}}
    if mem.get("quote") is None:
        # Quote from the order row (delay_days, status, fees), not from ticket numbers.
        return {"tool": "compute_compensation", "args": {"order": dict(order_view["order"])}}
    return {"final": {"status": "propose"}}


def _remember(mem: dict[str, Any], tool: str, result: dict[str, Any], trace: Trace) -> None:
    """Store a tool result in agent memory and trace a redacted summary of it."""
    if tool == "get_claim_view":
        mem["claim"] = {
            "found": bool(result.get("found")),
            "order_id": result.get("order_id"),
            "principal_id": result.get("principal_id"),
            "ticket": result.get("ticket") or "",
        }
        # The ticket and principal are not traced: ticket text is untrusted user data.
        trace.add("observe", {"tool": tool, "found": mem["claim"]["found"], "has_order_id": bool(result.get("order_id"))})
    elif tool == "lookup_order":
        mem["order_view"] = result
        # lookup_order already drops phone, address, internal note and item name.
        trace.add("observe", {"tool": tool, "visible": bool(result.get("visible")), "reason": result.get("reason")})
    elif tool == "compute_compensation":
        mem["quote"] = result
        trace.add(
            "observe",
            {
                "tool": tool,
                "amount_vnd": int(result.get("amount_vnd") or 0),
                "reason": result.get("reason"),
                "clause_ids": list(result.get("clause_ids") or []),
            },
        )


def _prompt(mem: dict[str, Any]) -> str:
    """What the simulated model reads this step. Never persisted; no secret is ever loaded."""
    parts = ["task: claim hoan phi; chi duoc goi tool doc; tien do compute_compensation tinh"]
    claim = mem.get("claim")
    if claim and claim["found"]:
        parts.append(f"ticket: {claim['ticket']}")
    order_view = mem.get("order_view")
    if order_view is not None:
        parts.append("order: " + json.dumps(order_view.get("order") or {"visible": False}, ensure_ascii=False))
    quote = mem.get("quote")
    if quote is not None:
        parts.append("quote: " + json.dumps({"amount_vnd": quote["amount_vnd"], "reason": quote["reason"]}))
    return "\n".join(parts)
