from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass


MAX_BRIEF_REPAIR_ATTEMPTS = 5
SOURCE_REF_RE = re.compile(r"\[(?P<number>\d+)\]")
_HORIZONTAL_RULE_RE = re.compile(r"^\s{0,3}[-*_]{3,}\s*$")
_TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*\s*$")


@dataclass(frozen=True, slots=True)
class BriefValidation:
    invalid_numbers: tuple[int, ...] = ()
    missing_numbers: tuple[int, ...] = ()
    unreferenced_lines: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.invalid_numbers and not self.missing_numbers and not self.unreferenced_lines


def validate_brief_text(
    text: str,
    *,
    valid_numbers: frozenset[int],
    required_numbers: frozenset[int],
) -> BriefValidation:
    cited_numbers = reference_numbers(text)
    valid_cited_numbers = cited_numbers & valid_numbers
    return BriefValidation(
        invalid_numbers=tuple(sorted(cited_numbers - valid_numbers)),
        missing_numbers=tuple(sorted(required_numbers - valid_cited_numbers)),
        unreferenced_lines=tuple(unreferenced_statement_lines(text, valid_numbers)),
    )


def reference_numbers(text: str) -> frozenset[int]:
    return frozenset(int(match.group("number")) for match in SOURCE_REF_RE.finditer(text))


def remove_invalid_references(text: str, valid_numbers: frozenset[int]) -> str:
    def replace_reference(match: re.Match[str]) -> str:
        number = int(match.group("number"))
        if number in valid_numbers:
            return match.group(0)
        return ""

    return SOURCE_REF_RE.sub(replace_reference, text)


def remove_unreferenced_statement_lines(text: str, valid_numbers: frozenset[int]) -> str:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            lines.append(raw_line)
            continue
        if line_can_skip_reference(line) or reference_numbers(line) & valid_numbers:
            lines.append(raw_line)
    return "\n".join(lines)


def format_validation(validation: BriefValidation) -> str:
    lines: list[str] = []
    if validation.invalid_numbers:
        lines.append(f"Invalid source markers: {format_numbers(validation.invalid_numbers)}")
    if validation.missing_numbers:
        lines.append(f"Missing required source markers: {format_numbers(validation.missing_numbers)}")
    if validation.unreferenced_lines:
        lines.append("Statements without valid source markers:")
        lines.extend(f"- {line}" for line in validation.unreferenced_lines[:10])
    return "\n".join(lines) or "No problems."


def format_numbers(numbers: Sequence[int] | frozenset[int]) -> str:
    return ", ".join(f"[{number}]" for number in sorted(numbers))


def unreferenced_statement_lines(text: str, valid_numbers: frozenset[int]) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line_can_skip_reference(line):
            continue
        numbers = reference_numbers(line)
        if numbers & valid_numbers:
            continue
        lines.append(line)
    return lines


def line_can_skip_reference(line: str) -> bool:
    return (
        line.startswith("#")
        or _HORIZONTAL_RULE_RE.match(line) is not None
        or _TABLE_SEPARATOR_RE.match(line) is not None
    )
