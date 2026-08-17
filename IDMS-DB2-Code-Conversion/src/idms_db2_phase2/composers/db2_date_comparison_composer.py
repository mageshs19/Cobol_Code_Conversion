"""
DB2 date comparison composer.

This composer realigns DB2 date host fields before comparing them with
numeric COBOL date fields such as PARMDATE.

The conversion template is stored in:
    rules/db2_date_conversion_rules.py

This class is generic:
- No program name is hardcoded.
- No table name is hardcoded.
- No DCLGEN group name is hardcoded.
- No business field name is hardcoded.
- DA-/DT- field names are detected from the COBOL being converted.
"""

from patterns.db2_date_patterns import (
    DATE_WORKING_STORAGE_MARKER_PATTERN,
    DB2_DATE_COMPARISON_PATTERN,
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
    WS_MARKER = DB2_DATE_COMPARISON_WS_MARKER

    def compose(
        self,
        text: str,
    ) -> str:
        if not text:
            return ""

        lines = self._normalize_line_endings(text).splitlines()

        date_fields = self._date_fields_used_in_comparisons(lines)

        if not date_fields:
            return text.rstrip() + "\n"

        lines = self._ensure_date_working_storage(
            lines=lines,
            date_fields=date_fields,
        )

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

            if logical.startswith("*") or logical.startswith("/"):
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

    def _ensure_date_working_storage(
        self,
        lines: list[str],
        date_fields: list[str],
    ) -> list[str]:
        if self._has_date_working_storage(lines):
            return lines

        block = self._date_working_storage_block(date_fields)

        insert_index = self._date_working_storage_insert_index(lines)

        if insert_index < 0:
            return block + [""] + lines

        return lines[:insert_index] + block + [""] + lines[insert_index:]

    def _has_date_working_storage(
        self,
        lines: list[str],
    ) -> bool:
        for line in lines:
            if DATE_WORKING_STORAGE_MARKER_PATTERN.search(line):
                return True

            logical = self._logical(line).upper()

            if logical.startswith("01 WS-DATUMVELDEN"):
                return True

            if logical.startswith("01  WS-DATUMVELDEN"):
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

            if logical.startswith("*") or logical.startswith("/"):
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

        while " " in text:
            text = text.replace(" ", "")

        return text

    def _leading_spaces_from_line(
        self,
        line: str,
        default: str,
    ) -> str:
        text = str(line or "")

        if self._is_fixed_format_line(text):
            body = text[7:72]
            return self._leading_spaces(body, default)

        return self._leading_spaces(text, default)

    def _is_fixed_format_line(
        self,
        line: str,
    ) -> bool:
        text = str(line or "")

        if len(text) < 80:
            return False

        if not text[:6].isdigit():
            return False

        if not text[72:80].isdigit():
            return False

        return True

    def _leading_spaces(
        self,
        text: str,
        default: str,
    ) -> str:
        value = str(text or "")

        if not value:
            return default

        count = len(value) - len(value.lstrip(" "))

        if count <= 0:
            return default

        return value[:count]