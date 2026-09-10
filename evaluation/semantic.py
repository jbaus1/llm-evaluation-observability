from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, Sequence

from evaluation.models import EvaluationResult, Evidence


class GroundednessClassification(str, Enum):
    FULLY_SUPPORTED = "fully_supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNSUPPORTED = "unsupported"
    CONTRADICTED = "contradicted"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True, slots=True)
class JudgeOutput:
    supported: bool
    score: float
    classification: GroundednessClassification
    reason: str


class SemanticJudge(Protocol):
    def judge(self, prompt: str) -> str: ...


class SemanticJudgeError(RuntimeError):
    pass


class SemanticJudgeOutputError(SemanticJudgeError):
    pass


RUBRIC = """Classify whether the claim is supported by the supplied evidence.

Use exactly one classification:
- fully_supported: all material parts of the claim follow from the evidence.
- partially_supported: some material parts follow, but at least one part is unsupported.
- unsupported: the evidence does not establish the claim and does not directly refute it.
- contradicted: the evidence directly conflicts with the claim.
- insufficient: the evidence is absent, too limited, or internally conflicting, so support cannot be determined.

Set supported=true only for fully_supported or partially_supported.
Set score from 0.0 to 1.0, where higher means stronger evidentiary support.
Return JSON only with keys: supported, score, classification, reason.
Keep reason to one short sentence."""


class SemanticGroundednessEvaluator:
    def __init__(self, judge: SemanticJudge) -> None:
        self._judge = judge

    def evaluate(
        self,
        claim: str,
        supporting_evidence: Sequence[Evidence],
    ) -> EvaluationResult:
        prompt = self._build_prompt(claim, supporting_evidence)
        try:
            raw_output = self._judge.judge(prompt)
        except Exception as error:
            raise SemanticJudgeError(
                f"Semantic judge failed: {type(error).__name__}: {error}"
            ) from error

        output = self._parse_output(raw_output)
        return EvaluationResult(
            metric_name="semantic_groundedness",
            score=output.score,
            numerator=int(output.supported),
            denominator=1,
            details={
                "supported": output.supported,
                "classification": output.classification.value,
            },
            reason=output.reason,
        )

    @staticmethod
    def _build_prompt(claim: str, evidence: Sequence[Evidence]) -> str:
        evidence_text = "\n".join(
            f"- {item.evidence_id}: {item.content}" for item in evidence
        )
        if not evidence_text:
            evidence_text = "- No evidence provided."
        return f"{RUBRIC}\n\nClaim:\n{claim}\n\nEvidence:\n{evidence_text}"

    @staticmethod
    def _parse_output(raw_output: str) -> JudgeOutput:
        try:
            payload = json.loads(raw_output)
        except (TypeError, json.JSONDecodeError) as error:
            raise SemanticJudgeOutputError(
                "Judge output must be valid JSON."
            ) from error

        if not isinstance(payload, dict):
            raise SemanticJudgeOutputError("Judge output must be a JSON object.")

        supported = payload.get("supported")
        score = payload.get("score")
        classification_value = payload.get("classification")
        reason = payload.get("reason")

        if not isinstance(supported, bool):
            raise SemanticJudgeOutputError("Judge field 'supported' must be boolean.")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise SemanticJudgeOutputError("Judge field 'score' must be numeric.")
        if not 0.0 <= float(score) <= 1.0:
            raise SemanticJudgeOutputError(
                "Judge field 'score' must be between 0.0 and 1.0."
            )
        try:
            classification = GroundednessClassification(classification_value)
        except (TypeError, ValueError) as error:
            raise SemanticJudgeOutputError(
                "Judge field 'classification' is not a rubric classification."
            ) from error
        if not isinstance(reason, str) or not reason.strip():
            raise SemanticJudgeOutputError(
                "Judge field 'reason' must be non-empty text."
            )

        expected_supported = classification in {
            GroundednessClassification.FULLY_SUPPORTED,
            GroundednessClassification.PARTIALLY_SUPPORTED,
        }
        if supported is not expected_supported:
            raise SemanticJudgeOutputError(
                "Judge field 'supported' is inconsistent with its classification."
            )

        return JudgeOutput(
            supported=supported,
            score=float(score),
            classification=classification,
            reason=reason.strip(),
        )
