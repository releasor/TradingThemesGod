#!/usr/bin/env python3
"""Initialize and append validated sections to review-report.md."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

VERDICTS = {"PASS", "NEEDS_FIXES"}
EVENTS = {
    "main-review-round",
    "repair-verification",
    "final-verification",
}
FINAL_HEADING = "## Final Result"


class ReportStateError(ValueError):
    """Raised when an operation would produce an invalid report lifecycle."""


def _require_object(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ReportStateError("input must be a JSON object")
    return data


def _require_text(data: dict[str, Any], name: str) -> str:
    value = data.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ReportStateError(f"{name} must be a non-empty string")
    return value.strip()


def _require_count(data: dict[str, Any], name: str, *, maximum: int | None = None) -> int:
    value = data.get(name)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ReportStateError(f"{name} must be a non-negative integer")
    if maximum is not None and value > maximum:
        raise ReportStateError(f"{name} cannot exceed {maximum}")
    return value


def _report_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise ReportStateError("report must be initialized before append") from error


def _ensure_appendable(path: Path) -> None:
    text = _report_text(path)
    if "## Status: IN_PROGRESS" not in text:
        raise ReportStateError("report is not an initialized in-progress execution")
    if FINAL_HEADING in text:
        raise ReportStateError("cannot append after Final Result")


def _append_section(path: Path, section: str) -> None:
    with path.open("a", encoding="utf-8") as report:
        report.write(section.rstrip() + "\n\n")


def initialize_report(path: Path) -> None:
    """Start a new execution and remove stale prior execution content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Review Report\n\n## Status: IN_PROGRESS\n\n", encoding="utf-8")


def _render_event(data: dict[str, Any]) -> str:
    event = data.get("event")
    if event not in EVENTS:
        raise ReportStateError(f"event has invalid value: {event!r}")

    if event == "main-review-round":
        round_number = _require_count(data, "round", maximum=10)
        if round_number < 1:
            raise ReportStateError("round must be at least 1")
        findings = _require_count(data, "findings")
        accepted = _require_count(data, "accepted")
        rejected = _require_count(data, "rejected")
        unresolved = _require_count(data, "unresolved")
        if accepted + rejected + unresolved != findings:
            raise ReportStateError(
                "accepted + rejected + unresolved must equal findings"
            )
        return "\n".join(
            [
                f"## Main Review Round {round_number}",
                "",
                "- Status: COMPLETED",
                f"- Findings: {findings}",
                f"- Accepted: {accepted}",
                f"- Rejected: {rejected}",
                f"- Unresolved: {unresolved}",
                f"- Next: {_require_text(data, 'next')}",
            ]
        )

    if event == "repair-verification":
        return "\n".join(
            [
                "## Repair Verification",
                "",
                f"- Fixed Findings: {_require_count(data, 'fixed_findings')}",
                f"- Verification: {_require_text(data, 'verification')}",
                f"- Next: {_require_text(data, 'next')}",
            ]
        )

    status = _require_text(data, "status")
    if status not in {"COMPLETED", "FAILED"}:
        raise ReportStateError(f"status has invalid value: {status!r}")
    return "\n".join(
        [
            "## Final Verification",
            "",
            f"- Status: {status}",
            f"- Evidence: {_require_text(data, 'evidence')}",
        ]
    )


def append_event(path: Path, data: Any) -> None:
    """Append one validated progress event to an active execution."""
    _ensure_appendable(path)
    _append_section(path, _render_event(_require_object(data)))


def append_final_result(path: Path, data: Any) -> None:
    """Append the sole terminal result for the current execution."""
    _ensure_appendable(path)
    valid = _require_object(data)
    verdict = valid.get("verdict")
    if verdict not in VERDICTS:
        raise ReportStateError(f"verdict has invalid value: {verdict!r}")
    main_rounds = _require_count(valid, "main_review_rounds", maximum=10)
    accepted = _require_count(valid, "accepted_findings")
    fixed = _require_count(valid, "fixed_findings")
    rejected = _require_count(valid, "rejected_findings")
    unresolved = _require_count(valid, "unresolved_findings")
    if fixed > accepted:
        raise ReportStateError("fixed_findings cannot exceed accepted_findings")
    if verdict == "PASS" and (unresolved or fixed != accepted):
        raise ReportStateError(
            "PASS requires every accepted finding fixed and no unresolved findings"
        )
    if verdict == "NEEDS_FIXES" and not unresolved and fixed == accepted:
        raise ReportStateError(
            "NEEDS_FIXES requires an unfixed accepted or unresolved finding"
        )

    section = "\n".join(
        [
            FINAL_HEADING,
            "",
            f"- Verdict: {verdict}",
            f"- Main Review Rounds: {main_rounds}",
            f"- Accepted Findings: {accepted}",
            f"- Fixed Findings: {fixed}",
            f"- Rejected Findings: {rejected}",
            f"- Unresolved Findings: {unresolved}",
            f"- Summary: {_require_text(valid, 'summary')}",
        ]
    )
    _append_section(path, section)


def _read_json_input() -> Any:
    try:
        return json.loads(sys.stdin.read())
    except json.JSONDecodeError as error:
        raise ReportStateError(f"invalid JSON input: {error}") from error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("init", "append", "finalize"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("report", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "init":
            initialize_report(args.report)
        elif args.command == "append":
            append_event(args.report, _read_json_input())
        else:
            append_final_result(args.report, _read_json_input())
    except (OSError, ReportStateError, KeyError) as error:
        print(json.dumps({"error": str(error)}, sort_keys=True))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
