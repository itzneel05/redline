<!--
PREPUBLISH CHECKLIST (delete this block before submitting)
- [ ] Tags exactly: devchallenge, hf26challenge
- [ ] Submit through https://dev.to/challenges/hacktoberfest-week2-2026-10-12 before the deadline (Oct 18)
- [ ] Replace the screenshot placeholder with a real screenshot of the UI
- [ ] AI disclosure kept in (it reads better honest)
- [ ] Add the repo link in the Code section
-->

# I built a contract reviewer that runs on your laptop, because you can't upload a client's contract to an AI chatbot

*A submission for the [Hacktoberfest Open-Source AI Challenge — Week 2: Side Hustle](https://dev.to/challenges/hacktoberfest-week2-2026-10-12). Tag: `#hf26challenge`.*

## What I Built

**Redline** finds the risky clauses in a freelance contract before you sign it.

You paste in a client agreement. Redline gives you back an overall risk level, a list of the clauses that are unfair to *you*, the exact words that triggered each one, why it matters in business terms, and the wording to ask for instead. If you want, it drafts the short, friendly email that raises them with the client.

The person who pays for this is a freelancer. They get contracts with the traps buried in clause 9, they can't justify a lawyer at \$300 an hour for a \$2,000 job, and — this is the important part — they **cannot paste a client's confidential agreement into a cloud AI**. That last constraint is not a feature request. It decides the whole architecture.

So Redline runs a local open-weight model. Nothing is uploaded. No account, no API key, no per-token bill.

## Demo

Run it against the example contract in the repo, with **no model and no network at all**:

```
$ redline samples/unfair-contract.txt --offline

# Redline report

**Overall risk: HIGH** (9 high, 4 medium, 1 low)

Found 14 clause(s) worth a second look: 9 high, 4 medium, 1 low.

## 1. 🔴 Broad IP assignment / work for hire  _(high · IP)_

> …All work shall be considered work for hire and Designer assigns all right, title…

**Why it matters:** Transferring everything can stop you reusing your own tools, templates, and style.
**Ask for:** Assign only the final deliverables; keep ownership of your pre-existing tools and methods.

## 2. 🔴 Payment tied to the client getting paid  _(high · Payment)_

> …Payment is contingent upon Client's receipt of payment from its own customers…

**Why it matters:** Your invoice should not depend on a deal you are not part of.
**Ask for:** Delete it. You are paid for the work, not the client's cash flow.
```

<!-- Screenshot: the local web UI at http://127.0.0.1:8765 with a report rendered -->
![Redline web UI](REPLACE_WITH_SCREENSHOT_URL)

`samples/fair-contract.txt` is a reasonable agreement, and Redline returns a single low finding —
the governing-law clause. I care about that as much as the scary output: a tool that flags
everything is a tool nobody trusts.

## Code

Repo: **https://github.com/itzneel05/redline**

## How I Built It

Redline is deliberately **hybrid**, because "paste text into an LLM and hope" is not a tool.

1. **A deterministic rules engine.** `redline/rules.py` is a small library of checks for the
   classic freelance traps: unlimited revisions, work-for-hire, net-90, pay-when-paid,
   approval-at-sole-discretion, indemnities, uncapped liability, non-competes, auto-renewal, and
   more. It is plain Python, fully tested, and works with **no model at all** — the demo above is
   running nothing but this.
2. **A local open-weight model.** The model reads the whole contract, catches risks the patterns
   miss, and writes the plain-English *why* and *ask-for*. I ask it for strict JSON and then
   validate, normalise, and cap the output before it is ever shown (`redline/analyze.py`). If the
   model is unavailable or returns nonsense, Redline degrades to the rules engine and says so,
   rather than crashing or inventing clauses.
3. **No runtime dependencies.** The whole thing is the Python standard library, including the web
   UI (one page, one JSON endpoint, `http.server`). That is why `pip install` is instant and why
   it runs fine on a bleeding-edge Python.

The model backend is one small interface (`redline/llm.py`), so the rest of the code never knows
which model is loaded. Point it at different Ollama models and the tool just works.

The open-source AI is not a garnish here — it is the reason the product can exist:

- **It keeps the contract private.** Running the model locally is the only way this is ethical to
  use on real client documents.
- **It costs nothing per run.** Open weights mean a freelancer can actually afford to check every
  contract instead of only the scary ones.
- **It can be swapped or fine-tuned.** Gemma today, Qwen or Llama tomorrow; later, fine-tune on a
  person's own clause history.

*AI disclosure: I used an AI coding agent (the GitHub Copilot CLI) to help write significant parts
of this project, including tests and documentation. The design decisions, the clause library, and
the prompts are mine, and every line was reviewed and run.*

## Why Does Open Innovation Matter?

Because the feature is privacy, and you cannot buy that from a closed API.

If Redline called a hosted model, its first instruction would have to be "please don't paste
anything confidential" — which is exactly the instruction a freelancer cannot follow, because the
whole document is confidential. A local open-weight model turns that constraint from a blocker
into the selling point.

Openness also sets the price. The commercial contract-AI tools are aimed at law firms and priced
accordingly. An open model running on a laptop has no marginal cost, so the tool can be free to
run and still be a real business for whoever wants to sell support, templates, or a hosted version
later.

And it is honest about its limits. The model is asked to explain and extend a set of checks a human
wrote, not to be an oracle — which is why Redline can tell you *why* it flagged a clause, and can
run with the model switched off.

## Prize Categories

- Best Use of Gemma — Redline's analysis runs on Gemma 3 through Ollama.

*(Not legal advice. Redline flags clauses worth a conversation with the client; it is not a lawyer.)*
