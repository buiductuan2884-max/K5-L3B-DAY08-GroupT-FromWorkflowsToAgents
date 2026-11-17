"""B7: metamorphic audit of grader_audit/grader_{a,b,c}.py (and the base lab8.metrics).

Each case pins exactly which keys break a relation, so the evidence is rerunnable:
a grader that changes behavior turns this file red.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bonus.grader_audit import (
    SUMMARIZE_CHECKS,
    _base_summarize,
    audit,
    check_claim_delay,
    grader,
    load,
)

DUP = "duplicated_list_keeps_rates_doubles_totals"
INFRA = "infra_errors_do_not_move_pass_rate"
ORDER = "NEW_trial_order_does_not_matter"
ISOLATION = "extra_other_shape_does_not_leak"
FLIP = "extra_flip_one_fail_to_pass"
ORACLE = "extra_oracle_docs_metrics"
DROP = "extra_drop_seed_row_lowers_pass5"
RELABEL = "extra_relabel_seeds_and_claims"

COST = {"cost_per_success_vnd", "total_simulated_cost_vnd"}
INFRA_AS_FAIL = {"pass_rate", "pass_5", "seed_pass_rates", "graded_trials"}
ORACLE_INFRA_AS_FAIL = {
    "graded_trials", "pass_rate", "seed_pass_rates", "seed_variance", "seed_min",
    "pass_5", "total_simulated_cost_vnd", "cost_per_success_vnd", "mean_steps",
}

# Keys each relation breaks, per implementation. Empty set = relation holds.
# pass_5 under DUP: lab8.metrics only counts a claim with exactly one row per seed,
# so every implementation that reuses it drops pass_5 to 0 on a duplicated list.
_HOLDS = {ISOLATION: set(), FLIP: set(), DROP: set(), RELABEL: set()}
EXPECTED = {
    "grader_a": {DUP: {"pass_5"} | COST, INFRA: set(), ORDER: COST, ORACLE: COST, **_HOLDS},
    "grader_b": {DUP: {"pass_5"}, INFRA: set(), ORDER: set(), ORACLE: set(), **_HOLDS},
    "grader_c": {DUP: {"pass_5"}, INFRA: INFRA_AS_FAIL, ORDER: set(), ORACLE: ORACLE_INFRA_AS_FAIL, **_HOLDS},
    # The base has no idea of infra_error: it grades any passed=False row, like grader_c.
    "lab8_metrics": {DUP: {"pass_5"}, INFRA: INFRA_AS_FAIL, ORDER: set(), ORACLE: ORACLE_INFRA_AS_FAIL, **_HOLDS},
}

CASES = [(name, rel) for name, rels in EXPECTED.items() for rel in rels]


def _fn(name):
    return _base_summarize if name == "lab8_metrics" else grader(name)


def test_every_relation_is_pinned_for_every_implementation():
    assert {rel for rels in EXPECTED.values() for rel in rels} == set(SUMMARIZE_CHECKS)


@pytest.mark.parametrize("name,relation", CASES, ids=[f"{n}-{r}" for n, r in CASES])
def test_relation_breaks_exactly_on(name, relation):
    issues = SUMMARIZE_CHECKS[relation](_fn(name))
    assert {i["key"] for i in issues} == EXPECTED[name][relation]


def _first_last_seed_grader(trials):
    """Planted defect: seed_min/seed_max are the rates of the first and last seed seen,
    not the real min/max. Everything else comes from the honest grader_b."""
    report = grader("grader_b")(trials)
    for shape, stats in report.items():
        rates = stats["seed_pass_rates"]
        order = [str(t["seed"]) for t in trials if t["shape"] == shape and str(t["seed"]) in rates]
        stats["seed_min"], stats["seed_max"] = rates[order[0]], rates[order[-1]]
    return report


def test_new_relation_catches_a_defect_the_three_given_relations_miss():
    # Duplicating keeps first/last order and infra rows are appended at the end,
    # so the planted defect survives both given relations; only reordering exposes it.
    fn = _first_last_seed_grader
    assert {i["key"] for i in SUMMARIZE_CHECKS[DUP](fn)} == {"pass_5"}  # the shared base defect only
    assert SUMMARIZE_CHECKS[INFRA](fn) == []
    assert check_claim_delay(load("metamorphic_claim_delay")) == []
    assert {i["key"] for i in SUMMARIZE_CHECKS[ORDER](fn)} >= {"seed_min", "seed_max"}


def test_new_relation_shows_grader_a_cost_depends_on_order():
    # grader_a passes INFRA on this input, yet reordering the same trials changes its cost.
    fn = grader("grader_a")
    assert SUMMARIZE_CHECKS[INFRA](fn) == []
    base = load("metamorphic_infra")["a"]
    assert fn(base)["workflow"]["total_simulated_cost_vnd"] != fn(base[::-1])["workflow"]["total_simulated_cost_vnd"]


def test_grader_c_counts_infra_trials_as_failures():
    fx = load("metamorphic_infra")
    infra_n = len(fx["b"]) - len(fx["a"])
    good = grader("grader_b")(fx["a"])["workflow"]
    bad = grader("grader_c")(fx["b"])["workflow"]
    assert bad["graded_trials"] == good["graded_trials"] + infra_n
    assert bad["successes"] == good["successes"]
    assert bad["pass_rate"] < good["pass_rate"]


def test_grader_a_adds_cost_once_more_per_claim():
    trials = load("metamorphic_duplicate")["a"]
    a, b = grader("grader_a")(trials), grader("grader_b")(trials)
    for shape in a:
        first_cost: dict[str, float] = {}
        for t in trials:
            if t["shape"] == shape and t.get("passed") is not None:
                first_cost.setdefault(t["claim_id"], float(t["cost_estimate"]))
        extra = a[shape]["total_simulated_cost_vnd"] - b[shape]["total_simulated_cost_vnd"]
        assert extra == pytest.approx(sum(first_cost.values()))


def test_delay_2_vs_3_flips_decision():
    assert check_claim_delay(load("metamorphic_claim_delay")) == []


def test_report_is_deterministic_and_json_safe():
    first, second = audit(), audit()
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert set(first["verdicts"]) == set(EXPECTED)


def test_committed_report_matches_a_fresh_run():
    # Catches a stale or hand-edited reports/bonus_grader_audit.json.
    path = Path(__file__).resolve().parents[1] / "reports" / "bonus_grader_audit.json"
    assert json.loads(path.read_text(encoding="utf-8")) == json.loads(json.dumps(audit()))
