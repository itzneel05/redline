"""Command line entry point: ``python -m redline contract.txt``."""

from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__, analyze
from .llm import DEFAULT_HOST, DEFAULT_MODEL, ModelError, OllamaModel


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="redline",
        description=(
            "Find the risky clauses in a client contract. The model runs on your "
            "machine, so the contract never leaves it."
        ),
    )
    parser.add_argument("contract", help="Path to a contract file, or - to read from stdin.")
    parser.add_argument(
        "--model",
        default=os.environ.get("REDLINE_MODEL", DEFAULT_MODEL),
        help=f"Ollama model to use (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("REDLINE_HOST", DEFAULT_HOST),
        help=f"Ollama host (default: {DEFAULT_HOST}).",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Skip the model and run the built-in clause checks only.",
    )
    parser.add_argument("--email", action="store_true", help="Also draft a negotiation email.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown.")
    parser.add_argument("--version", action="version", version=f"redline {__version__}")
    return parser


def read_contract(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _maybe_email(args: argparse.Namespace, report, model) -> str | None:
    if not (args.email and model is not None):
        return None
    try:
        return analyze.draft_email(report, model)
    except ModelError as exc:
        print(f"redline: could not draft the email ({exc})", file=sys.stderr)
        return None


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        contract = read_contract(args.contract)
    except OSError as exc:
        print(f"redline: cannot read {args.contract}: {exc}", file=sys.stderr)
        return 1

    if not contract.strip():
        print("redline: the contract is empty", file=sys.stderr)
        return 1

    model = None if args.offline else OllamaModel(model=args.model, host=args.host)
    report = analyze.analyze(contract, model=model)
    email = _maybe_email(args, report, model)

    if args.json:
        payload = report.to_dict()
        if email:
            payload["email"] = email
        print(json.dumps(payload, indent=2))
    else:
        sys.stdout.write(report.to_markdown())
        if email:
            print("\n---\n")
            print("## Draft negotiation email\n")
            print(email)

    for warning in report.warnings:
        print(f"redline: {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
