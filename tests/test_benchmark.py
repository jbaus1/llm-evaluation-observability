from __future__ import annotations

from evaluation.benchmark import CASES, get_case
from evaluation.evaluate import evaluate_case
from evaluation.models import ReviewAction


METRIC_NAMES = {"fact_coverage", "evidence_attribution", "human_alignment"}


def _scores(case_id: str) -> dict[str, float]:
    benchmark_case = get_case(case_id)
    return {
        result.metric_name: result.score
        for result in evaluate_case(benchmark_case.as_evaluation_case())
    }


def test_benchmark_has_exactly_ten_unique_cases() -> None:
    assert len(CASES) == 10
    assert len({case.case_id for case in CASES}) == 10
    assert [case.case_id for case in CASES] == [
        f"CASE-{index:03d}" for index in range(1, 11)
    ]


def test_every_case_has_required_documented_fields() -> None:
    for case in CASES:
        assert case.case_id
        assert case.title
        assert case.description
        assert case.purpose
        assert case.evidence
        assert case.required_facts
        assert case.proposed_facts
        assert case.human_review_decisions
        assert case.generated_claims
        assert {name for name, _ in case.expected_metrics} == METRIC_NAMES
        assert all(expected.explanation for _, expected in case.expected_metrics)


def test_expected_metrics_exactly_match_evaluation_engine() -> None:
    for case in CASES:
        actual = {
            result.metric_name: result
            for result in evaluate_case(case.as_evaluation_case())
        }
        for metric_name, expected in case.expected_metrics:
            result = actual[metric_name]
            assert result.score == expected.score, case.case_id
            assert result.numerator == expected.numerator, case.case_id
            assert result.denominator == expected.denominator, case.case_id


def test_case_001_remains_the_partial_baseline() -> None:
    assert _scores("CASE-001") == {
        "fact_coverage": 0.8,
        "evidence_attribution": 0.5,
        "human_alignment": 0.6,
    }


def test_case_002_is_a_clean_positive_control() -> None:
    case = get_case("CASE-002")
    assert "positive control" in case.purpose
    assert set(_scores(case.case_id).values()) == {1.0}


def test_case_003_reduces_fact_coverage() -> None:
    assert _scores("CASE-003")["fact_coverage"] == 0.6


def test_case_004_reduces_evidence_attribution() -> None:
    case = get_case("CASE-004")
    result = evaluate_case(case.as_evaluation_case())[1]
    assert result.score == 0.5
    assert result.details["missing_evidence_claim_ids"] == ["C3"]
    assert result.details["invalid_evidence_ids"] == {"C4": ["E99"]}


def test_case_005_has_valid_attribution_for_unsupported_claim() -> None:
    case = get_case("CASE-005")
    unsupported_claim = case.generated_claims[1]
    assert unsupported_claim.evidence_ids == ("E2",)
    assert "humidity" in case.evidence[1].content.lower()
    assert "ventilation system failed" in unsupported_claim.claim.lower()
    assert _scores(case.case_id)["evidence_attribution"] == 1.0
    assert "not semantic groundedness" in case.purpose


def test_case_006_exercises_human_disagreement() -> None:
    assert _scores("CASE-006")["human_alignment"] == 0.75


def test_case_007_exercises_revise_exact_label_behavior() -> None:
    case = get_case("CASE-007")
    generated = {fact.fact_id: fact.disposition for fact in case.proposed_facts}
    reviewed = {
        decision.fact_id: decision.action for decision in case.human_review_decisions
    }
    assert generated["F2"] is ReviewAction.REVISE
    assert reviewed["F2"] is ReviewAction.REVISE
    assert _scores(case.case_id)["human_alignment"] == 1.0


def test_case_008_contains_conflicting_evidence() -> None:
    case = get_case("CASE-008")
    evidence_text = " ".join(item.content for item in case.evidence)
    assert "green" in evidence_text
    assert "red" in evidence_text
    assert "incompatible" in case.description


def test_case_009_contains_sparse_evidence() -> None:
    case = get_case("CASE-009")
    assert len(case.evidence) == 1
    assert len(case.required_facts) == 4
    assert _scores(case.case_id)["fact_coverage"] == 0.5


def test_case_010_is_the_perfect_positive_control() -> None:
    case = get_case("CASE-010")
    assert "perfect control" in case.purpose
    assert set(_scores(case.case_id).values()) == {1.0}


def test_repeated_benchmark_evaluation_is_identical() -> None:
    first = tuple(evaluate_case(case.as_evaluation_case()) for case in CASES)
    second = tuple(evaluate_case(case.as_evaluation_case()) for case in CASES)
    assert first == second


def test_get_case_rejects_unknown_id() -> None:
    try:
        get_case("CASE-999")
    except KeyError as error:
        assert "CASE-999" in str(error)
    else:
        raise AssertionError("Unknown benchmark case should raise KeyError")
