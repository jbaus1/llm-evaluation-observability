# Quickstart

This example records one synthetic investigation without calling an external model API.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

## Run safely without payload capture

LLM input and output capture is disabled by default in the example. Model, provider, operation, prompt version, and token usage are still recorded.

```bash
python examples/run_investigation.py
```

The observer is fail-open, so the example also completes when Opik is not installed or configured.

## Run with local Opik

Start Opik locally, then configure the endpoint and project. Enable payload capture only when the synthetic content is appropriate to record:

```bash
export OPIK_URL_OVERRIDE=http://localhost:5173/api
export OPIK_PROJECT_NAME=llm-observability-reference
export OPIK_CAPTURE_LLM_IO=true
python examples/run_investigation.py
```

The resulting hierarchy is:

```text
investigation:CASE-001
├── evidence:process
├── llm:extract_facts
└── review:human
```

The LLM span contains synthetic input/output plus model, provider, operation, prompt version, and token usage, making it suitable for later evaluation examples.

## Verify against local Opik

The integration test is opt-in and skips unless the configured endpoint responds:

```bash
OPIK_ENABLED=true OPIK_CAPTURE_LLM_IO=true pytest tests/test_opik_integration.py
```
