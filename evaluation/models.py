from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ReviewAction(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    REVISE = "REVISE"


@dataclass(frozen=True, slots=True)
class Evidence:
    evidence_id: str
    content: str


@dataclass(frozen=True, slots=True)
class ProposedFact:
    fact_id: str
    claim: str
    evidence_ids: tuple[str, ...]
    disposition: ReviewAction


@dataclass(frozen=True, slots=True)
class HumanReviewDecision:
    fact_id: str
    action: ReviewAction


@dataclass(frozen=True, slots=True)
class GeneratedClaim:
    claim_id: str
    fact_id: str | None
    claim: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    case_id: str
    evidence: tuple[Evidence, ...]
    required_fact_ids: tuple[str, ...]
    proposed_facts: tuple[ProposedFact, ...]
    human_review_decisions: tuple[HumanReviewDecision, ...]
    generated_claims: tuple[GeneratedClaim, ...]


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    metric_name: str
    score: float
    numerator: int
    denominator: int
    details: dict[str, Any]
    reason: str
