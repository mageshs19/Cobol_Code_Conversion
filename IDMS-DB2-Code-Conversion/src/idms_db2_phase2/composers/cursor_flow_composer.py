"""
Cursor flow composer.

Normalizes generated cursor execution flow.

It converts mechanical flow:

    PERFORM 710-OPEN-CURSOR.
    PERFORM 720-FETCH-CURSOR.
    PERFORM BUSINESS-PARA
      UNTIL SQLCODE = 100.

to:

    PERFORM 710-OPEN-CURSOR.
    PERFORM 720-FETCH-CURSOR UNTIL CURSOR-EOC.
    PERFORM 730-CLOSE-CURSOR.

It also converts generated FETCH paragraphs:

    WHEN ZERO
        CONTINUE

to:

    WHEN ZERO
        PERFORM BUSINESS-PARA

It also removes leftover generated OBTAIN NEXT cursor calls after a cursor
has already been converted to FETCH UNTIL EOC flow.

This class is generic. It does not hardcode program names, record names,
table names, cursor names, or business paragraph names.
"""

import re
from dataclasses import dataclass

from patterns.sequence_patterns import strip_sequence_numbers


@dataclass
class CursorFlowPlan:
    cursor_name: str
    open_number: int
    fetch_number: int
    close_number: int
    open_paragraph: str
    fetch_paragraph: str
    close_paragraph: str
    eoc_condition: str
    business_paragraph: str
    open_index: int
    fetch_index: int
    business_index: int
    until_index: int


