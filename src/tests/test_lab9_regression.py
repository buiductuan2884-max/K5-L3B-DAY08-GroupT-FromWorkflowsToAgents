"""Additional regressions: real trials, FM-08, statistical boundaries and gate integrity."""
import copy
import itertools
from math import comb
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.student


def test_trace_first_error_and_fixed():
    from lab9.trace_case import investigate
    from lab9.graders import RefundAmountCorrect

    bad = investigate("seeded_regression", "C-002", 11)
    good = investigate("fixed", "C-002", 11)
    assert [e["kind"] for e in bad["trial"]["events"][:3]] == ["handoff", "investigator", "model_override"]
    assert bad["trial"]["events"][1]["payload"]["lookup_order"]["order"]["delay_days"] == 2
    assert bad["trial"]["events"][2]["payload"] == {"delay_days": 5}
    assert bad["trial"]["snapshot"]["refund_vnd"] == 20000
    assert good["trial"]["snapshot"]["refund_vnd"] == 0
    for case, expected in ((bad, False), (good, True)):
        assert RefundAmountCorrect().evaluate(SimpleNamespace(output=case["trial"], expected_output=case["label"])).value is expected
        assert case["trial"]["lab8_pass"] is expected


@pytest.mark.parametrize("bug,claim,kind", [
    ("leaky_trace", "C-001", "debug_claim_row"),
    ("ignore_denied", "C-007", "reply"),
    ("ticket_trust", "C-002", "model_override"),
    ("sum_parts", "C-014", "proposal"),
    ("pre_deducted", "C-014", "proposal"),
    ("stale_clause", "C-006", "quote"),
    ("sibling_refund", "C-001", "batch_refund"),
    ("misreport", "C-008", "reply"),
])
def test_taxonomy_evidence_replay(monkeypatch, bug, claim, kind):
    from lab8.shapes import SHAPES
    from lab9.trace_case import investigate
    from lab9.variant_agent import make_shape
    from lab9.graders import ReplyLedgerConsistent

    name = "evidence_" + bug
    monkeypatch.setitem(SHAPES, name, make_shape(name, {"no_override", bug}))
    case = investigate(name, claim, 11)
    assert kind in [e["kind"] for e in case["trial"]["events"]]
    if bug == "misreport":
        # Lab 8 correctly reports ledger effects yet cannot grade the prose reply.
        assert case["trial"]["lab8_pass"] is True
        assert ReplyLedgerConsistent().evaluate(SimpleNamespace(output=case["trial"])).value is False
    else:
        assert case["trial"]["lab8_pass"] is False
    assert investigate("fixed", claim, 11)["trial"]["lab8_pass"] is True


@pytest.mark.parametrize("text,amount,want", [
    ("Đã hoàn 35.000đ cho O-123.", 35000, True),
    ("Đã hoàn phí 35,000 VND cho O-123.", 35000, True),
    ("Đã hoàn 35 000 đồng.", 35000, True),
    ("Đã hoàn 35000₫.", 20000, False),
    ("Đã hoàn 20.000đ.", 0, False),
    ("Đơn O-35000 bị từ chối; chờ 3–5 ngày.", 0, True),
    ("Đã hoàn 0đ.", 0, True),
])
def test_reply_amount_formats(text, amount, want):
    from lab9.graders import ReplyLedgerConsistent
    trial = {"events": [{"kind": "reply", "payload": {"text": text}}],
             "snapshot": {"refund_vnd": amount}, "result": {"proposal_amount": 999999}}
    assert ReplyLedgerConsistent().evaluate(SimpleNamespace(output=trial)).value is want


def test_reply_metric_rejects_misreport_accepts_fixed(monkeypatch):
    from lab8.shapes import SHAPES
    from lab9.variant_agent import make_shape
    from lab9.trace_case import investigate
    from lab9.graders import ReplyLedgerConsistent
    monkeypatch.setitem(SHAPES, "amount_test", make_shape("amount_test", {"no_override", "misreport"}))
    for shape, want in (("amount_test", False), ("fixed", True), ("honest_refactor", True)):
        case = investigate(shape, "C-008", 11)
        assert case["trial"]["snapshot"]["refund_vnd"] == 20000
        assert ReplyLedgerConsistent().evaluate(SimpleNamespace(output=case["trial"])).value is want


