"""Shared test fakes and fixtures."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import pytest

MODEL_JSON = {
    "summary": "This contract leans hard toward the client.",
    "findings": [
        {
            "clause": "No kill fee",
            "quote": "Client may terminate this agreement at any time",
            "risk": "medium",
            "category": "Term",
            "why": "You can be dropped after doing the work.",
            "counter": "Add a kill fee of 25% if cancelled mid-project.",
        },
        {
            "clause": "Unilateral audit rights",
            "quote": "Client may audit the Designer's records at any time",
            "risk": "critical",
            "category": "Other",
            "why": "One-sided audit clauses invite fishing expeditions.",
            "counter": "Ask for reasonable notice and a defined purpose.",
        },
    ],
}


@dataclass
class FakeModel:
    """A model stand-in: returns canned JSON, or raises a chosen error."""

    model: str = "fake-model"
    payload: object = None
    error: Exception | None = None
    calls: list[tuple[str, str]] = field(default_factory=list)

    def complete(self, system: str, user: str, *, json_mode: bool = True) -> str:
        self.calls.append((system, user))
        if self.error is not None:
            raise self.error
        payload = MODEL_JSON if self.payload is None else self.payload
        return json.dumps(payload)


@pytest.fixture
def sample_contract() -> str:
    return (
        "Design services agreement. Client may request unlimited revisions until Client is "
        "satisfied. Payment is net 90 days from invoice. All work shall be considered work "
        "for hire. Designer shall indemnify and hold harmless Client and shall be liable for "
        "all damages without limitation of liability."
    )
