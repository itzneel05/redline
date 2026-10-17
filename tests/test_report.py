from __future__ import annotations

from redline.report import (
    Finding,
    Report,
    counts_of,
    default_summary,
    normalize_risk,
)


def test_normalize_risk_maps_aliases_and_defaults() -> None:
    assert normalize_risk("HIGH") == "high"
    assert normalize_risk("critical") == "high"
    assert normalize_risk("warning") == "medium"
    assert normalize_risk("green") == "low"
    assert normalize_risk("nonsense") == "medium"
    assert normalize_risk(None, default="low") == "low"


def test_finding_coerces_risk_on_creation() -> None:
    finding = Finding(clause="x", quote="", risk="sevERE", category="Other", why="", counter="")
    assert finding.risk == "high"


def test_counts_and_overall_risk() -> None:
    findings = [
        Finding("a", "", "low", "Other", "", ""),
        Finding("b", "", "medium", "Other", "", ""),
    ]
    assert counts_of(findings) == {"high": 0, "medium": 1, "low": 1}
    assert Report(findings=findings).overall_risk == "medium"
    assert Report(findings=[findings[0]]).overall_risk == "low"
    assert Report(findings=[Finding("c", "", "high", "Other", "", "")]).overall_risk == "high"


def test_sorted_findings_orders_by_severity() -> None:
    report = Report(
        findings=[
            Finding("low one", "", "low", "Other", "", ""),
            Finding("high one", "", "high", "Other", "", ""),
            Finding("medium one", "", "medium", "Other", "", ""),
        ]
    )
    assert [f.clause for f in report.sorted_findings()] == ["high one", "medium one", "low one"]


def test_default_summary_reports_counts() -> None:
    assert "2 clause" in default_summary({"high": 1, "medium": 1, "low": 0})
    assert "Nothing tripped" in default_summary({"high": 0, "medium": 0, "low": 0})


def test_to_markdown_includes_headline_and_advice() -> None:
    report = Report(
        summary="Looks one-sided.",
        findings=[
            Finding(
                clause="Unlimited revisions",
                quote="revise forever",
                risk="high",
                category="Scope",
                why="unpaid work",
                counter="cap it",
            )
        ],
        model="gemma3:4b",
    )
    markdown = report.to_markdown()
    assert "Overall risk: HIGH" in markdown
    assert "Unlimited revisions" in markdown
    assert "Why it matters:** unpaid work" in markdown
    assert "gemma3:4b" in markdown


def test_to_dict_is_json_ready() -> None:
    report = Report(
        summary="s",
        findings=[Finding("a", "q", "high", "Scope", "why", "counter")],
        warnings=["w"],
        model="m",
    )
    data = report.to_dict()
    assert data["overall_risk"] == "high"
    assert data["counts"] == {"high": 1, "medium": 0, "low": 0}
    assert data["findings"][0]["clause"] == "a"
    assert data["model"] == "m"


def test_empty_report_markdown() -> None:
    markdown = Report().to_markdown()
    assert "Overall risk: LOW" in markdown
    assert "No risky clauses" in markdown
