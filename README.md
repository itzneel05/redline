# Redline

**Find the risky clauses in a client contract — before you sign. Runs entirely on your machine.**

Redline reads a freelance contract and reports the clauses that are risky or unfair to *you*, in
plain English, with the wording to ask for instead. The model is an open-weight one running
locally through [Ollama](https://ollama.com), so a confidential client contract never leaves the
laptop it was opened on.

> Redline is not a lawyer, and this is not legal advice. It flags clauses worth a conversation.

---

## The problem

A freelancer gets a 6-page client contract. The unfavourable parts are buried in clause 9. A
lawyer costs \$300 an hour — more than the job. The obvious shortcut is a cloud AI chat, except
that pasting a client's confidential agreement into someone else's server is a bad idea, and the
good contract-review tools are priced for law firms anyway.

So most people just sign.

## What Redline does

Paste the contract (or point Redline at a file). You get:

- an **overall risk** score, plus a count of high / medium / low findings,
- every flagged clause with the **exact words** that triggered it,
- **why it matters** in business terms, and
- the **counter-language** to ask the client for.

Optionally, Redline drafts the **negotiation email** that raises the clauses — warm, short, and
collaborative, not a threat.

## Why open-source AI is the whole point

This is not a wrapper around a closed API. The open pieces are what make the tool usable at all:

- **Privacy is the feature, not a setting.** Client contracts are confidential. Running an
  open-weight model locally is the only way a freelancer can use an AI reviewer without leaking a
  client's document. A cloud API cannot offer this.
- **Zero marginal cost.** Redline runs on a laptop with no account, no key, and no per-token bill.
  That is the difference between "a tool for law firms" and "a tool a freelancer can afford".
- **Swap the model, keep the tool.** Anything Ollama can serve works: Gemma, Qwen, Llama, Phi.
  Pick the one that fits your hardware.
- **Works offline.** Point Redline at `--offline` and the built-in clause checks run with no model
  and no network at all.

## Install

Requires Python 3.11+ and [Ollama](https://ollama.com/download).

```bash
# 1. Get a local open-weight model (Gemma 3 is a good default)
ollama pull gemma3:4b

# 2. Install Redline
pip install -e .

# 3. Analyse a contract
redline path/to/contract.txt
```

Prefer a browser? Start the local web UI (it binds to 127.0.0.1 only):

```bash
redline-web
# then open http://127.0.0.1:8765
```

Pass `--model` if you pulled something other than the default, e.g. `redline-web --model gemma3:1b`.

## See it work without a model

The built-in checks run with no model at all, so you can try Redline immediately:

```bash
redline samples/unfair-contract.txt --offline
```

```
# Redline report

**Overall risk: HIGH** (9 high, 4 medium, 1 low)

Found 14 clause(s) worth a second look: 9 high, 4 medium, 1 low.

## 1. 🔴 Broad IP assignment / work for hire  _(high · IP)_

> …4. INTELLECTUAL PROPERTY All work shall be considered work for hire and Designer assigns all right, title, and interest in all…

**Why it matters:** Transferring everything can stop you reusing your own tools, templates, and style.
**Ask for:** Assign only the final deliverables; keep ownership of your pre-existing tools and methods.
```

`samples/fair-contract.txt` is a reasonable agreement — Redline returns a single low finding
(the governing-law clause), which is the point: it is not a scare machine.

## How it works

Redline is deliberately **hybrid**, not a single prompt:

1. **Built-in checks** (`redline/rules.py`) — a small library of regex checks for the classic
   freelance traps: unlimited revisions, work-for-hire, net-90, pay-when-paid, sole-discretion
   approval, indemnities, uncapped liability, non-competes, auto-renewal, and more. Deterministic,
   testable, and useful with no model.
2. **The local model** (`redline/analyze.py` + `redline/prompts.py`) — reads the whole contract,
   finds risks the patterns miss, and writes the plain-English *why* and *ask-for* for each one.
   It is asked for strict JSON, which is validated and normalised before it is ever shown.
3. **Both are merged** and rendered the same way, so a badly behaved model degrades the report
   instead of breaking it.

## Model choices

```bash
redline contract.txt --model gemma3:4b        # default
redline contract.txt --model qwen2.5:7b       # stronger, needs more RAM
redline contract.txt --model llama3.2:3b
redline contract.txt --offline                # no model at all
```

Set `REDLINE_MODEL` and `REDLINE_HOST` to change the defaults.

## Development

```bash
pip install -e ".[dev]"
python -m pytest        # 48 tests, no network or GPU required
python -m ruff check .
```

The whole suite runs against a fake model, so nothing here needs Ollama to be running.

## Project layout

```
redline/
  rules.py       built-in clause checks (deterministic)
  prompts.py     the prompts sent to the local model
  llm.py         the Ollama client (the only place we talk to a model)
  analyze.py     merge built-in checks + model output into a Report
  report.py      the report model and its renderers
  cli.py         the command line
  web.py         the local web UI server
  static/        the single-page interface
tests/           pytest suite (fake model; no network)
samples/         example contracts
docs/            the spec and the DEV submission draft
tasks/           the implementation plan and task list
```

## License

MIT — see [LICENSE](LICENSE).
