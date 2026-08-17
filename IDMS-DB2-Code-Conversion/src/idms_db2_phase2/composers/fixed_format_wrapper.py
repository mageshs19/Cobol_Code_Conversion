"""
Fixed-format COBOL body wrapper.

Responsibilities:
- Split long comments.
- Split long MOVE statements.
- Split IF statements with AND/OR safely.
- Split generic long statements by word boundaries.
- Keep each body within columns 8-72.
"""

from __future__ import annotations

import re


try:
    from patterns.fixed_format_patterns import (
        BOOLEAN_OPERATOR_END_PATTERN,
        IF_BOOLEAN_SPLIT_PATTERN,
        MOVE_STATEMENT_PATTERN,
    )
except Exception:
    BOOLEAN_OPERATOR_END_PATTERN = re.compile(
        r"\b(?:AND|OR)\s*$",
        flags=re.IGNORECASE,
    )

    IF_BOOLEAN_SPLIT_PATTERN = re.compile(
        r"(\s+AND\s+|\s+OR\s+)",
        flags=re.IGNORECASE,
    )

    MOVE_STATEMENT_PATTERN = re.compile(
        r"^MOVE\s+(?P<src>.+?)\s+TO\s+(?P<tgt>.+?\.?)$",
        flags=re.IGNORECASE,
    )


try:
    from rules.fixed_format_rules import (
        BODY_WIDTH,
        COMMENT_INDICATOR,
        PAGE_INDICATOR,
    )
except Exception:
    BODY_WIDTH = 65
    COMMENT_INDICATOR = "*"
    PAGE_INDICATOR = "/"


