# Spec: Redline

Status: implemented (Week 2 "Side Hustle" submission)
Owner: itzneel05

## Objective

Give a freelancer a fast, private, free first pass over a client contract, so the risky clauses
get caught before signing.

**User story.** As a freelancer who cannot afford a lawyer and cannot upload a confidential
client agreement to a cloud service, I want to see the clauses that are risky or unfair to me,
understand why, and know what to ask for instead — without the document leaving my machine.

**Success criteria:**

- Paste a contract, get a report with an overall risk level and clause-level findings.
- Every finding names the clause, quotes the contract, explains the business risk, and gives
  counter-language.
- A confidential contract is never sent anywhere except a model the user runs locally.
- The built-in checks work with no model and no network.
- A badly behaved or unavailable model degrades the report; it never crashes the tool.
- The full test suite runs without a GPU, a model, or a network.

## Tech stack

- Python 3.11+, **standard library only** at runtime (no third-party runtime dependencies).
- Local inference through **Ollama** with an open-weight model (default `gemma3:4b`).
- Web UI on the standard library `http.server`; plain HTML/CSS/JS with no build step.
- Dev tooling: `pytest`, `ruff`.

## Commands

```
Install:   pip install -e .
Model:     ollama pull gemma3:4b
CLI:       redline samples/unfair-contract.txt
Offline:   redline samples/unfair-contract.txt --offline
Web:       redline-web
Test:      python -m pytest
Lint:      python -m ruff check .
```

## Project structure

```
redline/redline/     application source (rules, prompts, llm, analyze, report, cli, web, static)
redline/tests/       unit tests + fake model; no network access
redline/samples/     example contracts
redline/docs/        this spec + the DEV submission draft
redline/tasks/       plan.md and todo.md
```

## Code style

- Type hints on every public function; `from __future__ import annotations`.
- Pure logic separated from I/O: `report.py` and `rules.py` never touch the network.
- The model is reached through one small interface (`llm.ChatModel`), so tests inject a fake.

```python
def scan(text: str) -> list[Finding]:
    findings: list[Finding] = []
    for rule, pattern in _COMPILED:
        match = pattern.search(text)
        if match:
            findings.append(Finding(...))
    return findings
```

## Testing strategy

- Framework: `pytest`. Location: `redline/tests/`.
- `test_report.py` / `test_rules.py` — pure logic, fully deterministic.
- `test_analyze.py` — parsing, normalisation, merging, and graceful degradation, via a fake model.
- `test_llm.py` — request shape and error handling with a patched `urlopen`.
- `test_web.py` — the HTTP server end to end on port 0, via `urllib`.
- `test_cli.py` — argument handling and exit codes.
- No test requires a model, a GPU, or a network.

## Boundaries

- **Always:** run `pytest` and `ruff` before committing; keep runtime deps at zero; validate all
  model output before showing it.
- **Ask first:** adding any runtime dependency; changing the default model; adding a network call.
- **Never:** send contract text anywhere but the configured local model; present output as legal
  advice; commit a real client contract.

## Success criteria (verification)

- [x] 48 tests pass with `python -m pytest`.
- [x] `python -m ruff check .` passes.
- [x] `redline samples/unfair-contract.txt --offline` produces a report with the expected findings.
- [x] A model failure produces a warning and a rule-only report, not a traceback.
- [x] The server binds to 127.0.0.1 only.

## Open questions

- Add `.docx` / PDF ingestion? Deferred — paste or `.txt` covers the MVP; PDF parsing adds a
  dependency and this is a "fast, local, zero-dependency" tool.
- A "compare against my standard terms" diff? Good next feature; out of scope for the deadline.
