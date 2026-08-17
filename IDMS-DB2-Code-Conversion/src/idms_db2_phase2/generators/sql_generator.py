from idms_db2_phase2.repositories.dclgen_repository import DclgenRepository
from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.column_name_resolver import ColumnNameResolver
from idms_db2_phase2.resolvers.host_variable_resolver import HostVariableResolver
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from rules.timestamp_audit_rules import INSERT_EXCLUDE_AUDIT_PREFIXES


class SqlGenerator:
    """
    Generates DB2 embedded SQL snippets.

    Authority:
    - Sheet Mapping determines intended DB2 table and column names.
    - DCLGEN determines final table availability, host variable spelling, and group names.
    - TableNameResolver resolves TB/TV mismatches using DCLGEN.
    """

    SELECT_EXCLUDE_PREFIXES = (
        "TS_CREATE",
        "TS_UPDATE",
        "ID_USERID",
        "NR_USERID",
    )

    FALLBACK_KEY_PREFIXES = (
        "CT_",
        "NR_CIO",
        "DA_CR",
        "NR_ID",
        "NS_",
    )

    def __init__(
        self,
        mapping_repository: MappingRepository,
        dclgen_repository: DclgenRepository,
        table_name_resolver: TableNameResolver,
        column_name_resolver: ColumnNameResolver,
        host_variable_resolver: HostVariableResolver,
    ) -> None:
        self.mapping_repository = mapping_repository
        self.dclgen_repository = dclgen_repository
        self.table_name_resolver = table_name_resolver
        self.column_name_resolver = column_name_resolver
        self.host_variable_resolver = host_variable_resolver

    def select_by_key(
        self,
        record_name: str,
    ) -> list[str]:
        record = NameNormalizer.normalize(record_name)
        table = self.table_name_resolver.table_for_record(record)

        if not table:
            return self._missing_mapping(record, "Missing SELECT table mapping")

        columns = self.column_name_resolver.columns_for_record(record)

        if not columns:
            columns = self._dclgen_column_names_for_table(table)

        columns = self._filter_select_columns(columns)

        if not columns:
            return self._missing_mapping(record, "Missing SELECT column mapping")

        hosts = self.host_variable_resolver.host_references_for_columns(
            table_name=table,
            columns=columns,
        )

        if not hosts:
            return self._missing_mapping(record, "Missing SELECT host mapping")

        key_columns = self.column_name_resolver.key_columns_for_record(record)

        if not key_columns:
            key_columns = self._fallback_key_columns(columns)

        if not key_columns and columns:
            key_columns = columns[:1]

        where_conditions = self._where_conditions(
            table_name=table,
            columns=key_columns,
        )

        lines: list[str] = [
            f"MOVE 'SELECT-{NameNormalizer.to_cobol(record)}' TO SQL-LOCATION.",
            "EXEC SQL",
            " SELECT",
        ]

        lines.extend(
            self._comma_lines(
                items=columns,
                indent="     ",
            )
        )

        lines.append(" INTO")

        lines.extend(
            self._comma_lines(
                items=hosts,
                indent="     ",
            )
        )

        lines.append(f" FROM {table}")

        if where_conditions:
            lines.append(" WHERE")
            lines.extend(
                self._and_lines(
                    items=where_conditions,
                    indent="     ",
                )
            )

        lines.append("END-EXEC.")

        return lines

    def insert(
        self,
        record_name: str,
    ) -> list[str]:
        record = NameNormalizer.normalize(record_name)
        table = self.table_name_resolver.table_for_record(record)

        if not table:
            return self._missing_mapping(record, "Missing INSERT table mapping")

        columns = self.column_name_resolver.columns_for_record(record)

        if not columns:
            columns = self._dclgen_column_names_for_table(table)

        columns = [
            column
            for column in columns
            if column
            and self._column_exists_in_table(
                table_name=table,
                column_name=column,
            )
            and not self._is_insert_excluded_audit_column(column)
        ]

        if not columns:
            return self._missing_mapping(record, "Missing INSERT column mapping")

        hosts = self.host_variable_resolver.host_references_for_columns(
            table_name=table,
            columns=columns,
        )

        if not hosts:
            return self._missing_mapping(record, "Missing INSERT host mapping")

        lines: list[str] = [
            f"MOVE 'INSERT-{NameNormalizer.to_cobol(record)}' TO SQL-LOCATION.",
            "EXEC SQL",
            f" INSERT INTO {table}",
            " (",
        ]

        lines.extend(
            self._comma_lines(
                items=columns,
                indent="     ",
            )
        )

        lines.extend(
            [
                " )",
                " VALUES",
                " (",
            ]
        )

        lines.extend(
            self._comma_lines(
                items=hosts,
                indent="     ",
            )
        )

        lines.extend(
            [
                " )",
                "END-EXEC.",
            ]
        )

        return lines

    def update(
        self,
        record_name: str,
        changed_fields: list[str] | None = None,
    ) -> list[str]:
        record = NameNormalizer.normalize(record_name)
        table = self.table_name_resolver.table_for_record(record)

        if not table:
            return self._missing_mapping(record, "Missing UPDATE table mapping")

        all_columns = self.column_name_resolver.columns_for_record(record)

        if not all_columns:
            all_columns = self._dclgen_column_names_for_table(table)

        all_columns = [
            column
            for column in all_columns
            if column
            and self._column_exists_in_table(
                table_name=table,
                column_name=column,
            )
        ]

        if not all_columns:
            return self._missing_mapping(record, "Missing UPDATE column mapping")

        key_columns = self.column_name_resolver.key_columns_for_record(record)

        if not key_columns:
            key_columns = self._fallback_key_columns(all_columns)

        if not key_columns:
            return self._missing_mapping(record, "Missing UPDATE key mapping")

        normalized_key_columns = {
            NameNormalizer.normalize(column)
            for column in key_columns
            if NameNormalizer.normalize(column)
        }

        set_columns = [
            column
            for column in all_columns
            if NameNormalizer.normalize(column) not in normalized_key_columns
            and not self._is_audit_column(column)
        ]

        if changed_fields:
            changed = {
                NameNormalizer.normalize(field)
                for field in changed_fields
                if NameNormalizer.normalize(field)
            }

            set_columns = [
                column
                for column in set_columns
                if NameNormalizer.normalize(column) in changed
            ]

        if not set_columns:
            return self._missing_mapping(record, "Missing UPDATE SET mapping")

        set_lines = self._set_lines(
            table_name=table,
            columns=set_columns,
        )

        where_conditions = self._where_conditions(
            table_name=table,
            columns=key_columns,
        )

        if not set_lines:
            return self._missing_mapping(record, "Missing UPDATE host mapping")

        if not where_conditions:
            return self._missing_mapping(record, "Missing UPDATE WHERE mapping")

        lines: list[str] = [
            f"MOVE 'UPDATE-{NameNormalizer.to_cobol(record)}' TO SQL-LOCATION.",
            "EXEC SQL",
            f" UPDATE {table}",
            " SET",
        ]

        lines.extend(
            self._comma_lines(
                items=set_lines,
                indent="     ",
            )
        )

        lines.append(" WHERE")

        lines.extend(
            self._and_lines(
                items=where_conditions,
                indent="     ",
            )
        )

        lines.append("END-EXEC.")

        return lines

    def delete(
        self,
        record_name: str,
    ) -> list[str]:
        record = NameNormalizer.normalize(record_name)
        table = self.table_name_resolver.table_for_record(record)

        if not table:
            return self._missing_mapping(record, "Missing DELETE table mapping")

        columns = self.column_name_resolver.columns_for_record(record)

        if not columns:
            columns = self._dclgen_column_names_for_table(table)

        key_columns = self.column_name_resolver.key_columns_for_record(record)

        if not key_columns:
            key_columns = self._fallback_key_columns(columns)

        if not key_columns:
            return self._missing_mapping(record, "Missing DELETE key mapping")

        where_conditions = self._where_conditions(
            table_name=table,
            columns=key_columns,
        )

        if not where_conditions:
            return self._missing_mapping(record, "Missing DELETE WHERE mapping")

        lines: list[str] = [
            f"MOVE 'DELETE-{NameNormalizer.to_cobol(record)}' TO SQL-LOCATION.",
            "EXEC SQL",
            f" DELETE FROM {table}",
            " WHERE",
        ]

        lines.extend(
            self._and_lines(
                items=where_conditions,
                indent="     ",
            )
        )

        lines.append("END-EXEC.")

        return lines

    def commit(
        self,
    ) -> list[str]:
        return [
            "MOVE 'COMMIT' TO SQL-LOCATION.",
            "EXEC SQL",
            " COMMIT",
            "END-EXEC.",
        ]

    def rollback(
        self,
    ) -> list[str]:
        return [
            "MOVE 'ROLLBACK' TO SQL-LOCATION.",
            "EXEC SQL",
            " ROLLBACK",
            "END-EXEC.",
        ]

    def _where_conditions(
        self,
        table_name: str,
        columns: list[str],
    ) -> list[str]:
        output: list[str] = []

        for column in columns:
            normalized_column = NameNormalizer.normalize(column)

            if not normalized_column:
                continue

            host = self.host_variable_resolver.host_reference_for_column(
                table_name=table_name,
                column_name=normalized_column,
            )

            if not host:
                continue

            output.append(f"{normalized_column} = {host}")

        return self._unique_non_empty(output)

    def _set_lines(
        self,
        table_name: str,
        columns: list[str],
    ) -> list[str]:
        output: list[str] = []

        for column in columns:
            normalized_column = NameNormalizer.normalize(column)

            if not normalized_column:
                continue

            host = self.host_variable_resolver.host_reference_for_column(
                table_name=table_name,
                column_name=normalized_column,
            )

            if not host:
                continue

            output.append(f"{normalized_column} = {host}")

        return self._unique_non_empty(output)

    def _comma_lines(
        self,
        items: list[str],
        indent: str,
    ) -> list[str]:
        clean_items = [
            str(item or "").strip()
            for item in items
            if str(item or "").strip()
        ]

        output: list[str] = []

        for index, item in enumerate(clean_items):
            suffix = "," if index < len(clean_items) - 1 else ""
            output.append(f"{indent}{item}{suffix}")

        return output

    def _and_lines(
        self,
        items: list[str],
        indent: str,
    ) -> list[str]:
        clean_items = [
            str(item or "").strip()
            for item in items
            if str(item or "").strip()
        ]

        output: list[str] = []

        for index, item in enumerate(clean_items):
            prefix = "AND " if index > 0 else ""
            output.append(f"{indent}{prefix}{item}")

        return output

    def _missing_mapping(
        self,
        record_name: str,
        reason: str,
    ) -> list[str]:
        record = NameNormalizer.to_cobol(record_name)

        if record:
            return [
                "* DB2: Conversion skipped because Sheet Mapping entry does not exist.",
                f"* DB2: Missing Sheet Mapping metadata for record {record}.",
                f"* DB2: Reason: {reason}.",
                "CONTINUE.",
            ]

        return [
            "* DB2: Conversion skipped because required Sheet Mapping metadata does not exist.",
            f"* DB2: Reason: {reason}.",
            "CONTINUE.",
        ]

    def _dclgen_column_names_for_table(
        self,
        table_name: str,
    ) -> list[str]:
        resolved_table = self.table_name_resolver.resolve_table(table_name)

        if not resolved_table:
            return []

        return self.dclgen_repository.column_names_for_table(resolved_table)

    def _column_exists_in_table(
        self,
        table_name: str,
        column_name: str,
    ) -> bool:
        resolved_table = self.table_name_resolver.resolve_table(table_name)
        normalized_column = NameNormalizer.normalize(column_name)

        if not resolved_table or not normalized_column:
            return False

        return self.dclgen_repository.has_column(
            table_name=resolved_table,
            column_name=normalized_column,
        )

    def _fallback_key_columns(
        self,
        columns: list[str],
    ) -> list[str]:
        output: list[str] = []

        for column in columns:
            normalized_column = NameNormalizer.normalize(column)

            if not normalized_column:
                continue

            if not normalized_column.startswith(self.FALLBACK_KEY_PREFIXES):
                continue

            if normalized_column in output:
                continue

            output.append(normalized_column)

            if len(output) >= 8:
                break

        return output

    def _filter_select_columns(
        self,
        columns: list[str],
    ) -> list[str]:
        output: list[str] = []

        for column in columns:
            normalized_column = NameNormalizer.normalize(column)

            if not normalized_column:
                continue

            if self._is_select_excluded_column(normalized_column):
                continue

            if normalized_column in output:
                continue

            output.append(normalized_column)

        return output

    def _is_select_excluded_column(
        self,
        column_name: str,
    ) -> bool:
        normalized = NameNormalizer.normalize(column_name)

        return normalized.startswith(self.SELECT_EXCLUDE_PREFIXES)

    def _is_audit_column(
        self,
        column_name: str,
    ) -> bool:
        normalized = NameNormalizer.normalize(column_name)

        return normalized.startswith(
            (
                "TS_CREATE",
                "TS_UPDATE",
                "ID_USERID",
                "NR_USERID",
            )
        )

    def _is_insert_excluded_audit_column(
        self,
        column_name: str,
    ) -> bool:
        column = NameNormalizer.normalize(column_name)

        return any(
            column.startswith(prefix)
            for prefix in INSERT_EXCLUDE_AUDIT_PREFIXES
        )

    def _unique_non_empty(
        self,
        values: list[str],
    ) -> list[str]:
        output: list[str] = []

        for value in values:
            text = str(value or "").strip()

            if not text:
                continue

            if text in output:
                continue

            output.append(text)

        return output