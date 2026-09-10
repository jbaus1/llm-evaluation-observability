from evaluation.models import (
    EvaluationCase,
    Evidence,
    GeneratedClaim,
    HumanReviewDecision,
    ProposedFact,
    ReviewAction,
)


CASE_001 = EvaluationCase(
    case_id="CASE-001",
    evidence=(
        Evidence("E1", "A response delay began at 09:15 UTC."),
        Evidence("E2", "Normal response times resumed at 09:22 UTC."),
        Evidence("E3", "A routine review was completed after recovery."),
    ),
    required_fact_ids=("F1", "F2", "F3", "F4", "F5"),
    proposed_facts=(
        ProposedFact(
            "F1", "A response delay began at 09:15 UTC.", ("E1",), ReviewAction.ACCEPT
        ),
        ProposedFact(
            "F2",
            "Normal response times resumed at 09:22 UTC.",
            ("E2",),
            ReviewAction.ACCEPT,
        ),
        ProposedFact(
            "F3", "The delay lasted seven minutes.", ("E1", "E2"), ReviewAction.ACCEPT
        ),
        ProposedFact(
            "F4", "A routine review followed recovery.", ("E3",), ReviewAction.ACCEPT
        ),
        ProposedFact(
            "F5", "No further delays were observed.", ("E3",), ReviewAction.ACCEPT
        ),
    ),
    human_review_decisions=(
        HumanReviewDecision("F1", ReviewAction.ACCEPT),
        HumanReviewDecision("F2", ReviewAction.ACCEPT),
        HumanReviewDecision("F3", ReviewAction.REJECT),
        HumanReviewDecision("F4", ReviewAction.ACCEPT),
        HumanReviewDecision("F5", ReviewAction.REVISE),
    ),
    generated_claims=(
        GeneratedClaim("C1", "F1", "A response delay began at 09:15 UTC.", ("E1",)),
        GeneratedClaim(
            "C2", "F2", "Normal response times resumed at 09:22 UTC.", ("E2",)
        ),
        GeneratedClaim("C3", "F3", "The delay lasted seven minutes.", ()),
        GeneratedClaim("C4", "F5", "No further delays were observed.", ("E99",)),
    ),
)
