"""
Fixed-format COBOL composer.

This composer orchestrates final physical COBOL formatting.

Detailed responsibilities are split into:
- fixed_format_line_parser.py
- fixed_format_body_formatter.py
- fixed_format_wrapper.py
- fixed_format_sequence_manager.py
- patterns/fixed_format_patterns.py
- rules/fixed_format_rules.py

Final physical layout:
- Columns 1-6   : left sequence number
- Column 7      : indicator area
- Columns 8-72  : COBOL body
- Columns 73-80 : right sequence number
"""

from idms_db2_phase2.composers.fixed_format_body_formatter import (
    FixedFormatBodyFormatter,
)
from idms_db2_phase2.composers.fixed_format_line_parser import (
    FixedFormatLineParser,
)
from idms_db2_phase2.composers.fixed_format_sequence_manager import (
    FixedFormatSequenceManager,
)
from idms_db2_phase2.composers.fixed_format_wrapper import FixedFormatWrapper
from patterns.fixed_format_patterns import (
    DIVISION_PATTERN,
    SEQUENCE_ONLY_PATTERN,
)
from rules.fixed_format_rules import (
    BODY_WIDTH,
    COMMENT_INDICATOR,
    DEBUG_INDICATOR,
    PAGE_INDICATOR,
    SPACE_INDICATOR,
    TOTAL_WIDTH,
    VALID_INDICATORS,
)