def _evidence():
    rows = [{"item_id": f"i{i}", "seed": seed, "pass_rate": True,
             "slices": ["money"] if i < 2 else []} for i in range(4) for seed in (7, 9)]
    report = {"manifest": {"items": 4, "seeds": [7, 9], "eval_set_sha": "test"},
              "rows": rows, "metrics": {"pass_rate": 1.0}, "evaluator_failures": []}
    spec = {"eval_set_version": "v2", "seeds": [7, 9],
            "metrics": [{"id": "pass_rate", "kind": "capability", "grader": "code", "blocking": True,
                         "threshold": {"min": 0.8, "no_significant_drop": True}}],
            "slices": [{"name": "money", "metric": "pass_rate", "min": 0.9,
                        "no_significant_drop": True, "blocking": True}]}
    return report, spec


@pytest.mark.parametrize("attack", ["nan", "inf", "missing_row", "duplicate", "seed_count", "nice_seeds",
    "item_count", "pair_swap", "grader_failure", "none_row", "nan_row", "missing_row_grade",
    "relabel_slice", "inconsistent_slice", "forged_aggregate", "missing_manifest", "missing_failures",
    "missing_aggregate", "nonbinary_row"])
def test_advanced_integrity_attacks(attack):
    from lab9.gate import check
    base, spec = _evidence()
    pr = copy.deepcopy(base)
    if attack in ("nan", "inf"):
        pr["metrics"]["pass_rate"] = float(attack)
    elif attack == "missing_row": pr["rows"].pop()
    elif attack == "duplicate": pr["rows"][-1] = copy.deepcopy(pr["rows"][0])
    elif attack == "seed_count": pr["manifest"]["seeds"].pop()
    elif attack == "nice_seeds":
        pr["manifest"]["seeds"] = [7]
        pr["rows"] = [r for r in pr["rows"] if r["seed"] == 7]
    elif attack == "item_count": pr["manifest"]["items"] = 3
    elif attack == "pair_swap":
        for r in pr["rows"]:
            if r["item_id"] == "i3": r["item_id"] = "other"
    elif attack == "grader_failure": pr["evaluator_failures"] = ["crash"]
    elif attack == "none_row": pr["rows"][0]["pass_rate"] = None
    elif attack == "nan_row": pr["rows"][0]["pass_rate"] = float("nan")
    elif attack == "missing_row_grade": pr["rows"][0].pop("pass_rate")
    elif attack == "relabel_slice":
        for r in pr["rows"]: r["slices"] = []
    elif attack == "inconsistent_slice": pr["rows"][0]["slices"] = []
    elif attack == "forged_aggregate": pr["rows"][0]["pass_rate"] = False
    elif attack == "missing_manifest": pr.pop("manifest")
    elif attack == "missing_failures": pr.pop("evaluator_failures")
    elif attack == "missing_aggregate": pr["metrics"].pop("pass_rate")
    elif attack == "nonbinary_row": pr["rows"][0]["pass_rate"] = 0.9
    blocked, lines = check(pr, base, spec)
    assert blocked == ["integrity"]
    assert all("INTEGRITY" in line for line in lines)


@pytest.mark.parametrize("attack", ["min", "max", "max_increase", "drop_metric", "blocking", "drop_ci",
    "drop_slice", "slice_floor", "slice_blocking", "slice_ci", "grader", "kind", "bootstrap", "pass_k"])
def test_advanced_ratchet_attacks(attack):
    from lab9.gate import integrity_check
    report, old = _evidence()
    old["metrics"][0]["threshold"].update(max=1, max_increase=0.1)
    old["bootstrap"] = {"method": "percentile", "confidence": 0.95}
    old["pass_k"] = [1]
    new = copy.deepcopy(old)
    metric = new["metrics"][0]
    if attack == "min": metric["threshold"]["min"] = 0.5
    elif attack == "max": metric["threshold"]["max"] = 2
    elif attack == "max_increase": metric["threshold"]["max_increase"] = 0.9
    elif attack == "drop_metric": new["metrics"] = []
    elif attack == "blocking": metric["blocking"] = False
    elif attack == "drop_ci": metric["threshold"].pop("no_significant_drop")
    elif attack == "drop_slice": new["slices"] = []
    elif attack == "slice_floor": new["slices"][0]["min"] = 0.3
    elif attack == "slice_blocking": new["slices"][0]["blocking"] = False
    elif attack == "slice_ci": new["slices"][0]["no_significant_drop"] = False
    elif attack == "grader": metric["grader"] = "different"
    elif attack == "kind": metric["kind"] = "system"
    elif attack == "bootstrap": new["bootstrap"]["confidence"] = 0.5
    elif attack == "pass_k": new["pass_k"] = []
    assert integrity_check(report, report, new, old)


