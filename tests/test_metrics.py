from __future__ import annotations

from dataclasses import replace

import pytest

from evaluation.cases import CASE_001
from evaluation.evaluate import evaluate_case
from evaluation.metrics import evidence_attribution, fact_coverage, human_alignment
from evaluation.models import (
    EvaluationCase,
    Evidence,
    GeneratedClaim,
    HumanReviewDecision,
    ProposedFact,
    ReviewAction,
)


def _case(
    *,
    required_fact_ids: tuple[str, ...] = (),
    evidence: tuple[Evidence, ...] = (),
    generated_claims: tuple[GeneratedClaim, ...] = (),
    proposed_facts: tuple[ProposedFact, ...] = (),
    human_review_decisions: tuple[HumanReviewDecision, ...] = (),
) -> EvaluationCase:
    return EvaluationCase(
        case_id="TEST",
        evidence=evidence,
        required_fact_ids=required_fact_ids,
        proposed_facts=proposed_facts,
        human_review_decisions=human_review_decisions,
        generated_claims=generated_claims,
    )


def _claim(claim_id: str, fact_id: str, *evidence_ids: str) -> GeneratedClaim:
    return GeneratedClaim(claim_id, fact_id, f"Claim {claim_id}", evidence_ids)


@pytest.mark.parametrize(
    ("represented", "expected_score", "missing"),
    [
        (("F1", "F2"), 1.0, []),
        (("F1",), 0.5, ["F2"]),
        ((), 0.0, ["F1", "F2"]),
    ],
)
def test_fact_coverage(
    represented: tuple[str, ...], expected_score: float, missing: list[str]
) -> None:
    case = _case(
        required_fact_ids=("F1", "F2"),
        generated_claims=tuple(
            _claim(f"C{index}", fact_id) for index, fact_id in enumerate(represented)
        ),
    )

    result = fact_coverage(case)

    assert result.score == expected_score
    assert result.numerator == len(represented)
    assert result.denominator == 2
    assert result.details["missing_fact_ids"] == missing


def test_fact_coverage_with_no_required_facts_is_not_assessable() -> None:
    result = fact_coverage(_case())

    assert result.score == 0.0
    assert result.numerator == 0
    assert result.denominator == 0
    assert "not assessable" in result.reason


@pytest.mark.parametrize(
    ("claims", "expected_score", "missing", "invalid"),
    [
        ((_claim("C1", "F1", "E1"),), 1.0, [], {}),
        (
            (_claim("C1", "F1", "E1"), _claim("C2", "F2")),
            0.5,
            ["C2"],
            {},
        ),
        ((_claim("C1", "F1"),), 0.0, ["C1"], {}),
        ((_claim("C1", "F1", "E99"),), 0.0, [], {"C1": ["E99"]}),
    ],
)
def test_evidence_attribution(
    claims: tuple[GeneratedClaim, ...],
    expected_score: float,
    missing: list[str],
    invalid: dict[str, list[str]],
) -> None:
    result = evidence_attribution(
        _case(evidence=(Evidence("E1", "Evidence"),), generated_claims=claims)
    )

    assert result.metric_name == "evidence_attribution"
    assert result.score == expected_score
    assert result.numerator == round(expected_score * len(claims))
    assert result.denominator == len(claims)
    assert result.details["missing_evidence_claim_ids"] == missing
    assert result.details["invalid_evidence_ids"] == invalid


def _fact(fact_id: str, action: ReviewAction) -> ProposedFact:
    return ProposedFact(fact_id, f"Claim {fact_id}", (), action)


@pytest.mark.parametrize(
    ("generated_actions", "human_actions", "expected_score", "mismatched"),
    [
        (
            (ReviewAction.ACCEPT, ReviewAction.REJECT),
            (ReviewAction.ACCEPT, ReviewAction.REJECT),
            1.0,
            [],
        ),
        (
            (ReviewAction.ACCEPT, ReviewAction.ACCEPT),
            (ReviewAction.ACCEPT, ReviewAction.REJECT),
            0.5,
            ["F2"],
        ),
        (
            (ReviewAction.REJECT, ReviewAction.REJECT),
            (ReviewAction.ACCEPT, ReviewAction.ACCEPT),
            0.0,
            ["F1", "F2"],
        ),
        ((ReviewAction.REVISE,), (ReviewAction.REVISE,), 1.0, []),
        ((ReviewAction.ACCEPT,), (ReviewAction.REVISE,), 0.0, ["F1"]),
    ],
)
def test_human_alignment(
    generated_actions: tuple[ReviewAction, ...],
    human_actions: tuple[ReviewAction, ...],
    expected_score: float,
    mismatched: list[str],
) -> None:
    fact_ids = tuple(f"F{index}" for index in range(1, len(human_actions) + 1))
    case = _case(
        proposed_facts=tuple(
            _fact(fact_id, action)
            for fact_id, action in zip(fact_ids, generated_actions)
        ),
        human_review_decisions=tuple(
            HumanReviewDecision(fact_id, action)
            for fact_id, action in zip(fact_ids, human_actions)
        ),
    )

    result = human_alignment(case)

    assert result.score == expected_score
    assert result.numerator == round(expected_score * len(human_actions))
    assert result.denominator == len(human_actions)
    assert result.details["mismatched_fact_ids"] == mismatched


def test_human_alignment_does_not_count_missing_generated_fact_as_agreement() -> None:
    case = _case(
        human_review_decisions=(HumanReviewDecision("F1", ReviewAction.ACCEPT),)
    )

    result = human_alignment(case)

    assert result.score == 0.0
    assert result.details["mismatched_fact_ids"] == ["F1"]
    assert result.details["missing_generated_fact_ids"] == ["F1"]


def test_human_alignment_with_no_final_decisions_is_not_assessable() -> None:
    result = human_alignment(_case(proposed_facts=(_fact("F1", ReviewAction.ACCEPT),)))

    assert result.score == 0.0
    assert result.numerator == 0
    assert result.denominator == 0
    assert "not assessable" in result.reason


def test_case_001_has_exact_expected_scores() -> None:
    results = {result.metric_name: result for result in evaluate_case(CASE_001)}

    assert results["fact_coverage"].score == 0.8
    assert results["evidence_attribution"].score == 0.5
    assert results["human_alignment"].score == 0.6


def test_evaluate_case_returns_all_metrics_in_stable_order() -> None:
    assert [result.metric_name for result in evaluate_case(CASE_001)] == [
        "fact_coverage",
        "evidence_attribution",
        "human_alignment",
    ]


def test_evaluate_case_is_deterministic() -> None:
    first = evaluate_case(CASE_001)
    second = evaluate_case(replace(CASE_001))

    assert first == second
