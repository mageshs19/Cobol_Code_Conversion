"""
Final sequence resequencer service.

Generic behavior:
- Resequences already fixed-format 80-column COBOL lines.
- Preserves column 7 indicator.
- Preserves columns 8-72 COBOL body.
- Rewrites only columns 1-6 and 73-80.
- Does not hardcode program names, tables, columns, cursors, DCLGEN names,
  host variables, or business fields.

Purpose:
- Remove sequence gaps introduced by safe generated-line cleanup.
"""

from __future__ import annotations

from rules.fixed_format_rules import (
    DEFAULT_LEFT_START,
    DEFAULT_LEFT_STEP,
    DEFAULT_RIGHT_START,
    DEFAULT_RIGHT_STEP,
    TOTAL_WIDTH,
)


class FinalSequenceResequencerService:
    """
    Resequences final manual-style COBOL output.

    Physical layout:
    - Columns 1-6   : left sequence number
    - Column 7      : indicator area
    - Columns 8-72  : COBOL body
    - Columns 73-80 : right sequence number

    This service assumes the final output is already fixed-format.
    It does not reformat or wrap COBOL statements.
    """

    LEFT_START = 0
    LEFT_END = 6
    RIGHT_START = 72
    RIGHT_END = 80

    def resequence(
        self,
        text: str,
        left_start: int = DEFAULT_LEFT_START,
        left_step: int = DEFAULT_LEFT_STEP,
        right_start: int = DEFAULT_RIGHT_START,
        right_step: int = DEFAULT_RIGHT_STEP,
    ) -> str:
        source = str(text or "")

        if not source:
            return ""

        output: list[str] = []
        left_value = int(left_start)
        right_value = int(right_start)

        for line in source.splitlines():
            if not self._is_fixed_format_line(line):
                output.append(line)
                continue

            output.append(
                self._replace_sequence(
                    line=line,
                    left_value=left_value,
                    right_value=right_value,
                )
            )

            left_value += int(left_step)
            right_value += int(right_step)

        return "\n".join(output).rstrip() + "\n"

    def _is_fixed_format_line(
        self,
        line: str,
    ) -> bool:
        text = str(line or "")

        if len(text) != TOTAL_WIDTH:
            return False

        if not text[self.LEFT_START:self.LEFT_END].isdigit():
            return False

        if not text[self.RIGHT_START:self.RIGHT_END].isdigit():
            return False

        return True

    def _replace_sequence(
        self,
        line: str,
        left_value: int,
        right_value: int,
    ) -> str:
        text = str(line or "")

        left = f"{left_value:06d}"
        right = f"{right_value:08d}"

        return (
            left
            + text[self.LEFT_END:self.RIGHT_START]
            + right
        )