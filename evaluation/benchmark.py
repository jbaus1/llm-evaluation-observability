from __future__ import annotations

from dataclasses import dataclass

from evaluation.cases import CASE_001
from evaluation.models import (
    EvaluationCase,
    Evidence,
    GeneratedClaim,
    HumanReviewDecision,
    ProposedFact,
    ReviewAction,
)


@dataclass(frozen=True, slots=True)
class ExpectedMetric:
    numerator: int
    denominator: int
    explanation: str

    @property
    def score(self) -> float:
        return self.numerator / self.denominator if self.denominator else 0.0


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    case_id: str
    title: str
    description: str
    purpose: str
    evidence: tuple[Evidence, ...]
    required_facts: tuple[str, ...]
    proposed_facts: tuple[ProposedFact, ...]
    human_review_decisions: tuple[HumanReviewDecision, ...]
    generated_claims: tuple[GeneratedClaim, ...]
    expected_metrics: tuple[tuple[str, ExpectedMetric], ...]

    def as_evaluation_case(self) -> EvaluationCase:
        return EvaluationCase(
            case_id=self.case_id,
            evidence=self.evidence,
            required_fact_ids=self.required_facts,
            proposed_facts=self.proposed_facts,
            human_review_decisions=self.human_review_decisions,
            generated_claims=self.generated_claims,
        )

    def expected_metric(self, metric_name: str) -> ExpectedMetric:
        return dict(self.expected_metrics)[metric_name]


def _expected(
    coverage: tuple[int, int, str],
    attribution: tuple[int, int, str],
    alignment: tuple[int, int, str],
) -> tuple[tuple[str, ExpectedMetric], ...]:
    return (
        ("fact_coverage", ExpectedMetric(*coverage)),
        ("evidence_attribution", ExpectedMetric(*attribution)),
        ("human_alignment", ExpectedMetric(*alignment)),
    )


def _evidence(evidence_id: str, content: str) -> Evidence:
    return Evidence(evidence_id, content)


def _fact(
    fact_id: str,
    claim: str,
    evidence_ids: tuple[str, ...],
    disposition: ReviewAction = ReviewAction.ACCEPT,
) -> ProposedFact:
    return ProposedFact(fact_id, claim, evidence_ids, disposition)


def _decision(fact_id: str, action: ReviewAction) -> HumanReviewDecision:
    return HumanReviewDecision(fact_id, action)


def _claim(
    claim_id: str,
    fact_id: str,
    claim: str,
    evidence_ids: tuple[str, ...],
) -> GeneratedClaim:
    return GeneratedClaim(claim_id, fact_id, claim, evidence_ids)


