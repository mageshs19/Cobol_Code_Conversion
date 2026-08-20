from __future__ import annotations

import re

from idms_db2_phase2.composers.update_program_feedback_shared import (
    UpdateProgramFeedbackShared,
)
from idms_db2_phase2.services.name_normalizer import NameNormalizer


class UpdateProgramSqlFeedbackComposer(UpdateProgramFeedbackShared):
    """
    Fixes update-program SQL feedback issues:
    - malformed PERFORM SQLERROR.END-IF.
    - bare changed field move before MODIFY.
    - unnecessary OBTAIN CALC SELECT.
    - broad MODIFY UPDATE / WHERE.
    - composite key WHERE must include all PK / CALC key fields.
    - FK / FOREIGN / relationship columns must not be used in WHERE.
    - DATE-YMD8 style values must be converted to DD.MM.CCYY before moving
      into DB2 DA_/DT_ date host fields.
    - STRING ... INTO date-host must be detected as a changed DB2 column so
      the converted date column is included in UPDATE SET.

    Generic behavior:
    - No program name is hardcoded.
    - No DB2 table name is hardcoded.
    - No DCLGEN group name is hardcoded.
    - No business field name is hardcoded.
    - Sheet Mapping decides table/column mapping.
    - DCLGEN decides host variable spelling.
    """

    MOVE_TO_DCL_DOT_HOST_PATTERN = re.compile(
        r"^\s*MOVE\s+(?P<src>.+?)\s+TO\s+(?P<group>DCL[A-Z0-9-]+)\.(?P<host>[A-Z][A-Z0-9-]+)\.?\s*$",
        flags=re.IGNORECASE,
    )

    STRING_INTO_DCL_HOST_PATTERN = re.compile(
        r"^\s*INTO\s+(?P<host>[A-Z][A-Z0-9-]+)\s+OF\s+(?P<group>DCL[A-Z0-9-]+)\.?\s*$",
        flags=re.IGNORECASE,
    )

    STRING_INTO_DCL_DOT_HOST_PATTERN = re.compile(
        r"^\s*INTO\s+(?P<group>DCL[A-Z0-9-]+)\.(?P<host>[A-Z][A-Z0-9-]+)\.?\s*$",
        flags=re.IGNORECASE,
    )

    ANY_DCL_OF_REFERENCE_PATTERN = re.compile(
        r"\b(?P<host>[A-Z][A-Z0-9-]+)\s+OF\s+(?P<group>DCL[A-Z0-9-]+)\b",
        flags=re.IGNORECASE,
    )

    ANY_DCL_DOT_REFERENCE_PATTERN = re.compile(
        r"\b(?P<group>DCL[A-Z0-9-]+)\.(?P<host>[A-Z][A-Z0-9-]+)\b",
        flags=re.IGNORECASE,
    )

    DATE_COLUMN_PREFIXES = (
        "DA_",
        "DT_",
    )

    def compose(
        self,
        text: str,
    ) -> str:
        self.messages = []
        output = str(text or "")

        if not output.strip():
            return output

        output = self._normalize_malformed_sqlerror_end_if(output)
        output = self._rewrite_contextual_bare_moves(output)
        output = self._rewrite_obtain_calc_selects(output)
        output = self._rewrite_modify_updates(output)

        return output.rstrip() + "\n"

    def _normalize_malformed_sqlerror_end_if(
        self,
        text: str,
    ) -> str:
        output: list[str] = []
        changed = False

        for line in text.splitlines():
            logical = self._logical(line)
            match = self.MALFORMED_SQLERROR_ENDIF_PATTERN.match(logical)

            if not match:
                output.append(line)
                continue

            leading = self._leading_spaces(line)
            output.append(f"{leading}PERFORM SQLERROR.")
            output.append(f"{leading}END-IF.")
            changed = True

        if changed:
            self.messages.append(
                "Update SQL feedback: normalized malformed PERFORM SQLERROR.END-IF."
            )

        return "\n".join(output).rstrip() + "\n"

    def _rewrite_contextual_bare_moves(
        self,
        text: str,
    ) -> str:
        lines = text.splitlines()
        output: list[str] = []
        changed = False

        for index, line in enumerate(lines):
            logical = self._logical(line)
            match = self.MOVE_TO_BARE_FIELD_PATTERN.match(logical)

            if not match:
                output.append(line)
                continue

            target = NameNormalizer.to_cobol(match.group("tgt"))

            if self._is_protected_bare_target(target):
                output.append(line)
                continue

            record = self._next_modify_record(lines, index, max_distance=15)

            if not record:
                output.append(line)
                continue

            table = self._table_for_record(record)
            column = self._column_for_source_field(record, target)

            if not table or not column:
                output.append(line)
                continue

            host_key = self._host_reference_key(table, column)

            if not host_key:
                output.append(line)
                continue

            leading = self._leading_spaces(line)
            source_value = match.group("src").strip()

            if self._is_db2_date_column(column):
                output.extend(
                    self._date_ymd8_to_db2_external_move(
                        source_value=source_value,
                        host_key=host_key,
                        leading=leading,
                    )
                )
            else:
                output.append(f"{leading}MOVE {source_value} TO {host_key}")

            changed = True

        if changed:
            self.messages.append(
                "Update SQL feedback: resolved bare MOVE target through Sheet Mapping and DCLGEN."
            )

        return "\n".join(output).rstrip() + "\n"

    def _rewrite_obtain_calc_selects(
        self,
        text: str,
    ) -> str:
        """
        Remove generated OBTAIN CALC SELECT blocks.

        Feedback rule:
        - SELECT before UPDATE is not required.
        - Direct UPDATE is enough.
        - Replace generated SELECT block with comment + CONTINUE.
        """
        lines = text.splitlines()
        output: list[str] = []
        index = 0
        changed = False

        while index < len(lines):
            logical = self._logical(lines[index])
            match = self.CONVERTED_OBTAIN_CALC_PATTERN.match(logical)

            if not match:
                output.append(lines[index])
                index += 1
                continue

            record = NameNormalizer.normalize(match.group("record"))
            leading = self._leading_spaces(lines[index])

            block_end = self._skip_generated_sql_and_sqlcode(lines, index + 1)

            output.extend(
                [
                    f"{leading}*DB2: Removed OBTAIN CALC SELECT for {NameNormalizer.to_cobol(record)}.",
                    f"{leading}*DB2: Direct UPDATE will use mapped composite key WHERE clause.",
                    f"{leading}CONTINUE.",
                ]
            )

            changed = True
            index = block_end

        if changed:
            self.messages.append(
                "Update SQL feedback: removed unnecessary OBTAIN CALC SELECT before direct UPDATE."
            )

        return "\n".join(output).rstrip() + "\n"

    def _rewrite_modify_updates(
        self,
        text: str,
    ) -> str:
        lines = text.splitlines()
        output: list[str] = []
        index = 0
        changed = False

        while index < len(lines):
            logical = self._logical(lines[index])
            match = self.CONVERTED_MODIFY_PATTERN.match(logical)

            if not match:
                output.append(lines[index])
                index += 1
                continue

            record = NameNormalizer.normalize(match.group("record"))
            table = self._table_for_record(record)
            key_columns = self._db2_primary_key_columns(record, table)

            changed_columns = self._changed_columns_after_obtain_calc(
                record=record,
                table=table,
                lines=lines,
                modify_index=index,
            )

            update_columns = self._update_columns(
                record=record,
                table=table,
                changed_columns=changed_columns,
            )

            if not table or not key_columns or not update_columns:
                output.append(lines[index])
                index += 1
                continue

            block_end = self._skip_generated_sql_and_sqlcode(lines, index + 1)

            output.extend(
                self._conservative_update_block(
                    record=record,
                    table=table,
                    update_columns=update_columns,
                    key_columns=key_columns,
                    leading=self._leading_spaces(lines[index]),
                )
            )

            changed = True
            index = block_end

        if changed:
            self.messages.append(
                "Update SQL feedback: rewrote MODIFY UPDATE to changed field plus update audit fields."
            )

        return "\n".join(output).rstrip() + "\n"

    def _key_only_select_block(
        self,
        record: str,
        table: str,
        key_columns: list[str],
        leading: str,
    ) -> list[str]:
        """
        Kept for backward compatibility only.

        The current feedback path removes OBTAIN CALC SELECT instead of
        rewriting it. If this method is called by older logic, it still keeps
        SELECT key-only and FK-free.
        """
        host_refs = self.host_variable_resolver.host_references_for_columns(
            table_name=table,
            columns=key_columns,
        )

        lines = [
            f"{leading}*DB2: Converted OBTAIN CALC for {NameNormalizer.to_cobol(record)}.",
            f"{leading}MOVE 'SELECT-{NameNormalizer.to_cobol(record)}' TO SQL-LOCATION.",
            f"{leading}EXEC SQL",
            f"{leading}   SELECT",
        ]

        lines.extend(self._comma_lines(key_columns, leading + "      "))
        lines.append(f"{leading}   INTO")
        lines.extend(self._comma_lines(host_refs, leading + "      "))
        lines.append(f"{leading}   FROM {table}")
        lines.append(f"{leading}   WHERE")
        lines.extend(self._where_lines(table, key_columns, leading + "      "))
        lines.append(f"{leading}END-EXEC.")
        lines.append(f"{leading}IF SQLCODE NOT = 0 AND SQLCODE NOT = 100")
        lines.append(f"{leading}   PERFORM SQLERROR.")
        lines.append(f"{leading}END-IF.")

        return lines

    def _conservative_update_block(
        self,
        record: str,
        table: str,
        update_columns: list[str],
        key_columns: list[str],
        leading: str,
    ) -> list[str]:
        lines = [
            f"{leading}*DB2: Converted MODIFY for {NameNormalizer.to_cobol(record)}.",
            f"{leading}MOVE 'UPDATE-{NameNormalizer.to_cobol(record)}' TO SQL-LOCATION.",
            f"{leading}EXEC SQL",
            f"{leading}   UPDATE {table}",
            f"{leading}   SET",
        ]

        lines.extend(self._set_lines(table, update_columns, leading + "      "))
        lines.append(f"{leading}   WHERE")
        lines.extend(self._where_lines(table, key_columns, leading + "      "))
        lines.append(f"{leading}END-EXEC.")
        lines.append(f"{leading}IF SQLCODE NOT = 0")
        lines.append(f"{leading}   PERFORM SQLERROR.")
        lines.append(f"{leading}END-IF.")

        return lines

    def _changed_columns_after_obtain_calc(
        self,
        record: str,
        table: str,
        lines: list[str],
        modify_index: int,
    ) -> list[str]:
        """
        Detect real update fields near the MODIFY block.

        This method intentionally scans between the removed OBTAIN CALC block
        and the MODIFY block. It detects:
        - MOVE ... TO bare source field
        - MOVE ... TO host OF DCLGROUP
        - MOVE ... TO DCLGROUP.host
        - STRING ... INTO host OF DCLGROUP
        - STRING ... INTO DCLGROUP.host
        """
        start = self._post_select_scan_start(lines, modify_index)

        return self._changed_columns_in_range(
            record=record,
            table=table,
            lines=lines,
            start=start,
            end=modify_index,
        )

    def _post_select_scan_start(
        self,
        lines: list[str],
        modify_index: int,
    ) -> int:
        search_start = max(0, modify_index - 80)
        latest_boundary = -1

        for index in range(search_start, modify_index):
            logical = self._logical(lines[index])
            upper = logical.upper()

            if self.EXEC_SQL_END_PATTERN.match(logical):
                latest_boundary = index
                continue

            if "REMOVED OBTAIN CALC SELECT" in upper:
                latest_boundary = index
                continue

            if "DIRECT UPDATE WILL USE MAPPED COMPOSITE KEY" in upper:
                latest_boundary = index
                continue

        if latest_boundary >= 0:
            return latest_boundary + 1

        return max(0, modify_index - 20)

    def _changed_columns_in_range(
        self,
        record: str,
        table: str,
        lines: list[str],
        start: int,
        end: int,
    ) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()
        in_string_block = False

        for index in range(start, end):
            logical = self._logical(lines[index])
            upper = logical.upper()

            if upper.startswith("STRING "):
                in_string_block = True

            column = self._changed_column_from_logical(
                record=record,
                table=table,
                logical=logical,
                in_string_block=in_string_block,
            )

            if column and column not in seen:
                seen.add(column)
                output.append(column)

            if upper.startswith("END-STRING"):
                in_string_block = False

        return self._filter_existing_dclgen_columns(table, output)

    def _changed_column_from_logical(
        self,
        record: str,
        table: str,
        logical: str,
        in_string_block: bool = False,
    ) -> str:
        bare_match = self.MOVE_TO_BARE_FIELD_PATTERN.match(logical)

        if bare_match:
            target = NameNormalizer.to_cobol(bare_match.group("tgt"))
            return self._column_for_source_field(record, target)

        of_match = self.MOVE_TO_DCL_HOST_PATTERN.match(logical)

        if of_match:
            return self._column_for_host(
                table=table,
                group=NameNormalizer.normalize(of_match.group("group")),
                host=NameNormalizer.to_cobol(of_match.group("host")),
            )

        dot_match = self.MOVE_TO_DCL_DOT_HOST_PATTERN.match(logical)

        if dot_match:
            return self._column_for_host(
                table=table,
                group=NameNormalizer.normalize(dot_match.group("group")),
                host=NameNormalizer.to_cobol(dot_match.group("host")),
            )

        string_into_match = self.STRING_INTO_DCL_HOST_PATTERN.match(logical)

        if string_into_match:
            return self._column_for_host(
                table=table,
                group=NameNormalizer.normalize(string_into_match.group("group")),
                host=NameNormalizer.to_cobol(string_into_match.group("host")),
            )

        string_dot_match = self.STRING_INTO_DCL_DOT_HOST_PATTERN.match(logical)

        if string_dot_match:
            return self._column_for_host(
                table=table,
                group=NameNormalizer.normalize(string_dot_match.group("group")),
                host=NameNormalizer.to_cobol(string_dot_match.group("host")),
            )

        if in_string_block and "INTO" in logical.upper():
            generic_of_match = self.ANY_DCL_OF_REFERENCE_PATTERN.search(logical)

            if generic_of_match:
                return self._column_for_host(
                    table=table,
                    group=NameNormalizer.normalize(generic_of_match.group("group")),
                    host=NameNormalizer.to_cobol(generic_of_match.group("host")),
                )

            generic_dot_match = self.ANY_DCL_DOT_REFERENCE_PATTERN.search(logical)

            if generic_dot_match:
                return self._column_for_host(
                    table=table,
                    group=NameNormalizer.normalize(generic_dot_match.group("group")),
                    host=NameNormalizer.to_cobol(generic_dot_match.group("host")),
                )

        return ""

    def _column_for_host(
        self,
        table: str,
        group: str,
        host: str,
    ) -> str:
        expected_group = NameNormalizer.normalize(
            self.dclgen_repository.group_for_table(table)
        )

        if group != expected_group:
            return ""

        target_host = NameNormalizer.to_cobol(host)

        for column in self.dclgen_repository.columns_for_table(table):
            current_host = NameNormalizer.to_cobol(
                column.cobol_host_name or column.column_name
            )

            if current_host == target_host:
                return NameNormalizer.normalize(column.column_name)

        return ""

    def _update_columns(
        self,
        record: str,
        table: str,
        changed_columns: list[str],
    ) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()
        key_columns = set(self._db2_primary_key_columns(record, table))

        for column in changed_columns:
            normalized = NameNormalizer.normalize(column)

            if not normalized:
                continue

            if normalized in key_columns:
                continue

            if normalized in seen:
                continue

            seen.add(normalized)
            output.append(normalized)

        for column in self._update_audit_columns(record, table):
            normalized = NameNormalizer.normalize(column)

            if not normalized:
                continue

            if normalized in key_columns:
                continue

            if normalized in seen:
                continue

            seen.add(normalized)
            output.append(normalized)

        return self._filter_existing_dclgen_columns(table, output)

    def _db2_primary_key_columns(
        self,
        record: str,
        table: str,
    ) -> list[str]:
        """
        Return all composite PK / CALC key columns for WHERE.

        Feedback rule:
        - Include all DB2 PRIMARY / KEY columns.
        - Include all IDMS CALC key columns.
        - Exclude FK / FOREIGN / relationship columns.
        - Preserve mapping order.
        """
        output: list[str] = []
        seen: set[str] = set()

        for row in self.mapping_repository.rows_for_record(record):
            idms_key = NameNormalizer.normalize(getattr(row, "idms_key", ""))
            db2_key = NameNormalizer.normalize(getattr(row, "db2_key", ""))
            relation = NameNormalizer.normalize(getattr(row, "relation", ""))

            column = NameNormalizer.normalize(
                getattr(row, "new_db2_field_name", "")
                or getattr(row, "cross_application_db2_field_name", "")
            )

            if not column:
                continue

            combined_text = " ".join(
                [
                    idms_key,
                    db2_key,
                    relation,
                ]
            )
            padded_text = f" {combined_text} "

            if "FOREIGN" in combined_text:
                continue

            if " FK " in padded_text:
                continue

            is_key_column = (
                "PRIMARY" in db2_key
                or db2_key == "KEY"
                or "PRIMARY" in idms_key
                or idms_key == "KEY"
                or "CALC" in idms_key
            )

            if not is_key_column:
                continue

            if column in seen:
                continue

            seen.add(column)
            output.append(column)

        return self._filter_existing_dclgen_columns(table, output)

    def _next_modify_record(
        self,
        lines: list[str],
        start_index: int,
        max_distance: int,
    ) -> str:
        end = min(len(lines), start_index + max_distance + 1)

        for index in range(start_index + 1, end):
            logical = self._logical(lines[index])
            match = self.CONVERTED_MODIFY_PATTERN.match(logical)

            if match:
                return NameNormalizer.normalize(match.group("record"))

        return ""

    def _skip_generated_sql_and_sqlcode(
        self,
        lines: list[str],
        start: int,
    ) -> int:
        index = start

        while index < len(lines):
            logical = self._logical(lines[index])
            upper = logical.upper()

            if not logical:
                index += 1
                continue

            if upper.startswith("MOVE 'SELECT-") or upper.startswith("MOVE 'UPDATE-"):
                index += 1
                continue

            if self.EXEC_SQL_START_PATTERN.match(logical):
                index = self._skip_exec_sql(lines, index)
                continue

            if self.SQLCODE_IF_PATTERN.match(logical):
                index = self._skip_if_block(lines, index)
                continue

            break

        return index

    def _is_db2_date_column(
        self,
        column_name: str,
    ) -> bool:
        column = NameNormalizer.normalize(column_name)

        return any(
            column.startswith(prefix)
            for prefix in self.DATE_COLUMN_PREFIXES
        )

    def _date_ymd8_to_db2_external_move(
        self,
        source_value: str,
        host_key: str,
        leading: str,
    ) -> list[str]:
        """
        Convert CCYYMMDD into DB2 external date format DD.MM.CCYY.

        Manual-style conversion:
        - Move source CCYYMMDD into DA-CCYYMMDD.
        - Redefined field DA-CCYYMMDD-R exposes CCYY, MM, DD.
        - MOVE CORR transfers CCYY/MM/DD into DA-DD-MM-CCYY.
        - Move DA-DD-MM-CCYY into the DB2 date host field.

        Example:
        - DATE-YMD8 = 20260820
        - DA-DD-MM-CCYY = 20.08.2026
        """
        source = str(source_value or "").strip()
        indent = leading if leading else "    "

        if not source:
            return [
                f"{indent}MOVE SPACES TO DA-DD-MM-CCYY",
                f"{indent}MOVE DA-DD-MM-CCYY TO {host_key}",
            ]

        return [
            f"{indent}MOVE ZEROES TO DA-CCYYMMDD",
            f"{indent}MOVE {source} TO DA-CCYYMMDD",
            f"{indent}MOVE CORR DA-CCYYMMDD-R TO DA-DD-MM-CCYY",
            f"{indent}MOVE DA-DD-MM-CCYY TO {host_key}",
        ]