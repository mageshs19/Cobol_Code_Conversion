"""
DB2 date comparison composer.

This composer realigns DB2 date host fields before comparing them with
numeric COBOL date fields such as PARMDATE.

It also ensures shared DB2 date helper Working-Storage is declared when
generated update or retrieval logic uses shared date helper fields such as:

- DA-CCYYMMDD
- DA-CCYYMMDD-R
- DA-DD-MM-CCYY

No program name is hardcoded.
No table name is hardcoded.
No DCLGEN group name is hardcoded.
No business field name is hardcoded.
"""

from patterns.db2_date_patterns import (
    DATE_WORKING_STORAGE_MARKER_PATTERN,
    DB2_DATE_COMPARISON_PATTERN,
    DB2_DATE_WORKING_STORAGE_BASE_PATTERN,
    DB2_SHARED_DATE_HELPER_USAGE_PATTERN,
    LINKAGE_SECTION_PATTERN,
    PROCEDURE_DIVISION_PATTERN,
)
from patterns.sequence_patterns import strip_sequence_numbers
from rules.db2_date_conversion_rules import (
    DB2_DATE_BASE_WORKING_STORAGE_LINES,
    DB2_DATE_COMPARISON_WS_MARKER,
    DB2_DATE_CONVERSION_LINE_TEMPLATES,
    DB2_DATE_HELPER_FIELD_TEMPLATE,
    DB2_DATE_HIGH_NUMERIC_LITERAL,
    DB2_DATE_HIGH_VALUE_LITERAL,
    DB2_DATE_IF_REPLACEMENT_TEMPLATE,
    DB2_DATE_LOW_VALUE_LITERAL,
)


