"""
Cursor SELECT minimizer service.

Generic behavior:
- Removes columns selected/fetched only for ORDER BY when safe.
- Does not hardcode cursor names, table names, columns, or host variables.
- Keeps SELECT and FETCH INTO synchronized by position.

Important:
- Comma normalization is scoped only to SELECT item lines between SELECT and FROM.
- FETCH comma normalization is scoped only to host variables between INTO and END-EXEC.
- SQL keywords such as WHERE, FROM, ORDER BY, and FOR READ ONLY are never
  treated as selected columns.
"""

from __future__ import annotations

from patterns.final_feedback_fix_patterns import (
    ASC_DESC_PATTERN,
    DECLARE_CURSOR_PATTERN,
    END_EXEC_PATTERN,
    FETCH_CURSOR_PATTERN,
    FOR_READ_ONLY_PATTERN,
    FROM_PATTERN,
    HOST_REFERENCE_PATTERN,
    ORDER_BY_PATTERN,
    SELECT_ITEM_PATTERN,
    SELECT_KEYWORD_PATTERN,
    SQL_NAME_TOKEN_PATTERN,
)
from rules.final_feedback_fix_rules import (
    ORDER_BY_COLUMNS_IN_SELECT_DEFAULT,
)
from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)


class CursorSelectMinimizerService:
    """
    Removes order-by-only columns from cursor SELECT/FETCH when safe.

    Safety:
    - If the SQL column appears elsewhere outside the cursor declare block,
      keep it.
    - If the host-like COBOL name appears elsewhere outside the matching fetch
      block, keep it.
    - SELECT and FETCH are modified by position only when both are structurally
      safe.
    """

    SQL_NON_COLUMN_KEYWORDS = {
        "SELECT",
        "FROM",
        "WHERE",
        "ORDER",
        "ORDER BY",
        "GROUP",
        "GROUP BY",
        "HAVING",
        "FOR",
        "FOR READ ONLY",
        "INTO",
        "END-EXEC",
        "EXEC SQL",
    }

    def __init__(
        self,
        fixed_format: FixedFormatLineService | None = None,
        require_order_by_columns_in_select: bool = ORDER_BY_COLUMNS_IN_SELECT_DEFAULT,
    ) -> None:
        self.fixed_format = fixed_format or FixedFormatLineService()
        self.require_order_by_columns_in_select = require_order_by_columns_in_select

    def minimize(self, text: str) -> str:
        source = str(text or "")

        if not source:
            return ""

        if self.require_order_by_columns_in_select:
            return source

        lines = source.splitlines()
        declare_blocks = self._find_declare_blocks(lines)
        fetch_blocks = self._find_fetch_blocks(lines)

        removals_by_cursor: dict[str, set[int]] = {}

        for cursor, start, end in declare_blocks:
            block = lines[start : end + 1]
            select_columns = self._select_columns(block)
            order_columns = self._order_by_columns(block)

            if not select_columns or not order_columns:
                continue

            order_set = {self._normalize_name(item) for item in order_columns}
            removable: set[int] = set()

            for index, column in enumerate(select_columns):
                if self._normalize_name(column) not in order_set:
                    continue

                if self._has_non_order_usage(
                    lines=lines,
                    declare_range=(start, end),
                    fetch_blocks=fetch_blocks,
                    cursor=cursor,
                    column=column,
                ):
                    continue

                removable.add(index)

            if removable:
                removals_by_cursor[cursor] = removable

        if not removals_by_cursor:
            return source

        updated = list(lines)

        for cursor, start, end in sorted(
            declare_blocks,
            key=lambda item: item[1],
            reverse=True,
        ):
            removable = removals_by_cursor.get(cursor)

            if not removable:
                continue

            block = updated[start : end + 1]
            updated[start : end + 1] = self._remove_select_positions(
                block,
                removable,
            )

        fetch_blocks = self._find_fetch_blocks(updated)

        for cursor, start, end in sorted(
            fetch_blocks,
            key=lambda item: item[1],
            reverse=True,
        ):
            removable = removals_by_cursor.get(cursor)

            if not removable:
                continue

            block = updated[start : end + 1]
            updated[start : end + 1] = self._remove_fetch_positions(
                block,
                removable,
            )

        return "\n".join(updated)

    def _find_declare_blocks(
        self,
        lines: list[str],
    ) -> list[tuple[str, int, int]]:
        blocks: list[tuple[str, int, int]] = []
        in_exec_sql = False
        start = -1
        cursor = ""

        for index, line in enumerate(lines):
            logical = self.fixed_format.logical(line)

            if logical.upper().startswith("EXEC SQL"):
                in_exec_sql = True
                start = index
                cursor = ""
                continue

            if in_exec_sql and not cursor:
                match = DECLARE_CURSOR_PATTERN.search(logical)
                if match:
                    cursor = match.group("cursor").upper()

            if in_exec_sql and END_EXEC_PATTERN.search(logical):
                if cursor:
                    blocks.append((cursor, start, index))

                in_exec_sql = False
                start = -1
                cursor = ""

        return blocks

    def _find_fetch_blocks(
        self,
        lines: list[str],
    ) -> list[tuple[str, int, int]]:
        blocks: list[tuple[str, int, int]] = []
        in_exec_sql = False
        start = -1
        cursor = ""

        for index, line in enumerate(lines):
            logical = self.fixed_format.logical(line)

            if logical.upper().startswith("EXEC SQL"):
                in_exec_sql = True
                start = index
                cursor = ""
                continue

            if in_exec_sql and not cursor:
                match = FETCH_CURSOR_PATTERN.search(logical)
                if match:
                    cursor = match.group("cursor").upper()

            if in_exec_sql and END_EXEC_PATTERN.search(logical):
                if cursor:
                    blocks.append((cursor, start, index))

                in_exec_sql = False
                start = -1
                cursor = ""

        return blocks

    def _select_columns(self, block: list[str]) -> list[str]:
        columns: list[str] = []
        in_select = False

        for line in block:
            logical = self.fixed_format.logical(line)

            if SELECT_KEYWORD_PATTERN.match(logical):
                in_select = True
                continue

            if in_select and FROM_PATTERN.search(logical):
                break

            if in_select:
                column = self._select_column_from_logical(logical)

                if column:
                    columns.append(column)

        return columns

    def _select_column_from_logical(self, logical: str) -> str:
        text = str(logical or "").strip()

        if not text:
            return ""

        if self._is_sql_non_column_keyword(text):
            return ""

        match = SELECT_ITEM_PATTERN.match(text)

        if not match:
            return ""

        column = match.group("column").upper()

        if self._is_sql_non_column_keyword(column):
            return ""

        return column

    def _order_by_columns(self, block: list[str]) -> list[str]:
        columns: list[str] = []
        in_order_by = False

        for line in block:
            logical = self.fixed_format.logical(line)

            if ORDER_BY_PATTERN.search(logical):
                in_order_by = True
                remainder = ORDER_BY_PATTERN.sub("", logical).strip()

                if remainder:
                    columns.extend(self._parse_order_by_columns(remainder))

                continue

            if in_order_by:
                if FOR_READ_ONLY_PATTERN.search(logical) or END_EXEC_PATTERN.search(logical):
                    break

                columns.extend(self._parse_order_by_columns(logical))

        return columns

    def _parse_order_by_columns(self, text: str) -> list[str]:
        columns: list[str] = []

        for item in str(text or "").split(","):
            token = item.strip()
            token = ASC_DESC_PATTERN.sub("", token).strip()
            token = token.strip(",")

            if SQL_NAME_TOKEN_PATTERN.match(token):
                columns.append(token.upper())

        return columns

    def _has_non_order_usage(
        self,
        lines: list[str],
        declare_range: tuple[int, int],
        fetch_blocks: list[tuple[str, int, int]],
        cursor: str,
        column: str,
    ) -> bool:
        host_like = column.replace("_", "-").upper()
        column_upper = column.upper()

        fetch_range = self._matching_fetch_range(fetch_blocks, cursor)

        for index, line in enumerate(lines):
            if self._index_in_range(index, declare_range):
                continue

            if fetch_range and self._index_in_range(index, fetch_range):
                continue

            logical = self.fixed_format.logical(line).upper()

            if column_upper in logical:
                return True

            if host_like in logical:
                return True

        return False

    def _matching_fetch_range(
        self,
        fetch_blocks: list[tuple[str, int, int]],
        cursor: str,
    ) -> tuple[int, int] | None:
        for fetch_cursor, start, end in fetch_blocks:
            if fetch_cursor == cursor:
                return start, end

        return None

    def _index_in_range(self, index: int, value_range: tuple[int, int]) -> bool:
        start, end = value_range
        return start <= index <= end

    def _remove_select_positions(
        self,
        block: list[str],
        positions: set[int],
    ) -> list[str]:
        output: list[str] = []
        in_select = False
        position = -1

        for line in block:
            logical = self.fixed_format.logical(line)

            if SELECT_KEYWORD_PATTERN.match(logical):
                in_select = True
                output.append(line)
                continue

            if in_select and FROM_PATTERN.search(logical):
                in_select = False
                output = self._normalize_select_commas(output)
                output.append(line)
                continue

            if in_select:
                column = self._select_column_from_logical(logical)

                if column:
                    position += 1

                    if position in positions:
                        continue

            output.append(line)

        return self._normalize_select_commas(output)

    def _remove_fetch_positions(
        self,
        block: list[str],
        positions: set[int],
    ) -> list[str]:
        output: list[str] = []
        in_into = False
        position = -1

        for line in block:
            logical = self.fixed_format.logical(line)

            if logical.upper() == "INTO":
                in_into = True
                output.append(line)
                continue

            if in_into and END_EXEC_PATTERN.search(logical):
                in_into = False
                output = self._normalize_fetch_commas(output)
                output.append(line)
                continue

            if in_into and HOST_REFERENCE_PATTERN.search(logical):
                position += 1

                if position in positions:
                    continue

            output.append(line)

        return self._normalize_fetch_commas(output)

    def _normalize_select_commas(self, lines: list[str]) -> list[str]:
        result = list(lines)
        indexes: list[int] = []
        in_select = False

        for index, line in enumerate(result):
            logical = self.fixed_format.logical(line)

            if SELECT_KEYWORD_PATTERN.match(logical):
                in_select = True
                continue

            if in_select and FROM_PATTERN.search(logical):
                break

            if not in_select:
                continue

            column = self._select_column_from_logical(logical)

            if column:
                indexes.append(index)

        for item_number, line_index in enumerate(indexes):
            line = result[line_index]
            logical = self.fixed_format.logical(line)
            column = logical.lstrip(",").strip()

            if item_number == 0:
                body = f"        {column}"
            else:
                body = f"       , {column}"

            result[line_index] = self.fixed_format.replace_body(line, body)

        return result

    def _normalize_fetch_commas(self, lines: list[str]) -> list[str]:
        result = list(lines)
        indexes: list[int] = []
        in_into = False

        for index, line in enumerate(result):
            logical = self.fixed_format.logical(line)

            if logical.upper() == "INTO":
                in_into = True
                continue

            if in_into and END_EXEC_PATTERN.search(logical):
                break

            if not in_into:
                continue

            if HOST_REFERENCE_PATTERN.search(logical):
                indexes.append(index)

        for item_number, line_index in enumerate(indexes):
            line = result[line_index]
            logical = self.fixed_format.logical(line).rstrip(",")

            if item_number < len(indexes) - 1:
                logical = logical + ","

            result[line_index] = self.fixed_format.replace_body(
                line,
                "        " + logical,
            )

        return result

    def _is_sql_non_column_keyword(self, value: str) -> bool:
        text = str(value or "").strip().upper().lstrip(",").strip()
        return text in self.SQL_NON_COLUMN_KEYWORDS

    def _normalize_name(self, value: str) -> str:
        return str(value or "").strip().upper().replace("-", "_")