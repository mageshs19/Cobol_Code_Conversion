"""
Update final feedback service.

Generic behavior:
- Converts non-SQL DCLGEN dot references to COBOL OF qualification.
- Replaces residual bare IDMS record initialization with resolved DCLGEN
  group initialization when there is strong local DCLGEN context.
- Populates update audit host variables before UPDATE SQL blocks.
- Replaces generated DB2 diagnostic labels that still contain IDMS record names
  with nearby resolved DB2 table names.
- Does not hardcode program names, records, DB2 tables, DB2 columns,
  DCLGEN groups, or host variables.
"""

from __future__ import annotations

from collections import Counter

from patterns.update_final_feedback_patterns import (
    CONVERTED_DB2_OPERATION_COMMENT_PATTERN,
    DCLGEN_OF_REFERENCE_PATTERN,
    EXEC_SQL_END_PATTERN,
    EXEC_SQL_START_PATTERN,
    FROM_STATEMENT_PATTERN,
    INITIALIZE_DCL_PATTERN,
    MOVE_TO_BARE_RECORD_PATTERN,
    MOVE_TO_DCL_OF_REFERENCE_PATTERN,
    NON_SQL_DCL_DOT_REFERENCE_PATTERN,
    SET_KEYWORD_PATTERN,
    SQL_LOCATION_DB_OPERATION_PATTERN,
    SQL_SET_ASSIGNMENT_PATTERN,
    UPDATE_STATEMENT_PATTERN,
    WHERE_KEYWORD_PATTERN,
)
from rules.timestamp_audit_rules import UPDATE_AUDIT_COLUMN_PREFIXES
from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)


