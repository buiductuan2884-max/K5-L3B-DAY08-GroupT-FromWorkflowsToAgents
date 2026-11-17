"""B7: metamorphic checks for the three candidate graders in grader_audit/.

Each check returns a list of issues; an empty list means the relation holds.
Run `python -m bonus.grader_audit --out reports/bonus_grader_audit.json` from src/.
"""

from __future__ import annotations

import argparse
import importlib
import json
import math
import random
from pathlib import Path
from typing import Any, Callable

from lab8.compensation import quote
from lab8.metrics import summarize as _base_summarize

FIXTURES = Path(__file__).resolve().parents[1] / "grader_audit" / "fixtures"
GRADERS = ("grader_a", "grader_b", "grader_c")

# Ratios and means must not move when the trial list is duplicated; totals must double.
RATE_KEYS = (
    "pass_rate",
    "pass_5",
    "seed_pass_rates",
    "seed_variance",
    "seed_min",
    "seed_max",
    "cost_per_success_vnd",
    "mean_steps",
    "mean_model_calls",
    "mean_tool_calls",
)
TOTAL_KEYS = ("trials", "graded_trials", "successes", "total_simulated_cost_vnd")
# Infra trials are not decisions of the shape, so scores over graded trials must not move.
INFRA_KEYS = ("pass_rate", "pass_5", "seed_pass_rates", "successes", "graded_trials")

Summarize = Callable[[list[dict[str, Any]]], dict[str, Any]]


