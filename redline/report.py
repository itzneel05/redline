"""The report model and its renderers.

Pure logic: no I/O, no model calls. Everything here is deterministic and
therefore easy to test without a GPU or a running model.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

RISK_ORDER = {"high": 0, "medium": 1, "low": 2}
VALID_RISKS = ("high", "medium", "low")
RISK_EMOJI = {"high": "\U0001f534", "medium": "\U0001f7e0", "low": "\U0001f7e2"}

_RISK_ALIASES = {
    "critical": "high",
    "severe": "high",
    "red": "high",
    "warning": "medium",
    "warn": "medium",
    "amber": "medium",
    "moderate": "medium",
    "yellow": "medium",
    "ok": "low",
    "info": "low",
    "note": "low",
    "green": "low",
    "none": "low",
}


def normalize_risk(value: object, default: str = "medium") -> str:
    """Coerce a model-provided risk label into one of high/medium/low."""
    if isinstance(value, str):
        key = _RISK_ALIASES.get(value.strip().lower(), value.strip().lower())
        if key in RISK_ORDER:
            return key
    return default


def counts_of(findings: list[Finding]) -> dict[str, int]:
    counts = {risk: 0 for risk in VALID_RISKS}
    for finding in findings:
        counts[finding.risk] = counts.get(finding.risk, 0) + 1
    return counts


def default_summary(counts: dict[str, int]) -> str:
    total = sum(counts.values())
    if total == 0:
        return (
            "Nothing tripped the built-in checks. Read it once more yourself "
            "before you sign anything."
        )
    return (
        f"Found {total} clause(s) worth a second look: "
        f"{counts['high']} high, {counts['medium']} medium, {counts['low']} low."
    )


@dataclass
class Finding:
    """One clause worth a second look."""

    clause: str
    quote: str
    risk: str
    category: str
    why: str
    counter: str
    source: str = "rule"  # "rule" (built-in check) or "model"

    def __post_init__(self) -> None:
        self.risk = normalize_risk(self.risk)


@dataclass
class Report:
    summary: str = ""
    findings: list[Finding] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    model: str | None = None

    @property
    def counts(self) -> dict[str, int]:
        return counts_of(self.findings)

    @property
    def overall_risk(self) -> str:
        counts = self.counts
        if counts["high"]:
            return "high"
        if counts["medium"]:
            return "medium"
        return "low"

    def sorted_findings(self) -> list[Finding]:
        return sorted(
            self.findings,
            key=lambda f: (RISK_ORDER.get(f.risk, 9), f.category, f.clause.lower()),
        )

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "overall_risk": self.overall_risk,
            "counts": self.counts,
            "model": self.model,
            "warnings": list(self.warnings),
            "findings": [asdict(f) for f in self.sorted_findings()],
        }

    def to_markdown(self) -> str:
        counts = self.counts
        lines = [
            "# Redline report",
            "",
            f"**Overall risk: {self.overall_risk.upper()}** "
            f"({counts['high']} high, {counts['medium']} medium, {counts['low']} low)",
        ]
        if self.model:
            lines += ["", f"_Local model: `{self.model}` — your contract never left this machine._"]
        if self.summary:
            lines += ["", self.summary]
        for warning in self.warnings:
            lines += ["", f"> :warning: {warning}"]

        ordered = self.sorted_findings()
        if not ordered:
            lines += ["", "No risky clauses found by the built-in checks."]
        for index, finding in enumerate(ordered, start=1):
            emoji = RISK_EMOJI.get(finding.risk, "")
            lines += [
                "",
                f"## {index}. {emoji} {finding.clause}  _({finding.risk} · {finding.category})_",
            ]
            if finding.quote:
                lines += ["", f"> {finding.quote}"]
            if finding.why:
                lines += ["", f"**Why it matters:** {finding.why}"]
            if finding.counter:
                lines += ["", f"**Ask for:** {finding.counter}"]
        lines.append("")
        return "\n".join(lines)
