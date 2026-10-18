from __future__ import annotations

import pytest
from conftest import MODEL_JSON, FakeModel

from redline import analyze
from redline.llm import ModelError


def test_parse_json_handles_fences_and_chatter() -> None:
    raw = 'Here you go:\n```json\n{"summary": "ok", "findings": []}\n```\nThanks!'
    assert analyze.parse_json(raw) == {"summary": "ok", "findings": []}


@pytest.mark.parametrize("raw", ["no json here", "{not valid json}", "[1, 2, 3]"])
def test_parse_json_rejects_bad_output(raw: str) -> None:
    with pytest.raises(analyze.ModelOutputError):
        analyze.parse_json(raw)


def test_findings_from_model_normalises_and_caps() -> None:
    data = {
        "findings": [
            {"clause": "A", "risk": "critical", "why": "b", "counter": "c", "category": "Payment"},
            {"title": "B", "explanation": "why b"},  # alias fields
            {"quote": "nothing useful"},  # dropped
            "not a dict",  # dropped
        ]
        + [{"clause": f"f{i}", "why": "w"} for i in range(20)]
    }
    findings = analyze.findings_from_model(data)
    assert len(findings) == analyze._MAX_FINDINGS
    assert findings[0].risk == "high"
    assert findings[0].source == "model"
    assert findings[1].clause == "B"
    assert findings[1].category == "Other"


def test_findings_from_model_without_list() -> None:
    assert analyze.findings_from_model({"findings": "nope"}) == []


def test_merge_dedupes_by_clause() -> None:
    from redline.report import Finding

    rules_findings = [Finding("Payment terms", "", "high", "Payment", "w", "c")]
    model_findings = [
        Finding("payment TERMS", "", "high", "Payment", "w", "c"),
        Finding("Kill fee", "", "medium", "Term", "w", "c"),
    ]
    merged = analyze.merge(rules_findings, model_findings)
    assert [f.clause for f in merged] == ["Payment terms", "Kill fee"]


def test_merge_dedupes_by_quote_overlap() -> None:
    from redline.report import Finding

    rule_finding = Finding(
        "Broad IP assignment",
        "All work shall be considered work for hire and Designer assigns all right, "
        "title, and interest",
        "high",
        "IP",
        "w",
        "c",
    )
    model_finding = Finding(
        "4. INTELLECTUAL PROPERTY",
        "All work shall be considered work for hire and Designer assigns all right, title, and "
        "interest in all intellectual property to Client, including any pre-existing tools.",
        "high",
        "IP",
        "w",
        "c",
    )
    assert analyze.merge([rule_finding], [model_finding]) == [rule_finding]


def test_findings_from_model_strips_section_numbers() -> None:
    data = {"findings": [{"clause": "4. INTELLECTUAL PROPERTY", "why": "w"}]}
    assert analyze.findings_from_model(data)[0].clause == "INTELLECTUAL PROPERTY"


def test_findings_from_model_truncates_runaway_text() -> None:
    data = {"findings": [{"clause": "X", "why": "word " * 500}]}
    finding = analyze.findings_from_model(data)[0]
    assert len(finding.why) <= analyze._MAX_TEXT
    assert finding.why.endswith("\u2026")


def test_analyze_combines_rules_and_model(sample_contract: str) -> None:
    report = analyze.analyze(sample_contract, model=FakeModel())
    sources = {finding.source for finding in report.findings}
    assert sources == {"rule", "model"}
    assert report.summary == MODEL_JSON["summary"]
    assert report.model == "fake-model"
    assert report.warnings == []
    assert report.overall_risk == "high"


def test_analyze_degrades_when_model_fails(sample_contract: str) -> None:
    report = analyze.analyze(sample_contract, model=FakeModel(error=ModelError("ollama down")))
    assert report.findings and all(f.source == "rule" for f in report.findings)
    assert report.warnings and "built-in checks" in report.warnings[0]


def test_analyze_degrades_on_unusable_model_output(sample_contract: str) -> None:
    report = analyze.analyze(sample_contract, model=FakeModel(payload="not json at all"))
    assert report.warnings
    assert report.findings


def test_analyze_offline_uses_default_summary(sample_contract: str) -> None:
    report = analyze.analyze(sample_contract, model=None)
    assert report.model is None
    assert "clause" in report.summary


def test_email_bullets_and_draft_email(sample_contract: str) -> None:
    report = analyze.analyze(sample_contract, model=FakeModel())
    bullets = analyze.email_bullets(report)
    assert bullets and "|" in bullets[0]

    email_model = FakeModel(payload=None)
    email_model.complete = lambda system, user: "  Hi there, a small ask.  "  # type: ignore[method-assign]
    assert analyze.draft_email(report, email_model) == "Hi there, a small ask."