CASES = (
    BenchmarkCase(
        case_id=CASE_001.case_id,
        title="Partial extraction baseline",
        description="A service delay investigation with incomplete extraction and review disagreement.",
        purpose="Provide the established partial-extraction baseline for all three metrics.",
        evidence=CASE_001.evidence,
        required_facts=CASE_001.required_fact_ids,
        proposed_facts=CASE_001.proposed_facts,
        human_review_decisions=CASE_001.human_review_decisions,
        generated_claims=CASE_001.generated_claims,
        expected_metrics=_expected(
            (4, 5, "Four of five required facts are represented; F4 is missing."),
            (2, 4, "Two of four claims reference valid evidence IDs."),
            (3, 5, "Three of five generated dispositions match human decisions."),
        ),
    ),
    BenchmarkCase(
        case_id="CASE-002",
        title="Clean complete case",
        description="A scheduled file transfer completed and was verified without exceptions.",
        purpose="Act as a compact positive control with complete, attributed, aligned output.",
        evidence=(
            _evidence("E1", "The scheduled transfer completed at 14:00 UTC."),
            _evidence("E2", "The destination checksum matched the source checksum."),
            _evidence("E3", "The completion review recorded no exceptions."),
        ),
        required_facts=("F1", "F2", "F3"),
        proposed_facts=(
            _fact("F1", "The transfer completed at 14:00 UTC.", ("E1",)),
            _fact("F2", "Source and destination checksums matched.", ("E2",)),
            _fact("F3", "The review found no exceptions.", ("E3",)),
        ),
        human_review_decisions=(
            _decision("F1", ReviewAction.ACCEPT),
            _decision("F2", ReviewAction.ACCEPT),
            _decision("F3", ReviewAction.ACCEPT),
        ),
        generated_claims=(
            _claim("C1", "F1", "The transfer completed at 14:00 UTC.", ("E1",)),
            _claim("C2", "F2", "The checksums matched.", ("E2",)),
            _claim("C3", "F3", "The review found no exceptions.", ("E3",)),
        ),
        expected_metrics=_expected(
            (3, 3, "All three required facts are represented."),
            (3, 3, "All three claims reference valid evidence."),
            (3, 3, "All three dispositions match human decisions."),
        ),
    ),
    BenchmarkCase(
        case_id="CASE-003",
        title="Missing required fact",
        description="A delivery review omits two required facts from the generated investigation.",
        purpose="Force fact_coverage below 1.0 through explicit missing fact IDs.",
        evidence=(
            _evidence("E1", "The delivery arrived at 08:10 UTC."),
            _evidence("E2", "The delivery contained twelve labeled containers."),
            _evidence("E3", "The receiving checklist was signed."),
            _evidence("E4", "Two outer cartons had minor dents."),
            _evidence("E5", "All container seals were intact."),
        ),
        required_facts=("F1", "F2", "F3", "F4", "F5"),
        proposed_facts=tuple(
            _fact(f"F{index}", f"Required delivery fact {index}.", (f"E{index}",))
            for index in range(1, 6)
        ),
        human_review_decisions=tuple(
            _decision(f"F{index}", ReviewAction.ACCEPT) for index in range(1, 6)
        ),
        generated_claims=(
            _claim("C1", "F1", "The delivery arrived at 08:10 UTC.", ("E1",)),
            _claim("C2", "F2", "Twelve labeled containers arrived.", ("E2",)),
            _claim("C3", "F3", "The receiving checklist was signed.", ("E3",)),
        ),
        expected_metrics=_expected(
            (
                3,
                5,
                "Three of five required facts are represented; F4 and F5 are missing.",
            ),
            (3, 3, "Every generated claim references valid evidence."),
            (5, 5, "All proposed dispositions match the final human decisions."),
        ),
    ),
    BenchmarkCase(
        case_id="CASE-004",
        title="Invalid evidence reference",
        description="A four-claim inspection includes one missing citation and one unknown evidence ID.",
        purpose="Force evidence_attribution below 1.0 and distinguish missing from invalid references.",
        evidence=(
            _evidence("E1", "The package count was forty."),
            _evidence("E2", "Two package labels required replacement."),
        ),
        required_facts=("F1", "F2", "F3", "F4"),
        proposed_facts=tuple(
            _fact(f"F{index}", f"Inspection fact {index}.", ()) for index in range(1, 5)
        ),
        human_review_decisions=tuple(
            _decision(f"F{index}", ReviewAction.ACCEPT) for index in range(1, 5)
        ),
        generated_claims=(
            _claim("C1", "F1", "The package count was forty.", ("E1",)),
            _claim("C2", "F2", "Two labels required replacement.", ("E2",)),
            _claim("C3", "F3", "The count was independently confirmed.", ()),
            _claim("C4", "F4", "No additional label issues existed.", ("E99",)),
        ),
        expected_metrics=_expected(
            (4, 4, "All four required fact IDs appear in generated claims."),
            (
                2,
                4,
                "Two claims have valid evidence; one is missing and one is invalid.",
            ),
            (4, 4, "All generated dispositions match human decisions."),
        ),
    ),
    BenchmarkCase(
        case_id="CASE-005",
        title="Structurally attributed unsupported claim",
        description="A claim cites a real evidence ID whose text does not support the claim.",
        purpose="Demonstrate that evidence_attribution is not semantic groundedness.",
        evidence=(
            _evidence("E1", "The room temperature was 21 degrees Celsius."),
            _evidence("E2", "The humidity reading was 45 percent."),
        ),
        required_facts=("F1", "F2"),
        proposed_facts=(
            _fact("F1", "The room temperature was 21 degrees Celsius.", ("E1",)),
            _fact("F2", "The ventilation system failed.", ("E2",)),
        ),
        human_review_decisions=(
            _decision("F1", ReviewAction.ACCEPT),
            _decision("F2", ReviewAction.REJECT),
        ),
        generated_claims=(
            _claim("C1", "F1", "The room temperature was 21 degrees Celsius.", ("E1",)),
            _claim("C2", "F2", "The ventilation system failed.", ("E2",)),
        ),
        expected_metrics=_expected(
            (2, 2, "Both required fact IDs appear in generated claims."),
            (
                2,
                2,
                "Both claims cite structurally valid evidence IDs, including the unsupported claim.",
            ),
            (
                1,
                2,
                "The unsupported claim is generated as ACCEPT but reviewed as REJECT.",
            ),
        ),
    ),
    BenchmarkCase(
        case_id="CASE-006",
        title="Human rejection",
        description="One accepted generated fact is rejected during final human review.",
        purpose="Demonstrate disagreement between a generated disposition and final review.",
        evidence=(
            _evidence("E1", "The service restarted at 11:00 UTC."),
            _evidence("E2", "The health check passed at 11:02 UTC."),
            _evidence("E3", "One warning remained in the diagnostic log."),
            _evidence("E4", "The monitoring window ended at 11:30 UTC."),
        ),
        required_facts=("F1", "F2", "F3", "F4"),
        proposed_facts=tuple(
            _fact(f"F{index}", f"Service review fact {index}.", (f"E{index}",))
            for index in range(1, 5)
        ),
        human_review_decisions=(
            _decision("F1", ReviewAction.ACCEPT),
            _decision("F2", ReviewAction.ACCEPT),
            _decision("F3", ReviewAction.REJECT),
            _decision("F4", ReviewAction.ACCEPT),
        ),
        generated_claims=tuple(
            _claim(
                f"C{index}",
                f"F{index}",
                f"Service review fact {index}.",
                (f"E{index}",),
            )
            for index in range(1, 5)
        ),
        expected_metrics=_expected(
            (4, 4, "All four required facts are represented."),
            (4, 4, "All four claims reference valid evidence."),
            (
                3,
                4,
                "Three dispositions agree; F3 is accepted by generation and rejected by review.",
            ),
        ),
    ),
    BenchmarkCase(
        case_id="CASE-007",
        title="Human revision",
        description="A generated REVISE disposition is confirmed by the final human decision.",
        purpose="Exercise the v0.1 exact-label behavior for REVISE dispositions.",
        evidence=(
            _evidence("E1", "The maintenance note identifies the replaced cable."),
            _evidence("E2", "The note does not include the replacement time."),
            _evidence("E3", "The post-maintenance check passed."),
        ),
        required_facts=("F1", "F2", "F3"),
        proposed_facts=(
            _fact("F1", "A cable was replaced.", ("E1",), ReviewAction.ACCEPT),
            _fact(
                "F2", "The replacement time is missing.", ("E2",), ReviewAction.REVISE
            ),
            _fact(
                "F3", "The post-maintenance check passed.", ("E3",), ReviewAction.ACCEPT
            ),
        ),
        human_review_decisions=(
            _decision("F1", ReviewAction.ACCEPT),
            _decision("F2", ReviewAction.REVISE),
            _decision("F3", ReviewAction.ACCEPT),
        ),
        generated_claims=(
            _claim("C1", "F1", "A cable was replaced.", ("E1",)),
            _claim("C2", "F2", "The replacement time is missing.", ("E2",)),
            _claim("C3", "F3", "The post-maintenance check passed.", ("E3",)),
        ),
        expected_metrics=_expected(
            (3, 3, "All three required facts are represented."),
            (3, 3, "All three claims reference valid evidence."),
            (
                3,
                3,
                "The generated REVISE label matches the human REVISE label exactly.",
            ),
        ),
    ),
    BenchmarkCase(
        case_id="CASE-008",
        title="Conflicting evidence",
        description="Two observations report incompatible states for the same indicator.",
        purpose="Represent incompatible evidence without adding semantic conflict resolution.",
        evidence=(
            _evidence(
                "E1", "Observer A recorded the status indicator as green at 16:05 UTC."
            ),
            _evidence(
                "E2", "Observer B recorded the same indicator as red at 16:05 UTC."
            ),
            _evidence("E3", "The follow-up log marks the status as unresolved."),
        ),
        required_facts=("F1", "F2", "F3"),
        proposed_facts=(
            _fact("F1", "Observer A recorded green.", ("E1",)),
            _fact("F2", "Observer B recorded red.", ("E2",)),
            _fact(
                "F3",
                "The status remained unresolved.",
                ("E1", "E2", "E3"),
                ReviewAction.REVISE,
            ),
        ),
        human_review_decisions=(
            _decision("F1", ReviewAction.ACCEPT),
            _decision("F2", ReviewAction.ACCEPT),
            _decision("F3", ReviewAction.REVISE),
        ),
        generated_claims=(
            _claim("C1", "F1", "Observer A recorded green.", ("E1",)),
            _claim("C2", "F2", "Observer B recorded red.", ("E2",)),
            _claim("C3", "F3", "The status remained unresolved.", ("E1", "E2", "E3")),
        ),
        expected_metrics=_expected(
            (
                3,
                3,
                "All sides of the conflict and its unresolved state are represented.",
            ),
            (
                3,
                3,
                "Every claim references evidence, including both conflicting sources.",
            ),
            (
                3,
                3,
                "All dispositions, including REVISE for the unresolved fact, align.",
            ),
        ),
    ),
    BenchmarkCase(
        case_id="CASE-009",
        title="Sparse evidence",
        description="One short observation is available for an investigation requiring four facts.",
        purpose="Exercise an underspecified case that cannot support a complete investigation.",
        evidence=(
            _evidence("E1", "A connection interruption was recorded at 18:40 UTC."),
        ),
        required_facts=("F1", "F2", "F3", "F4"),
        proposed_facts=(
            _fact("F1", "A connection interruption occurred.", ("E1",)),
            _fact(
                "F2", "The interruption lasted five minutes.", (), ReviewAction.ACCEPT
            ),
            _fact("F3", "The cause was identified.", (), ReviewAction.ACCEPT),
            _fact("F4", "Recovery was verified.", (), ReviewAction.ACCEPT),
        ),
        human_review_decisions=(
            _decision("F1", ReviewAction.ACCEPT),
            _decision("F2", ReviewAction.REJECT),
            _decision("F3", ReviewAction.REVISE),
        ),
        generated_claims=(
            _claim("C1", "F1", "A connection interruption occurred.", ("E1",)),
            _claim("C2", "F2", "The interruption lasted five minutes.", ()),
        ),
        expected_metrics=_expected(
            (2, 4, "Only two of four required facts are represented."),
            (1, 2, "Only the interruption claim has a valid evidence reference."),
            (
                1,
                3,
                "Only F1 aligns; sparse support leads to REJECT and REVISE decisions.",
            ),
        ),
    ),
    BenchmarkCase(
        case_id="CASE-010",
        title="Perfect end-to-end positive control",
        description="A complete operational review includes full evidence and mixed aligned decisions.",
        purpose="Provide a broad perfect control across coverage, attribution, and human alignment.",
        evidence=(
            _evidence("E1", "The scheduled check began at 07:00 UTC."),
            _evidence("E2", "All six checklist items were completed."),
            _evidence("E3", "One note required wording clarification."),
            _evidence("E4", "The final review closed at 07:20 UTC."),
        ),
        required_facts=("F1", "F2", "F3", "F4"),
        proposed_facts=(
            _fact("F1", "The check began at 07:00 UTC.", ("E1",), ReviewAction.ACCEPT),
            _fact(
                "F2",
                "All checklist items were completed.",
                ("E2",),
                ReviewAction.ACCEPT,
            ),
            _fact("F3", "One note needs clarification.", ("E3",), ReviewAction.REVISE),
            _fact(
                "F4", "The review closed at 07:20 UTC.", ("E4",), ReviewAction.ACCEPT
            ),
        ),
        human_review_decisions=(
            _decision("F1", ReviewAction.ACCEPT),
            _decision("F2", ReviewAction.ACCEPT),
            _decision("F3", ReviewAction.REVISE),
            _decision("F4", ReviewAction.ACCEPT),
        ),
        generated_claims=(
            _claim("C1", "F1", "The check began at 07:00 UTC.", ("E1",)),
            _claim("C2", "F2", "All six checklist items were completed.", ("E2",)),
            _claim("C3", "F3", "One note needs clarification.", ("E3",)),
            _claim("C4", "F4", "The review closed at 07:20 UTC.", ("E4",)),
        ),
        expected_metrics=_expected(
            (4, 4, "All four required facts are represented."),
            (4, 4, "All four claims reference valid evidence."),
            (4, 4, "All four generated dispositions match human decisions."),
        ),
    ),
)


def get_case(case_id: str) -> BenchmarkCase:
    for benchmark_case in CASES:
        if benchmark_case.case_id == case_id:
            return benchmark_case
    raise KeyError(f"Unknown benchmark case: {case_id}")
