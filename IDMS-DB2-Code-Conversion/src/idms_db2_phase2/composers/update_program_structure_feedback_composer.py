from __future__ import annotations

import re

from idms_db2_phase2.composers.update_program_feedback_shared import (
    UpdateProgramFeedbackShared,
)
from idms_db2_phase2.services.name_normalizer import NameNormalizer


class UpdateProgramStructureFeedbackComposer(UpdateProgramFeedbackShared):
    """
    Fixes update-program structure feedback issues:
    - DCLGEN INCLUDE placement.
    - timestamp paragraph fall-through.
    """

    def compose(
        self,
        text: str,
    ) -> str:
        self.messages = []
        output = str(text or "")

        if not output.strip():
            return output

        output = self._move_dclgen_includes_to_infrastructure(output)
        output = self._prevent_timestamp_fallthrough(output)

        return output.rstrip() + "\n"

    def _move_dclgen_includes_to_infrastructure(
        self,
        text: str,
    ) -> str:
        lines = text.splitlines()
        output: list[str] = []
        includes_to_move: list[str] = []
        index = 0
        changed = False

        while index < len(lines):
            block, next_index = self._collect_exec_sql_block(lines, index)

            if not block:
                output.append(lines[index])
                index += 1
                continue

            include = self._include_name_from_block(block)

            if include and include not in {"SQLCA", "SQLERRWS", "SQLERROR"}:
                if self._is_after_procedure(lines, index):
                    includes_to_move.append(include)
                    changed = True
                    index = next_index
                    continue

            output.extend(block)
            index = next_index

        if not includes_to_move:
            return text

        output = self._insert_includes_near_sqlca(output, includes_to_move)

        if changed:
            self.messages.append(
                "Update structure feedback: moved DCLGEN includes into DB2 infrastructure."
            )

        return "\n".join(output).rstrip() + "\n"

    def _prevent_timestamp_fallthrough(
        self,
        text: str,
    ) -> str:
        lines = text.splitlines()
        timestamp_index = -1
        stop_index = -1

        for index, line in enumerate(lines):
            logical = self._logical(line)

            if timestamp_index < 0 and self.TIMESTAMP_PARAGRAPH_PATTERN.match(logical):
                timestamp_index = index

            if stop_index < 0 and self.STOP_RUN_PATTERN.match(logical):
                stop_index = index

        if timestamp_index < 0 or stop_index < 0:
            return text

        if stop_index < timestamp_index:
            return text

        stop_line = lines.pop(stop_index)

        if stop_index < timestamp_index:
            timestamp_index -= 1

        lines.insert(timestamp_index, stop_line)

        self.messages.append(
            "Update structure feedback: moved STOP RUN before timestamp paragraph."
        )

        return "\n".join(lines).rstrip() + "\n"

    def _collect_exec_sql_block(
        self,
        lines: list[str],
        index: int,
    ) -> tuple[list[str], int]:
        if index >= len(lines):
            return [], index

        if not self.EXEC_SQL_START_PATTERN.match(self._logical(lines[index])):
            return [], index

        output: list[str] = []

        while index < len(lines):
            output.append(lines[index])
            logical = self._logical(lines[index])
            index += 1

            if self.EXEC_SQL_END_PATTERN.match(logical):
                break

        return output, index

    def _include_name_from_block(
        self,
        block: list[str],
    ) -> str:
        for line in block:
            logical = self._logical(line)
            match = self.INCLUDE_PATTERN.match(logical)

            if match:
                return NameNormalizer.normalize(match.group("include"))

        return ""

    def _is_after_procedure(
        self,
        lines: list[str],
        index: int,
    ) -> bool:
        for prior in lines[:index]:
            if self._logical(prior).upper().startswith("PROCEDURE DIVISION"):
                return True

        return False

    def _insert_includes_near_sqlca(
        self,
        lines: list[str],
        includes: list[str],
    ) -> list[str]:
        existing = self._existing_includes("\n".join(lines))
        unique: list[str] = []

        for include in includes:
            clean = NameNormalizer.normalize(include)

            if not clean:
                continue
            if clean in existing:
                continue
            if clean in unique:
                continue

            unique.append(clean)

        if not unique:
            return lines

        insert_index = self._include_insert_index(lines)
        include_lines: list[str] = []

        for include in unique:
            include_lines.extend(
                [
                    " EXEC SQL",
                    f"    INCLUDE {include}",
                    " END-EXEC.",
                ]
            )

        if insert_index < 0:
            return include_lines + lines

        return lines[:insert_index] + include_lines + lines[insert_index:]

    def _include_insert_index(
        self,
        lines: list[str],
    ) -> int:
        last_include_end = -1
        index = 0

        while index < len(lines):
            block, next_index = self._collect_exec_sql_block(lines, index)

            if block:
                include = self._include_name_from_block(block)

                if include and include != "SQLERROR":
                    last_include_end = next_index

                index = next_index
                continue

            if self.SQL_LOCATION_PATTERN.match(self._logical(lines[index])):
                return index

            if self.LINKAGE_SECTION_PATTERN.match(self._logical(lines[index])):
                return index

            index += 1

        return last_include_end

    def _existing_includes(
        self,
        text: str,
    ) -> set[str]:
        output: set[str] = set()

        for match in re.finditer(
            r"\bINCLUDE\s+([A-Z0-9]+)\b",
            text,
            flags=re.IGNORECASE,
        ):
            include = NameNormalizer.normalize(match.group(1))

            if include:
                output.add(include)

        return output