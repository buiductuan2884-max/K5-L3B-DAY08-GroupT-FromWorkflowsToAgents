"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item
from lab9.graders import GRADERS


def _finite(value) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value)


def _ratchet(current: dict, previous: dict, where: str) -> list[str]:
    problems = []
    if previous.get("blocking") and not current.get("blocking"):
        problems.append(f"ratchet {where}: blocking removed")
    for key in ("kind", "grader", "level", "metric"):
        if key in previous and current.get(key) != previous[key]:
            problems.append(f"ratchet {where}: {key} changed")
    old = previous.get("threshold", previous)
    new = current.get("threshold", current)
    for key in ("min", "max", "max_increase"):
        if key in old and (key not in new or not _finite(new[key]) or
                           (new[key] < old[key] if key == "min" else new[key] > old[key])):
            problems.append(f"ratchet {where}: {key} loosened/removed")
    if old.get("no_significant_drop") and not new.get("no_significant_drop"):
        problems.append(f"ratchet {where}: no_significant_drop removed")
    return problems


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    problems = []
    try:
        metrics = spec["metrics"]
        mids = [m["id"] for m in metrics]
        if not mids or len(set(mids)) != len(mids):
            problems.append("spec metrics empty or duplicated")
        for m in metrics:
            if not isinstance(m.get("blocking"), bool):
                problems.append(f"metric {m['id']}: blocking must be boolean")
            th = m.get("threshold", {})
            for key in ("min", "max", "max_increase"):
                if key in th and (not _finite(th[key]) or isinstance(th[key], bool)):
                    problems.append(f"metric {m['id']}: invalid {key}")
            if "no_significant_drop" in th and not isinstance(th["no_significant_drop"], bool):
                problems.append(f"metric {m['id']}: invalid no_significant_drop")
            if m.get("blocking") and not any(k in th for k in ("min", "max", "max_increase", "no_significant_drop")):
                problems.append(f"metric {m['id']}: no blocking criterion")
        slice_ids = [(s["name"], s["metric"]) for s in spec.get("slices", [])]
        if len(set(slice_ids)) != len(slice_ids):
            problems.append("duplicate slice constraints")
        for s in spec.get("slices", []):
            if s["metric"] not in mids:
                problems.append("slice references an unconfigured metric")
            for key in ("min", "max"):
                if key in s and not _finite(s[key]):
                    problems.append("invalid slice threshold")
        bs = spec.get("bootstrap", {})
        if bs.get("method", "percentile") != "percentile":
            problems.append("bootstrap must use percentile")
        n = bs.get("n_resamples", 1000)
        if isinstance(n, bool) or not isinstance(n, int) or n < 1:
            problems.append("invalid bootstrap n_resamples")
        if not _finite(bs.get("confidence", 0.95)) or not 0 < bs.get("confidence", 0.95) < 1:
            problems.append("invalid bootstrap confidence")
        pair_sets, slice_maps = [], []
        for name, report in (("PR", pr), ("baseline", base)):
            manifest, rows, scores = report["manifest"], report["rows"], report["metrics"]
            if not isinstance(manifest.get("eval_set_sha"), str) or not manifest["eval_set_sha"]:
                problems.append(f"{name}: missing eval_set_sha")
            if not isinstance(report["evaluator_failures"], list) or report["evaluator_failures"]:
                problems.append(f"{name}: evaluator_failures nonempty or malformed")
            count, seeds = manifest["items"], manifest["seeds"]
            if isinstance(count, bool) or not isinstance(count, int) or count < 1:
                problems.append(f"{name}: invalid item count")
            if not isinstance(seeds, list) or not seeds or any(type(s) is not int for s in seeds) or len(set(seeds)) != len(seeds):
                problems.append(f"{name}: invalid/duplicate seeds")
            if "seeds" in spec and set(seeds) != set(spec["seeds"]):
                problems.append(f"{name}: seeds differ from spec")
            if not isinstance(rows, list) or len(rows) != count * len(seeds):
                problems.append(f"{name}: rows != items x seeds")
            pairs = [(r["item_id"], r["seed"]) for r in rows]
            items = {i for i, _ in pairs}
            if any(not isinstance(i, str) or not i or type(seed) is not int for i, seed in pairs):
                problems.append(f"{name}: invalid row identity")
            if len(set(pairs)) != len(pairs):
                problems.append(f"{name}: duplicate item/seed")
            if len(items) != count or set(pairs) != {(i, s) for i in items for s in seeds}:
                problems.append(f"{name}: incomplete Cartesian item/seed grid")
            pair_sets.append(set(pairs))
            if any(not _finite(v) for v in scores.values()):
                problems.append(f"{name}: nonfinite/missing aggregate")
            for mid in mids:
                if mid not in scores or not _finite(scores[mid]):
                    problems.append(f"{name}: missing/invalid metric {mid}")
            # Registered code graders and any additional row metric must be present
            # on EVERY row, including nonblocking metrics. Never drop crashed grades.
            row_ids = [mid for mid in mids if mid in GRADERS or any(mid in r for r in rows)]
            item_slices = {}
            for r in rows:
                tags = r.get("slices", [])
                if not isinstance(tags, list) or any(not isinstance(t, str) for t in tags) or len(set(tags)) != len(tags):
                    problems.append(f"{name}: malformed slices")
                    continue
                tags = frozenset(tags)
                if r["item_id"] in item_slices and item_slices[r["item_id"]] != tags:
                    problems.append(f"{name}: slices differ across seeds")
                item_slices[r["item_id"]] = tags
                for mid in row_ids:
                    if not _finite(r.get(mid)):
                        problems.append(f"{name}: invalid row grade {mid}")
                    elif mid in GRADERS and r[mid] not in (0, 1):
                        problems.append(f"{name}: nonbinary row grade {mid}")
                if "cost_per_success" in mids and (not _finite(r.get("cost")) or r["cost"] < 0):
                    problems.append(f"{name}: invalid row cost")
            slice_maps.append(item_slices)
            # Recompute claimed aggregates from evidence; reject fabricated summaries.
            if rows and all(all(_finite(r.get(mid)) for mid in row_ids) for r in rows):
                for mid in row_ids:
                    vals = [r[mid] for r in rows]
                    kind = next(m.get("kind") for m in metrics if m["id"] == mid)
                    expected = sum(vals) if kind == "safety" else round(sum(vals) / len(vals), 4)
                    if _finite(scores.get(mid)) and abs(scores[mid] - expected) > 0.00005:
                        problems.append(f"{name}: aggregate {mid} disagrees with rows")
                if "pass_rate" in row_ids:
                    by_item = {i: [bool(r["pass_rate"]) for r in rows if r["item_id"] == i] for i in items}
                    for mid in mids:
                        match = re.fullmatch(r"pass_(at|hat)_(\d+)", mid)
                        if mid == "pass_5":
                            expected = sum(all(v) for v in by_item.values()) / len(by_item)
                        elif match:
                            fn = stats.pass_at_k if match[1] == "at" else stats.pass_hat_k
                            expected = sum(fn(len(v), sum(v), int(match[2])) for v in by_item.values()) / len(by_item)
                        elif mid == "cost_per_success" and all(_finite(r.get("cost")) for r in rows):
                            passes = sum(r["pass_rate"] for r in rows)
                            expected = sum(r["cost"] for r in rows) / passes if passes else None
                        else:
                            continue
                        if expected is None or not _finite(scores.get(mid)) or abs(scores[mid] - round(expected, 4)) > 0.00005:
                            problems.append(f"{name}: derived metric {mid} disagrees with rows")
        if pair_sets[0] != pair_sets[1]:
            problems.append("PR (item_id, seed) set differs from baseline")
        if slice_maps[0] != slice_maps[1]:
            problems.append("PR slice assignments differ from baseline")
        if pr["manifest"].get("eval_set_sha") != base["manifest"].get("eval_set_sha"):
            problems.append("eval_set_sha differs")
        for report in (pr, base):
            if "eval_set_version" in report["manifest"] and report["manifest"]["eval_set_version"] != spec.get("eval_set_version"):
                problems.append("manifest eval_set_version differs from spec")
        base_spec = base_spec if base_spec is not None else base["manifest"].get("metric_spec")
        if base_spec and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
            old_metrics = {m["id"]: m for m in base_spec["metrics"]}
            new_metrics = {m["id"]: m for m in metrics}
            for mid, old in old_metrics.items():
                if mid not in new_metrics:
                    problems.append(f"ratchet metric {mid} removed")
                else:
                    problems.extend(_ratchet(new_metrics[mid], old, mid))
            current = {(s["name"], s["metric"]): s for s in spec.get("slices", [])}
            for old in base_spec.get("slices", []):
                key = old["name"], old["metric"]
                if key not in current:
                    problems.append(f"ratchet slice {key} removed")
                else:
                    problems.extend(_ratchet(current[key], old, str(key)))
            old_bs = base_spec.get("bootstrap", {})
            for key in ("method", "rng", "n_resamples", "confidence"):
                if key in old_bs and bs.get(key) != old_bs[key]:
                    problems.append(f"ratchet bootstrap {key} changed")
            for key in ("eval_set", "labels", "adversarial_pack", "seeds", "pass_k"):
                if key in base_spec and spec.get(key) != base_spec[key]:
                    problems.append(f"ratchet {key} changed on same eval-set version")
    except (KeyError, TypeError, ValueError, AttributeError, ZeroDivisionError) as exc:
        problems.append(f"malformed evaluation evidence: {type(exc).__name__}: {exc}")
    return list(dict.fromkeys(problems))


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for s in spec.get("slices", []):
        sid = f"slice:{s['name']}/{s['metric']}"
        left = [r for r in pr.get("rows", []) if s["name"] in (r.get("slices") or [])]
        right = [r for r in base.get("rows", []) if s["name"] in (r.get("slices") or [])]
        evidence_ok = bool(left) and bool(right) and all(_finite(r.get(s["metric"])) for r in [*left, *right])
        evidence_ok &= {(r.get("item_id"), r.get("seed")) for r in left} == {(r.get("item_id"), r.get("seed")) for r in right}
        if not evidence_ok:
            if s.get("blocking"):
                blocked.append(sid)
            lines.append(f"  {sid} invalid or empty slice evidence {'BLOCK' if s.get('blocking') else 'warn'}")
            continue
        a, b = per_item(pr, s["metric"], s["name"]), per_item(base, s["metric"], s["name"])
        valid = bool(a) and set(a) == set(b) and all(_finite(v) for v in [*a.values(), *b.values()])
        note, failed = "", not valid
        if valid:
            value = sum(a.values()) / len(a)
            failed = ("min" in s and value < s["min"]) or ("max" in s and value > s["max"])
            note = f"value={value:.4f}"
            if s.get("no_significant_drop"):
                keys = sorted(a)
                d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                    n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027), confidence=bs.get("confidence", 0.95))
                failed |= hi < 0
                note += f" Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
        else:
            note = "missing, empty or invalid slice evidence"
        if failed and s.get("blocking"):
            blocked.append(sid)
        lines.append(f"  {sid} {note} {'BLOCK' if failed and s.get('blocking') else 'warn' if failed else 'ok'}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid) is not None:
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                                               confidence=bs.get("confidence", 0.95))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    try:
        pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
        base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
        base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
        blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"  INTEGRITY unreadable report/spec: {exc}")
        print("exit 1 — blocked: integrity")
        return 1
    print(f"gate: PR {pr.get('run_id', '?')} vs main {base.get('run_id', '?')} · eval set {pr.get('manifest', {}).get('eval_set_sha', '?')}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
