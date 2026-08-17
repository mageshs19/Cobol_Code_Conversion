from __future__ import annotations

import re

from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.host_variable_resolver import HostVariableResolver
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver


class TimestampGenerator:
    """
    Generates timestamp and audit support.

    This generator is intentionally conservative.

    For retrieval-only programs, it does not inject timestamp working storage,
    timestamp paragraphs, or audit MOVE statements.

    For update/insert/delete programs, it adds a safe timestamp working-storage
    block and a safe timestamp paragraph only when DB2 write activity is found.

    The full audit-field MOVE generation can be enhanced later after retrieval
    execution is stable.
    """

    WS_MARKER = "DB2 GENERATED TIMESTAMP AND AUDIT WORKING STORAGE"
    PARAGRAPH_NAME = "600-GET-TIMESTAMP"
    PARAGRAPH_EXIT_NAME = "600-GET-TIMESTAMP-EXIT"

    PROCEDURE_DIVISION_PATTERN = re.compile(
        r"^\s*(?:\d{6}\s+)?PROCEDURE\s+DIVISION\b.*\.?\s*(?:\d{8})?\s*$",
        flags=re.IGNORECASE | re.MULTILINE,
    )

    WORKING_STORAGE_PATTERN = re.compile(
        r"^\s*(?:\d{6}\s+)?WORKING-STORAGE\s+SECTION\.\s*(?:\d{8})?\s*$",
        flags=re.IGNORECASE | re.MULTILINE,
    )

    LINKAGE_SECTION_PATTERN = re.compile(
        r"^\s*(?:\d{6}\s+)?LINKAGE\s+SECTION\.\s*(?:\d{8})?\s*$",
        flags=re.IGNORECASE | re.MULTILINE,
    )

    END_PROGRAM_PATTERN = re.compile(
        r"^\s*(?:\d{6}\s+)?END\s+PROGRAM\b.*\.?\s*(?:\d{8})?\s*$",
        flags=re.IGNORECASE | re.MULTILINE,
    )

    STOP_RUN_PATTERN = re.compile(
        r"^\s*(?:\d{6}\s+)?STOP\s+RUN\.?\s*(?:\d{8})?\s*$",
        flags=re.IGNORECASE,
    )

    EXEC_SQL_PATTERN = re.compile(
        r"^\s*EXEC\s+SQL\b",
        flags=re.IGNORECASE,
    )

    END_EXEC_PATTERN = re.compile(
        r"^\s*END-EXEC\.?\s*$",
        flags=re.IGNORECASE,
    )

    DB2_WRITE_OPERATION_PATTERN = re.compile(
        r"^\s*(INSERT|UPDATE|DELETE)\b",
        flags=re.IGNORECASE,
    )

    COBOL_WRITE_OPERATION_PATTERN = re.compile(
        r"^\s*(STORE|MODIFY|ERASE)\b",
        flags=re.IGNORECASE,
    )

    def __init__(
        self,
        mapping_repository: MappingRepository,
        table_name_resolver: TableNameResolver,
        host_variable_resolver: HostVariableResolver,
    ) -> None:
        self.mapping_repository = mapping_repository
        self.table_name_resolver = table_name_resolver
        self.host_variable_resolver = host_variable_resolver
        self.messages: list[str] = []

    def apply(
        self,
        cobol_text: str,
        target_program_id: str = "",
    ) -> tuple[str, list[str]]:
        self.messages = []

        if not cobol_text:
            return "", self.messages

        if not self._has_db2_write_activity(cobol_text):
            self.messages.append(
                "Timestamp generator: no DB2 write activity found; timestamp audit generation skipped."
            )
            return cobol_text.rstrip() + "\n", self.messages

        updated_text = cobol_text

        updated_text = self._ensure_timestamp_working_storage(
            text=updated_text,
            target_program_id=target_program_id,
        )

        updated_text = self._ensure_timestamp_paragraph(
            text=updated_text,
        )

        updated_text = self._ensure_timestamp_perform(
            text=updated_text,
        )

        self.messages.append(
            "Timestamp generator: timestamp working storage and paragraph ensured."
        )

        return updated_text.rstrip() + "\n", self.messages

    def _has_db2_write_activity(
        self,
        text: str,
    ) -> bool:
        in_exec_sql = False

        for line in str(text or "").splitlines():
            logical = self._logical_line(line)

            if self.EXEC_SQL_PATTERN.match(logical):
                in_exec_sql = True
                continue

            if in_exec_sql and self.DB2_WRITE_OPERATION_PATTERN.search(logical):
                return True

            if self.END_EXEC_PATTERN.match(logical):
                in_exec_sql = False
                continue

            if self.COBOL_WRITE_OPERATION_PATTERN.search(logical):
                return True

        return False

    def _ensure_timestamp_working_storage(
        self,
        text: str,
        target_program_id: str,
    ) -> str:
        if self.WS_MARKER in text:
            return text

        block = self._timestamp_working_storage_block(
            target_program_id=target_program_id,
        )

        lines = text.splitlines()
        insert_index = self._working_storage_insert_index(lines)

        if insert_index < 0:
            return block.rstrip() + "\n\n" + text.rstrip() + "\n"

        updated_lines = (
            lines[:insert_index]
            + [""]
            + block.splitlines()
            + [""]
            + lines[insert_index:]
        )

        return "\n".join(updated_lines).rstrip() + "\n"

    def _ensure_timestamp_paragraph(
        self,
        text: str,
    ) -> str:
        if re.search(
            rf"^\s*(?:\d{{6}}\s+)?{re.escape(self.PARAGRAPH_NAME)}\.",
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        ):
            return text

        block = self._timestamp_paragraph_block()

        lines = text.splitlines()
        insert_index = self._timestamp_paragraph_insert_index(lines)

        if insert_index < 0:
            return text.rstrip() + "\n\n" + block + "\n"

        updated_lines = (
            lines[:insert_index]
            + block.splitlines()
            + [""]
            + lines[insert_index:]
        )

        return "\n".join(updated_lines).rstrip() + "\n"

    def _ensure_timestamp_perform(
        self,
        text: str,
    ) -> str:
        if re.search(
            rf"\bPERFORM\s+{re.escape(self.PARAGRAPH_NAME)}\b",
            text,
            flags=re.IGNORECASE,
        ):
            return text

        lines = text.splitlines()
        procedure_index = self._find_pattern_index(
            lines=lines,
            pattern=self.PROCEDURE_DIVISION_PATTERN,
        )

        if procedure_index < 0:
            return text

        insert_index = procedure_index + 1

        while insert_index < len(lines):
            logical = self._logical_line(lines[insert_index])

            if not logical:
                insert_index += 1
                continue

            if logical.startswith("*"):
                insert_index += 1
                continue

            break

        updated_lines = (
            lines[:insert_index]
            + [f"    PERFORM {self.PARAGRAPH_NAME}."]
            + lines[insert_index:]
        )

        return "\n".join(updated_lines).rstrip() + "\n"

    def _timestamp_working_storage_block(
        self,
        target_program_id: str,
    ) -> str:
        program_id = str(target_program_id or "").strip().upper()

        if not program_id:
            program_id = "DB2PGM"

        if len(program_id) > 8:
            program_id = program_id[:8]

        return "\n".join(
            [
                f"* {self.WS_MARKER}",
                f"01 CS-PROGRAM                 PIC X(8) VALUE '{program_id:<8}'.",
                "01 WS-TIMESTAMP-FIELDS.",
                "   05 TS-SYSTEM.",
                "      10 DA-SYS.",
                "         15 DA-SYS-CCYY.",
                "            20 CC             PIC X(2).",
                "            20 YY             PIC X(2).",
                "         15 MM                PIC X(2).",
                "         15 DD                PIC X(2).",
                "      10 HR-SYS.",
                "         15 HH                PIC X(2).",
                "         15 MI                PIC X(2).",
                "         15 SS                PIC X(2).",
                "         15 TT                PIC X(2).",
                "   05 TS-TIMESTAMP.",
                "      10 DA-TIMESTAMP.",
                "         15 DA-TIMESTAMP-CCYY.",
                "            20 CC             PIC X(2).",
                "            20 YY             PIC X(2).",
                "         15 MM                PIC X(2).",
                "         15 DD                PIC X(2).",
                "      10 HR-TIMESTAMP.",
                "         15 HH                PIC X(2).",
                "         15 MI                PIC X(2).",
                "         15 SS                PIC X(2).",
                "         15 TT                PIC X(2).",
            ]
        )

    def _timestamp_paragraph_block(
        self,
    ) -> str:
        return "\n".join(
            [
                f"{self.PARAGRAPH_NAME}.",
                "    ACCEPT TS-SYSTEM FROM DATE.",
                "    ACCEPT HR-SYS FROM TIME.",
                "    MOVE DA-SYS TO DA-TIMESTAMP.",
                "    MOVE HR-SYS TO HR-TIMESTAMP.",
                "    DISPLAY 'TIMESTAMP: ' TS-TIMESTAMP.",
                f"{self.PARAGRAPH_EXIT_NAME}.",
                "    EXIT.",
            ]
        )

    def _working_storage_insert_index(
        self,
        lines: list[str],
    ) -> int:
        linkage_index = self._find_pattern_index(
            lines=lines,
            pattern=self.LINKAGE_SECTION_PATTERN,
        )

        if linkage_index >= 0:
            return linkage_index

        procedure_index = self._find_pattern_index(
            lines=lines,
            pattern=self.PROCEDURE_DIVISION_PATTERN,
        )

        if procedure_index >= 0:
            return procedure_index

        working_storage_index = self._find_pattern_index(
            lines=lines,
            pattern=self.WORKING_STORAGE_PATTERN,
        )

        if working_storage_index >= 0:
            return working_storage_index + 1

        return -1

    def _timestamp_paragraph_insert_index(
        self,
        lines: list[str],
    ) -> int:
        for index, line in enumerate(lines):
            logical = self._logical_line(line)

            if self.STOP_RUN_PATTERN.match(logical):
                return index

            if self.END_PROGRAM_PATTERN.match(logical):
                return index

        return -1

    def _find_pattern_index(
        self,
        lines: list[str],
        pattern: re.Pattern,
    ) -> int:
        for index, line in enumerate(lines):
            logical = self._logical_line(line)

            if pattern.match(logical):
                return index

        return -1

    def _logical_line(
        self,
        line: str,
    ) -> str:
        text = str(line or "").rstrip()

        if len(text) > 6 and text[:6].strip().isdigit():
            return text[6:].strip()

        return text.strip()