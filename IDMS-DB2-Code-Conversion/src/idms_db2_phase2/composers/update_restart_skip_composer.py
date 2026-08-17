"""
Update restart/control skip composer.

Purpose:
- Do not hardcode FFRECAB to any DB2 restart table.
- Do not invent restart DB2 SQL.
- When generated output contains missing-mapping conversion blocks for
  restart/control-like IDMS records, replace those blocks with a clean
  manual-redesign comment and CONTINUE.

This is generic:
- If a record has valid Sheet Mapping + DCLGEN metadata, normal conversion
  should already have happened and this composer does nothing.
- If a record has missing mapping metadata, this composer removes the
  invalid generated SQLCODE checks because no SQL was executed.
"""

from __future__ import annotations

import re

from patterns.sequence_patterns import strip_sequence_numbers


class UpdateRestartSkipComposer:
    """
    Cleans generated missing-mapping blocks for unmapped IDMS records.

    This is intentionally conservative and only acts when the generated
    converter already emitted clear missing-mapping diagnostics.
    """

    CONVERTED_FOR_PATTERN = re.compile(
        r"^\s*\*\s*DB2:\s*Converted\s+"
        r"(?P<operation>OBTAIN\s+CALC|STORE|MODIFY|ERASE|DELETE|UPDATE|INSERT)"
        r"\s+(?:for\s+)?(?P<record>[A-Z0-9-]+)\.?\s*$",
        flags=re.IGNORECASE,
    )

    MISSING_MAPPING_MARKERS = (
        "CONVERSION SKIPPED BECAUSE SHEET MAPPING ENTRY DOES NOT EXIST",
        "MISSING SHEET MAPPING METADATA",
        "MISSING SELECT",
        "MISSING INSERT",
        "MISSING UPDATE",
        "MISSING DELETE",
        "MISSING MAPPING",
    )

    RESTART_CONTROL_HINTS = (
        "RECAB",
        "RESTART",
        "RST",
        "CONTROL",
        "CTRL",
        "CHECKPOINT",
        "CHKPT",
    )

    SQLCODE_IF_PATTERN = re.compile(
        r"^\s*IF\s+SQLCODE\b",
        flags=re.IGNORECASE,
    )

    END_IF_PATTERN = re.compile(
        r"^\s*END-IF\.?\s*$",
        flags=re.IGNORECASE,
    )

    CONTINUE_PATTERN = re.compile(
        r"^\s*CONTINUE\.?\s*$",
        flags=re.IGNORECASE,
    )

    def __init__(
        self,
    ) -> None:
        self.messages: list[str] = []

    def compose(
        self,
        text: str,
    ) -> str:
        self.messages = []

        if not text:
            return ""

        lines = self._normalize_line_endings(text).splitlines()
        output: list[str] = []
        index = 0

        while index < len(lines):
            line = lines[index]
            logical = self._logical(line)

            converted_match = self.CONVERTED_FOR_PATTERN.match(logical)

            if not converted_match:
                output.append(line)
                index += 1
                continue

            record_name = str(converted_match.group("record") or "").upper()
            block_end = self._missing_mapping_block_end(
                lines=lines,
                start_index=index,
            )

            if block_end <= index:
                output.append(line)
                index += 1
                continue

            block_lines = lines[index:block_end]

            if not self._contains_missing_mapping_marker(block_lines):
                output.append(line)
                index += 1
                continue

            output.extend(
                self._replacement_block(record_name)
            )

            index = block_end

            index = self._skip_following_sqlcode_blocks(
                lines=lines,
                start_index=index,
            )

            self.messages.append(
                f"Update restart/control skip: unmapped IDMS record {record_name} was skipped for manual redesign."
            )

        return "\n".join(output).rstrip() + "\n"

    def _missing_mapping_block_end(
        self,
        lines: list[str],
        start_index: int,
    ) -> int:
        index = start_index + 1

        while index < len(lines):
            logical = self._logical(lines[index])
            upper = logical.upper()

            if not logical:
                index += 1
                continue

            if upper.startswith("*DB2:") or upper.startswith("* DB2:"):
                index += 1
                continue

            if self.CONTINUE_PATTERN.match(logical):
                index += 1
                break

            break

        return index

    def _contains_missing_mapping_marker(
        self,
        lines: list[str],
    ) -> bool:
        combined = "\n".join(
            self._logical(line).upper()
            for line in lines
        )

        return any(
            marker in combined
            for marker in self.MISSING_MAPPING_MARKERS
        )

    def _replacement_block(
        self,
        record_name: str,
    ) -> list[str]:
        if self._looks_like_restart_or_control(record_name):
            return [
                f"* DB2: IDMS record {record_name} was not converted automatically.",
                "* DB2: Missing Sheet Mapping and DCLGEN metadata.",
                "* DB2: Restart/control logic requires manual DB2 redesign.",
                "CONTINUE.",
            ]

        return [
            f"* DB2: IDMS record {record_name} was not converted automatically.",
            "* DB2: Missing Sheet Mapping and DCLGEN metadata.",
            "* DB2: No one-to-one DB2 SQL conversion generated.",
            "CONTINUE.",
        ]

    def _looks_like_restart_or_control(
        self,
        record_name: str,
    ) -> bool:
        normalized = str(record_name or "").upper()

        return any(
            hint in normalized
            for hint in self.RESTART_CONTROL_HINTS
        )

    def _skip_following_sqlcode_blocks(
        self,
        lines: list[str],
        start_index: int,
    ) -> int:
        index = start_index

        while index < len(lines):
            logical = self._logical(lines[index])

            if not logical:
                index += 1
                continue

            if not self.SQLCODE_IF_PATTERN.match(logical):
                break

            index = self._skip_if_block(
                lines=lines,
                start_index=index,
            )

        return index

    def _skip_if_block(
        self,
        lines: list[str],
        start_index: int,
    ) -> int:
        index = start_index
        depth = 0

        while index < len(lines):
            logical = self._logical(lines[index])
            upper = logical.upper()

            if upper.startswith("IF "):
                depth += 1

            if self.END_IF_PATTERN.match(logical):
                depth -= 1
                index += 1

                if depth <= 0:
                    return index

                continue

            index += 1

        return index

    def _normalize_line_endings(
        self,
        text: str,
    ) -> str:
        return str(text or "").replace("\r\n", "\n").replace("\r", "\n")

    def _logical(
        self,
        line: str,
    ) -> str:
        text = str(line or "").rstrip()

        try:
            stripped = strip_sequence_numbers(text)
            if stripped:
                return stripped.strip()
        except Exception:
            pass

        if len(text) >= 80 and text[:6].isdigit() and text[72:80].isdigit():
            return text[7:72].strip()

        if len(text) > 6 and text[:6].isdigit():
            text = text[6:].strip()

        if len(text) >= 8 and text[-8:].isdigit():
            text = text[:-8].rstrip()

        return text.strip()