"""
Cursor ORDER BY cleanup composer.

This composer removes unintended ORDER BY clauses from parent/root cursor
declarations.

Generic rule:
- A cursor declaration without a WHERE clause is treated as a parent/root cursor.
- Parent/root cursor ORDER BY is removed unless explicit ordering is already
  handled upstream.
- A cursor declaration with a WHERE clause is treated as a child/dependent
  cursor and keeps ORDER BY.

This class does not hardcode cursor names, table names, record names, or
business fields.
"""

from patterns.sequence_patterns import strip_sequence_numbers


class CursorOrderCleanupComposer:
    def compose(
        self,
        text: str,
    ) -> str:
        if not text:
            return ""

        lines = self._normalize_line_endings(text).splitlines()

        output: list[str] = []
        index = 0

        while index < len(lines):
            if not self._is_exec_sql_start(lines[index]):
                output.append(lines[index])
                index += 1
                continue

            block, next_index = self._collect_exec_sql_block(
                lines=lines,
                start_index=index,
            )

            if not self._is_cursor_declare_block(block):
                output.extend(block)
                index = next_index
                continue

            output.extend(
                self._cleanup_cursor_declare_block(block)
            )
            index = next_index

        return "\n".join(output).rstrip() + "\n"

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

    def _logical_upper(
        self,
        line: str,
    ) -> str:
        return self._logical(line).upper()

    def _is_exec_sql_start(
        self,
        line: str,
    ) -> bool:
        return self._logical_upper(line) == "EXEC SQL"

    def _is_exec_sql_end(
        self,
        line: str,
    ) -> bool:
        logical = self._logical_upper(line).rstrip(".")

        return logical == "END-EXEC"

    def _collect_exec_sql_block(
        self,
        lines: list[str],
        start_index: int,
    ) -> tuple[list[str], int]:
        block: list[str] = []
        index = start_index

        while index < len(lines):
            block.append(lines[index])

            if self._is_exec_sql_end(lines[index]):
                return block, index + 1

            index += 1

        return block, index

    def _is_cursor_declare_block(
        self,
        block: list[str],
    ) -> bool:
        for line in block:
            logical = self._logical_upper(line)

            if "DECLARE " in logical and " CURSOR " in logical:
                return True

        return False

    def _cleanup_cursor_declare_block(
        self,
        block: list[str],
    ) -> list[str]:
        if self._has_where_clause(block):
            return list(block)

        if not self._has_order_by_clause(block):
            return list(block)

        return self._remove_order_by_block(block)

    def _has_where_clause(
        self,
        block: list[str],
    ) -> bool:
        for line in block:
            logical = self._logical_upper(line)

            if logical == "WHERE":
                return True

            if logical.startswith("WHERE "):
                return True

        return False

    def _has_order_by_clause(
        self,
        block: list[str],
    ) -> bool:
        for line in block:
            logical = self._logical_upper(line)

            if logical == "ORDER BY":
                return True

            if logical.startswith("ORDER BY "):
                return True

        return False

    def _remove_order_by_block(
        self,
        block: list[str],
    ) -> list[str]:
        output: list[str] = []
        skipping_order_by = False

        for line in block:
            logical = self._logical_upper(line)

            if self._is_order_by_start(logical):
                skipping_order_by = True
                continue

            if skipping_order_by:
                if self._is_order_by_end(logical):
                    skipping_order_by = False
                    output.append(line)

                continue

            output.append(line)

        return output

    def _is_order_by_start(
        self,
        logical: str,
    ) -> bool:
        if logical == "ORDER BY":
            return True

        if logical.startswith("ORDER BY "):
            return True

        return False

    def _is_order_by_end(
        self,
        logical: str,
    ) -> bool:
        if logical == "FOR READ ONLY":
            return True

        if logical.startswith("FOR READ ONLY"):
            return True

        if logical == "END-EXEC":
            return True

        if logical == "END-EXEC.":
            return True

        return False