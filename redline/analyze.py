"""Turn contract text into a :class:`Report`.

This is the only module that combines the built-in checks, the prompts, and a
model. It always returns a plain, validated data structure - never raw model
output - so a badly behaved model degrades the report instead of breaking it.
"""

from __future__ import annotations

import json
import re

from . import prompts, rules
from .llm import ChatModel, ModelError
from .report import Finding, Report, counts_of, default_summary

_FENCE = re.compile(r"```(?:json)?", re.IGNORECASE)
_NUMBERING = re.compile(r"^\s*(?:\d+(?:\.\d+)*|[ivxlc]+)[.)]\s+", re.IGNORECASE)
_MAX_FINDINGS = 12
_MAX_TEXT = 600


class ModelOutputError(ValueError):
    """The model replied with something that is not usable JSON."""


def parse_json(raw: str) -> dict:
    """Pull a JSON object out of a model reply, fences and chatter included."""
    text = _FENCE.sub("", raw).replace("```", "").strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ModelOutputError("no JSON object found in the model output")
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ModelOutputError(f"invalid JSON from the model: {exc}") from exc
    if not isinstance(data, dict):
        raise ModelOutputError("the model output was not a JSON object")
    return data


def _clean(value: object, limit: int = _MAX_TEXT) -> str:
    if value is None:
        return ""
    text = " ".join(str(value).split())
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "\u2026"
    return text


def _strip_numbering(name: str) -> str:
    """Turn "4. INTELLECTUAL PROPERTY" into "INTELLECTUAL PROPERTY"."""
    return _NUMBERING.sub("", name).strip()


def findings_from_model(data: dict) -> list[Finding]:
    """Validate and normalise the ``findings`` array from model JSON."""
    raw = data.get("findings")
    if not isinstance(raw, list):
        return []
    findings: list[Finding] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        clause = _strip_numbering(_clean(item.get("clause")) or _clean(item.get("title")))
        why = _clean(item.get("why")) or _clean(item.get("explanation"))
        if not clause and not why:
            continue
        findings.append(
            Finding(
                clause=clause or "Unnamed clause",
                quote=_clean(item.get("quote")),
                risk=item.get("risk", "medium"),
                category=_clean(item.get("category")) or "Other",
                why=why,
                counter=_clean(item.get("counter")) or _clean(item.get("fix")),
                source="model",
            )
        )
        if len(findings) >= _MAX_FINDINGS:
            break
    return findings


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _similar(left: str, right: str, threshold: float = 0.6, min_tokens: int = 1) -> bool:
    """True when one string's words are mostly contained in the other's.

    The built-in checks quote a padded snippet while the model may quote the
    whole clause or name the finding after the clause text, so a simple
    set-containment ratio catches the same clause reported twice.
    """
    a, b = _tokens(left), _tokens(right)
    if len(a) < min_tokens or len(b) < min_tokens:
        return False
    return len(a & b) / min(len(a), len(b)) >= threshold


def merge(primary: list[Finding], secondary: list[Finding]) -> list[Finding]:
    """Keep both sources, dropping model findings that repeat a built-in one."""
    merged = list(primary)
    for finding in secondary:
        if any(
            finding.clause.strip().lower() == kept.clause.strip().lower()
            or _similar(finding.clause, kept.clause)
            or _similar(finding.quote, kept.quote)
            or _similar(finding.clause, kept.quote, min_tokens=3)
            for kept in merged
        ):
            continue
        merged.append(finding)
    return merged


def analyze(contract: str, model: ChatModel | None = None) -> Report:
    """Run the built-in checks and, if a model is given, the model pass."""
    rule_findings = rules.scan(contract)
    model_findings: list[Finding] = []
    warnings: list[str] = []
    summary = ""
    model_label: str | None = None

    if model is not None:
        model_label = getattr(model, "model", None)
        try:
            raw = model.complete(prompts.SYSTEM, prompts.user(contract))
            data = parse_json(raw)
            model_findings = findings_from_model(data)
            summary = _clean(data.get("summary"))
        except (ModelOutputError, ModelError) as exc:
            warnings.append(
                f"Model unavailable or unusable ({exc}); showing built-in checks only."
            )

    findings = merge(rule_findings, model_findings)
    if not summary:
        summary = default_summary(counts_of(findings))
    return Report(summary=summary, findings=findings, warnings=warnings, model=model_label)


def email_bullets(report: Report) -> list[str]:
    """The handful of clauses worth raising, for the negotiation email prompt."""
    return [
        f"{f.clause} | {f.why or 'risky for the freelancer'} | {f.counter or 'renegotiate'}"
        for f in report.sorted_findings()
        if f.risk in ("high", "medium")
    ]


_EMAIL_KEYS = ("body", "email", "text", "message", "content")


def _strip_subject(text: str) -> str:
    """Drop a leading "Subject: ..." line the model adds despite the prompt."""
    lines = text.splitlines()
    if lines and lines[0].strip().lower().startswith("subject:"):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines.pop(0)
    return "\n".join(lines).strip()


def _email_body(raw: str) -> str:
    """Pull the email text out of a reply, unwrapping JSON the model may add."""
    text = raw.strip()
    if text.startswith("{"):
        try:
            data = parse_json(text)
        except ModelOutputError:
            pass
        else:
            for key in _EMAIL_KEYS:
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    text = value.strip()
                    break
    return _strip_subject(text)


def draft_email(report: Report, model: ChatModel) -> str:
    """Ask the model for a short negotiation email based on the report."""
    raw = model.complete(
        prompts.EMAIL_SYSTEM,
        prompts.email_user(report.summary, email_bullets(report)),
        json_mode=False,
    )
    return _email_body(raw)
