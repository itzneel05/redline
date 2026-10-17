"""Built-in clause detection.

These regex checks are the tool's backbone. They run with no model and no
network at all, which keeps Redline useful offline, keeps the risky parts
testable without a GPU, and gives the model a floor to explain and extend
rather than a blank page to hallucinate on.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .report import Finding


@dataclass(frozen=True)
class Rule:
    id: str
    category: str
    risk: str
    title: str
    pattern: str
    why: str
    counter: str


RULES: tuple[Rule, ...] = (
    Rule(
        id="unlimited-revisions",
        category="Scope",
        risk="high",
        title="Unlimited revisions",
        pattern=r"unlimited\s+revisions?|revisions?\s+(?:until|in\s+perpetuity)|"
        r"as\s+many\s+revisions\s+as|revise\s+until\s+(?:the\s+)?(?:client|they)\s+(?:is|are)\s+satisfied",
        why="An open-ended revision loop turns a fixed-price project into unpaid work.",
        counter="Cap it: two rounds of revisions are included, then further work is billed hourly.",
    ),
    Rule(
        id="work-for-hire",
        category="IP",
        risk="high",
        title="Broad IP assignment / work for hire",
        pattern=r"work\s+for\s+hire|assigns?\s+(?:all\s+)?(?:right,?\s+title,?\s+and\s+interest|"
        r"all\s+rights|intellectual\s+property)|all\s+intellectual\s+property\s+rights",
        why="Transferring everything can stop you reusing your own tools, templates, and style.",
        counter=(
            "Assign only the final deliverables; keep ownership of your pre-existing "
            "tools and methods."
        ),
    ),
    Rule(
        id="perpetual-license",
        category="IP",
        risk="medium",
        title="Perpetual / irrevocable licence",
        pattern=r"perpetual|in\s+perpetuity|irrevocabl",
        why="A licence that never ends can outlive the relationship and the payment.",
        counter="Scope the licence to the agreed use, and make it revocable if invoices go unpaid.",
    ),
    Rule(
        id="non-compete",
        category="Restrictions",
        risk="high",
        title="Non-compete",
        pattern=r"non-?compet|shall\s+not\s+(?:directly\s+or\s+indirectly\s+)?(?:work\s+for|engage|provide\s+services)",
        why="A non-compete can lock you out of the rest of your own market.",
        counter="Strike it, or narrow it to named direct competitors for a short, fixed period.",
    ),
    Rule(
        id="exclusivity",
        category="Restrictions",
        risk="medium",
        title="Exclusivity",
        pattern=r"exclusiv",
        why="Exclusivity blocks you from taking other work in the same space.",
        counter="Remove exclusivity, or price it as an explicit premium retainer.",
    ),
    Rule(
        id="net-90",
        category="Payment",
        risk="high",
        title="Very long payment terms (net 60/90/120)",
        pattern=r"net\s*(?:60|90|120)|payment\s+within\s+(?:60|90|120)\s+days",
        why="Waiting three months to be paid means you are financing the client for free.",
        counter="Ask for net 14 or net 30, with a deposit up front.",
    ),
    Rule(
        id="net-45",
        category="Payment",
        risk="medium",
        title="Slow payment terms (net 45)",
        pattern=r"net\s*45|payment\s+within\s+45\s+days",
        why="Terms longer than a month strain your cash flow for no good reason.",
        counter="Ask for net 14 or net 30.",
    ),
    Rule(
        id="pay-when-paid",
        category="Payment",
        risk="high",
        title="Payment tied to the client getting paid",
        pattern=r"pay\s+when\s+paid|payment\s+(?:is\s+)?contingent|upon\s+receipt\s+of\s+payment\s+from",
        why="Your invoice should not depend on a deal you are not part of.",
        counter="Delete it. You are paid for the work, not the client's cash flow.",
    ),
    Rule(
        id="sole-discretion",
        category="Payment",
        risk="high",
        title="Approval at the client's sole discretion",
        pattern=r"sole\s+(?:and\s+absolute\s+)?discretion|at\s+(?:the\s+)?(?:company|client|their|its)\s+discretion|"
        r"upon\s+(?:client|company)\s+approval",
        why=(
            "If the client alone decides whether work is 'acceptable', payment can be "
            "withheld indefinitely."
        ),
        counter="Make acceptance objective: deliver against the agreed brief and specs.",
    ),
    Rule(
        id="no-additional-cost",
        category="Scope",
        risk="high",
        title="Extra work at no additional cost",
        pattern=r"at\s+no\s+(?:additional\s+)?(?:cost|charge|fee)|free\s+of\s+charge|at\s+no\s+extra\s+cost",
        why="Sweeping 'no extra cost' language swallows every change request.",
        counter="Add a change-order clause: new work needs a written order and a price.",
    ),
    Rule(
        id="indemnify",
        category="Liability",
        risk="high",
        title="Indemnity",
        pattern=r"indemnif|hold\s+harmless",
        why="Indemnities can make you pay for the client's problems, not just your own.",
        counter="Limit it to your own negligence, and cap the total at the fees you were paid.",
    ),
    Rule(
        id="uncapped-liability",
        category="Liability",
        risk="high",
        title="Uncapped liability",
        pattern=r"uncapped|unlimited\s+liability|liable\s+for\s+all\s+damages|without\s+limitation\s+of\s+liability",
        why="Without a cap, a single mistake can cost more than the entire project.",
        counter="Cap total liability at the fees paid for the project (or a fixed figure).",
    ),
    Rule(
        id="auto-renewal",
        category="Term",
        risk="medium",
        title="Automatic renewal",
        pattern=r"automatic(?:ally)?\s+renew|auto-?renew",
        why="Silent renewals extend a deal you may want to renegotiate.",
        counter="Require written agreement to renew, with a notice window.",
    ),
    Rule(
        id="termination-for-convenience",
        category="Term",
        risk="medium",
        title="Termination for convenience",
        pattern=r"terminat\w*\s+(?:this\s+agreement\s+)?(?:at\s+any\s+time|for\s+convenience|without\s+cause)",
        why="If the client can walk away instantly, you can be left with unfinished, unpaid work.",
        counter="Require written notice and payment for all work completed to date.",
    ),
    Rule(
        id="legal-jurisdiction",
        category="Legal",
        risk="low",
        title="Governing law / jurisdiction",
        pattern=r"governing\s+law|exclusive\s+jurisdiction|venue\s+shall",
        why="A distant or unfamiliar forum makes a dispute expensive to pursue.",
        counter="Check the named courts; ask for your own region if the gap is large.",
    ),
)

_COMPILED = tuple((rule, re.compile(rule.pattern, re.IGNORECASE)) for rule in RULES)

_SNIPPET_PAD = 60


def _snippet(text: str, start: int, end: int) -> str:
    left = max(0, start - _SNIPPET_PAD)
    right = min(len(text), end + _SNIPPET_PAD)
    snippet = " ".join(text[left:right].split())
    prefix = "\u2026" if left > 0 else ""
    suffix = "\u2026" if right < len(text) else ""
    return f"{prefix}{snippet}{suffix}"


def scan(text: str) -> list[Finding]:
    """Return one Finding per built-in rule that matches the contract."""
    findings: list[Finding] = []
    for rule, pattern in _COMPILED:
        match = pattern.search(text)
        if match:
            findings.append(
                Finding(
                    clause=rule.title,
                    quote=_snippet(text, match.start(), match.end()),
                    risk=rule.risk,
                    category=rule.category,
                    why=rule.why,
                    counter=rule.counter,
                    source="rule",
                )
            )
    return findings
