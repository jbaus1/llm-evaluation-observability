from __future__ import annotations

import json
import os
import shlex
import subprocess

import pytest

from evaluation.benchmark import get_case
from evaluation.evaluate import evaluate_case
from evaluation.models import Evidence
from evaluation.semantic import (
    SemanticGroundednessEvaluator,
    SemanticJudgeError,
    SemanticJudgeOutputError,
)


class StaticJudge:
    def __init__(self, output: dict[str, object] | str) -> None:
        self.output = output
        self.prompts: list[str] = []

    def judge(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.output if isinstance(self.output, str) else json.dumps(self.output)


@pytest.mark.parametrize(
    ("classification", "supported", "score"),
    [
        ("fully_supported", True, 1.0),
        ("partially_supported", True, 0.6),
        ("unsupported", False, 0.1),
        ("contradicted", False, 0.0),
        ("insufficient", False, 0.25),
    ],
)
def test_semantic_groundedness_rubric_outcomes(
    classification: str, supported: bool, score: float
) -> None:
    judge = StaticJudge(
        {
            "supported": supported,
            "score": score,
            "classification": classification,
            "reason": f"The claim is {classification}.",
        }
    )
    evaluator = SemanticGroundednessEvaluator(judge)

    result = evaluator.evaluate("A claim.", (Evidence("E1", "Evidence text."),))

    assert result.metric_name == "semantic_groundedness"
    assert result.score == score
    assert result.numerator == int(supported)
    assert result.denominator == 1
    assert result.details == {
        "supported": supported,
        "classification": classification,
    }
    assert "Claim:\nA claim." in judge.prompts[0]
    assert "E1: Evidence text." in judge.prompts[0]


def test_case_005_distinguishes_attribution_from_semantic_support() -> None:
    case = get_case("CASE-005")
    claim = case.generated_claims[1]
    evidence = (case.evidence[1],)
    deterministic = {
        result.metric_name: result
        for result in evaluate_case(case.as_evaluation_case())
    }
    evaluator = SemanticGroundednessEvaluator(
        StaticJudge(
            {
                "supported": False,
                "score": 0.1,
                "classification": "unsupported",
                "reason": "Humidity does not establish ventilation failure.",
            }
        )
    )

    semantic = evaluator.evaluate(claim.claim, evidence)

    assert deterministic["evidence_attribution"].score == 1.0
    assert semantic.details["classification"] == "unsupported"
    assert semantic.details["supported"] is False
    assert 0.0 <= semantic.score <= 0.4


def test_case_008_conflicting_evidence_is_passed_without_resolution() -> None:
    case = get_case("CASE-008")
    claim = case.generated_claims[2]
    judge = StaticJudge(
        {
            "supported": False,
            "score": 0.25,
            "classification": "insufficient",
            "reason": "The observations conflict, so support cannot be determined.",
        }
    )
    evaluator = SemanticGroundednessEvaluator(judge)

    result = evaluator.evaluate(claim.claim, case.evidence)

    assert result.details["classification"] == "insufficient"
    assert "status indicator as green" in judge.prompts[0]
    assert "same indicator as red" in judge.prompts[0]


@pytest.mark.parametrize(
    "output",
    [
        "not json",
        json.dumps({"supported": False}),
        json.dumps(
            {
                "supported": False,
                "score": 1.5,
                "classification": "unsupported",
                "reason": "Out of range.",
            }
        ),
        json.dumps(
            {
                "supported": True,
                "score": 0.2,
                "classification": "unsupported",
                "reason": "Inconsistent support flag.",
            }
        ),
    ],
)
def test_malformed_judge_output_is_rejected(output: str) -> None:
    evaluator = SemanticGroundednessEvaluator(StaticJudge(output))

    with pytest.raises(SemanticJudgeOutputError):
        evaluator.evaluate("A claim.", ())


def test_judge_exception_is_wrapped() -> None:
    class FailingJudge:
        def judge(self, prompt: str) -> str:
            raise TimeoutError("judge timed out")

    evaluator = SemanticGroundednessEvaluator(FailingJudge())

    with pytest.raises(SemanticJudgeError, match="TimeoutError: judge timed out"):
        evaluator.evaluate("A claim.", ())


@pytest.mark.integration
def test_real_model_semantic_judge() -> None:
    command = os.getenv("SEMANTIC_JUDGE_COMMAND")
    if not command:
        pytest.skip(
            "set SEMANTIC_JUDGE_COMMAND to an opt-in real-model command that accepts "
            "a prompt on stdin and returns judge JSON"
        )

    class CommandJudge:
        def judge(self, prompt: str) -> str:
            completed = subprocess.run(
                shlex.split(command),
                input=prompt,
                capture_output=True,
                text=True,
                check=True,
            )
            return completed.stdout

    result = SemanticGroundednessEvaluator(CommandJudge()).evaluate(
        "The ventilation system failed.",
        (Evidence("E2", "The humidity reading was 45 percent."),),
    )

    assert result.details["classification"] in {"unsupported", "insufficient"}
    assert result.details["supported"] is False
    assert 0.0 <= result.score <= 0.4
