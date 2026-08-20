from __future__ import annotations

import re

from idms_db2_phase2.repositories.dclgen_repository import DclgenRepository
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from patterns.sequence_patterns import strip_sequence_numbers
from rules.db2_output_date_conversion_rules import (
    DB2_OUTPUT_DATE_CONVERSION_LINE_TEMPLATES,
    DB2_OUTPUT_DATE_HIGH_NUMERIC_LITERAL,
    DB2_OUTPUT_DATE_HIGH_VALUE_LITERAL,
    DB2_OUTPUT_DATE_LOW_VALUE_LITERAL,
)


class FeedbackCleanupComposer:
    """
    Generic feedback cleanup composer.

    This composer fixes only feedback-driven issues:

    - Replace residual IDMS ERROR-STATUS loop control with DB2 flag control.
    - Declare SW-STATUS-D only when needed.
    - Add SW-STATUS-D early stop to nested child cursor fetch loops.
    - Keep child cursor stop condition in manual-style two-line form.
    - Add INITIALIZE before output-record population.
    - Convert DB2 date host fields to output numeric date format before WRITE.
    - Ensure DCLGEN INCLUDE exists when a DCLGEN group is referenced.

    No program names, table names, record names, or business-specific fields
    are hardcoded.
    """

    EXEC_SQL_INCLUDE_PATTERN = re.compile(
        r"\bINCLUDE\s+(?P<include>[A-Z0-9]+)\b",
        flags=re.IGNORECASE,
    )

    DCL_GROUP_PATTERN = re.compile(
        r"\bDCL(?P<table>[A-Z0-9]+)\b",
        flags=re.IGNORECASE,
    )

    WORKING_STORAGE_PATTERN = re.compile(
        r"^\s*(?:\d{6}\s*)?WORKING-STORAGE\s+SECTION\.",
        flags=re.IGNORECASE,
    )

    LINKAGE_SECTION_PATTERN = re.compile(
        r"^\s*(?:\d{6}\s*)?LINKAGE\s+SECTION\.",
        flags=re.IGNORECASE,
    )

    ERROR_STATUS_MOVE_PATTERN = re.compile(
        r"^\s*MOVE\s+['\"]?[A-Z0-9]+['\"]?\s+TO\s+ERROR-STATUS\.?\s*$",
        flags=re.IGNORECASE,
    )

    WS_STATUS_PATTERN = re.compile(
        r"^\s*10\s+WS-STATUS\b",
        flags=re.IGNORECASE,
    )

    SW_STATUS_D_PIC_PATTERN = re.compile(
        r"\bSW-STATUS-D\b.+\bPIC\b",
        flags=re.IGNORECASE,
    )

    SW_STATUS_D_MOVE_N_PATTERN = re.compile(
        r"^\s*MOVE\s+['\"]N['\"]\s+TO\s+SW-STATUS-D\.?\s*$",
        flags=re.IGNORECASE,
    )

    FETCH_UNTIL_EOC_PATTERN = re.compile(
        r"^(?P<prefix>\s*PERFORM\s+)"
        r"(?P<fetch>[0-9]+-FETCH-[A-Z0-9-]+)"
        r"\s+UNTIL\s+(?P<eoc>[A-Z0-9-]+-EOC)\.?\s*$",
        flags=re.IGNORECASE,
    )

    FETCH_UNTIL_EOC_OR_SW_PATTERN = re.compile(
        r"^(?P<prefix>\s*PERFORM\s+)"
        r"(?P<fetch>[0-9]+-FETCH-[A-Z0-9-]+)"
        r"\s+UNTIL\s+(?P<eoc>[A-Z0-9-]+-EOC)\s+OR\s+SW-STATUS-D\s*$",
        flags=re.IGNORECASE,
    )

    FETCH_UNTIL_EOC_FULL_SW_PATTERN = re.compile(
        r"^(?P<prefix>\s*PERFORM\s+)"
        r"(?P<fetch>[0-9]+-FETCH-[A-Z0-9-]+)"
        r"\s+UNTIL\s+(?P<eoc>[A-Z0-9-]+-EOC)"
        r"\s+OR\s+SW-STATUS-D\s*=?\s*['\"]?Y['\"]?\.?\s*$",
        flags=re.IGNORECASE,
    )

    SW_STATUS_Y_CONTINUATION_PATTERN = re.compile(
        r"^\s*=?\s*['\"]?Y['\"]?\.?\s*$",
        flags=re.IGNORECASE,
    )

    WRITE_PATTERN = re.compile(
        r"^\s*WRITE\s+(?P<record>[A-Z0-9-]+)\.?\s*$",
        flags=re.IGNORECASE,
    )

    INITIALIZE_PATTERN = re.compile(
        r"^\s*INITIALIZE\s+(?P<record>[A-Z0-9-]+)\.?\s*$",
        flags=re.IGNORECASE,
    )

    MOVE_START_PATTERN = re.compile(
        r"^\s*MOVE\b",
        flags=re.IGNORECASE,
    )

    MOVE_TO_OUTPUT_FIELD_PATTERN = re.compile(
        r"^\s*MOVE\b.+\bTO\s+(?P<target>UIT-[A-Z0-9-]+)\.?\s*$",
        flags=re.IGNORECASE,
    )

    TO_OUTPUT_FIELD_PATTERN = re.compile(
        r"^\s*TO\s+(?P<target>UIT-[A-Z0-9-]+)\.?\s*$",
        flags=re.IGNORECASE,
    )

    DB2_DATE_MOVE_START_PATTERN = re.compile(
        r"^\s*MOVE\s+(?P<field>(?:DA|DT)-[A-Z0-9-]+)\s+OF\s+"
        r"(?P<group>DCL[A-Z0-9-]+)\s*$",
        flags=re.IGNORECASE,
    )

    DB2_DATE_MOVE_ONE_LINE_PATTERN = re.compile(
        r"^\s*MOVE\s+(?P<field>(?:DA|DT)-[A-Z0-9-]+)\s+OF\s+"
        r"(?P<group>DCL[A-Z0-9-]+)\s+TO\s+"
        r"(?P<target>(?:UIT|OUT)-(?:DA|DT)-[A-Z0-9-]+)\.?\s*$",
        flags=re.IGNORECASE,
    )

    TO_UIT_DATE_FIELD_PATTERN = re.compile(
        r"^\s*TO\s+(?P<target>(?:UIT|OUT)-(?:DA|DT)-[A-Z0-9-]+)\.?\s*$",
        flags=re.IGNORECASE,
    )

    SW_STATUS_D_DECLARATION = "    10  SW-STATUS-D              PIC X    VALUE 'N'."

    STOP_BACKWARD_SCAN_WORDS = (
        "IF ",
        "ELSE",
        "END-IF",
        "PERFORM ",
        "EVALUATE ",
        "WHEN ",
        "WRITE ",
        "EXEC SQL",
        "END-EXEC",
        "OPEN ",
        "CLOSE ",
        "READ ",
        "STOP ",
        "EXIT",
    )

    def __init__(
        self,
        dclgen_repository: DclgenRepository,
    ) -> None:
        self.dclgen_repository = dclgen_repository
        self.messages: list[str] = []

    def compose(
        self,
        text: str,
    ) -> str:
        self.messages = []
        output = str(text or "")

        if not output.strip():
            return output

        output = self._ensure_missing_dclgen_includes(output)
        output = self._replace_error_status_with_flag(output)
        output = self._ensure_sw_status_d_declaration(output)
        output = self._ensure_child_fetch_early_stop(output)
        output = self._ensure_initialize_before_output_population(output)
        output = self._convert_db2_date_moves_to_output_dates(output)

        return output.rstrip() + "\n"

    def _ensure_missing_dclgen_includes(
        self,
        text: str,
    ) -> str:
        existing_includes = self._existing_includes(text)
        referenced_tables = self._referenced_dclgen_tables(text)

        missing_tables = [
            table
            for table in referenced_tables
            if table not in existing_includes
            and self.dclgen_repository.has_table(table)
        ]

        if not missing_tables:
            return text

        include_lines: list[str] = []

        for table in missing_tables:
            include_lines.extend(
                [
                    " EXEC SQL",
                    f"    INCLUDE {table}",
                    " END-EXEC.",
                ]
            )
            self.messages.append(
                f"Feedback cleanup: added missing DCLGEN include {table}."
            )

        lines = text.splitlines()
        insert_index = self._db2_include_insert_index(lines)

        if insert_index < 0:
            return text.rstrip() + "\n" + "\n".join(include_lines) + "\n"

        updated = (
            lines[:insert_index]
            + include_lines
            + lines[insert_index:]
        )

        return "\n".join(updated).rstrip() + "\n"

    def _existing_includes(
        self,
        text: str,
    ) -> set[str]:
        output: set[str] = set()

        for match in self.EXEC_SQL_INCLUDE_PATTERN.finditer(text):
            include_name = NameNormalizer.normalize(match.group("include"))

            if include_name:
                output.add(include_name)

        return output

    def _referenced_dclgen_tables(
        self,
        text: str,
    ) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()

        for match in self.DCL_GROUP_PATTERN.finditer(text):
            table = NameNormalizer.normalize(match.group("table"))

            if not table:
                continue
            if table in seen:
                continue

            seen.add(table)
            output.append(table)

        return output

    def _db2_include_insert_index(
        self,
        lines: list[str],
    ) -> int:
        last_include_end = -1
        in_exec_sql = False
        include_seen_in_block = False

        for index, line in enumerate(lines):
            logical = self._logical(line).upper()

            if logical.startswith("EXEC SQL"):
                in_exec_sql = True
                include_seen_in_block = False

            if in_exec_sql and "INCLUDE " in logical:
                include_seen_in_block = True

            if in_exec_sql and logical.startswith("END-EXEC"):
                if include_seen_in_block:
                    last_include_end = index + 1

                in_exec_sql = False
                include_seen_in_block = False

        if last_include_end >= 0:
            return last_include_end

        for index, line in enumerate(lines):
            if self.LINKAGE_SECTION_PATTERN.match(line):
                return index

        return -1

    def _replace_error_status_with_flag(
        self,
        text: str,
    ) -> str:
        output_lines: list[str] = []
        replaced = False

        for line in text.splitlines():
            logical = self._logical(line)

            if self.ERROR_STATUS_MOVE_PATTERN.match(logical):
                leading = self._leading_spaces(line)
                output_lines.append(f"{leading}MOVE 'Y' TO SW-STATUS-D")
                replaced = True
                continue

            output_lines.append(line)

        if replaced:
            self.messages.append(
                "Feedback cleanup: replaced ERROR-STATUS move with SW-STATUS-D flag."
            )

        return "\n".join(output_lines).rstrip() + "\n"

    def _ensure_sw_status_d_declaration(
        self,
        text: str,
    ) -> str:
        if "SW-STATUS-D" not in text:
            return text

        if self.SW_STATUS_D_PIC_PATTERN.search(text):
            return text

        lines = text.splitlines()
        output: list[str] = []
        inserted = False

        for line in lines:
            output.append(line)

            if inserted:
                continue

            logical = self._logical(line)

            if self.WS_STATUS_PATTERN.match(logical):
                output.append(self.SW_STATUS_D_DECLARATION)
                inserted = True
                self.messages.append(
                    "Feedback cleanup: declared SW-STATUS-D working-storage flag."
                )

        if inserted:
            return "\n".join(output).rstrip() + "\n"

        return self._insert_sw_status_d_after_working_storage(text)

    def _insert_sw_status_d_after_working_storage(
        self,
        text: str,
    ) -> str:
        lines = text.splitlines()
        output: list[str] = []
        inserted = False

        for line in lines:
            output.append(line)

            if inserted:
                continue

            logical = self._logical(line)

            if self.WORKING_STORAGE_PATTERN.match(logical):
                output.append(" 01  WS-DB2-FEEDBACK-FLAGS.")
                output.append(self.SW_STATUS_D_DECLARATION)
                inserted = True
                self.messages.append(
                    "Feedback cleanup: declared SW-STATUS-D in generated flag block."
                )

        if inserted:
            return "\n".join(output).rstrip() + "\n"

        return text

    def _ensure_child_fetch_early_stop(
        self,
        text: str,
    ) -> str:
        if "SW-STATUS-D" not in text:
            return text

        lines = text.splitlines()
        output: list[str] = []
        changed = False
        index = 0

        while index < len(lines):
            line = lines[index]
            logical = self._logical(line)

            full_match = self.FETCH_UNTIL_EOC_FULL_SW_PATTERN.match(logical)
            if full_match and self._is_child_or_nested_fetch(full_match.group("fetch")):
                leading = self._leading_spaces(line)
                fetch_paragraph = full_match.group("fetch")
                eoc_flag = full_match.group("eoc")

                if not self._previous_output_has_move_n(output):
                    output.append(f"{leading}MOVE 'N' TO SW-STATUS-D")

                output.append(
                    f"{leading}PERFORM {fetch_paragraph} UNTIL {eoc_flag} OR"
                )
                output.append(
                    f"{leading}                             SW-STATUS-D = 'Y'"
                )
                changed = True
                index += 1
                continue

            or_match = self.FETCH_UNTIL_EOC_OR_SW_PATTERN.match(logical)
            if or_match and self._is_child_or_nested_fetch(or_match.group("fetch")):
                leading = self._leading_spaces(line)
                fetch_paragraph = or_match.group("fetch")
                eoc_flag = or_match.group("eoc")

                if not self._previous_output_has_move_n(output):
                    output.append(f"{leading}MOVE 'N' TO SW-STATUS-D")

                output.append(
                    f"{leading}PERFORM {fetch_paragraph} UNTIL {eoc_flag} OR"
                )
                output.append(
                    f"{leading}                             SW-STATUS-D = 'Y'"
                )
                changed = True

                if self._next_line_is_sw_status_y_continuation(lines, index):
                    index += 2
                else:
                    index += 1
                continue

            match = self.FETCH_UNTIL_EOC_PATTERN.match(logical)
            if match and self._is_child_or_nested_fetch(match.group("fetch")):
                leading = self._leading_spaces(line)
                fetch_paragraph = match.group("fetch")
                eoc_flag = match.group("eoc")

                if not self._previous_output_has_move_n(output):
                    output.append(f"{leading}MOVE 'N' TO SW-STATUS-D")

                output.append(
                    f"{leading}PERFORM {fetch_paragraph} UNTIL {eoc_flag} OR"
                )
                output.append(
                    f"{leading}                             SW-STATUS-D = 'Y'"
                )
                changed = True
                index += 1
                continue

            output.append(line)
            index += 1

        if changed:
            self.messages.append(
                "Feedback cleanup: added SW-STATUS-D early-stop to child fetch loop."
            )

        return "\n".join(output).rstrip() + "\n"

    def _next_line_is_sw_status_y_continuation(
        self,
        lines: list[str],
        index: int,
    ) -> bool:
        if index + 1 >= len(lines):
            return False

        logical = self._logical(lines[index + 1])

        return bool(self.SW_STATUS_Y_CONTINUATION_PATTERN.match(logical))

    def _previous_output_has_move_n(
        self,
        output: list[str],
    ) -> bool:
        lookback = output[-3:]

        return any(
            self.SW_STATUS_D_MOVE_N_PATTERN.match(self._logical(line))
            for line in lookback
        )

    def _is_child_or_nested_fetch(
        self,
        fetch_paragraph: str,
    ) -> bool:
        paragraph = str(fetch_paragraph or "").upper()
        match = re.match(r"^(?P<number>\d+)-FETCH-", paragraph)

        if not match:
            return False

        try:
            number = int(match.group("number"))
        except ValueError:
            return False

        return number >= 800

    def _ensure_initialize_before_output_population(
        self,
        text: str,
    ) -> str:
        lines = text.splitlines()
        output = list(lines)
        changed = False

        write_blocks = self._output_write_blocks(output)

        for block in reversed(write_blocks):
            write_index = int(block["write_index"])
            record = str(block["record"])
            first_move_index = int(block["first_move_index"])

            if write_index < 0 or first_move_index < 0:
                continue

            output, removed_count = self._remove_initialize_for_record_in_range(
                lines=output,
                record=record,
                start_index=first_move_index,
                end_index=write_index,
            )

            if removed_count:
                changed = True
                write_index -= removed_count

            if self._has_initialize_immediately_before(
                lines=output,
                index=first_move_index,
                record=record,
            ):
                continue

            leading = self._leading_spaces(output[first_move_index])
            output.insert(
                first_move_index,
                f"{leading}INITIALIZE {record}",
            )
            changed = True

            self.messages.append(
                f"Feedback cleanup: moved INITIALIZE before output population for {record}."
            )

        if changed:
            return "\n".join(output).rstrip() + "\n"

        return text

    def _output_write_blocks(
        self,
        lines: list[str],
    ) -> list[dict[str, object]]:
        output: list[dict[str, object]] = []

        for index, line in enumerate(lines):
            logical = self._logical(line)
            match = self.WRITE_PATTERN.match(logical)

            if not match:
                continue

            record = match.group("record")
            first_move_index = self._first_output_move_block_start_before_write(
                lines=lines,
                write_index=index,
            )

            output.append(
                {
                    "write_index": index,
                    "record": record,
                    "first_move_index": first_move_index,
                }
            )

        return output

    def _first_output_move_block_start_before_write(
        self,
        lines: list[str],
        write_index: int,
    ) -> int:
        start = max(0, write_index - 60)
        first_move_start = -1

        for index in range(start, write_index):
            if self._line_targets_output_field(lines[index]):
                move_start = self._move_block_start(
                    lines=lines,
                    target_index=index,
                    search_start=start,
                )

                if move_start >= 0:
                    if first_move_start < 0 or move_start < first_move_start:
                        first_move_start = move_start

        return first_move_start

    def _line_targets_output_field(
        self,
        line: str,
    ) -> bool:
        logical = self._logical(line)

        if self.MOVE_TO_OUTPUT_FIELD_PATTERN.match(logical):
            return True

        if self.TO_OUTPUT_FIELD_PATTERN.match(logical):
            return True

        return False

    def _move_block_start(
        self,
        lines: list[str],
        target_index: int,
        search_start: int,
    ) -> int:
        logical = self._logical(lines[target_index])

        if self.MOVE_TO_OUTPUT_FIELD_PATTERN.match(logical):
            return target_index

        for index in range(target_index, search_start - 1, -1):
            candidate = self._logical(lines[index])
            upper = candidate.upper()

            if self.MOVE_START_PATTERN.match(candidate):
                return index

            if index == target_index:
                continue

            if self._is_comment_or_blank(candidate):
                continue

            if upper.startswith(self.STOP_BACKWARD_SCAN_WORDS):
                break

        return target_index

    def _remove_initialize_for_record_in_range(
        self,
        lines: list[str],
        record: str,
        start_index: int,
        end_index: int,
    ) -> tuple[list[str], int]:
        output: list[str] = []
        removed_count = 0

        for index, line in enumerate(lines):
            if start_index <= index < end_index:
                logical = self._logical(line)
                match = self.INITIALIZE_PATTERN.match(logical)

                if match:
                    current_record = NameNormalizer.normalize(match.group("record"))
                    target_record = NameNormalizer.normalize(record)

                    if current_record == target_record:
                        removed_count += 1
                        continue

            output.append(line)

        return output, removed_count

    def _has_initialize_immediately_before(
        self,
        lines: list[str],
        index: int,
        record: str,
    ) -> bool:
        lookback_start = max(0, index - 3)
        target_record = NameNormalizer.normalize(record)

        for prior_index in range(lookback_start, index):
            logical = self._logical(lines[prior_index])
            match = self.INITIALIZE_PATTERN.match(logical)

            if not match:
                continue

            current_record = NameNormalizer.normalize(match.group("record"))

            if current_record == target_record:
                return True

        return False

    def _convert_db2_date_moves_to_output_dates(
        self,
        text: str,
    ) -> str:
        lines = text.splitlines()
        output: list[str] = []
        changed = False
        index = 0

        while index < len(lines):
            line = lines[index]
            logical = self._logical(line)

            one_line = self.DB2_DATE_MOVE_ONE_LINE_PATTERN.match(logical)

            if one_line:
                field = one_line.group("field")
                group = one_line.group("group")
                target = one_line.group("target")

                if self._should_generate_output_date_conversion(
                    field_name=field,
                    target_name=target,
                ):
                    output.extend(
                        self._date_conversion_lines(
                            leading=self._leading_spaces(line),
                            field=field,
                            group=group,
                            target=target,
                        )
                    )
                    changed = True
                    index += 1
                    continue

            start_match = self.DB2_DATE_MOVE_START_PATTERN.match(logical)

            if start_match and index + 1 < len(lines):
                next_logical = self._logical(lines[index + 1])
                target_match = self.TO_UIT_DATE_FIELD_PATTERN.match(next_logical)

                if target_match:
                    field = start_match.group("field")
                    group = start_match.group("group")
                    target = target_match.group("target")

                    if self._should_generate_output_date_conversion(
                        field_name=field,
                        target_name=target,
                    ):
                        output.extend(
                            self._date_conversion_lines(
                                leading=self._leading_spaces(line),
                                field=field,
                                group=group,
                                target=target,
                            )
                        )
                        changed = True
                        index += 2
                        continue

            output.append(line)
            index += 1

        if changed:
            self.messages.append(
                "Feedback cleanup: converted DB2 date move before output write."
            )

        return "\n".join(output).rstrip() + "\n"

    def _should_generate_output_date_conversion(
        self,
        field_name: str,
        target_name: str,
    ) -> bool:
        """
        Return True only for DB2 date-host to output-date-field conversion.

        This prevents date ZEROES/SPACES logic from being generated for:
        - non-date output fields
        - DB2 DCLGEN host variables
        - update host moves
        - unrelated MOVE statements
        """

        field = str(field_name or "").strip().upper()
        target = str(target_name or "").strip().upper()

        if not field or not target:
            return False

        if not field.startswith(("DA-", "DT-")):
            return False

        if not target.startswith(("UIT-DA-", "UIT-DT-", "OUT-DA-", "OUT-DT-")):
            return False

        if " OF DCL" in target:
            return False

        if target.startswith("DCL"):
            return False

        return True

    def _date_conversion_lines(
        self,
        leading: str,
        field: str,
        group: str,
        target: str,
    ) -> list[str]:
        field_name = NameNormalizer.to_cobol(field)
        group_name = NameNormalizer.to_cobol(group)
        target_name = NameNormalizer.to_cobol(target)

        if not self._should_generate_output_date_conversion(
            field_name=field_name,
            target_name=target_name,
        ):
            return []

        output: list[str] = []

        for template in DB2_OUTPUT_DATE_CONVERSION_LINE_TEMPLATES:
            line = template.format(
                indent=leading,
                field_name=field_name,
                group_name=group_name,
                target_name=target_name,
                low_value=DB2_OUTPUT_DATE_LOW_VALUE_LITERAL,
                high_value=DB2_OUTPUT_DATE_HIGH_VALUE_LITERAL,
                high_numeric=DB2_OUTPUT_DATE_HIGH_NUMERIC_LITERAL,
            )

            if not line.strip():
                continue

            output.append(line.rstrip())

        return output

    def _logical(
        self,
        line: str,
    ) -> str:
        return strip_sequence_numbers(str(line or "")).strip()

    def _leading_spaces(
        self,
        line: str,
    ) -> str:
        value = str(line or "")
        return value[: len(value) - len(value.lstrip())]

    def _is_comment_or_blank(
        self,
        logical: str,
    ) -> bool:
        stripped = str(logical or "").strip()

        if not stripped:
            return True

        return stripped.startswith("*") or stripped.startswith("/")