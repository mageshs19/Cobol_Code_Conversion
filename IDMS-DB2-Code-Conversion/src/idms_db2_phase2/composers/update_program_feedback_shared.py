from __future__ import annotations

import re
from difflib import SequenceMatcher

from idms_db2_phase2.repositories.dclgen_repository import DclgenRepository
from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.host_variable_resolver import HostVariableResolver
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from patterns.sequence_patterns import strip_sequence_numbers


class UpdateProgramFeedbackShared:
    """
    Shared helpers for update-program feedback cleanup.

    Generic rules:
    - Sheet Mapping is authority for DB2 tables and columns.
    - DCLGEN is authority for host variable spelling.
    - Do not hardcode program names, table names, columns, or host variables.
    - For CALC/update flows, prefer DB2 primary-key metadata.
    - Avoid broad WHERE clauses when a narrower DB2 identity key is available.
    """

    CONVERTED_OBTAIN_CALC_PATTERN = re.compile(
        r"^\s*\*?\s*DB2:\s*Converted\s+OBTAIN\s+CALC\s+for\s+(?P<record>[A-Z0-9-]+)\.?\s*$",
        flags=re.IGNORECASE,
    )

    CONVERTED_MODIFY_PATTERN = re.compile(
        r"^\s*\*?\s*DB2:\s*Converted\s+MODIFY\s+for\s+(?P<record>[A-Z0-9-]+)\.?\s*$",
        flags=re.IGNORECASE,
    )

    EXEC_SQL_START_PATTERN = re.compile(
        r"^\s*EXEC\s+SQL\b",
        flags=re.IGNORECASE,
    )

    EXEC_SQL_END_PATTERN = re.compile(
        r"^\s*END-EXEC\.?\s*$",
        flags=re.IGNORECASE,
    )

    INCLUDE_PATTERN = re.compile(
        r"^\s*INCLUDE\s+(?P<include>[A-Z0-9]+)\b",
        flags=re.IGNORECASE,
    )

    SQLCODE_IF_PATTERN = re.compile(
        r"^\s*IF\s+SQLCODE\b",
        flags=re.IGNORECASE,
    )

    END_IF_PATTERN = re.compile(
        r"^\s*END-IF\.?\s*$",
        flags=re.IGNORECASE,
    )

    MALFORMED_SQLERROR_ENDIF_PATTERN = re.compile(
        r"^(?P<indent>\s*)PERFORM\s+SQLERROR\.?END-IF\.?\s*$",
        flags=re.IGNORECASE,
    )

    MOVE_TO_BARE_FIELD_PATTERN = re.compile(
        r"^\s*MOVE\s+(?P<src>.+?)\s+TO\s+(?P<tgt>[A-Z][A-Z0-9-]+)\.?\s*$",
        flags=re.IGNORECASE,
    )

    MOVE_TO_DCL_HOST_PATTERN = re.compile(
        r"^\s*MOVE\s+(?P<src>.+?)\s+TO\s+(?P<host>[A-Z][A-Z0-9-]+)\s+OF\s+(?P<group>DCL[A-Z0-9-]+)\.?\s*$",
        flags=re.IGNORECASE,
    )

    SQL_LOCATION_PATTERN = re.compile(
        r"^\s*01\s+SQL-LOCATION\b",
        flags=re.IGNORECASE,
    )

    LINKAGE_SECTION_PATTERN = re.compile(
        r"^\s*LINKAGE\s+SECTION\.",
        flags=re.IGNORECASE,
    )

    TIMESTAMP_PARAGRAPH_PATTERN = re.compile(
        r"^\s*600-GET-TIMESTAMP\.\s*$",
        flags=re.IGNORECASE,
    )

    STOP_RUN_PATTERN = re.compile(
        r"^\s*STOP\s+RUN\.?\s*$",
        flags=re.IGNORECASE,
    )

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

    UPDATE_AUDIT_PREFIXES = (
        "TS_UPDATE",
        "ID_USERID",
        "NR_USERID",
        "ID_USER",
        "NR_USER",
    )

    INSERT_ONLY_AUDIT_PREFIXES = (
        "TS_CREATE",
    )

    IDENTITY_KEY_PREFIXES = (
        "NS_ID",
        "NR_ID",
        "ID_",
        "CO_ID",
        "NR_IS",
    )

    MIN_FIELD_MATCH_SCORE = 0.84

    def __init__(
        self,
        mapping_repository: MappingRepository,
        dclgen_repository: DclgenRepository,
        table_name_resolver: TableNameResolver,
        host_variable_resolver: HostVariableResolver,
    ) -> None:
        self.mapping_repository = mapping_repository
        self.dclgen_repository = dclgen_repository
        self.table_name_resolver = table_name_resolver
        self.host_variable_resolver = host_variable_resolver
        self.messages: list[str] = []

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

    def _table_for_record(
        self,
        record: str,
    ) -> str:
        mapped_table = self.mapping_repository.db2_table_for_record(record)

        if not mapped_table:
            return ""

        return self.table_name_resolver.resolve_table(mapped_table)

    def _db2_primary_key_columns(
        self,
        record: str,
        table: str,
    ) -> list[str]:
        """
        Return DB2 primary-key columns for SQL WHERE.

        Order:
        1. Use Sheet Mapping rows marked DB2 PRIMARY/KEY.
        2. Remove rows marked as foreign/relationship.
        3. If multiple primary columns exist and a DB2 identity-style key is present,
           narrow to identity-style keys to avoid broad CALC source-key WHERE.
        4. If no DB2 primary-key metadata exists, fall back conservatively to existing
           repository key metadata to preserve older behavior.
        """
        strict_keys = self._strict_db2_primary_key_columns(record)
        strict_keys = self._filter_existing_dclgen_columns(table, strict_keys)

        if len(strict_keys) <= 1:
            return strict_keys

        identity_keys = [
            column
            for column in strict_keys
            if column.startswith(self.IDENTITY_KEY_PREFIXES)
        ]

        if identity_keys:
            return identity_keys

        return strict_keys

    def _strict_db2_primary_key_columns(
        self,
        record: str,
    ) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()

        for row in self.mapping_repository.rows_for_record(record):
            db2_key = NameNormalizer.normalize(getattr(row, "db2_key", ""))
            relation = NameNormalizer.normalize(getattr(row, "relation", ""))
            column = NameNormalizer.normalize(getattr(row, "new_db2_field_name", ""))

            if not column:
                continue

            if "FOREIGN" in relation:
                continue

            if "FOREIGN" in db2_key:
                continue

            if "PRIMARY" not in db2_key and db2_key != "KEY":
                continue

            if column in seen:
                continue

            seen.add(column)
            output.append(column)

        if output:
            return output

        if hasattr(self.mapping_repository, "key_columns_for_record"):
            return self.mapping_repository.key_columns_for_record(record)

        return []

    def _column_for_source_field(
        self,
        record: str,
        source_field: str,
    ) -> str:
        """
        Resolve source field to DB2 column using Sheet Mapping.

        Handles:
        - exact normalized match
        - compact match
        - DB2 suffix-insensitive match
        - similarity fallback

        This is needed for cases like:
        MOVE DATE-YMD8 TO DA-INFSD-GDIFAR

        without hardcoding that field name.
        """
        source = NameNormalizer.normalize(source_field)

        if not source:
            return ""

        if hasattr(self.mapping_repository, "column_for_source_field"):
            column = self.mapping_repository.column_for_source_field(
                record_name=record,
                source_field_name=source_field,
            )

            if column:
                return NameNormalizer.normalize(column)

        rows = self.mapping_repository.rows_for_record(record)

        exact = self._column_for_source_exact(rows, source)

        if exact:
            return exact

        compact = self._column_for_source_compact(rows, source)

        if compact:
            return compact

        return self._column_for_source_similarity(rows, source)

    def _column_for_source_exact(
        self,
        rows,
        source: str,
    ) -> str:
        for row in rows:
            column = NameNormalizer.normalize(getattr(row, "new_db2_field_name", ""))

            if not column:
                continue

            for candidate in self._source_candidates(row):
                if NameNormalizer.normalize(candidate) == source:
                    return column

        return ""

    def _column_for_source_compact(
        self,
        rows,
        source: str,
    ) -> str:
        compact_source = self._compact_for_compare(source)

        if not compact_source:
            return ""

        for row in rows:
            column = NameNormalizer.normalize(getattr(row, "new_db2_field_name", ""))

            if not column:
                continue

            candidates = self._source_candidates(row)
            candidates.append(column)

            for candidate in candidates:
                compact_candidate = self._compact_for_compare(candidate)

                if not compact_candidate:
                    continue

                if compact_candidate == compact_source:
                    return column

                if compact_candidate.startswith(compact_source):
                    return column

                if compact_source.startswith(compact_candidate):
                    return column

        return ""

    def _column_for_source_similarity(
        self,
        rows,
        source: str,
    ) -> str:
        compact_source = self._compact_for_compare(source)

        if not compact_source:
            return ""

        best_column = ""
        best_score = 0.0

        for row in rows:
            column = NameNormalizer.normalize(getattr(row, "new_db2_field_name", ""))

            if not column:
                continue

            candidates = self._source_candidates(row)
            candidates.append(column)

            for candidate in candidates:
                compact_candidate = self._compact_for_compare(candidate)

                if not compact_candidate:
                    continue

                score = SequenceMatcher(
                    None,
                    compact_source,
                    compact_candidate,
                ).ratio()

                if score > best_score:
                    best_score = score
                    best_column = column

        if best_score >= self.MIN_FIELD_MATCH_SCORE:
            return best_column

        return ""

    def _source_candidates(
        self,
        row,
    ) -> list[str]:
        return [
            str(getattr(row, "cobol_zone", "") or ""),
            str(getattr(row, "reference_field_name_copybook", "") or ""),
            str(getattr(row, "new_db2_field_name", "") or ""),
            str(getattr(row, "cross_application_db2_field_name", "") or ""),
        ]

    def _compact_for_compare(
        self,
        value: str,
    ) -> str:
        text = NameNormalizer.compact(value)
        return self._remove_db2_suffix(text)

    def _remove_db2_suffix(
        self,
        value: str,
    ) -> str:
        text = str(value or "").upper()

        if len(text) <= 7:
            return text

        for index, char in enumerate(text):
            if not char.isdigit():
                continue

            suffix = text[index:]

            if len(suffix) >= 4 and any(item.isalpha() for item in suffix):
                return text[:index]

        return text

    def _update_audit_columns(
        self,
        record: str,
        table: str,
    ) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()

        for row in self.mapping_repository.rows_for_record(record):
            column = NameNormalizer.normalize(getattr(row, "new_db2_field_name", ""))

            if not column:
                continue

            if column.startswith(self.INSERT_ONLY_AUDIT_PREFIXES):
                continue

            if not column.startswith(self.UPDATE_AUDIT_PREFIXES):
                continue

            if column in seen:
                continue

            seen.add(column)
            output.append(column)

        return self._filter_existing_dclgen_columns(table, output)

    def _filter_existing_dclgen_columns(
        self,
        table: str,
        columns: list[str],
    ) -> list[str]:
        valid_columns = set(self.dclgen_repository.column_names_for_table(table))
        output: list[str] = []
        seen: set[str] = set()

        for column in columns:
            normalized = NameNormalizer.normalize(column)

            if not normalized:
                continue

            if normalized not in valid_columns:
                continue

            if normalized in seen:
                continue

            if not self.host_variable_resolver.has_host_for_column(
                table_name=table,
                column_name=normalized,
            ):
                continue

            seen.add(normalized)
            output.append(normalized)

        return output

    def _host_reference(
        self,
        table: str,
        column: str,
    ) -> str:
        return self.host_variable_resolver.host_reference_for_column(
            table_name=table,
            column_name=column,
        )

    def _host_reference_key(
        self,
        table: str,
        column: str,
    ) -> str:
        if hasattr(self.host_variable_resolver, "host_reference_key"):
            return self.host_variable_resolver.host_reference_key(
                table_name=table,
                column_name=column,
            )

        reference = self._host_reference(table, column)

        if reference.startswith(":"):
            return reference[1:].strip()

        return reference

    def _set_lines(
        self,
        table: str,
        columns: list[str],
        indent: str,
    ) -> list[str]:
        output: list[str] = []

        for index, column in enumerate(columns):
            host = self._host_reference(table, column)

            if not host:
                continue

            suffix = "," if index < len(columns) - 1 else ""
            output.append(f"{indent}{column} = {host}{suffix}")

        return output

    def _where_lines(
        self,
        table: str,
        columns: list[str],
        indent: str,
    ) -> list[str]:
        output: list[str] = []

        for index, column in enumerate(columns):
            host = self._host_reference(table, column)

            if not host:
                continue

            prefix = "" if index == 0 else "AND "
            output.append(f"{indent}{prefix}{column} = {host}")

        return output

    def _comma_lines(
        self,
        values: list[str],
        indent: str,
    ) -> list[str]:
        output: list[str] = []

        for index, value in enumerate(values):
            suffix = "," if index < len(values) - 1 else ""
            output.append(f"{indent}{value}{suffix}")

        return output

    def _is_protected_bare_target(
        self,
        target: str,
    ) -> bool:
        clean = NameNormalizer.to_cobol(target).upper()
        return clean.startswith(self.PROTECTED_BARE_TARGET_PREFIXES)

    def _skip_exec_sql(
        self,
        lines: list[str],
        index: int,
    ) -> int:
        while index < len(lines):
            logical = self._logical(lines[index])
            index += 1

            if self.EXEC_SQL_END_PATTERN.match(logical):
                break

        return index

    def _skip_if_block(
        self,
        lines: list[str],
        index: int,
    ) -> int:
        while index < len(lines):
            logical = self._logical(lines[index])
            index += 1

            if self.END_IF_PATTERN.match(logical):
                break

        return index