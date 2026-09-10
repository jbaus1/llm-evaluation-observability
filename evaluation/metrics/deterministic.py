from __future__ import annotations

from evaluation.models import EvaluationCase, EvaluationResult


def _score(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def fact_coverage(case: EvaluationCase) -> EvaluationResult:
    represented_fact_ids = {
        claim.fact_id for claim in case.generated_claims if claim.fact_id is not None
    }
    missing_fact_ids = [
        fact_id
        for fact_id in case.required_fact_ids
        if fact_id not in represented_fact_ids
    ]
    denominator = len(case.required_fact_ids)
    numerator = denominator - len(missing_fact_ids)

    if denominator == 0:
        reason = "No required facts were provided; coverage is not assessable."
    else:
        reason = f"{numerator} of {denominator} required facts were represented."

    return EvaluationResult(
        metric_name="fact_coverage",
        score=_score(numerator, denominator),
        numerator=numerator,
        denominator=denominator,
        details={"missing_fact_ids": missing_fact_ids},
        reason=reason,
    )


def evidence_attribution(case: EvaluationCase) -> EvaluationResult:
    valid_evidence_ids = {evidence.evidence_id for evidence in case.evidence}
    attributed_claim_ids: list[str] = []
    missing_evidence_claim_ids: list[str] = []
    invalid_evidence_ids: dict[str, list[str]] = {}

    for claim in case.generated_claims:
        invalid_ids = sorted(set(claim.evidence_ids) - valid_evidence_ids)
        if invalid_ids:
            invalid_evidence_ids[claim.claim_id] = invalid_ids

        if set(claim.evidence_ids) & valid_evidence_ids:
            attributed_claim_ids.append(claim.claim_id)
        elif not claim.evidence_ids:
            missing_evidence_claim_ids.append(claim.claim_id)

    numerator = len(attributed_claim_ids)
    denominator = len(case.generated_claims)
    if denominator == 0:
        reason = "No generated claims were provided; attribution is not assessable."
    else:
        reason = (
            f"{numerator} of {denominator} generated claims referenced at least "
            "one valid evidence ID."
        )

    return EvaluationResult(
        metric_name="evidence_attribution",
        score=_score(numerator, denominator),
        numerator=numerator,
        denominator=denominator,
        details={
            "attributed_claim_ids": attributed_claim_ids,
            "missing_evidence_claim_ids": missing_evidence_claim_ids,
            "invalid_evidence_ids": invalid_evidence_ids,
        },
        reason=reason,
    )


def human_alignment(case: EvaluationCase) -> EvaluationResult:
    generated_dispositions = {
        fact.fact_id: fact.disposition for fact in case.proposed_facts
    }
    final_human_dispositions = {
        decision.fact_id: decision.action for decision in case.human_review_decisions
    }
    matched_fact_ids: list[str] = []
    mismatched_fact_ids: list[str] = []
    missing_generated_fact_ids: list[str] = []

    for fact_id, human_action in final_human_dispositions.items():
        generated_action = generated_dispositions.get(fact_id)
        if generated_action == human_action:
            matched_fact_ids.append(fact_id)
        else:
            mismatched_fact_ids.append(fact_id)
            if generated_action is None:
                missing_generated_fact_ids.append(fact_id)

    numerator = len(matched_fact_ids)
    denominator = len(final_human_dispositions)
    if denominator == 0:
        reason = "No final human decisions were provided; alignment is not assessable."
    else:
        reason = (
            f"{numerator} of {denominator} generated dispositions matched the final "
            "human dispositions."
        )

    return EvaluationResult(
        metric_name="human_alignment",
        score=_score(numerator, denominator),
        numerator=numerator,
        denominator=denominator,
        details={
            "matched_fact_ids": matched_fact_ids,
            "mismatched_fact_ids": mismatched_fact_ids,
            "missing_generated_fact_ids": missing_generated_fact_ids,
            "revise_rule": "REVISE matches only an explicit generated REVISE disposition.",
        },
        reason=reason,
    )