class Db2DateComparisonComposer:
    """
    Compose DB2 date comparison and shared date helper support.

    Existing behavior:
    - Detect DA-/DT- DCLGEN date fields compared with PARMDATE.
    - Generate conversion logic.
    - Add date helper Working-Storage.

    Added generic behavior:
    - If generated PROCEDURE DIVISION already contains shared date helper
      usage, ensure the base Working-Storage date block exists.
    - This covers update programs where DATE-YMD8 is converted to the DB2
      external date host format without a comparison IF statement.

    Safety behavior:
    - If the base date Working-Storage already exists, add only missing
      HELP-* date helper fields required by comparison conversion.
    - Do not duplicate WS-DATUMVELDEN.
    - Do not duplicate HELP-* fields.
    """

    WS_MARKER = DB2_DATE_COMPARISON_WS_MARKER

    def compose(
        self,
        text: str,
    ) -> str:
        if not text:
            return ""

        lines = self._normalize_line_endings(text).splitlines()

        date_fields = self._date_fields_used_in_comparisons(lines)
        shared_helpers_used = self._shared_date_helpers_used_in_procedure(
            lines
        )

        if date_fields or shared_helpers_used:
            lines = self._ensure_date_working_storage(
                lines=lines,
                date_fields=date_fields,
            )

        if date_fields:
            lines = self._rewrite_date_comparisons(lines)

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

    def _date_fields_used_in_comparisons(
        self,
        lines: list[str],
    ) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()

        for line in lines:
            logical = self._logical(line)

            if self._is_comment_or_blank(logical):
                continue

            match = DB2_DATE_COMPARISON_PATTERN.match(logical)

            if not match:
                continue

            field_name = self._clean_cobol_name(match.group("field"))

            if not field_name:
                continue

            if field_name in seen:
                continue

            seen.add(field_name)
            output.append(field_name)

        return output

    def _shared_date_helpers_used_in_procedure(
        self,
        lines: list[str],
    ) -> bool:
        in_procedure_division = False

        for line in lines:
            logical = self._logical(line)

            if not logical:
                continue

            if PROCEDURE_DIVISION_PATTERN.match(logical):
                in_procedure_division = True
                continue

            if not in_procedure_division:
                continue

            if self._is_comment_or_blank(logical):
                continue

            if DB2_SHARED_DATE_HELPER_USAGE_PATTERN.search(logical):
                return True

        return False

    def _ensure_date_working_storage(
        self,
        lines: list[str],
        date_fields: list[str],
    ) -> list[str]:
        """
        Ensure DB2 date Working-Storage exists.

        Behavior:
        - If no date Working-Storage exists, insert the full base block.
        - If date Working-Storage already exists, add only missing HELP-* fields.
        - Update-only flows normally pass no date_fields, so only the base block
          is required.
        - Retrieval/date comparison flows may require HELP-* fields.
        """

        if not self._has_date_working_storage(lines):
            block = self._date_working_storage_block(date_fields)
            insert_index = self._date_working_storage_insert_index(lines)

            if insert_index < 0:
                return block + [""] + lines

            return lines[:insert_index] + block + [""] + lines[insert_index:]

        return self._ensure_missing_date_helper_fields(
            lines=lines,
            date_fields=date_fields,
        )

    def _ensure_missing_date_helper_fields(
        self,
        lines: list[str],
        date_fields: list[str],
    ) -> list[str]:
        """
        Add missing HELP-* date fields when WS-DATUMVELDEN already exists.

        This prevents a retrieval/date-comparison regression where the base
        date block exists but a newly required HELP-* field is missing.
        """

        if not date_fields:
            return lines

        missing_helpers: list[str] = []

        for field_name in date_fields:
            helper = self._helper_name(field_name)

            if self._helper_declared(
                lines=lines,
                helper=helper,
            ):
                continue

            missing_helpers.append(helper)

        if not missing_helpers:
            return lines

        helper_lines = [
            DB2_DATE_HELPER_FIELD_TEMPLATE.format(
                helper=helper,
            )
            for helper in missing_helpers
        ]

        insert_index = self._date_helper_insert_index(lines)

        if insert_index < 0:
            return lines + helper_lines

        return lines[:insert_index] + helper_lines + lines[insert_index:]

    def _helper_declared(
        self,
        lines: list[str],
        helper: str,
    ) -> bool:
        """
        Return True only when the HELP-* field is declared before PROCEDURE DIVISION.

        Important:
        - Do not treat a PROCEDURE DIVISION usage as a declaration.
        - This avoids missing declaration false positives on reruns.
        """

        helper_upper = str(helper or "").strip().upper()

        if not helper_upper:
            return True

        for line in lines:
            logical = self._logical(line)

            if PROCEDURE_DIVISION_PATTERN.match(logical):
                return False

            if helper_upper in logical.upper():
                return True

        return False

    def _date_helper_insert_index(
        self,
        lines: list[str],
    ) -> int:
        """
        Return index where missing HELP-* fields should be inserted.

        Preferred placement:
        - Inside the existing date Working-Storage area.
        - Before LINKAGE SECTION.
        - Before PROCEDURE DIVISION when LINKAGE SECTION is absent.
        - Before the next 01-level item after WS-DATUMVELDEN.
        """

        ws_datumvelden_seen = False

        for index, line in enumerate(lines):
            logical = self._logical(line)
            upper_logical = logical.upper()

            if upper_logical.startswith("01 WS-DATUMVELDEN"):
                ws_datumvelden_seen = True
                continue

            if not ws_datumvelden_seen:
                continue

            if LINKAGE_SECTION_PATTERN.match(logical):
                return index

            if PROCEDURE_DIVISION_PATTERN.match(logical):
                return index

            if upper_logical.startswith("01 "):
                return index

        return -1

    def _has_date_working_storage(
        self,
        lines: list[str],
    ) -> bool:
        in_procedure_division = False

        for line in lines:
            logical = self._logical(line)

            if DATE_WORKING_STORAGE_MARKER_PATTERN.search(line):
                return True

            if PROCEDURE_DIVISION_PATTERN.match(logical):
                in_procedure_division = True

            if in_procedure_division:
                continue

            upper_logical = logical.upper()

            if upper_logical.startswith("01 WS-DATUMVELDEN"):
                return True

            if DB2_DATE_WORKING_STORAGE_BASE_PATTERN.search(upper_logical):
                return True

        return False

    def _date_working_storage_insert_index(
        self,
        lines: list[str],
    ) -> int:
        for index, line in enumerate(lines):
            logical = self._logical(line)

            if LINKAGE_SECTION_PATTERN.match(logical):
                return index

        for index, line in enumerate(lines):
            logical = self._logical(line)

            if PROCEDURE_DIVISION_PATTERN.match(logical):
                return index

        return -1

    def _date_working_storage_block(
        self,
        date_fields: list[str],
    ) -> list[str]:
        lines = list(DB2_DATE_BASE_WORKING_STORAGE_LINES)

        for field_name in date_fields:
            helper = self._helper_name(field_name)

            lines.append(
                DB2_DATE_HELPER_FIELD_TEMPLATE.format(
                    helper=helper,
                )
            )

        return lines

    def _rewrite_date_comparisons(
        self,
        lines: list[str],
    ) -> list[str]:
        output: list[str] = []

        for line in lines:
            logical = self._logical(line)

            if self._is_comment_or_blank(logical):
                output.append(line)
                continue

            match = DB2_DATE_COMPARISON_PATTERN.match(logical)

            if not match:
                output.append(line)
                continue

            field_name = self._clean_cobol_name(match.group("field"))
            group_name = self._clean_cobol_name(match.group("group"))
            condition = str(match.group("condition") or "").strip()

            if not field_name or not group_name or not condition:
                output.append(line)
                continue

            indent = self._leading_spaces_from_line(
                line=line,
                default="    ",
            )

            output.extend(
                self._date_conversion_lines(
                    indent=indent,
                    field_name=field_name,
                    group_name=group_name,
                )
            )

            output.append(
                self._replace_date_field_in_if(
                    indent=indent,
                    field_name=field_name,
                    condition=condition,
                )
            )

        return output

    def _date_conversion_lines(
        self,
        indent: str,
        field_name: str,
        group_name: str,
    ) -> list[str]:
        helper = self._helper_name(field_name)

        output: list[str] = []

        for template in DB2_DATE_CONVERSION_LINE_TEMPLATES:
            output.append(
                template.format(
                    indent=indent,
                    field_name=field_name,
                    group_name=group_name,
                    helper=helper,
                    low_value=DB2_DATE_LOW_VALUE_LITERAL,
                    high_value=DB2_DATE_HIGH_VALUE_LITERAL,
                    high_numeric=DB2_DATE_HIGH_NUMERIC_LITERAL,
                )
            )

        return output

    def _replace_date_field_in_if(
        self,
        indent: str,
        field_name: str,
        condition: str,
    ) -> str:
        helper = self._helper_name(field_name)

        return DB2_DATE_IF_REPLACEMENT_TEMPLATE.format(
            indent=indent,
            helper=helper,
            condition=condition,
        )

    def _helper_name(
        self,
        field_name: str,
    ) -> str:
        return f"HELP-{self._clean_cobol_name(field_name)}"

    def _clean_cobol_name(
        self,
        value: str,
    ) -> str:
        text = str(value or "").strip().upper()
        text = text.replace("_", "-")
        text = text.rstrip(".")

        while " " in text:
            text = text.replace(" ", "")

        return text

    def _leading_spaces_from_line(
        self,
        line: str,
        default: str = "",
    ) -> str:
        value = str(line or "")

        if not value:
            return default

        count = len(value) - len(value.lstrip(" "))

        if count <= 0:
            return default

        return value[:count]

    def _is_comment_or_blank(
        self,
        logical: str,
    ) -> bool:
        stripped = str(logical or "").strip()

        if not stripped:
            return True

        return stripped.startswith("*") or stripped.startswith("/")