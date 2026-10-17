"""Redline — local-first AI contract red-flag scanner for freelancers.

Redline reads a client contract and reports the clauses that are risky or
unfair to the freelancer, in plain English, with suggested counter-language.

The model runs locally (Ollama + an open-weight model such as Gemma), so a
confidential contract never leaves the machine it was opened on.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