def test_advanced_valid_reordering_stricter_spec_and_new_version():
    from lab9.gate import check, integrity_check
    report, spec = _evidence()
    shuffled = copy.deepcopy(report)
    shuffled["rows"].reverse()
    assert check(shuffled, report, spec, spec)[0] == []
    stricter = copy.deepcopy(spec)
    stricter["metrics"][0]["threshold"]["min"] = 0.95
    assert integrity_check(report, report, stricter, spec) == []
    newer = copy.deepcopy(spec)
    newer["eval_set_version"] = "v3"
    newer["metrics"][0]["threshold"]["min"] = 0.5
    assert integrity_check(report, report, newer, spec) == []


def test_advanced_slice_bootstrap_and_empty():
    from lab9.gate import slice_check
    base, spec = _evidence()
    pr = copy.deepcopy(base)
    for r in pr["rows"]:
        if "money" in r["slices"] and r["seed"] == 7: r["pass_rate"] = False
    spec["slices"][0]["min"] = 0.1  # isolate significant-drop criterion, not a submitted threshold
    assert slice_check(pr, base, spec)[0] == ["slice:money/pass_rate"]
    spec["slices"][0]["name"] = "absent"
    assert slice_check(base, base, spec)[0] == ["slice:absent/pass_rate"]


def test_advanced_quiet_flaky_failure_needs_stability(monkeypatch):
    from pathlib import Path
    from lab8.shapes import SHAPES
    from lab9 import gate, variants
    from lab9.eval import load_spec, run_eval
    from lab9.variant_agent import make_shape
    variants.register()
    monkeypatch.setitem(SHAPES, "quiet_check", make_shape("quiet_check", {"no_override", "round_down", "rare", "quiet_override"}))
    spec = load_spec(Path("config/metric_spec_v2.yaml"))
    base = run_eval("swarm", spec)
    candidate = run_eval("quiet_check", spec)
    assert candidate["metrics"]["db_fact_kept"] == 1.0
    blocked, _ = gate.check(candidate, base, spec)
    assert "pass_hat_5" in blocked
    assert gate.check(base, base, spec)[0] == []


def test_advanced_pass_estimators_exhaustive_small_populations():
    from lab9.stats import pass_at_k, pass_hat_k
    for n in range(1, 9):
        for c in range(n + 1):
            for k in range(1, n + 1):
                draws = list(itertools.combinations(range(n), k))
                successes = [sum(i < c for i in draw) for draw in draws]
                assert pass_at_k(n, c, k) == pytest.approx(sum(x > 0 for x in successes) / comb(n, k))
                assert pass_hat_k(n, c, k) == pytest.approx(sum(x == k for x in successes) / comb(n, k))


@pytest.mark.parametrize("args", [(0, 0, 1), (-1, 0, 1), (5, -1, 1), (5, 6, 1), (5, 1, 0), (5, 1, 6),
    (5.0, 1, 1), (5, 1.0, 1), (5, 1, 1.5), (True, 1, 1), (5, 1, False), (5, None, 1)])
def test_advanced_invalid_pass_arguments(args):
    from lab9.stats import pass_at_k, pass_hat_k
    for fn in (pass_at_k, pass_hat_k):
        with pytest.raises(ValueError): fn(*args)


def test_invalid_calibration_and_bootstrap_inputs():
    from lab9 import stats
    for human, judge in (([], []), (["PASS"], []), (["maybe"], ["FAIL"])):
        with pytest.raises(ValueError): stats.confusion(human, judge)
    assert stats.precision_recall(["PASS"], ["PASS"]) == (0, 0)
    assert stats.cohen_kappa(["PASS"], ["FAIL"]) == 0
    for args in ((0.5, 0.5, 0.5), (0.5, 0.2, 0.2), (float("nan"), 0.8, 0.9), (1.1, 0.8, 0.9)):
        with pytest.raises(ValueError): stats.rogan_gladen(*args)
    for a, b in (([], []), ([1], [1, 0]), ([float("inf")], [1]), ([[1]], [[1]])):
        with pytest.raises(ValueError): stats.paired_bootstrap(a, b)
    assert stats.paired_bootstrap([1], [0]) == (1, 1, 1)