class CursorFlowComposer:
    LOOKAHEAD_LIMIT = 120

    PERFORM_CURSOR_PATTERN = re.compile(
        r"^\s*PERFORM\s+"
        r"(?P<number>\d{3})-"
        r"(?P<operation>OPEN|FETCH|CLOSE)-"
        r"(?P<cursor>[A-Z0-9-]+)"
        r"\.?\s*$",
        flags=re.IGNORECASE,
    )

    PERFORM_BUSINESS_PATTERN = re.compile(
        r"^\s*PERFORM\s+"
        r"(?P<paragraph>[A-Z0-9][A-Z0-9-]*)"
        r"\.?\s*$",
        flags=re.IGNORECASE,
    )

    UNTIL_SQLCODE_100_PATTERN = re.compile(
        r"^\s*UNTIL\s+SQLCODE\s*=\s*100\.?\s*$",
        flags=re.IGNORECASE,
    )

    CURSOR_PARAGRAPH_HEADER_PATTERN = re.compile(
        r"^\s*"
        r"(?P<number>\d{3})-"
        r"(?P<operation>OPEN|FETCH|CLOSE)-"
        r"(?P<cursor>[A-Z0-9-]+)"
        r"\.\s*$",
        flags=re.IGNORECASE,
    )

    ANY_PARAGRAPH_HEADER_PATTERN = re.compile(
        r"^\s*[A-Z0-9][A-Z0-9-]*\.\s*$",
        flags=re.IGNORECASE,
    )

    WHEN_ZERO_PATTERN = re.compile(
        r"^\s*WHEN\s+ZERO\s*$",
        flags=re.IGNORECASE,
    )

    CONTINUE_PATTERN = re.compile(
        r"^\s*CONTINUE\.?\s*$",
        flags=re.IGNORECASE,
    )

    CONVERTED_OBTAIN_NEXT_COMMENT_PATTERN = re.compile(
        r"^\s*\*\s*DB2:\s*Converted\s+OBTAIN\s+NEXT\b",
        flags=re.IGNORECASE,
    )

    CONVERTED_OBTAIN_COMMENT_PATTERN = re.compile(
        r"^\s*\*\s*DB2:\s*Converted\s+OBTAIN\b",
        flags=re.IGNORECASE,
    )

    NON_PARAGRAPH_DOTTED_LINES = {
        "CONTINUE.",
        "END-EXEC.",
        "END-EVALUATE.",
        "END-IF.",
        "END-PERFORM.",
        "EXIT.",
        "GOBACK.",
        "STOP.",
    }

    def compose(
        self,
        text: str,
    ) -> str:
        if not text:
            return ""

        lines = self._normalize_line_endings(text).splitlines()

        plans = self._discover_plans(lines)

        if plans:
            lines = self._rewrite_main_flow(
                lines=lines,
                plans=plans,
            )

            lines = self._rewrite_fetch_paragraphs(
                lines=lines,
                plans=plans,
            )

        lines = self._remove_leftover_obtain_next_cursor_calls(lines)

        return "\n".join(lines).rstrip() + "\n"

    def _normalize_line_endings(
        self,
        text: str,
    ) -> str:
        return str(text or "").replace("\r\n", "\n").replace("\r", "\n")

    def _logical(
        self,
        line: str,
    ) -> str:
        return strip_sequence_numbers(str(line or "")).strip()

    def _discover_plans(
        self,
        lines: list[str],
    ) -> list[CursorFlowPlan]:
        plans: list[CursorFlowPlan] = []
        index = 0

        while index < len(lines):
            logical = self._logical(lines[index])
            open_match = self.PERFORM_CURSOR_PATTERN.match(logical)

            if not open_match:
                index += 1
                continue

            if open_match.group("operation").upper() != "OPEN":
                index += 1
                continue

            cursor_name = open_match.group("cursor").upper()
            open_number = int(open_match.group("number"))
            fetch_number = open_number + 10
            close_number = open_number + 20

            fetch_index = self._find_fetch_after_open(
                lines=lines,
                start_index=index + 1,
                cursor_name=cursor_name,
                fetch_number=fetch_number,
            )

            if fetch_index < 0:
                index += 1
                continue

            business_info = self._find_business_loop_after_fetch(
                lines=lines,
                start_index=fetch_index + 1,
            )

            if business_info is None:
                index += 1
                continue

            business_index, until_index, business_paragraph = business_info

            plans.append(
                CursorFlowPlan(
                    cursor_name=cursor_name,
                    open_number=open_number,
                    fetch_number=fetch_number,
                    close_number=close_number,
                    open_paragraph=f"{open_number:03d}-OPEN-{cursor_name}",
                    fetch_paragraph=f"{fetch_number:03d}-FETCH-{cursor_name}",
                    close_paragraph=f"{close_number:03d}-CLOSE-{cursor_name}",
                    eoc_condition=f"{cursor_name}-EOC",
                    business_paragraph=business_paragraph,
                    open_index=index,
                    fetch_index=fetch_index,
                    business_index=business_index,
                    until_index=until_index,
                )
            )

            index = until_index + 1

        return plans

    def _find_fetch_after_open(
        self,
        lines: list[str],
        start_index: int,
        cursor_name: str,
        fetch_number: int,
    ) -> int:
        end_index = min(
            len(lines),
            start_index + self.LOOKAHEAD_LIMIT,
        )

        for index in range(start_index, end_index):
            logical = self._logical(lines[index])
            match = self.PERFORM_CURSOR_PATTERN.match(logical)

            if not match:
                continue

            if match.group("operation").upper() != "FETCH":
                continue

            if match.group("cursor").upper() != cursor_name:
                continue

            if int(match.group("number")) != fetch_number:
                continue

            return index

        return -1

    def _find_business_loop_after_fetch(
        self,
        lines: list[str],
        start_index: int,
    ) -> tuple[int, int, str] | None:
        end_index = min(
            len(lines),
            start_index + self.LOOKAHEAD_LIMIT,
        )

        for index in range(start_index, end_index):
            logical = self._logical(lines[index])

            if not logical:
                continue

            if logical.startswith("*") or logical.startswith("/"):
                continue

            if self.PERFORM_CURSOR_PATTERN.match(logical):
                continue

            business_match = self.PERFORM_BUSINESS_PATTERN.match(logical)

            if not business_match:
                continue

            business_paragraph = business_match.group("paragraph").upper()

            until_index = self._find_until_sqlcode_100(
                lines=lines,
                start_index=index + 1,
            )

            if until_index < 0:
                continue

            return index, until_index, business_paragraph

        return None

    def _find_until_sqlcode_100(
        self,
        lines: list[str],
        start_index: int,
    ) -> int:
        end_index = min(
            len(lines),
            start_index + 10,
        )

        for index in range(start_index, end_index):
            logical = self._logical(lines[index])

            if self.UNTIL_SQLCODE_100_PATTERN.match(logical):
                return index

        return -1

    def _rewrite_main_flow(
        self,
        lines: list[str],
        plans: list[CursorFlowPlan],
    ) -> list[str]:
        plan_by_open_index = {
            plan.open_index: plan
            for plan in plans
        }

        indexes_to_skip: set[int] = set()

        for plan in plans:
            indexes_to_skip.add(plan.fetch_index)
            indexes_to_skip.add(plan.business_index)
            indexes_to_skip.add(plan.until_index)

        output: list[str] = []

        for index, line in enumerate(lines):
            if index in indexes_to_skip:
                continue

            plan = plan_by_open_index.get(index)

            if plan is None:
                output.append(line)
                continue

            output.append(line)
            output.append(
                self._format_like_line(
                    reference_line=line,
                    replacement_body=(
                        f"PERFORM {plan.fetch_paragraph} "
                        f"UNTIL {plan.eoc_condition}."
                    ),
                )
            )
            output.append(
                self._format_like_line(
                    reference_line=line,
                    replacement_body=f"PERFORM {plan.close_paragraph}.",
                )
            )

        return output

    def _rewrite_fetch_paragraphs(
        self,
        lines: list[str],
        plans: list[CursorFlowPlan],
    ) -> list[str]:
        business_by_fetch_paragraph = {
            plan.fetch_paragraph.upper(): plan.business_paragraph
            for plan in plans
        }

        output: list[str] = []
        index = 0

        while index < len(lines):
            logical = self._logical(lines[index])
            header_match = self.CURSOR_PARAGRAPH_HEADER_PATTERN.match(logical)

            if not header_match:
                output.append(lines[index])
                index += 1
                continue

            if header_match.group("operation").upper() != "FETCH":
                output.append(lines[index])
                index += 1
                continue

            fetch_paragraph = (
                f"{header_match.group('number')}-"
                f"FETCH-"
                f"{header_match.group('cursor')}"
            ).upper()

            business_paragraph = business_by_fetch_paragraph.get(fetch_paragraph)

            if not business_paragraph:
                output.append(lines[index])
                index += 1
                continue

            paragraph_lines, next_index = self._collect_paragraph(
                lines=lines,
                start_index=index,
            )

            rewritten = self._replace_when_zero_continue(
                paragraph_lines=paragraph_lines,
                business_paragraph=business_paragraph,
            )

            output.extend(rewritten)
            index = next_index

        return output

    def _collect_paragraph(
        self,
        lines: list[str],
        start_index: int,
    ) -> tuple[list[str], int]:
        output = [lines[start_index]]
        index = start_index + 1

        while index < len(lines):
            logical = self._logical(lines[index])

            if self.CURSOR_PARAGRAPH_HEADER_PATTERN.match(logical):
                break

            if self._is_non_cursor_paragraph_header(logical):
                break

            output.append(lines[index])
            index += 1

        return output, index

    def _replace_when_zero_continue(
        self,
        paragraph_lines: list[str],
        business_paragraph: str,
    ) -> list[str]:
        output: list[str] = []
        index = 0

        while index < len(paragraph_lines):
            line = paragraph_lines[index]
            logical = self._logical(line)

            output.append(line)

            if not self.WHEN_ZERO_PATTERN.match(logical):
                index += 1
                continue

            next_index = self._next_non_blank_index(
                lines=paragraph_lines,
                start_index=index + 1,
            )

            if next_index < 0:
                index += 1
                continue

            next_line = paragraph_lines[next_index]
            next_logical = self._logical(next_line)

            if not self.CONTINUE_PATTERN.match(next_logical):
                index += 1
                continue

            output.extend(
                paragraph_lines[index + 1 : next_index]
            )
            output.append(
                self._format_like_line(
                    reference_line=next_line,
                    replacement_body=f"PERFORM {business_paragraph}",
                )
            )

            index = next_index + 1

        return output

    def _remove_leftover_obtain_next_cursor_calls(
        self,
        lines: list[str],
    ) -> list[str]:
        output: list[str] = []
        index = 0

        while index < len(lines):
            logical = self._logical(lines[index])

            if not self.CONVERTED_OBTAIN_NEXT_COMMENT_PATTERN.match(logical):
                output.append(lines[index])
                index += 1
                continue

            skipped_lines = [lines[index]]
            index += 1

            while index < len(lines):
                next_logical = self._logical(lines[index])

                if not next_logical:
                    skipped_lines.append(lines[index])
                    index += 1
                    continue

                if next_logical.startswith("*") and not self.CONVERTED_OBTAIN_COMMENT_PATTERN.match(next_logical):
                    break

                if self.CONVERTED_OBTAIN_COMMENT_PATTERN.match(next_logical):
                    break

                if self.PERFORM_CURSOR_PATTERN.match(next_logical):
                    skipped_lines.append(lines[index])
                    index += 1
                    continue

                break

            output.append(
                self._replacement_comment_for_removed_obtain_next(
                    reference_line=skipped_lines[0],
                )
            )
            output.append(
                self._format_like_line(
                    reference_line=skipped_lines[0],
                    replacement_body="CONTINUE.",
                )
            )

        return output

    def _replacement_comment_for_removed_obtain_next(
        self,
        reference_line: str,
    ) -> str:
        return self._format_like_line(
            reference_line=reference_line,
            replacement_body="* DB2: Removed redundant OBTAIN NEXT after cursor EOC loop.",
        )

    def _next_non_blank_index(
        self,
        lines: list[str],
        start_index: int,
    ) -> int:
        for index in range(start_index, len(lines)):
            logical = self._logical(lines[index])

            if logical:
                return index

        return -1

    def _is_non_cursor_paragraph_header(
        self,
        logical: str,
    ) -> bool:
        normalized = str(logical or "").strip().upper()

        if not normalized:
            return False

        if normalized in self.NON_PARAGRAPH_DOTTED_LINES:
            return False

        if normalized.startswith("WHEN "):
            return False

        if normalized.startswith("END-"):
            return False

        if normalized.startswith("EXEC "):
            return False

        if normalized.startswith("MOVE "):
            return False

        if normalized.startswith("DISPLAY "):
            return False

        if normalized.startswith("PERFORM "):
            return False

        if normalized.startswith("SET "):
            return False

        if normalized.startswith("OPEN "):
            return False

        if normalized.startswith("CLOSE "):
            return False

        if normalized.startswith("FETCH "):
            return False

        if normalized.startswith("INTO"):
            return False

        if normalized.startswith(":"):
            return False

        if not self.ANY_PARAGRAPH_HEADER_PATTERN.match(normalized):
            return False

        if self.CURSOR_PARAGRAPH_HEADER_PATTERN.match(normalized):
            return False

        return True

    def _format_like_line(
        self,
        reference_line: str,
        replacement_body: str,
    ) -> str:
        line = str(reference_line or "").rstrip()

        if self._is_fixed_format_line(line):
            left = line[:6]
            indicator = line[6]
            right = line[72:80]
            body = self._body_with_reference_indent(
                reference_line=line,
                replacement_body=replacement_body,
            )

            return f"{left}{indicator}{body[:65].ljust(65)}{right}"

        indent = self._leading_spaces(
            reference_line,
            default="    ",
        )

        return f"{indent}{replacement_body}"

    def _body_with_reference_indent(
        self,
        reference_line: str,
        replacement_body: str,
    ) -> str:
        body = reference_line[7:72].rstrip()
        indent = self._leading_spaces(
            body,
            default="    ",
        )

        return f"{indent}{replacement_body}"

    def _is_fixed_format_line(
        self,
        line: str,
    ) -> bool:
        if len(line) < 80:
            return False

        if not line[:6].isdigit():
            return False

        if not line[72:80].isdigit():
            return False

        return True

    def _leading_spaces(
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