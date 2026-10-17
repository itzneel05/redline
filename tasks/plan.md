# Implementation Plan: Redline

## Overview

A local-first contract red-flag scanner for freelancers: built-in clause checks plus a locally-run
open-weight model (Gemma via Ollama) that explains each risk and proposes counter-language.
Delivered as both a CLI and a tiny local web UI.

## Architecture decisions

- **Hybrid detection.** A deterministic rule library is the backbone; the model explains and
  extends it. This keeps the tool useful offline, keeps the risky parts testable without a GPU,
  and defends against "it's just a prompt".
- **Stdlib-only runtime.** No third-party runtime dependencies (consistent with the author's other
  projects), which keeps install friction at zero and survives bleeding-edge Python versions.
- **One model interface.** `llm.ChatModel` is the single seam; everything else is pure and
  testable with a fake. Ollama is the default backend.
- **Local-only server.** The web UI binds to 127.0.0.1, reinforcing the privacy promise.
- **Model output is never trusted raw.** JSON is extracted, validated, normalised, and capped.

## Task list

### Phase 1: Foundation

- [x] Task 1: Project scaffold — `pyproject.toml`, `.gitignore`, `LICENSE`, package skeleton.
- [x] Task 2: `report.py` — `Finding` / `Report`, risk normalisation, counts, Markdown + dict
      renderers.
- [x] Task 3: `rules.py` — the deterministic clause library (~15 rules) with snippet extraction.

### Checkpoint: Foundation

- [x] `test_report.py` and `test_rules.py` pass.

### Phase 2: Model integration

- [x] Task 4: `prompts.py` — system/user prompts for analysis and for the negotiation email.
- [x] Task 5: `llm.py` — `OllamaModel` over `urllib`, `ModelError`, install guidance.
- [x] Task 6: `analyze.py` — `parse_json`, `findings_from_model`, `merge`, `analyze`,
      `draft_email`, with graceful degradation.

### Checkpoint: Model integration

- [x] `test_llm.py` and `test_analyze.py` pass; a failed model yields a warning, not a crash.

### Phase 3: Interfaces and polish

- [x] Task 7: `cli.py` — arguments, Markdown/JSON output, `--offline`, `--email`.
- [x] Task 8: `web.py` + `static/` — local server, `/api/analyze`, single-page UI with sample load.
- [x] Task 9: Docs and CI — README, SPEC, DEV post draft, GitHub Actions workflow, samples.

### Checkpoint: Complete

- [x] All 39 tests pass; `ruff` clean.
- [x] Offline run produces the expected report on `samples/unfair-contract.txt`.
- [ ] Human reviews the report UI and captures a screenshot for the submission.

## Risks and mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Model returns malformed JSON | Med | `parse_json` + validation; degrade to rule-only with a warning |
| Ollama not installed / not running | Med | Friendly `INSTALL_HELP` message; `--offline` mode still works |
| Python 3.15 without third-party wheels | Med | Runtime is stdlib-only |
| "Just a prompt wrapper" criticism | High | Hybrid rules engine + deterministic tests + offline mode |
| Confidential data leaking | High | Local-only model, 127.0.0.1 server, no telemetry |

## Open questions

- PDF/DOCX ingestion — deferred (dependency cost).
- Standard-terms diff — deferred (scope).
