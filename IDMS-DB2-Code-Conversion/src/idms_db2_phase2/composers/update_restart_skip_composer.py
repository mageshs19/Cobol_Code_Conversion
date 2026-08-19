from __future__ import annotations

import re

from patterns.sequence_patterns import strip_sequence_numbers


class UpdateRestartSkipComposer:
    """
    Cleans generated missing-mapping blocks for unmapped restart/control records.

    Generic rule:
    - Do not hardcode FFRECAB to any DB2 restart table.
    - Do not invent DB2 restart SQL.
    - If generated output says SELECT/INSERT/UPDATE conversion was skipped
      for a restart/control-like record, replace that generated block with
      a manual redesign comment and CONTINUE.
    - Remove SQLCODE checks after skipped SQL because no SQL was executed.
    """

    CONVERTED_FOR_PATTERN = re.compile(
        r"^\s*\*?\s*DB2:\s*Converted\s+"
        r"(?P<operation>OBTAIN\s+CALC|STORE|MODIFY|ERASE|DELETE|UPDATE|INSERT)"
        r"\s+(?:for\s+)?(?P<record>[A-Z0-9-]+)\.?\s*$",
        flags=re.IGNORECASE,
    )

    SKIPPED_FOR_PATTERN = re.compile(
        r"^\s*\*?\s*DB2:\s*"
        r"(?P<operation>SELECT|INSERT|UPDATE|DELETE|STORE|MODIFY|OBTAIN\s+CALC)"
        r"\s+conversion\s+skipped\s+for\s+(?P<record>[A-Z0-9-]+)\.?\s*$",
        flags=re.IGNORECASE,
    )

    MISSING_MAPPING_MARKERS = (
        "CONVERSION SKIPPED",
        "MISSING SHEET MAPPING",
        "MISSING DCLGEN",
        "MISSING SELECT",
        "MISSING INSERT",
        "MISSING UPDATE",
        "MISSING DELETE",
        "MISSING MAPPING",
        "MISSING KEY COLUMN METADATA",
        "INCOMPLETE CONSERVATIVE UPDATE METADATA",
        "MISSING INSERT COLUMNS",
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

    DB2_COMMENT_PATTERN = re.compile(
        r"^\s*\*?\s*DB2:",
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
            logical = self._logical(lines[index])

            skipped_match = self.SKIPPED_FOR_PATTERN.match(logical)
            converted_match = self.CONVERTED_FOR_PATTERN.match(logical)

            if skipped_match:
                record_name = str(skipped_match.group("record") or "").upper()

                if not self._looks_like_restart_or_control(record_name):
                    output.append(lines[index])
                    index += 1
                    continue

                block_end = self._skipped_block_end(
                    lines=lines,
                    start_index=index,
                )

                output.extend(self._replacement_block(record_name))
                index = self._skip_following_sqlcode_blocks(
                    lines=lines,
                    start_index=block_end,
                )
                self.messages.append(
                    f"Update restart/control skip: restart/control record {record_name} requires manual DB2 redesign."
                )
                continue

            if converted_match:
                record_name = str(converted_match.group("record") or "").upper()

                if not self._looks_like_restart_or_control(record_name):
                    output.append(lines[index])
                    index += 1
                    continue

                block_end = self._converted_missing_mapping_block_end(
                    lines=lines,
                    start_index=index,
                )

                block_lines = lines[index:block_end]

                if not self._contains_missing_mapping_marker(block_lines):
                    output.append(lines[index])
                    index += 1
                    continue

                output.extend(self._replacement_block(record_name))
                index = self._skip_following_sqlcode_blocks(
                    lines=lines,
                    start_index=block_end,
                )
                self.messages.append(
                    f"Update restart/control skip: restart/control record {record_name} requires manual DB2 redesign."
                )
                continue

            output.append(lines[index])
            index += 1

        return "\n".join(output).rstrip() + "\n"

    def _converted_missing_mapping_block_end(
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

            if self.DB2_COMMENT_PATTERN.match(logical):
                index += 1
                continue

            if self.CONTINUE_PATTERN.match(logical):
                index += 1
                break

            break

        return index

    def _skipped_block_end(
        self,
        lines: list[str],
        start_index: int,
    ) -> int:
        index = start_index + 1

        while index < len(lines):
            logical = self._logical(lines[index])

            if not logical:
                index += 1
                continue

            if self.DB2_COMMENT_PATTERN.match(logical):
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
        return [
            f"*DB2: IDMS record {record_name} was not converted automatically.",
            "*DB2: Missing Sheet Mapping and DCLGEN metadata.",
            "*DB2: Restart/control logic requires manual DB2 redesign.",
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

            if not self.SQLCODE_IF_PATTERN.match(logical):
                break

            index = self._skip_if_block(lines, index)

        return index

    def _skip_if_block(
        self,
        lines: list[str],
        start_index: int,
    ) -> int:
        index = start_index

        while index < len(lines):
            logical = self._logical(lines[index])
            index += 1

            if self.END_IF_PATTERN.match(logical):
                break

        return index

    def _logical(
        self,
        line: str,
    ) -> str:
        return strip_sequence_numbers(str(line or "")).strip()

    def _normalize_line_endings(
        self,
        text: str,
    ) -> str:
        return str(text or "").replace("\r\n", "\n").replace("\r", "\n")