"""Raw Opik SDK verification script.

Reads a trace back using the raw Opik 2.2.56 SDK and prints detailed
integrity information for the trace and all its spans.

Usage:
    python verify_trace.py <project_name> <trace_id>

Or set environment variables:
    export OPIK_PROJECT_NAME=<project_name>
    export OPIK_TRACE_ID=<trace_id>
    python verify_trace.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime


def main() -> None:
    project_name = os.getenv("OPIK_PROJECT_NAME")
    trace_id = os.getenv("OPIK_TRACE_ID")

    if len(sys.argv) > 1:
        project_name = sys.argv[1]
    if len(sys.argv) > 2:
        trace_id = sys.argv[2]

    if not project_name or not trace_id:
        print("Usage: python verify_trace.py <project_name> <trace_id>")
        print("Or set OPIK_PROJECT_NAME and OPIK_TRACE_ID environment variables")
        sys.exit(1)

    try:
        from opik import Opik
    except ImportError:
        print("ERROR: opik SDK not installed. Run: pip install opik")
        sys.exit(1)

    client = Opik(project_name=project_name, batching=False)

    # Fetch trace by ID
    trace = client.get_trace(trace_id=trace_id)

    if not trace:
        print(f"ERROR: Trace {trace_id} not found in project {project_name}")
        sys.exit(1)

    # Print trace information
    print("=" * 60)
    print("RAW SDK TRACE VERIFICATION")
    print("=" * 60)
    print(f"trace_id:        {trace.id}")
    print(f"trace_name:      {trace.name}")
    print(f"trace_type:      {getattr(trace, 'type', 'N/A')}")
    print(f"trace_start:     {trace.start_time}")
    print(f"trace_end:       {trace.end_time}")
    print(f"span_count:      {trace.span_count}")
    print(f"input:           {trace.input}")
    print(f"output:          {trace.output}")
    print(f"metadata:        {trace.metadata}")

    # Verify trace integrity
    errors = []
    if trace.name is None or trace.name == "":
        errors.append("FAIL: trace.name is null or empty")
    if trace.start_time is None:
        errors.append("FAIL: trace.start_time is None")
    elif trace.start_time.year == 1970:
        errors.append(f"FAIL: trace.start_time is Unix epoch: {trace.start_time}")
    if trace.end_time is None:
        errors.append("FAIL: trace.end_time is None")
    elif trace.end_time.year == 1970:
        errors.append(f"FAIL: trace.end_time is Unix epoch: {trace.end_time}")
    if trace.span_count is None or trace.span_count == 0:
        errors.append("FAIL: trace.span_count is null or zero")

    if errors:
        print("\nTRACE INTEGRITY ERRORS:")
        for error in errors:
            print(f"  {error}")
    else:
        print("\n✓ Trace integrity verified")

    # Fetch and display spans
    print("\n" + "=" * 60)
    print("RAW SDK SPAN VERIFICATION")
    print("=" * 60)

    spans = client.search_spans(
        project_name=project_name, trace_id=trace_id, max_results=100
    )

    if not spans:
        print("WARNING: No spans found for this trace")
        return

    print(f"\nTotal spans: {len(spans)}\n")

    span_errors = []
    for i, span in enumerate(spans, 1):
        print(f"--- Span {i} ---")
        print(f"name:            {span.name}")
        print(f"type:            {span.type}")
        print(f"start_time:      {span.start_time}")
        print(f"end_time:        {span.end_time}")
        print(f"trace_id:        {span.trace_id}")
        print(f"input_present:   {span.input is not None}")
        print(f"output_present:  {span.output is not None}")
        print(f"usage_present:   {span.usage is not None}")
        if span.usage:
            print(
                f"  usage.total_tokens: {getattr(span.usage, 'total_tokens', 'N/A')}"
            )

        # Verify span integrity
        if span.name is None or span.name == "":
            span_errors.append(
                f"Span {i}: FAIL - name is null or empty"
            )
        if span.type is None or span.type == "":
            span_errors.append(f"Span {i}: FAIL - type is null or empty")
        if span.start_time is None:
            span_errors.append(f"Span {i}: FAIL - start_time is None")
        elif span.start_time.year == 1970:
            span_errors.append(
                f"Span {i}: FAIL - start_time is Unix epoch: {span.start_time}"
            )
        if span.trace_id != trace.id:
            span_errors.append(
                f"Span {i}: FAIL - trace_id mismatch: {span.trace_id} != {trace.id}"
            )

        print()

    if span_errors:
        print("SPAN INTEGRITY ERRORS:")
        for error in span_errors:
            print(f"  {error}")
    else:
        print("✓ All spans integrity verified")


if __name__ == "__main__":
    main()
