from idms_db2_phase2.repositories.dclgen_repository import DclgenRepository
from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.column_name_resolver import ColumnNameResolver
from idms_db2_phase2.resolvers.host_variable_resolver import HostVariableResolver
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
from idms_db2_phase2.resolvers.update_sql_plan_resolver import (
    UpdateSqlPlanResolver,
)
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from rules.timestamp_audit_rules import INSERT_EXCLUDE_AUDIT_PREFIXES


class SqlGenerator:
    """
    Generates DB2 embedded SQL snippets.

    Authority:
    - Sheet Mapping determines intended DB2 table and column names.
    - DCLGEN determines final table availability, host variable spelling,
      and group names.
    - TableNameResolver resolves TB/TV mismatches using DCLGEN.

    Feedback-driven rules:
    - OBTAIN CALC SELECT is not required for update flow.
    - Direct UPDATE is enough when UPDATE WHERE has proper key columns.
    - Composite key means all PK / CALC key columns must be used in WHERE.
    - FK / FOREIGN / relationship columns must never be used in WHERE.
    - UPDATE is conservative/manual-style, not broad all-column update.
    - DATE-YMD8 style values must be converted to DD.MM.CCYY before moving
      into DB2 DA_/DT_ date host fields.
    - COMMIT and ROLLBACK are retained because IDMS FINISH/COMMIT conversion
      depends on these methods.
    """

    SELECT_EXCLUDE_PREFIXES = (
        "TS_CREATE",
        "TS_UPDATE",
        "ID_USERID",
        "NR_USERID",
    )

    FALLBACK_KEY_PREFIXES = (
        "CT_",
        "NR_",
        "NS_",
        "CO_",
    )

    DATE_COLUMN_PREFIXES = (
        "DA_",
        "DT_",
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
        self.messages: list[str] = []
        self.update_plan_resolver = UpdateSqlPlanResolver(
            mapping_repository=mapping_repository,
            dclgen_repository=dclgen_repository,
            table_name_resolver=table_name_resolver,
            host_variable_resolver=host_variable_resolver,
        )

    def select_by_key(
        self,
        record_name: str,
    ) -> list[str]:
        """
        Convert OBTAIN CALC for update flow.

        Feedback rule:
        - SELECT before UPDATE is not required.
        - Direct UPDATE using composite-key WHERE is enough.
        - We still remove the original IDMS executable statement safely by
          generating a DB2 comment and CONTINUE.
        """
        self.messages = []

        record = NameNormalizer.normalize(record_name)

        return [
            f"*DB2: Removed OBTAIN CALC SELECT for {NameNormalizer.to_cobol(record)}.",
            "*DB2: Direct UPDATE will use mapped composite key WHERE clause.",
            "CONTINUE.",
        ]

    def insert(
        self,
        record_name: str,
    ) -> list[str]:
        """
        Generate INSERT for STORE conversion.

        Existing STORE behavior is retained, with insert-only audit exclusions.
        """
        self.messages = []

        record = NameNormalizer.normalize(record_name)
        table = self._resolved_table_for_record(record)

        if not record or not table:
            return self._missing_sql(
                operation="INSERT",
                record_name=record_name,
                reason="missing Sheet Mapping or DCLGEN table metadata",
            )

        columns = self._insert_columns_for_record(
            record_name=record,
            table_name=table,
        )

        if not columns:
            return self._missing_sql(
                operation="INSERT",
                record_name=record,
                reason="missing insert columns",
            )

        host_variables = self.host_variable_resolver.host_references_for_columns(
            table_name=table,
            columns=columns,
        )

        if not host_variables:
            return self._missing_sql(
                operation="INSERT",
                record_name=record,
                reason="missing INSERT host variables in DCLGEN",
            )

        lines: list[str] = [
            f"*DB2: Converted STORE for {NameNormalizer.to_cobol(record)}.",
            f"MOVE 'INSERT-{NameNormalizer.to_cobol(record)}' TO SQL-LOCATION.",
            "EXEC SQL",
            f"   INSERT INTO {table}",
            "      (",
        ]

        lines.extend(self._sql_column_list(columns, indent="       "))
        lines.extend(
            [
                "      )",
                "   VALUES",
                "      (",
            ]
        )
        lines.extend(self._host_variable_list(host_variables, indent="       "))
        lines.extend(
            [
                "      )",
                "END-EXEC.",
                "IF SQLCODE NOT = 0",
                "   PERFORM SQLERROR",
                "END-IF.",
            ]
        )

        return lines

    def update(
        self,
        record_name: str,
        changed_source_fields: list[str] | None = None,
    ) -> list[str]:
        """
        Generate conservative/manual-style UPDATE.

        Feedback fixes:
        - Updates only changed fields resolved through Sheet Mapping.
        - Adds update audit fields only if present in Sheet Mapping and DCLGEN.
        - Uses all composite PK / CALC key fields in WHERE.
        - Never uses FK / FOREIGN / relationship fields in WHERE.
        """
        self.messages = []

        record = NameNormalizer.normalize(record_name)
        plan = self.update_plan_resolver.resolve(
            record_name=record,
            changed_source_fields=changed_source_fields or [],
        )

        self.messages.extend(plan.diagnostics)

        if plan.table_name:
            plan.key_columns = self._key_columns_for_record(
                record_name=record,
                table_name=plan.table_name,
            )

        if not plan.is_complete:
            return self._missing_sql(
                operation="UPDATE",
                record_name=record,
                reason="incomplete conservative UPDATE metadata",
            )

        set_lines = self._set_lines(
            table_name=plan.table_name,
            columns=plan.update_columns,
            indent="      ",
        )

        where_lines = self._where_lines(
            table_name=plan.table_name,
            key_columns=plan.key_columns,
            indent="      ",
        )

        if not set_lines or not where_lines:
            return self._missing_sql(
                operation="UPDATE",
                record_name=record,
                reason="missing SET or WHERE host variables in DCLGEN",
            )

        lines: list[str] = [
            f"*DB2: Converted MODIFY for {NameNormalizer.to_cobol(record)}.",
            f"MOVE 'UPDATE-{NameNormalizer.to_cobol(record)}' TO SQL-LOCATION.",
            "EXEC SQL",
            f"   UPDATE {plan.table_name}",
            "   SET",
        ]

        lines.extend(set_lines)
        lines.append("   WHERE")
        lines.extend(where_lines)
        lines.extend(
            [
                "END-EXEC.",
                "IF SQLCODE NOT = 0",
                "   PERFORM SQLERROR",
                "END-IF.",
            ]
        )

        return lines

    def delete(
        self,
        record_name: str,
    ) -> list[str]:
        """
        Generate DELETE for ERASE conversion.

        Uses the same composite-key-only WHERE rule:
        - Include all PK / CALC key fields.
        - Exclude FK / FOREIGN / relationship fields.
        """
        self.messages = []

        record = NameNormalizer.normalize(record_name)
        table = self._resolved_table_for_record(record)

        if not record or not table:
            return self._missing_sql(
                operation="DELETE",
                record_name=record_name,
                reason="missing Sheet Mapping or DCLGEN table metadata",
            )

        key_columns = self._key_columns_for_record(
            record_name=record,
            table_name=table,
        )

        where_lines = self._where_lines(
            table_name=table,
            key_columns=key_columns,
            indent="      ",
        )

        if not where_lines:
            return self._missing_sql(
                operation="DELETE",
                record_name=record,
                reason="missing DELETE key host variables in DCLGEN",
            )

        lines: list[str] = [
            f"*DB2: Converted ERASE for {NameNormalizer.to_cobol(record)}.",
            f"MOVE 'DELETE-{NameNormalizer.to_cobol(record)}' TO SQL-LOCATION.",
            "EXEC SQL",
            f"   DELETE FROM {table}",
            "   WHERE",
        ]

        lines.extend(where_lines)
        lines.extend(
            [
                "END-EXEC.",
                "IF SQLCODE NOT = 0",
                "   PERFORM SQLERROR",
                "END-IF.",
            ]
        )

        return lines

    def commit(
        self,
    ) -> list[str]:
        """
        Generate DB2 COMMIT.

        Required by IdmsStatementTransformer for:
        - FINISH
        - COMMIT outside EXEC SQL
        """
        return [
            "MOVE 'COMMIT' TO SQL-LOCATION.",
            "EXEC SQL",
            "   COMMIT",
            "END-EXEC.",
        ]

    def rollback(
        self,
    ) -> list[str]:
        """
        Generate DB2 ROLLBACK.

        Retained for compatibility and future IDMS/DB2 rollback conversion.
        """
        return [
            "MOVE 'ROLLBACK' TO SQL-LOCATION.",
            "EXEC SQL",
            "   ROLLBACK",
            "END-EXEC.",
        ]

    def changed_field_move(
        self,
        record_name: str,
        source_value: str,
        target_source_field: str,
    ) -> list[str]:
        """
        Generate a MOVE to a resolved DCLGEN host field.

        Feedback fix:
        - If target DB2 column is a date column, do not move DATE-YMD8 directly.
        - Convert CCYYMMDD to DD.MM.CCYY before moving to DB2 date host field.

        Example:
        - DATE-YMD8 contains 20260820
        - DB2 host receives 20.08.2026
        """
        record = NameNormalizer.normalize(record_name)
        table = self._resolved_table_for_record(record)
        column = self.mapping_repository.column_for_source_field(
            record_name=record,
            source_field_name=target_source_field,
        )
        column = NameNormalizer.normalize(column)

        if not table or not column:
            return [
                f"*DB2: Conversion skipped for MOVE target {target_source_field}.",
                "*DB2: Missing Sheet Mapping or DCLGEN metadata.",
                "CONTINUE.",
            ]

        host_key = self.host_variable_resolver.host_reference_key(
            table_name=table,
            column_name=column,
        )

        if not host_key:
            return [
                f"*DB2: Conversion skipped for MOVE target {target_source_field}.",
                "*DB2: Missing DCLGEN host variable.",
                "CONTINUE.",
            ]

        if self._is_db2_date_column(column):
            return self._date_ymd8_to_db2_external_move(
                source_value=source_value,
                host_key=host_key,
            )

        return [
            f"MOVE {source_value} TO {host_key}",
        ]

    def missing_mapping(
        self,
        record_name: str,
        reason: str,
    ) -> list[str]:
        """
        Backward-compatible alias for older callers/tests.
        """
        return self._missing_sql(
            operation="DB2",
            record_name=record_name,
            reason=reason,
        )

    def _resolved_table_for_record(
        self,
        record_name: str,
    ) -> str:
        mapped_table = self.mapping_repository.db2_table_for_record(record_name)

        if not mapped_table:
            return ""

        return self.table_name_resolver.resolve_table(mapped_table)

    def _key_columns_for_record(
        self,
        record_name: str,
        table_name: str,
    ) -> list[str]:
        """
        Return key columns for SQL WHERE clauses.

        Feedback rule:
        - If key is composite, all PK / CALC key columns are required.
        - FK / FOREIGN / relationship columns must never be included.
        - Preserve Sheet Mapping order.
        - Do not use broad fallback prefix columns.
        """
        columns: list[str] = []

        if hasattr(self.mapping_repository, "rows_for_record"):
            columns = self._key_columns_from_mapping_rows(record_name)

        if not columns and hasattr(
            self.mapping_repository,
            "primary_key_columns_for_record",
        ):
            columns = self.mapping_repository.primary_key_columns_for_record(record_name)

        return self._filter_to_existing_dclgen_columns(
            table_name=table_name,
            columns=columns,
        )

    def _key_columns_from_mapping_rows(
        self,
        record_name: str,
    ) -> list[str]:
        """
        Read Sheet Mapping rows directly to avoid old repository behavior that
        may return only one primary key or may include FK fields.

        Include:
        - DB2 PRIMARY / PRIMARY KEY / KEY
        - IDMS CALC / KEY metadata

        Exclude:
        - DB2 FOREIGN KEY
        - relation FOREIGN
        - FK markers
        """
        output: list[str] = []
        seen: set[str] = set()

        for row in self.mapping_repository.rows_for_record(record_name):
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

        return output

    def _minimal_select_columns(
        self,
        record_name: str,
        table_name: str,
        key_columns: list[str],
    ) -> list[str]:
        """
        Minimal SELECT fallback.

        SELECT is no longer required for update flow, but if any older caller
        still invokes this path, keep it key-only and FK-free.
        """
        return self._filter_to_existing_dclgen_columns(
            table_name=table_name,
            columns=key_columns,
        )

    def _insert_columns_for_record(
        self,
        record_name: str,
        table_name: str,
    ) -> list[str]:
        columns = self.mapping_repository.db2_columns_for_table(table_name)
        columns = [
            column
            for column in columns
            if not self._is_insert_excluded_audit_column(column)
        ]

        return self._filter_to_existing_dclgen_columns(table_name, columns)

    def _filter_to_existing_dclgen_columns(
        self,
        table_name: str,
        columns: list[str],
    ) -> list[str]:
        resolved_table = self.table_name_resolver.resolve_table(table_name)

        if not resolved_table:
            return []

        dclgen_columns = set(
            self.dclgen_repository.column_names_for_table(resolved_table)
        )

        if not dclgen_columns:
            return []

        output: list[str] = []

        for column in columns:
            normalized = NameNormalizer.normalize(column)

            if not normalized:
                continue

            if normalized not in dclgen_columns:
                continue

            output.append(normalized)

        return self._unique(output)

    def _set_lines(
        self,
        table_name: str,
        columns: list[str],
        indent: str,
    ) -> list[str]:
        assignments: list[tuple[str, str]] = []

        for column in columns:
            normalized = NameNormalizer.normalize(column)

            if not normalized:
                continue

            host = self.host_variable_resolver.host_reference_for_column(
                table_name=table_name,
                column_name=normalized,
            )

            if not host:
                continue

            assignments.append((normalized, host))

        output: list[str] = []

        for index, item in enumerate(assignments):
            column, host = item
            suffix = "," if index < len(assignments) - 1 else ""
            output.append(f"{indent}{column} = {host}{suffix}")

        return output

    def _where_lines(
        self,
        table_name: str,
        key_columns: list[str],
        indent: str,
    ) -> list[str]:
        """
        Build SQL WHERE lines from composite key columns.

        The caller must pass only PK / CALC key columns.
        FK exclusion is handled in _key_columns_for_record().
        """
        conditions: list[tuple[str, str]] = []

        for column in key_columns:
            normalized = NameNormalizer.normalize(column)

            if not normalized:
                continue

            host = self.host_variable_resolver.host_reference_for_column(
                table_name=table_name,
                column_name=normalized,
            )

            if not host:
                continue

            conditions.append((normalized, host))

        output: list[str] = []

        for index, item in enumerate(conditions):
            column, host = item
            prefix = "" if index == 0 else "AND "
            output.append(f"{indent}{prefix}{column} = {host}")

        return output

    def _sql_column_list(
        self,
        columns: list[str],
        indent: str,
    ) -> list[str]:
        output: list[str] = []

        for index, column in enumerate(columns):
            suffix = "," if index < len(columns) - 1 else ""
            output.append(f"{indent}{column}{suffix}")

        return output

    def _host_variable_list(
        self,
        host_variables: list[str],
        indent: str,
    ) -> list[str]:
        output: list[str] = []

        for index, host in enumerate(host_variables):
            suffix = "," if index < len(host_variables) - 1 else ""
            output.append(f"{indent}{host}{suffix}")

        return output

    def _missing_sql(
        self,
        operation: str,
        record_name: str,
        reason: str,
    ) -> list[str]:
        record = NameNormalizer.to_cobol(record_name)

        return [
            f"*DB2: {operation} conversion skipped for {record}.",
            f"*DB2: {reason}.",
            "CONTINUE.",
        ]

    def _is_insert_excluded_audit_column(
        self,
        column_name: str,
    ) -> bool:
        column = NameNormalizer.normalize(column_name)

        return any(
            column.startswith(prefix)
            for prefix in INSERT_EXCLUDE_AUDIT_PREFIXES
        )

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

        if not source:
            return [
                "MOVE SPACES TO DA-DD-MM-CCYY",
                f"MOVE DA-DD-MM-CCYY TO {host_key}",
            ]

        return [
            "MOVE ZEROES TO DA-CCYYMMDD",
            f"MOVE {source} TO DA-CCYYMMDD",
            "MOVE CORR DA-CCYYMMDD-R TO DA-DD-MM-CCYY",
            f"MOVE DA-DD-MM-CCYY TO {host_key}",
        ]

    def _unique(
        self,
        values: list[str],
    ) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()

        for value in values:
            normalized = NameNormalizer.normalize(value)

            if not normalized:
                continue

            if normalized in seen:
                continue

            seen.add(normalized)
            output.append(normalized)

        return output