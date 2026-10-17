from __future__ import annotations

from redline import rules


def test_scan_flags_known_risky_clauses(sample_contract: str) -> None:
    found = {finding.clause for finding in rules.scan(sample_contract)}
    assert "Unlimited revisions" in found
    assert "Very long payment terms (net 60/90/120)" in found
    assert "Broad IP assignment / work for hire" in found
    assert "Indemnity" in found
    assert "Uncapped liability" in found


def test_scan_returns_findings_sorted_by_rule_order_not_text() -> None:
    findings = rules.scan("Payment is net 90 days. Client may request unlimited revisions.")
    assert {f.risk for f in findings} == {"high"}
    assert all(f.source == "rule" for f in findings)


def test_clean_contract_has_no_findings() -> None:
    clean = "The freelancer will deliver a logo. The client will pay 500 USD within 14 days."
    assert rules.scan(clean) == []


def test_quote_is_trimmed_and_ellipsised() -> None:
    text = ("Introduction " * 30) + "unlimited revisions" + (" tail" * 30)
    findings = rules.scan(text)
    assert findings
    quote = findings[0].quote
    assert quote.startswith("\u2026")
    assert quote.endswith("\u2026")
    assert "  " not in quote  # whitespace collapsed
    assert "unlimited revisions" in quote


def test_each_rule_id_is_unique() -> None:
    ids = [rule.id for rule in rules.RULES]
    assert len(ids) == len(set(ids))
