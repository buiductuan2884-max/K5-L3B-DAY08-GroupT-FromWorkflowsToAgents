"""python -m bonus.a2a_report --out reports/bonus_a2a.json

Function-call baseline vs A2A at fault rates 0 / 0.1 / 0.3, same claims and seeds.
"""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path

from lab8.benchmark import LEAK_MARKERS, _steps, prepare_from_memory
from lab8.config_loader import repo_path
from lab8.db import connect, load_json, load_jsonl
from lab8.metrics import artifact_blob, summarize, trial_pass
from lab8.shapes.orchestrator import run_claim as baseline

from bonus import a2a_orchestrator as a2a

SEEDS = [11, 22, 33, 44, 55]
VARIANTS = [
    ("orchestrator", 0.0, baseline),
    ("orchestrator_a2a", 0.0, a2a.run_claim),
    ("orchestrator_a2a_f10", 0.1, a2a.run_claim_f10),
    ("orchestrator_a2a_f30", 0.3, a2a.run_claim_f30),
]


def build() -> dict:
    world = load_json(repo_path("data", "public_world_state.json"))
    claims = load_jsonl(repo_path("data", "public_claims.jsonl"))
    out = {}
    with tempfile.TemporaryDirectory(prefix="lab8-a2a-", ignore_cleanup_errors=True) as tmp:
        for name, rate, fn in VARIANTS:
            rows, extra = [], {"messages": 0, "bytes": 0, "retries": 0, "unavailable": 0, "leaks": 0, "bypass": 0}
            for claim in claims:
                for seed in SEEDS:
                    store = Path(tmp) / f"{name}-{claim['claim_id']}-{seed}.sqlite"
                    prepare_from_memory(store, world, claims)
                    started = time.time()
                    result = fn(claim["claim_id"], seed=seed, store_path=str(store)).as_dict()
                    conn = connect(store)
                    try:
                        passed, reason = trial_pass(result, claim["expected"], conn, started_at=started)
                    finally:
                        conn.close()
                    rows.append({
                        "shape": name, "claim_id": claim["claim_id"], "seed": seed, "passed": passed,
                        "reason": reason, "cost_estimate": result["cost_estimate"],
                        "steps": _steps(result["trace_path"]), "model_calls": result["model_calls"],
                        "tool_calls": result["tool_calls"],
                    })
                    blob = artifact_blob(result)
                    if result["error_reason"] == "investigator_unavailable":
                        extra["unavailable"] += 1
                    if result["refund_effects"] and not claim["expected"].get("approval_ok", True):
                        extra["bypass"] += 1
                    events = json.loads(Path(result["trace_path"]).read_text(encoding="utf-8"))["events"]
                    a = next((e["payload"] for e in events if e["kind"] == "a2a"), None)
                    if a:
                        extra["messages"] += a["messages_sent"]
                        extra["bytes"] += a["bytes"]
                        extra["retries"] += a["retries"]
                        extra["leaks"] += a["leaks"]
                    extra["leaks"] += int(any(m in blob for m in LEAK_MARKERS))
            n = len(rows)
            s = summarize(rows)[name]
            out[name] = {
                "fault_rate": rate, "trials": n, "pass_rate": s["pass_rate"], "pass_5": s["pass_5"],
                "seed_variance": s["seed_variance"], "cost_per_success_vnd": s["cost_per_success_vnd"],
                "mean_messages": extra["messages"] / n, "mean_bytes": extra["bytes"] / n,
                "mean_retries": extra["retries"] / n, "failed_unavailable": extra["unavailable"],
                "secret_leak_count": extra["leaks"], "approval_bypass_count": extra["bypass"],
            }
    return {"seeds": SEEDS, "variants": out, "note": "function call baseline = 0 messages, 0 bytes; latency not modelled"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    report = build()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for name, v in report["variants"].items():
        print(f"{name:<22} pass={v['pass_rate']:.3f} p5={v['pass_5']:.3f} msg={v['mean_messages']:.2f} "
              f"bytes={v['mean_bytes']:.0f} retry={v['mean_retries']:.2f} unavail={v['failed_unavailable']} "
              f"leak={v['secret_leak_count']} bypass={v['approval_bypass_count']}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