class FixedFormatComposer:
    """
    Final fixed-format COBOL composer.

    This class does not own regex patterns, layout constants, or sequence
    detection rules. It only coordinates the helper classes.

    Sequence numbering is generic:
    - Existing valid left sequence pattern is detected.
    - Existing valid manual-style right sequence pattern is detected.
    - Invalid small right sequence patterns are normalized by the sequence manager.
    """

    def __init__(
        self,
    ) -> None:
        self.line_parser = FixedFormatLineParser()
        self.body_formatter = FixedFormatBodyFormatter()
        self.wrapper = FixedFormatWrapper()
        self.sequence_manager = FixedFormatSequenceManager()

    def format(
        self,
        text: str,
        left_start: int | None = None,
        left_step: int | None = None,
        right_start: int | None = None,
        right_step: int | None = None,
        preserve_blank_lines: bool = True,
    ) -> str:
        if not text:
            return ""

        lines = self._normalize_line_endings(text).splitlines()
        lines = self._merge_dangling_boolean_lines(lines)

        sequence_state = self.sequence_manager.create_state(
            lines=lines,
            left_start=left_start,
            left_step=left_step,
            right_start=right_start,
            right_step=right_step,
        )

        output_lines: list[str] = []
        current_division = ""
        inside_exec_sql = False
        previous_procedure_indent = " "

        for raw_line in lines:
            raw_text = str(raw_line or "").rstrip()

            if not raw_text.strip():
                if preserve_blank_lines:
                    output_lines.append(
                        self._compose_line(
                            left_seq=sequence_state.current_left(),
                            indicator=SPACE_INDICATOR,
                            area_body="",
                            right_seq=sequence_state.current_right(),
                        )
                    )
                    sequence_state.advance()
                continue

            if SEQUENCE_ONLY_PATTERN.match(raw_text.strip()):
                continue

            parsed = self.line_parser.parse_line(raw_text)

            indicator = str(parsed["indicator"])
            body = str(parsed["body"])
            logical = body.strip()

            if not body.strip() and indicator == SPACE_INDICATOR:
                if preserve_blank_lines:
                    output_lines.append(
                        self._compose_line(
                            left_seq=sequence_state.current_left(),
                            indicator=SPACE_INDICATOR,
                            area_body="",
                            right_seq=sequence_state.current_right(),
                        )
                    )
                    sequence_state.advance()
                continue

            division_match = DIVISION_PATTERN.match(logical)

            if division_match:
                current_division = division_match.group(1).upper()
                previous_procedure_indent = " "

            if self.body_formatter.is_exec_sql_start(logical):
                inside_exec_sql = True

            area_body = self.body_formatter.area_body(
                body=body,
                logical=logical,
                current_division=current_division,
                inside_exec_sql=inside_exec_sql,
                indicator=indicator,
                previous_procedure_indent=previous_procedure_indent,
            )

            physical_bodies = self.wrapper.wrap_body(
                body=area_body,
                indicator=indicator,
                inside_exec_sql=inside_exec_sql,
                current_division=current_division,
                previous_procedure_indent=previous_procedure_indent,
            )

            physical_bodies = self.wrapper.repair_boolean_operator_only_lines(
                physical_bodies
            )

            for index, physical_body in enumerate(physical_bodies):
                physical_indicator = indicator

                if index > 0:
                    physical_indicator = self._continuation_indicator(indicator)

                output_lines.append(
                    self._compose_line(
                        left_seq=sequence_state.current_left(),
                        indicator=physical_indicator,
                        area_body=physical_body,
                        right_seq=sequence_state.current_right(),
                    )
                )

                sequence_state.advance()

            if (
                current_division == "PROCEDURE"
                and indicator == SPACE_INDICATOR
                and physical_bodies
                and not self.body_formatter.is_area_a_statement(logical)
            ):
                previous_procedure_indent = self.body_formatter.leading_spaces(
                    physical_bodies[0],
                    default=" ",
                )

            if self.body_formatter.is_exec_sql_end(logical):
                inside_exec_sql = False

        return "\n".join(output_lines).rstrip() + "\n"

    def validate_fixed_format(
        self,
        text: str,
    ) -> list[str]:
        messages: list[str] = []

        for line_number, line in enumerate(
            str(text or "").splitlines(),
            start=1,
        ):
            if not line:
                continue

            if len(line) != TOTAL_WIDTH:
                messages.append(
                    f"Line {line_number}: expected 80 columns, found {len(line)}."
                )
                continue

            left_seq = line[0:6]
            indicator = line[6:7]
            right_seq = line[72:80]

            if not left_seq.isdigit():
                messages.append(
                    f"Line {line_number}: left sequence is not numeric."
                )

            if indicator not in VALID_INDICATORS:
                messages.append(
                    f"Line {line_number}: invalid indicator column value."
                )

            if not right_seq.isdigit():
                messages.append(
                    f"Line {line_number}: right sequence is not numeric."
                )

        return messages

    def _normalize_line_endings(
        self,
        text: str,
    ) -> str:
        return str(text or "").replace("\r\n", "\n").replace("\r", "\n")

    def _merge_dangling_boolean_lines(
        self,
        lines: list[str],
    ) -> list[str]:
        output: list[str] = []
        index = 0

        while index < len(lines):
            current = str(lines[index] or "").rstrip()

            if index + 1 >= len(lines):
                output.append(current)
                index += 1
                continue

            next_line = str(lines[index + 1] or "").rstrip()

            current_body = self.line_parser.body_for_boolean_merge(current)
            next_body = self.line_parser.body_for_boolean_merge(next_line)

            if not current_body.strip() or not next_body.strip():
                output.append(current)
                index += 1
                continue

            if self.wrapper.is_comment_or_page_line(current_body):
                output.append(current)
                index += 1
                continue

            if self.wrapper.is_comment_or_page_line(next_body):
                output.append(current)
                index += 1
                continue

            if self.wrapper.ends_with_boolean_operator(current_body):
                merged_body = f"{current_body.rstrip()} {next_body.strip()}"

                output.append(
                    self.line_parser.replace_body_preserving_sequence(
                        original_line=current,
                        new_body=merged_body,
                    )
                )
                index += 2
                continue

            output.append(current)
            index += 1

        return output

    def _continuation_indicator(
        self,
        indicator: str,
    ) -> str:
        if indicator in {COMMENT_INDICATOR, PAGE_INDICATOR}:
            return indicator

        if indicator in {DEBUG_INDICATOR, DEBUG_INDICATOR.lower()}:
            return DEBUG_INDICATOR

        return SPACE_INDICATOR

    def _compose_line(
        self,
        left_seq: str,
        indicator: str,
        area_body: str,
        right_seq: str,
    ) -> str:
        safe_left = str(left_seq or "").zfill(6)[-6:]
        safe_right = str(right_seq or "").zfill(8)[-8:]
        safe_indicator = str(indicator or SPACE_INDICATOR)[:1]

        if safe_indicator not in VALID_INDICATORS:
            safe_indicator = SPACE_INDICATOR

        if safe_indicator == "d":
            safe_indicator = DEBUG_INDICATOR

        safe_body = str(area_body or "").rstrip()

        if len(safe_body) > BODY_WIDTH:
            safe_body = safe_body[:BODY_WIDTH]

        body_area = safe_body.ljust(BODY_WIDTH)
        line = f"{safe_left}{safe_indicator}{body_area}{safe_right}"

        if len(line) > TOTAL_WIDTH:
            return line[:TOTAL_WIDTH]

        if len(line) < TOTAL_WIDTH:
            return line.ljust(TOTAL_WIDTH)

        return line