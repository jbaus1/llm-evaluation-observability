from __future__ import annotations

import os

from app.llm.models import TokenUsage
from app.observability import OpikObserver

CASE_ID = "CASE-001"


def _capture_llm_io_enabled() -> bool:
    return os.getenv("OPIK_CAPTURE_LLM_IO", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def run_investigation(observer: OpikObserver | None = None) -> dict[str, str]:
    observer = observer or OpikObserver(capture_llm_io=_capture_llm_io_enabled())
    evidence = {
        "case_id": CASE_ID,
        "records": [
            "The service reported a delayed response at 09:15 UTC.",
            "Normal response times resumed at 09:22 UTC.",
        ],
    }
    extracted_facts = {
        "facts": [
            "A response delay began at 09:15 UTC.",
            "Normal response times resumed seven minutes later.",
        ]
    }

    with observer.trace(
        f"investigation:{CASE_ID}",
        input={"case_id": CASE_ID},
        metadata={"workflow": "synthetic-investigation"},
    ) as trace:
        with trace.span(
            "evidence:process",
            input=evidence,
            metadata={"record_count": len(evidence["records"])},
        ) as evidence_span:
            evidence_span.complete(output={"status": "prepared"})

        with trace.llm_span(
            "llm:extract_facts",
            input={
                "instruction": "Extract concise facts from the evidence.",
                "evidence": evidence["records"],
            },
            model="synthetic-extractor-v1",
            provider="local-simulation",
            operation="extract_facts",
            prompt_version="1.0",
        ) as llm_span:
            llm_span.complete(
                output=extracted_facts,
                usage=TokenUsage(input_tokens=34, output_tokens=20),
            )

        with trace.span(
            "review:human",
            input={"case_id": CASE_ID, "facts": extracted_facts["facts"]},
        ) as review_span:
            review_span.complete(
                output={"action": "approved", "reviewer": "human-reviewer"}
            )

        result = {"case_id": CASE_ID, "status": "reviewed"}
        trace.complete(output=result)

    return result


if __name__ == "__main__":
    print(run_investigation())
