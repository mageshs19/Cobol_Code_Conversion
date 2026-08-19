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
    - broad OBTAIN CALC SELECT.
    - broad MODIFY UPDATE / WHERE.
    """

    MOVE_TO_DCL_DOT_HOST_PATTERN = re.compile(
        r"^\s*MOVE\s+(?P<src>.+?)\s+TO\s+(?P<group>DCL[A-Z0-9-]+)\.(?P<host>[A-Z][A-Z0-9-]+)\.?\s*$",
        flags=re.IGNORECASE,
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
            output.append(f"{leading}MOVE {match.group('src').strip()} TO {host_key}")
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
            table = self._table_for_record(record)
            key_columns = self._db2_primary_key_columns(record, table)

            if not table or not key_columns:
                output.append(lines[index])
                index += 1
                continue

            block_end = self._skip_generated_sql_and_sqlcode(lines, index + 1)
            output.extend(
                self._key_only_select_block(
                    record=record,
                    table=table,
                    key_columns=key_columns,
                    leading=self._leading_spaces(lines[index]),
                )
            )
            changed = True
            index = block_end

        if changed:
            self.messages.append(
                "Update SQL feedback: rewrote OBTAIN CALC SELECT to primary-key-only SELECT."
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
        Detect real update fields only after the previous OBTAIN CALC SELECT block.

        This prevents setup/key fields moved before SELECT from being included
        in UPDATE SET.
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
        latest_end_exec = -1

        for index in range(search_start, modify_index):
            logical = self._logical(lines[index])

            if self.EXEC_SQL_END_PATTERN.match(logical):
                latest_end_exec = index

        if latest_end_exec >= 0:
            return latest_end_exec + 1

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

        for index in range(start, end):
            logical = self._logical(lines[index])

            column = self._changed_column_from_logical(
                record=record,
                table=table,
                logical=logical,
            )

            if not column:
                continue
            if column in seen:
                continue

            seen.add(column)
            output.append(column)

        return self._filter_existing_dclgen_columns(table, output)

    def _changed_column_from_logical(
        self,
        record: str,
        table: str,
        logical: str,
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

            if normalized and normalized not in seen:
                seen.add(normalized)
                output.append(normalized)

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