class UpdateFinalFeedbackService:
    """
    Performs generic update-program final cleanup.

    The service is intentionally conservative:
    - It only changes non-SQL DCLGROUP.HOST references.
    - It only replaces MOVE SPACES TO bare-record when a nearby DCLGEN group
      context is clear.
    - It only inserts audit MOVE statements for audit columns already present
      in generated UPDATE SET assignments.
    - It only rewrites diagnostic labels when a nearby DB2 table can be
      resolved from generated SQL.
    """

    LOOKAHEAD_LIMIT = 25
    LOOKBACK_DUPLICATE_LIMIT = 15

    PROTECTED_BARE_TARGET_PREFIXES = (
        "WS-",
        "SW-",
        "WK-",
        "W-",
        "UIT-",
        "OUT-",
        "ES-",
        "SQL",
        "DCL",
        "ERROR-",
        "USER",
        "CS-",
        "TS-",
        "HR-",
        "HELP-",
        "PROGRAM-",
    )

    TIMESTAMP_AUDIT_PREFIXES = (
        "TS_UPDATE",
    )

    USER_AUDIT_PREFIXES = (
        "ID_USERID",
        "NR_USERID",
        "ID_USER",
        "NR_USER",
    )

    def __init__(
        self,
        fixed_format: FixedFormatLineService | None = None,
    ) -> None:
        self.fixed_format = fixed_format or FixedFormatLineService()

    def apply(
        self,
        text: str,
    ) -> str:
        output = str(text or "")

        if not output:
            return ""

        output = self._normalize_non_sql_dcl_dot_references(output)
        output = self._replace_bare_record_initialization(output)
        output = self._insert_update_audit_moves(output)
        output = self._normalize_db2_diagnostic_labels(output)

        return output.rstrip() + "\n"

    def _normalize_non_sql_dcl_dot_references(
        self,
        text: str,
    ) -> str:
        lines = text.splitlines()
        output: list[str] = []
        in_exec_sql = False

        for line in lines:
            logical = self.fixed_format.logical(line)

            if EXEC_SQL_START_PATTERN.match(logical):
                in_exec_sql = True
                output.append(line)
                continue

            if in_exec_sql:
                output.append(line)

                if EXEC_SQL_END_PATTERN.match(logical):
                    in_exec_sql = False

                continue

            updated_logical = NON_SQL_DCL_DOT_REFERENCE_PATTERN.sub(
                self._replace_dcl_dot_with_of,
                logical,
            )

            if updated_logical == logical:
                output.append(line)
                continue

            output.append(
                self.fixed_format.replace_body(
                    line,
                    self._body_with_existing_indent(
                        original_line=line,
                        new_logical=updated_logical,
                    ),
                )
            )

        return "\n".join(output).rstrip() + "\n"

    def _replace_dcl_dot_with_of(
        self,
        match,
    ) -> str:
        group = str(match.group("group") or "").upper()
        host = str(match.group("host") or "").upper()
        return f"{host} OF {group}"

    def _replace_bare_record_initialization(
        self,
        text: str,
    ) -> str:
        lines = text.splitlines()
        output: list[str] = []
        in_exec_sql = False

        for index, line in enumerate(lines):
            logical = self.fixed_format.logical(line)

            if EXEC_SQL_START_PATTERN.match(logical):
                in_exec_sql = True
                output.append(line)
                continue

            if in_exec_sql:
                output.append(line)

                if EXEC_SQL_END_PATTERN.match(logical):
                    in_exec_sql = False

                continue

            match = MOVE_TO_BARE_RECORD_PATTERN.match(logical)

            if not match:
                output.append(line)
                continue

            target = str(match.group("target") or "").upper()

            if self._is_protected_bare_target(target):
                output.append(line)
                continue

            group = self._nearest_dcl_group_after(
                lines=lines,
                start_index=index + 1,
            )

            if not group:
                output.append(line)
                continue

            if self._recent_output_has_initialize(output, group):
                output.append(line)
                continue

            output.append(
                self.fixed_format.replace_body(
                    line,
                    self._body_with_existing_indent(
                        original_line=line,
                        new_logical=f"INITIALIZE {group}",
                    ),
                )
            )

        return "\n".join(output).rstrip() + "\n"

    def _insert_update_audit_moves(
        self,
        text: str,
    ) -> str:
        lines = text.splitlines()
        update_blocks = self._find_update_exec_sql_blocks(lines)

        if not update_blocks:
            return text.rstrip() + "\n"

        output = list(lines)

        for start, end in sorted(update_blocks, reverse=True):
            block = output[start : end + 1]
            audit_targets = self._audit_targets_from_update_block(block)

            if not audit_targets:
                continue

            reference_line = output[start]
            insert_lines: list[str] = []

            for group, host, audit_kind in audit_targets:
                if self._has_recent_move_to_host(
                    lines=output,
                    insert_index=start,
                    group=group,
                    host=host,
                ):
                    continue

                source = self._source_for_audit_kind(audit_kind)

                if not source:
                    continue

                move_logical = f"MOVE {source} TO {host} OF {group}"
                insert_lines.append(
                    self.fixed_format.replace_body(
                        reference_line,
                        self._body_with_existing_indent(
                            original_line=reference_line,
                            new_logical=move_logical,
                        ),
                    )
                )

            if not insert_lines:
                continue

            output[start:start] = insert_lines

        return "\n".join(output).rstrip() + "\n"

    def _normalize_db2_diagnostic_labels(
        self,
        text: str,
    ) -> str:
        lines = text.splitlines()
        output: list[str] = []

        for index, line in enumerate(lines):
            logical = self.fixed_format.logical(line)

            sql_location_match = SQL_LOCATION_DB_OPERATION_PATTERN.match(
                logical
            )

            if sql_location_match:
                table = self._nearby_table_for_operation(
                    lines=lines,
                    start_index=index + 1,
                    operation=str(
                        sql_location_match.group("operation") or ""
                    ),
                )

                if table:
                    operation = str(
                        sql_location_match.group("operation") or ""
                    ).upper()

                    output.append(
                        self.fixed_format.replace_body(
                            line,
                            self._body_with_existing_indent(
                                original_line=line,
                                new_logical=(
                                    f"MOVE '{operation}-{table}' "
                                    "TO SQL-LOCATION."
                                ),
                            ),
                        )
                    )
                    continue

            comment_match = CONVERTED_DB2_OPERATION_COMMENT_PATTERN.match(
                logical
            )

            if comment_match:
                operation_text = str(
                    comment_match.group("operation") or ""
                ).upper()
                table = self._nearby_table_for_comment_operation(
                    lines=lines,
                    start_index=index + 1,
                    operation_text=operation_text,
                )

                if table:
                    updated_comment = (
                        str(comment_match.group("prefix") or "")
                        + table
                        + str(comment_match.group("suffix") or ".")
                    )

                    output.append(
                        self.fixed_format.replace_body(
                            line,
                            self._comment_body_for_line(
                                original_line=line,
                                comment_text=updated_comment,
                            ),
                        )
                    )
                    continue

            output.append(line)

        return "\n".join(output).rstrip() + "\n"

    def _find_update_exec_sql_blocks(
        self,
        lines: list[str],
    ) -> list[tuple[int, int]]:
        blocks: list[tuple[int, int]] = []
        in_exec_sql = False
        start = -1
        has_update = False

        for index, line in enumerate(lines):
            logical = self.fixed_format.logical(line)

            if EXEC_SQL_START_PATTERN.match(logical):
                in_exec_sql = True
                start = index
                has_update = False
                continue

            if in_exec_sql and UPDATE_STATEMENT_PATTERN.match(logical):
                has_update = True

            if in_exec_sql and EXEC_SQL_END_PATTERN.match(logical):
                if has_update:
                    blocks.append((start, index))

                in_exec_sql = False
                start = -1
                has_update = False

        return blocks

    def _audit_targets_from_update_block(
        self,
        block: list[str],
    ) -> list[tuple[str, str, str]]:
        in_set = False
        targets: list[tuple[str, str, str]] = []

        for line in block:
            logical = self.fixed_format.logical(line)

            if SET_KEYWORD_PATTERN.match(logical):
                in_set = True
                continue

            if in_set and WHERE_KEYWORD_PATTERN.match(logical):
                break

            if not in_set:
                continue

            match = SQL_SET_ASSIGNMENT_PATTERN.match(logical.strip())

            if not match:
                continue

            column = str(match.group("column") or "").upper()
            group = str(match.group("group") or "").upper()
            host = str(match.group("host") or "").upper()

            audit_kind = self._audit_kind_for_column(column)

            if not audit_kind:
                continue

            targets.append((group, host, audit_kind))

        return self._unique_targets(targets)

    def _audit_kind_for_column(
        self,
        column: str,
    ) -> str:
        normalized = str(column or "").upper()

        if not self._has_update_audit_prefix(normalized):
            return ""

        if normalized.startswith(self.TIMESTAMP_AUDIT_PREFIXES):
            return "timestamp"

        if normalized.startswith(self.USER_AUDIT_PREFIXES):
            return "user"

        return ""

    def _has_update_audit_prefix(
        self,
        column: str,
    ) -> bool:
        normalized = str(column or "").upper()

        return any(
            normalized.startswith(str(prefix or "").upper())
            for prefix in UPDATE_AUDIT_COLUMN_PREFIXES
        )

    def _source_for_audit_kind(
        self,
        audit_kind: str,
    ) -> str:
        if audit_kind == "timestamp":
            return "TS-TIMESTAMP"

        if audit_kind == "user":
            return "CS-PROGRAM"

        return ""

    def _nearest_dcl_group_after(
        self,
        lines: list[str],
        start_index: int,
    ) -> str:
        groups: list[str] = []
        in_exec_sql = False

        for index in range(
            start_index,
            min(len(lines), start_index + self.LOOKAHEAD_LIMIT),
        ):
            logical = self.fixed_format.logical(lines[index])

            if EXEC_SQL_START_PATTERN.match(logical):
                in_exec_sql = True
                continue

            if in_exec_sql:
                if EXEC_SQL_END_PATTERN.match(logical):
                    in_exec_sql = False
                continue

            for match in DCLGEN_OF_REFERENCE_PATTERN.finditer(logical):
                group = str(match.group("group") or "").upper()

                if group:
                    groups.append(group)

            for match in NON_SQL_DCL_DOT_REFERENCE_PATTERN.finditer(logical):
                group = str(match.group("group") or "").upper()

                if group:
                    groups.append(group)

            if SQL_LOCATION_DB_OPERATION_PATTERN.match(logical):
                break

        if not groups:
            return ""

        return Counter(groups).most_common(1)[0][0]

    def _nearby_table_for_comment_operation(
        self,
        lines: list[str],
        start_index: int,
        operation_text: str,
    ) -> str:
        normalized = str(operation_text or "").upper()

        if "MODIFY" in normalized:
            return self._nearby_table_for_operation(
                lines=lines,
                start_index=start_index,
                operation="UPDATE",
            )

        if "OBTAIN" in normalized or "FIND" in normalized:
            return self._nearby_table_for_operation(
                lines=lines,
                start_index=start_index,
                operation="SELECT",
            )

        if "STORE" in normalized:
            return self._nearby_table_for_operation(
                lines=lines,
                start_index=start_index,
                operation="INSERT",
            )

        if "ERASE" in normalized:
            return self._nearby_table_for_operation(
                lines=lines,
                start_index=start_index,
                operation="DELETE",
            )

        return ""

    def _nearby_table_for_operation(
        self,
        lines: list[str],
        start_index: int,
        operation: str,
    ) -> str:
        wanted_operation = str(operation or "").upper()
        in_exec_sql = False

        for index in range(
            start_index,
            min(len(lines), start_index + self.LOOKAHEAD_LIMIT),
        ):
            logical = self.fixed_format.logical(lines[index])

            if EXEC_SQL_START_PATTERN.match(logical):
                in_exec_sql = True
                continue

            if in_exec_sql and EXEC_SQL_END_PATTERN.match(logical):
                in_exec_sql = False
                continue

            if wanted_operation == "UPDATE":
                update_match = UPDATE_STATEMENT_PATTERN.match(logical)

                if update_match:
                    return str(update_match.group("table") or "").upper()

            if wanted_operation == "SELECT":
                from_match = FROM_STATEMENT_PATTERN.match(logical)

                if from_match:
                    return str(from_match.group("table") or "").upper()

            if wanted_operation in {"INSERT", "DELETE"}:
                table = self._table_for_insert_or_delete(logical)

                if table:
                    return table

        return ""

    def _table_for_insert_or_delete(
        self,
        logical: str,
    ) -> str:
        text = str(logical or "").strip().upper()
        parts = text.split()

        if len(parts) < 3:
            return ""

        if parts[0] == "INSERT" and parts[1] == "INTO":
            return parts[2]

        if parts[0] == "DELETE" and parts[1] == "FROM":
            return parts[2]

        return ""

    def _recent_output_has_initialize(
        self,
        output: list[str],
        group: str,
    ) -> bool:
        target = str(group or "").upper()

        for line in output[-self.LOOKBACK_DUPLICATE_LIMIT:]:
            logical = self.fixed_format.logical(line)
            match = INITIALIZE_DCL_PATTERN.match(logical)

            if match and str(match.group("group") or "").upper() == target:
                return True

        return False

    def _has_recent_move_to_host(
        self,
        lines: list[str],
        insert_index: int,
        group: str,
        host: str,
    ) -> bool:
        target_group = str(group or "").upper()
        target_host = str(host or "").upper()

        start = max(0, insert_index - self.LOOKBACK_DUPLICATE_LIMIT)

        for index in range(start, insert_index):
            logical = self.fixed_format.logical(lines[index])
            match = MOVE_TO_DCL_OF_REFERENCE_PATTERN.match(logical)

            if not match:
                continue

            found_group = str(match.group("group") or "").upper()
            found_host = str(match.group("host") or "").upper()

            if found_group == target_group and found_host == target_host:
                return True

        return False

    def _unique_targets(
        self,
        values: list[tuple[str, str, str]],
    ) -> list[tuple[str, str, str]]:
        output: list[tuple[str, str, str]] = []
        seen: set[tuple[str, str, str]] = set()

        for group, host, audit_kind in values:
            key = (
                str(group or "").upper(),
                str(host or "").upper(),
                str(audit_kind or "").lower(),
            )

            if not key[0] or not key[1] or not key[2]:
                continue

            if key in seen:
                continue

            seen.add(key)
            output.append(key)

        return output

    def _is_protected_bare_target(
        self,
        target: str,
    ) -> bool:
        normalized = str(target or "").upper()

        return any(
            normalized.startswith(prefix)
            for prefix in self.PROTECTED_BARE_TARGET_PREFIXES
        )

    def _body_with_existing_indent(
        self,
        original_line: str,
        new_logical: str,
    ) -> str:
        body = self.fixed_format.body(original_line)
        leading = body[: len(body) - len(body.lstrip(" "))]

        if not leading:
            leading = "    "

        return leading + str(new_logical or "").strip()

    def _comment_body_for_line(
        self,
        original_line: str,
        comment_text: str,
    ) -> str:
        """
        Return the correct body for a comment line.

        In fixed-format COBOL, the comment indicator is already in column 7.
        Therefore, if the replacement text starts with '*', remove it from
        the body to avoid producing '**DB2...' physically.
        """

        text = str(comment_text or "").strip()

        if text.startswith("*"):
            text = text[1:].lstrip()

        body = self.fixed_format.body(original_line)
        leading = body[: len(body) - len(body.lstrip(" "))]

        return leading + text