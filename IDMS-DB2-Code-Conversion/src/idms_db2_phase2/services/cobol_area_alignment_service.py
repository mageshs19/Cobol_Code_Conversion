"""
COBOL Area A / Area B alignment service.

Generic behavior:
- Does not change 80-column sequencing.
- Does not change business logic.
- Only realigns Procedure Division executable statements to Area B when safe.
- Never truncates a fixed-format COBOL body to force alignment.
- Safely reflows long two-line Procedure Division statements by using the
  existing continuation line when available.

No program names, cursor names, DB2 tables, DB2 columns, DCLGEN groups,
or host variables are hardcoded.
"""

from __future__ import annotations

from patterns.final_feedback_fix_patterns import (
    DIVISION_SECTION_HEADER_PATTERN,
    END_EXEC_PATTERN,
    EXEC_SQL_START_PATTERN,
    PARAGRAPH_HEADER_PATTERN,
    PROCEDURE_DIVISION_TOKEN_PATTERN,
)
from rules.cobol_statement_rules import NON_PARAGRAPH_SINGLE_WORDS
from rules.final_feedback_fix_rules import (
    AREA_B_BODY_INDENT,
    SQL_BODY_INDENT,
)
from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)


class CobolAreaAlignmentService:
    """
    Aligns generated Procedure Division executable statements to Area B.

    Area B starts at physical column 12.
    Since COBOL body starts at physical column 8, four body spaces are used.

    Safety:
    - If adding the indent would exceed the fixed body width, the line is not
      blindly truncated.
    - If the next line is a continuation, this service combines both logical
      fragments and re-wraps them back into the same two physical lines.
    - If safe reflow is not possible, the original line is preserved.
    """

    CONTINUATION_BODY_INDENT = "       "

    def __init__(
        self,
        fixed_format: FixedFormatLineService | None = None,
    ) -> None:
        self.fixed_format = fixed_format or FixedFormatLineService()

    def align(self, text: str) -> str:
        if not text:
            return ""

        lines = str(text).splitlines()
        output: list[str] = []

        in_procedure_division = False
        in_exec_sql = False
        index = 0

        while index < len(lines):
            line = lines[index]
            logical = self.fixed_format.logical(line)

            if PROCEDURE_DIVISION_TOKEN_PATTERN.search(logical):
                in_procedure_division = True
                output.append(line)
                index += 1
                continue

            if not in_procedure_division:
                output.append(line)
                index += 1
                continue

            if self.fixed_format.is_comment_or_control_line(line):
                output.append(line)
                index += 1
                continue

            if not logical:
                output.append(line)
                index += 1
                continue

            if EXEC_SQL_START_PATTERN.match(logical):
                in_exec_sql = True
                output.append(
                    self._replace_body_when_safe(
                        line=line,
                        new_body=SQL_BODY_INDENT + logical,
                    )
                )
                index += 1
                continue

            if in_exec_sql:
                output.append(
                    self._replace_body_when_safe(
                        line=line,
                        new_body=SQL_BODY_INDENT + logical,
                    )
                )

                if END_EXEC_PATTERN.search(logical):
                    in_exec_sql = False

                index += 1
                continue

            if self._is_area_a(logical):
                output.append(
                    self._replace_body_when_safe(
                        line=line,
                        new_body=logical,
                    )
                )
                index += 1
                continue

            aligned_body = AREA_B_BODY_INDENT + logical

            if self._body_fits(aligned_body):
                output.append(
                    self.fixed_format.replace_body(
                        line,
                        aligned_body,
                    )
                )
                index += 1
                continue

            reflowed_lines = self._try_reflow_with_next_line(
                current_line=line,
                next_line=lines[index + 1] if index + 1 < len(lines) else "",
            )

            if reflowed_lines:
                output.extend(reflowed_lines)
                index += 2
                continue

            output.append(line)
            index += 1

        return "\n".join(output)

    def _replace_body_when_safe(
        self,
        line: str,
        new_body: str,
    ) -> str:
        """
        Replace fixed-format body only when it will not truncate.

        This prevents corruption such as losing operators at the end of long
        Procedure Division statements.
        """

        if not self.fixed_format.is_fixed_line(line):
            return self.fixed_format.replace_body(line, new_body)

        if not self._body_fits(new_body):
            return line

        return self.fixed_format.replace_body(line, new_body)

    def _try_reflow_with_next_line(
        self,
        current_line: str,
        next_line: str,
    ) -> list[str]:
        """
        Safely reflow a long fixed-format Procedure Division statement by using
        the existing next line as continuation storage.

        Example input:
            PERFORM X UNTIL A OR B =
            'Y'

        Example output:
            PERFORM X UNTIL A OR
               B = 'Y'

        This method does not add new physical lines. It only rewrites the
        current line and the existing next line.
        """

        if not current_line or not next_line:
            return []

        if not self.fixed_format.is_fixed_line(current_line):
            return []

        if not self.fixed_format.is_fixed_line(next_line):
            return []

        current_logical = self.fixed_format.logical(current_line)
        next_logical = self.fixed_format.logical(next_line)

        if not current_logical or not next_logical:
            return []

        if self.fixed_format.is_comment_or_control_line(next_line):
            return []

        if self._is_area_a(next_logical):
            return []

        if not self._looks_like_continuation(
            current_logical=current_logical,
            next_logical=next_logical,
        ):
            return []

        combined = self._combine_logical_fragments(
            current_logical=current_logical,
            next_logical=next_logical,
        )

        if not combined:
            return []

        wrapped_bodies = self._wrap_into_two_bodies(
            logical=combined,
            first_indent=AREA_B_BODY_INDENT,
            continuation_indent=self.CONTINUATION_BODY_INDENT,
        )

        if len(wrapped_bodies) != 2:
            return []

        return [
            self.fixed_format.replace_body(current_line, wrapped_bodies[0]),
            self.fixed_format.replace_body(next_line, wrapped_bodies[1]),
        ]

    def _looks_like_continuation(
        self,
        current_logical: str,
        next_logical: str,
    ) -> bool:
        """
        Detect generic continuation lines.

        This deliberately avoids hardcoded field/cursor names.

        Continuation is likely when:
        - current line ends with an operator or boolean connector
        - next line starts with a literal
        - next line starts with a comparison operand, not a COBOL verb/header
        """

        current = str(current_logical or "").strip().upper()
        next_text = str(next_logical or "").strip()
        next_upper = next_text.upper()

        if not current or not next_text:
            return False

        if current.endswith(("=", ">", "<", ">=", "<=", "OR", "AND", "NOT")):
            return True

        if next_text.startswith(("'", '"')):
            return True

        first_word = next_upper.split()[0] if next_upper.split() else ""

        if first_word in NON_PARAGRAPH_SINGLE_WORDS:
            return False

        if DIVISION_SECTION_HEADER_PATTERN.match(next_text):
            return False

        if PARAGRAPH_HEADER_PATTERN.match(next_text):
            return False

        return True

    def _combine_logical_fragments(
        self,
        current_logical: str,
        next_logical: str,
    ) -> str:
        current = str(current_logical or "").strip()
        continuation = str(next_logical or "").strip()

        if not current:
            return continuation

        if not continuation:
            return current

        if current.endswith(("=", ">", "<")):
            return f"{current} {continuation}"

        return f"{current} {continuation}"

    def _wrap_into_two_bodies(
        self,
        logical: str,
        first_indent: str,
        continuation_indent: str,
    ) -> list[str]:
        """
        Wrap one logical COBOL statement into exactly two body lines.

        Returns an empty list if the statement cannot be represented safely in
        two fixed-format body lines.
        """

        words = str(logical or "").split()

        if not words:
            return []

        first_limit = self.fixed_format.BODY_WIDTH - len(first_indent)
        second_limit = self.fixed_format.BODY_WIDTH - len(continuation_indent)

        if first_limit <= 0 or second_limit <= 0:
            return []

        first_words: list[str] = []
        second_words: list[str] = []

        for word in words:
            candidate = " ".join(first_words + [word])

            if len(candidate) <= first_limit:
                first_words.append(word)
                continue

            second_words.append(word)

        if not second_words:
            first_body = first_indent + " ".join(first_words)

            if self._body_fits(first_body):
                return [first_body, ""]

            return []

        # Move remaining words into the second line.
        first_word_count = len(first_words)
        second_words = words[first_word_count:]

        second_text = " ".join(second_words)

        if len(second_text) > second_limit:
            return []

        first_body = first_indent + " ".join(first_words)
        second_body = continuation_indent + second_text

        if not self._body_fits(first_body):
            return []

        if not self._body_fits(second_body):
            return []

        return [first_body, second_body]

    def _body_fits(
        self,
        body: str,
    ) -> bool:
        return len(str(body or "")) <= self.fixed_format.BODY_WIDTH

    def _is_area_a(
        self,
        logical: str,
    ) -> bool:
        text = str(logical or "").strip()
        upper = text.upper()

        if not text:
            return False

        if DIVISION_SECTION_HEADER_PATTERN.match(text):
            return True

        if not PARAGRAPH_HEADER_PATTERN.match(text):
            return False

        statement_name = upper.rstrip(".")

        if statement_name in NON_PARAGRAPH_SINGLE_WORDS:
            return False

        return True