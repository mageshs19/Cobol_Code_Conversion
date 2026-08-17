import re

from catalogs.output_sections import (
    DB2_CURSOR_PARAGRAPH_MARKER,
    DB2_INFRASTRUCTURE_MARKER,
)
from patterns.db2_patterns import END_PROGRAM_PATTERN


class ManualLayoutComposer:
    """
    Keeps generated DB2 blocks in a manual-style production layout.

    Required output order:
    1. Original COBOL header starts first.
    2. Original DATA and PROCEDURE structure remains.
    3. Generated DB2 infrastructure remains one complete block.
    4. Generated cursor OPEN/FETCH/CLOSE paragraphs are near the end.
    5. SQL-ERROR paragraph is near the end.
    6. END PROGRAM remains last.

    This composer is intentionally conservative. It normalizes spacing and
    keeps END PROGRAM as the final program boundary without rewriting business
    logic.
    """

    def compose(
        self,
        text: str,
    ) -> str:
        if not text:
            return ""

        lines = self._normalize_line_endings(text).splitlines()
        lines = self._rstrip_blank_lines(lines)

        if not lines:
            return ""

        end_program_line = ""
        end_program_index = self._find_end_program_index(lines)

        if end_program_index >= 0:
            end_program_line = lines[end_program_index]
            lines = lines[:end_program_index] + lines[end_program_index + 1:]

        lines = self._normalize_generated_block_spacing(lines)

        if end_program_line:
            lines = self._append_end_program(lines, end_program_line)

        result = "\n".join(lines)
        result = self._normalize_blank_lines(result)

        return result.strip() + "\n"

    def _normalize_line_endings(
        self,
        text: str,
    ) -> str:
        return str(text or "").replace("\r\n", "\n").replace("\r", "\n")

    def _normalize_generated_block_spacing(
        self,
        lines: list[str],
    ) -> list[str]:
        output: list[str] = []

        for line in lines:
            logical = str(line or "").upper()

            if DB2_INFRASTRUCTURE_MARKER in logical:
                output = self._rstrip_blank_lines(output)
                output.append("")

            if DB2_CURSOR_PARAGRAPH_MARKER in logical:
                output = self._rstrip_blank_lines(output)
                output.append("")

            output.append(line)

        return output

    def _append_end_program(
        self,
        lines: list[str],
        end_program_line: str,
    ) -> list[str]:
        if not end_program_line:
            return lines

        trimmed = self._rstrip_blank_lines(lines)

        if not trimmed:
            return [end_program_line]

        return trimmed + ["", end_program_line]

    def _find_end_program_index(
        self,
        lines: list[str],
    ) -> int:
        for index, line in enumerate(lines):
            logical = self._logical_line(line)

            if END_PROGRAM_PATTERN.match(logical):
                return index

        return -1

    def _logical_line(
        self,
        line: str,
    ) -> str:
        text = str(line or "").rstrip()

        text = self._remove_right_sequence(text)
        text = self._remove_left_sequence(text)

        return text.strip()

    def _remove_left_sequence(
        self,
        line: str,
    ) -> str:
        text = str(line or "")

        if len(text) > 6 and text[:6].strip().isdigit():
            return text[6:].strip()

        return text

    def _remove_right_sequence(
        self,
        line: str,
    ) -> str:
        text = str(line or "").rstrip()

        match = re.match(
            r"^(?P<body>.*?)(?:\s+(?P<right>\d{8}))\s*$",
            text,
            flags=re.IGNORECASE,
        )

        if match:
            return match.group("body").rstrip()

        return text

    def _rstrip_blank_lines(
        self,
        lines: list[str],
    ) -> list[str]:
        index = len(lines)

        while index > 0 and not str(lines[index - 1] or "").strip():
            index -= 1

        return lines[:index]

    def _lstrip_blank_lines(
        self,
        lines: list[str],
    ) -> list[str]:
        index = 0

        while index < len(lines) and not str(lines[index] or "").strip():
            index += 1

        return lines[index:]

    def _trim_blank_edges(
        self,
        lines: list[str],
    ) -> list[str]:
        return self._lstrip_blank_lines(
            self._rstrip_blank_lines(lines)
        )

    def _normalize_blank_lines(
        self,
        text: str,
    ) -> str:
        normalized = str(text or "")

        normalized = re.sub(
            r"\n{4,}",
            "\n\n\n",
            normalized,
        )

        normalized = re.sub(
            r"\n[ \t]+\n",
            "\n\n",
            normalized,
        )

        return normalized