class FixedFormatWrapper:
    def wrap_body(
        self,
        body: str,
        indicator: str,
        inside_exec_sql: bool,
        current_division: str,
        previous_procedure_indent: str,
    ) -> list[str]:
        text = str(body or "").rstrip()

        if len(text) <= BODY_WIDTH:
            return [text]

        if indicator in {COMMENT_INDICATOR, PAGE_INDICATOR}:
            return self.wrap_comment_body(text)

        return self.wrap_cobol_body(
            text=text,
            inside_exec_sql=inside_exec_sql,
            current_division=current_division,
            previous_procedure_indent=previous_procedure_indent,
        )

    def wrap_comment_body(
        self,
        text: str,
    ) -> list[str]:
        clean = str(text or "").strip()

        if not clean:
            return [""]

        return self.wrap_by_words(
            text=clean,
            continuation_indent="",
        )

    def wrap_cobol_body(
        self,
        text: str,
        inside_exec_sql: bool,
        current_division: str,
        previous_procedure_indent: str,
    ) -> list[str]:
        raw = str(text or "").rstrip()
        logical = raw.strip()

        indent = self.leading_spaces(
            raw,
            default=" " if current_division == "PROCEDURE" else "",
        )

        if inside_exec_sql:
            indent = self.leading_spaces(
                raw,
                default=" ",
            )

        if_lines = self.wrap_if_statement(
            logical=logical,
            indent=indent,
        )

        if if_lines:
            return if_lines

        move_lines = self.wrap_move_statement(
            logical=logical,
            indent=indent,
        )

        if move_lines:
            return move_lines

        return self.wrap_by_words(
            text=indent + logical,
            continuation_indent=indent + " ",
        )

    def wrap_if_statement(
        self,
        logical: str,
        indent: str,
    ) -> list[str]:
        text = str(logical or "").strip()

        if not text.upper().startswith("IF "):
            return []

        split_result = self.split_condition_on_boolean_operator(text)

        if not split_result:
            return self.wrap_by_words(
                text=indent + text,
                continuation_indent=indent + " ",
            )

        left_part, operator, right_part = split_result

        first_line = f"{indent}{left_part.rstrip()}"
        second_line = f"{indent}{operator.strip().upper()} {right_part.strip()}"

        return self.force_lines_to_body_width(
            lines=[first_line, second_line],
            continuation_indent=indent + " ",
        )

    def split_condition_on_boolean_operator(
        self,
        logical: str,
    ) -> tuple[str, str, str] | None:
        text = str(logical or "").strip()

        tokens = IF_BOOLEAN_SPLIT_PATTERN.split(
            text,
            maxsplit=1,
        )

        if len(tokens) < 3:
            return None

        left_part = tokens[0].rstrip()
        operator = tokens[1].strip().upper()
        right_part = tokens[2].strip()

        if not left_part or not operator or not right_part:
            return None

        return left_part, operator, right_part

    def wrap_move_statement(
        self,
        logical: str,
        indent: str,
    ) -> list[str]:
        match = MOVE_STATEMENT_PATTERN.match(str(logical or "").strip())

        if not match:
            return []

        src = match.group("src").strip()
        tgt = match.group("tgt").strip()

        first = f"{indent}MOVE {src}"
        second = f"{indent}TO {tgt}"

        if len(first) <= BODY_WIDTH and len(second) <= BODY_WIDTH:
            return [first, second]

        return self.wrap_by_words(
            text=indent + logical,
            continuation_indent=indent + " ",
        )

    def wrap_by_words(
        self,
        text: str,
        continuation_indent: str,
    ) -> list[str]:
        raw = str(text or "").rstrip()

        if len(raw) <= BODY_WIDTH:
            return [raw]

        leading_indent = self.leading_spaces(
            raw,
            default="",
        )
        content = raw.strip()
        words = content.split()

        lines: list[str] = []
        current = leading_indent

        for word in words:
            if current.strip():
                candidate = current.rstrip() + " " + word
            else:
                candidate = leading_indent + word

            if len(candidate) <= BODY_WIDTH:
                current = candidate
                continue

            if current.strip():
                lines.append(current.rstrip())

            current = continuation_indent + word

        if current.strip():
            lines.append(current.rstrip())

        return self.force_lines_to_body_width(
            lines=lines,
            continuation_indent=continuation_indent,
        )

    def force_lines_to_body_width(
        self,
        lines: list[str],
        continuation_indent: str,
    ) -> list[str]:
        output: list[str] = []

        for line in lines:
            text = str(line or "").rstrip()

            if len(text) <= BODY_WIDTH:
                output.append(text)
                continue

            indent = self.leading_spaces(
                text,
                default=continuation_indent,
            )
            available_width = max(1, BODY_WIDTH - len(indent))
            content = text.strip()

            while content:
                part = content[:available_width].rstrip()

                if not part:
                    part = content[:available_width]

                output.append(indent + part)
                content = content[len(part):].strip()

        return self.repair_boolean_operator_only_lines(output)

    def repair_boolean_operator_only_lines(
        self,
        lines: list[str],
    ) -> list[str]:
        output: list[str] = []
        index = 0

        while index < len(lines):
            current = str(lines[index] or "").rstrip()
            current_stripped = current.strip().upper()

            if current_stripped in {"AND", "OR"} and index + 1 < len(lines):
                next_line = str(lines[index + 1] or "").rstrip()
                next_stripped = next_line.strip()

                if next_stripped:
                    indent = self.leading_spaces(
                        current,
                        default=" ",
                    )
                    repaired = f"{indent}{current_stripped} {next_stripped}"

                    if len(repaired) <= BODY_WIDTH:
                        output.append(repaired)
                        index += 2
                        continue

            output.append(current)
            index += 1

        return output

    def ends_with_boolean_operator(
        self,
        body: str,
    ) -> bool:
        return bool(
            BOOLEAN_OPERATOR_END_PATTERN.search(
                str(body or "").strip(),
            )
        )

    def is_comment_or_page_line(
        self,
        logical: str,
    ) -> bool:
        stripped = str(logical or "").strip()
        return stripped.startswith("*") or stripped.startswith("/")

    def leading_spaces(
        self,
        text: str,
        default: str = "",
    ) -> str:
        value = str(text or "")

        if not value:
            return default

        count = len(value) - len(value.lstrip(" "))

        if count <= 0:
            return default

        return value[:count]