def load(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def grader(name: str) -> Summarize:
    return importlib.import_module(f"grader_audit.{name}").summarize


def _same(x: Any, y: Any) -> bool:
    if isinstance(x, dict) and isinstance(y, dict):
        return x.keys() == y.keys() and all(_same(x[k], y[k]) for k in x)
    if isinstance(x, (int, float)) and isinstance(y, (int, float)):
        return math.isclose(x, y, rel_tol=1e-9, abs_tol=1e-9)
    return x == y


def _issue(shape: str, key: str, a: Any, b: Any, expected: Any) -> dict[str, Any]:
    return {"shape": shape, "key": key, "a": a, "b": b, "expected_b": expected}


def _pair(ra: dict[str, Any], rb: dict[str, Any]):
    """Shapes present in a with their stats in b; a shape missing from b is itself an issue."""
    issues, pairs = [], []
    for shape, sa in ra.items():
        if shape in rb:
            pairs.append((shape, sa, rb[shape]))
        else:
            issues.append(_issue(shape, "shape_missing", True, None, True))
    return issues, pairs


def check_duplicate(summarize: Summarize, fx: dict[str, Any]) -> list[dict[str, Any]]:
    issues, pairs = _pair(summarize(fx["a"]), summarize(fx["b"]))
    for shape, sa, sb in pairs:
        for key in RATE_KEYS:
            if not _same(sa.get(key), sb.get(key)):
                issues.append(_issue(shape, key, sa.get(key), sb.get(key), sa.get(key)))
        for key in TOTAL_KEYS:
            want = 2 * sa[key]
            if not _same(want, sb.get(key)):
                issues.append(_issue(shape, key, sa[key], sb.get(key), want))
    return issues


def check_infra(summarize: Summarize, fx: dict[str, Any]) -> list[dict[str, Any]]:
    issues, pairs = _pair(summarize(fx["a"]), summarize(fx["b"]))
    for shape, sa, sb in pairs:
        for key in INFRA_KEYS:
            if not _same(sa.get(key), sb.get(key)):
                issues.append(_issue(shape, key, sa.get(key), sb.get(key), sa.get(key)))
        # Infra trials are not graded but must stay visible, or the crash rate is hidden.
        k = sum(1 for t in fx["b"] if t["shape"] == shape) - sum(1 for t in fx["a"] if t["shape"] == shape)
        if not _same(sa.get("trials", 0) + k, sb.get("trials")):
            issues.append(_issue(shape, "trials", sa.get("trials"), sb.get("trials"), sa.get("trials", 0) + k))
    return issues


def check_claim_delay(fx: dict[str, Any]) -> list[dict[str, Any]]:
    """Business decision, not summarize: 2 days late -> no entitlement, 3 days late ->
    the SHIP-LATE-03 clause pays the shipping fee."""
    qa = quote(fx["a"]["order"], fx["policies"], as_of=fx["as_of"])
    qb = quote(fx["b"]["order"], fx["policies"], as_of=fx["as_of"])
    fee = int(fx["b"]["order"]["shipping_fee_vnd"])
    checks = [
        ("amount_vnd_delay_2", qa.amount_vnd, 0),
        ("reason_delay_2", qa.reason, "no_entitlement"),
        ("amount_vnd_delay_3", qb.amount_vnd, fee),
        ("reason_delay_3", qb.reason, "entitled"),
        ("clause_delay_3", "SHIP-LATE-03" in qb.clause_ids, True),
    ]
    return [_issue("-", key, None, got, want) for key, got, want in checks if got != want]


def _diff(sa: dict[str, Any], sb: dict[str, Any], shape: str, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    return [_issue(shape, k, sa.get(k), sb.get(k), sa.get(k)) for k in keys if not _same(sa.get(k), sb.get(k))]


ALL_KEYS = RATE_KEYS + TOTAL_KEYS + ("p95_steps",)


def check_permutation(summarize: Summarize) -> list[dict[str, Any]]:
    """New relation (group): the order of trials carries no meaning, so any reordering
    (reversed, or a fixed shuffle) must give identical stats. Inputs: both trial lists
    of the infra fixture, so infra rows are reordered too."""
    issues = []
    for base in (load("metamorphic_infra")["a"], load("metamorphic_infra")["b"]):
        ref = summarize(base)
        shuffled = list(base)
        random.Random(8).shuffle(shuffled)
        for label, variant in (("reversed", base[::-1]), ("shuffled", shuffled)):
            missing, pairs = _pair(ref, summarize(variant))
            issues += [dict(m, order=label, input_size=len(base)) for m in missing]
            for shape, sa, sb in pairs:
                for item in _diff(sa, sb, shape, ALL_KEYS):
                    issues.append(dict(item, order=label, input_size=len(base)))
    return issues


def check_shape_isolation(summarize: Summarize) -> list[dict[str, Any]]:
    """Extra: trials of another shape must not change this shape's stats."""
    base = load("metamorphic_infra")["b"]
    other = [dict(t, shape="swarm", passed=not t["passed"], cost_estimate=99.0) for t in base]
    issues, pairs = _pair(summarize(base), summarize(base + other))
    return issues + [i for shape, sa, sb in pairs for i in _diff(sa, sb, shape, ALL_KEYS)]


def check_flip_one_pass(summarize: Summarize) -> list[dict[str, Any]]:
    """Extra: turning one graded failure into a pass adds exactly one success and 1/n pass rate
    for that trial's shape, and changes nothing for other shapes."""
    base = load("metamorphic_infra")["b"]
    i = next(k for k, t in enumerate(base) if t["passed"] is False and not t.get("infra_error"))
    flipped = [dict(t, passed=True) if k == i else t for k, t in enumerate(base)]
    issues, pairs = _pair(summarize(base), summarize(flipped))
    for shape, sa, sb in pairs:
        if shape != base[i]["shape"]:
            issues += _diff(sa, sb, shape, ALL_KEYS)
            continue
        want = {"successes": sa["successes"] + 1, "pass_rate": sa["pass_rate"] + 1 / sa["graded_trials"]}
        issues += [_issue(shape, k, sa[k], sb.get(k), v) for k, v in want.items() if not _same(v, sb.get(k))]
    return issues


def check_drop_seed_row(summarize: Summarize) -> list[dict[str, Any]]:
    """Extra: remove one seed row of a claim that passes on every seed. That claim no longer
    covers all seeds, so pass_5 must drop by exactly 1/claims (catches a grader that ignores
    seed coverage)."""
    base = load("metamorphic_infra")["a"]
    by_claim: dict[str, list[dict[str, Any]]] = {}
    for t in base:
        by_claim.setdefault(t["claim_id"], []).append(t)
    claim = next(c for c, rows in by_claim.items() if all(r["passed"] for r in rows) and len(rows) > 1)
    drop = next(k for k, t in enumerate(base) if t["claim_id"] == claim)
    issues, pairs = _pair(summarize(base), summarize(base[:drop] + base[drop + 1:]))
    for shape, sa, sb in pairs:
        want = sa["pass_5"] - 1 / len(by_claim)
        if not _same(want, sb.get("pass_5")):
            issues.append(_issue(shape, "pass_5", sa["pass_5"], sb.get("pass_5"), want))
    return issues


def check_relabel(summarize: Summarize) -> list[dict[str, Any]]:
    """Extra: renaming seeds and claim ids consistently changes only the seed keys
    (catches hard-coded seeds such as 55 or the public seed list)."""
    base = load("metamorphic_infra")["b"]
    seed_map = {s: s * 10 + 7 for s in {t["seed"] for t in base}}
    renamed = [dict(t, seed=seed_map[t["seed"]], claim_id="X-" + t["claim_id"]) for t in base]
    issues, pairs = _pair(summarize(base), summarize(renamed))
    for shape, sa, sb in pairs:
        issues += _diff(sa, sb, shape, tuple(k for k in ALL_KEYS if k != "seed_pass_rates"))
        mapped = {str(seed_map[int(s)]): r for s, r in (sa.get("seed_pass_rates") or {}).items()}
        if not _same(mapped, sb.get("seed_pass_rates")):
            issues.append(_issue(shape, "seed_pass_rates", sa.get("seed_pass_rates"), sb.get("seed_pass_rates"), mapped))
    return issues


def check_oracle(summarize: Summarize) -> list[dict[str, Any]]:
    """Extra, not metamorphic: tiny hand-made set whose expected numbers were computed by hand
    from docs/metrics.md (see bonus/oracle_trials.json)."""
    fx = json.loads((Path(__file__).with_name("oracle_trials.json")).read_text(encoding="utf-8"))
    got = summarize(fx["trials"])[fx["shape"]]
    return [_issue(fx["shape"], k, None, got.get(k), v) for k, v in fx["expected"].items() if not _same(v, got.get(k))]


SUMMARIZE_CHECKS: dict[str, Callable[[Summarize], list[dict[str, Any]]]] = {
    "duplicated_list_keeps_rates_doubles_totals": lambda fn: check_duplicate(fn, load("metamorphic_duplicate")),
    "infra_errors_do_not_move_pass_rate": lambda fn: check_infra(fn, load("metamorphic_infra")),
    "NEW_trial_order_does_not_matter": check_permutation,
    "extra_other_shape_does_not_leak": check_shape_isolation,
    "extra_flip_one_fail_to_pass": check_flip_one_pass,
    "extra_drop_seed_row_lowers_pass5": check_drop_seed_row,
    "extra_relabel_seeds_and_claims": check_relabel,
    "extra_oracle_docs_metrics": check_oracle,
}

# Defects named by behavior, read from the code and confirmed by the relations above.
VERDICTS = {
    "grader_a": "Bo trial ha tang dung, nhung cong them mot lan cost cua trial graded DAU TIEN gap o moi claim "
                "(+tong cost dau tien theo claim): chi phi phu thuoc thu tu trial va khong gap doi khi nhan doi danh sach. "
                "Thua huong loi pass_5 cua lab8.metrics.",
    "grader_b": "Khong co loi rieng tren cac quan he da viet. Thua huong loi pass_5 cua lab8.metrics khi mot cap (claim, seed) lap lai.",
    "grader_c": "Tinh trial ha tang la FAIL va dua vao mau so (graded 12 -> 16, pass_rate 0.75 -> 0.5625). "
                "Thua huong loi pass_5 cua lab8.metrics.",
    "lab8_metrics": "Ban goc khong biet infra_error: trial passed=False nao cung bi cham. pass_5 dem so dong "
                    "(len(claim_rows) == len(seeds)) thay vi so seed da phu, nen sai khi (claim, seed) lap lai.",
}


def audit() -> dict[str, Any]:
    table: dict[str, Any] = {}
    for name in GRADERS + ("lab8_metrics",):
        fn = _base_summarize if name == "lab8_metrics" else grader(name)
        table[name] = {}
        for relation, check in SUMMARIZE_CHECKS.items():
            issues = check(fn)
            table[name][relation] = {"holds": not issues, "issues": issues}
    delay = check_claim_delay(load("metamorphic_claim_delay"))
    return {
        "graders": table,
        "delay_days_2_vs_3": {"holds": not delay, "issues": delay},
        "verdicts": VERDICTS,
    }


def _cell(result: dict[str, Any]) -> str:
    if result["holds"]:
        return "dat"
    parts = []
    for i in result["issues"]:
        part = f"{i['key']}: {_fmt(i['b'])} (dung: {_fmt(i['expected_b'])})"
        if part not in parts:
            parts.append(part)
    return "LECH " + "; ".join(parts)


def _fmt(v: Any) -> str:
    if isinstance(v, float):
        return f"{v:.4g}"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{k}: {_fmt(x)}" for k, x in v.items()) + "}"
    return str(v)


def markdown_table(report: dict[str, Any]) -> str:
    names = list(report["graders"])
    lines = ["| Quan he | " + " | ".join(names) + " |", "|---" * (len(names) + 1) + "|"]
    for rel in SUMMARIZE_CHECKS:
        lines.append(f"| {rel} | " + " | ".join(_cell(report["graders"][n][rel]) for n in names) + " |")
    delay = "dat" if report["delay_days_2_vs_3"]["holds"] else "LECH"
    lines.append(f"| delay_days_2_vs_3 (quote, khong qua summarize) | {delay} (chung cho moi ban) |" + " |" * (len(names) - 1))
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--md", default=None, help="also write the grader x relation table as Markdown")
    args = parser.parse_args()
    report = audit()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.md:
        Path(args.md).write_text(markdown_table(report), encoding="utf-8")
    for name, rels in report["graders"].items():
        print(name, {rel: ("holds" if r["holds"] else f"{len(r['issues'])} issues") for rel, r in rels.items()})
    print("delay_days_2_vs_3", "holds" if report["delay_days_2_vs_3"]["holds"] else "broken")


if __name__ == "__main__":
    main()
