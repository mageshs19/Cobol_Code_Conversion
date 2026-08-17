import re

from catalogs.output_sections import (
    DB2_CURSOR_DECLARATIONS_MARKER,
    DB2_CURSOR_FLAGS_MARKER,
    DB2_INFRASTRUCTURE_MARKER,
    DB2_SQL_ERROR_LOCATION_MARKER,
    SQL_LOCATION_FIELD_NAME,
    SQL_LOCATION_PICTURE,
    SQLCA_INCLUDE_NAME,
    SQLERRWS_INCLUDE_NAME,
)
from idms_db2_phase2.analyzers.field_usage_analyzer import FieldUsageAnalyzer
from idms_db2_phase2.domain.models import IdmsOperation
from idms_db2_phase2.resolvers.column_name_resolver import ColumnNameResolver
from idms_db2_phase2.resolvers.cursor_column_resolver import CursorColumnResolver
from idms_db2_phase2.resolvers.cursor_name_resolver import CursorNameResolver
from idms_db2_phase2.resolvers.host_variable_resolver import HostVariableResolver
from idms_db2_phase2.resolvers.relationship_resolver import RelationshipResolver
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
from idms_db2_phase2.services.name_normalizer import NameNormalizer


class Db2InfrastructureGenerator:
    """
    Generates DB2 infrastructure in DATA DIVISION.

    Generic behavior:
    - Include SQLERRWS and SQLCA.
    - Include DCLGEN views/tables actually used by cursor specs.
    - Generate SQL-LOCATION.
    - Generate cursor EOC flags.
    - Generate cursor declarations using WITH HOLD.
    - Reduce SELECT columns using actual field usage and relationship keys.
    - Generate child cursor WHERE from FK mapping.
    - Generate child cursor ORDER BY from non-FK primary/order key.
    - Do not generate parent/root ORDER BY unless explicitly required.
    - Add FOR READ ONLY.
    - Initialize generated DCLGEN groups in PROCEDURE DIVISION.
    """

    CURSOR_OPERATIONS = {
        "OBTAIN_FIRST",
        "OBTAIN_NEXT",
        "FIND_FIRST",
    }

    PROCEDURE_DIVISION_PATTERN = re.compile(
        r"^\s*(?:\d{6}\s+)?PROCEDURE\s+DIVISION\b.*\.?\s*(?:\d{8})?\s*$",
        flags=re.IGNORECASE | re.MULTILINE,
    )

    LINKAGE_SECTION_PATTERN = re.compile(
        r"^\s*(?:\d{6}\s+)?LINKAGE\s+SECTION\.\s*(?:\d{8})?\s*$",
        flags=re.IGNORECASE | re.MULTILINE,
    )

    WORKING_STORAGE_PATTERN = re.compile(
        r"^\s*(?:\d{6}\s+)?WORKING-STORAGE\s+SECTION\.\s*(?:\d{8})?\s*$",
        flags=re.IGNORECASE | re.MULTILINE,
    )

    DATA_DIVISION_PATTERN = re.compile(
        r"^\s*(?:\d{6}\s+)?DATA\s+DIVISION\.\s*(?:\d{8})?\s*$",
        flags=re.IGNORECASE | re.MULTILINE,
    )

    def __init__(
        self,
        table_name_resolver: TableNameResolver,
        column_name_resolver: ColumnNameResolver,
        host_variable_resolver: HostVariableResolver,
        cursor_name_resolver: CursorNameResolver,
    ) -> None:
        self.table_name_resolver = table_name_resolver
        self.column_name_resolver = column_name_resolver
        self.host_variable_resolver = host_variable_resolver
        self.cursor_name_resolver = cursor_name_resolver

        self.mapping_repository = table_name_resolver.mapping_repository

        self.relationship_resolver = RelationshipResolver(
            mapping_repository=self.mapping_repository,
            table_name_resolver=self.table_name_resolver,
            host_variable_resolver=self.host_variable_resolver,
        )

        self.cursor_column_resolver = CursorColumnResolver(
            mapping_repository=self.mapping_repository,
            table_name_resolver=self.table_name_resolver,
            column_name_resolver=self.column_name_resolver,
            relationship_resolver=self.relationship_resolver,
        )

        self.last_cursor_specs: list[dict[str, object]] = []

    def apply(
        self,
        cobol_text: str,
        operations: list[IdmsOperation],
    ) -> tuple[str, list[str]]:
        messages: list[str] = []
        text = str(cobol_text or "")

        if not text:
            self.last_cursor_specs = []
            return text, messages

        field_usage_analysis = FieldUsageAnalyzer(
            mapping_repository=self.mapping_repository,
            table_name_resolver=self.table_name_resolver,
        ).analyze(text)

        messages.extend(field_usage_analysis.diagnostics)

        cursor_specs = self.cursor_specs(
            operations=operations,
            cobol_text=text,
            field_usage_analysis=field_usage_analysis,
        )

        self.last_cursor_specs = cursor_specs

        include_names = self.include_names(cursor_specs)

        if include_names:
            messages.append(
                "DB2 infrastructure: DCLGEN includes selected: "
                + ", ".join(include_names)
            )
        else:
            messages.append(
                "DB2 infrastructure: no operation-specific DCLGEN includes resolved."
            )

        for message in self._cursor_spec_messages(cursor_specs):
            messages.append(message)

        if DB2_INFRASTRUCTURE_MARKER in text:
            messages.append(
                "DB2 infrastructure: existing generated DB2 infrastructure block detected; not inserted again."
            )
            updated = text
        else:
            block = self.infrastructure_block(
                include_names=include_names,
                cursor_specs=cursor_specs,
            )

            updated = self._insert_in_data_division(
                text=text,
                block=block,
            )

            messages.append(
                "DB2 infrastructure: generated infrastructure block inserted."
            )

        updated = self._ensure_dclgen_initialization(
            text=updated,
            include_names=include_names,
        )

        return updated, messages

    def cursor_specs(
        self,
        operations: list[IdmsOperation],
        cobol_text: str = "",
        field_usage_analysis=None,
    ) -> list[dict[str, object]]:
        output: list[dict[str, object]] = []
        seen: set[tuple[str, str, str]] = set()
        cursor_order = 1

        if field_usage_analysis is None:
            field_usage_analysis = FieldUsageAnalyzer(
                mapping_repository=self.mapping_repository,
                table_name_resolver=self.table_name_resolver,
            ).analyze(cobol_text)

        for operation in operations or []:
            operation_name = str(operation.operation or "").upper()

            if operation_name not in self.CURSOR_OPERATIONS:
                continue

            record_name = NameNormalizer.normalize(operation.record_name)
            set_name = NameNormalizer.normalize(operation.set_name)

            if not record_name:
                continue

            table_name = self.table_name_resolver.table_for_record(record_name)

            if not table_name:
                continue

            key = (
                set_name,
                record_name,
                table_name,
            )

            if key in seen:
                continue

            seen.add(key)

            cursor_name = self.cursor_name_resolver.cursor_name_from_table(
                table_name
            )

            paragraph_spec = self._cursor_paragraph_spec(
                cursor_order=cursor_order,
                table_name=table_name,
            )

            select_columns = self.cursor_column_resolver.select_columns_for_record(
                record_name=record_name,
                field_usage_analysis=field_usage_analysis,
            )

            relationship = self.relationship_resolver.resolve_for_child_record(
                record_name
            )

            where_conditions = self._where_conditions_from_relationship(
                relationship.conditions
            )

            order_by_columns = self.cursor_column_resolver.order_by_columns_for_record(
                record_name
            )

            host_variables = self.host_variable_resolver.host_references_for_columns(
                table_name=table_name,
                columns=select_columns,
            )

            output.append(
                {
                    "set_name": set_name,
                    "record_name": record_name,
                    "table_name": table_name,
                    "cursor_name": cursor_name,
                    "select_columns": select_columns,
                    "host_variables": host_variables,
                    "where_conditions": where_conditions,
                    "order_by_columns": order_by_columns,
                    "open_paragraph": paragraph_spec["open_paragraph"],
                    "fetch_paragraph": paragraph_spec["fetch_paragraph"],
                    "close_paragraph": paragraph_spec["close_paragraph"],
                    "cursor_order": cursor_order,
                }
            )

            cursor_order += 1

        return output

    def include_names(
        self,
        cursor_specs: list[dict[str, object]],
    ) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()

        for spec in cursor_specs or []:
            table_name = NameNormalizer.normalize(
                str(spec.get("table_name", ""))
            )

            if not table_name:
                continue

            include_name = self._normalize_include_name(table_name)

            if not include_name:
                continue

            if include_name in seen:
                continue

            seen.add(include_name)
            output.append(include_name)

        return output

    def infrastructure_block(
        self,
        include_names: list[str],
        cursor_specs: list[dict[str, object]],
    ) -> str:
        lines: list[str] = []

        lines.extend(
            self._comment_block(DB2_INFRASTRUCTURE_MARKER)
        )

        lines.extend(
            self._include_lines(
                include_names=[
                    SQLERRWS_INCLUDE_NAME,
                    SQLCA_INCLUDE_NAME,
                    *include_names,
                ]
            )
        )

        lines.append("")

        lines.extend(
            self._comment_block(DB2_SQL_ERROR_LOCATION_MARKER)
        )

        lines.append(
            f"01  {SQL_LOCATION_FIELD_NAME:<30} {SQL_LOCATION_PICTURE}"
        )

        if cursor_specs:
            lines.append("")
            lines.extend(
                self._comment_block(DB2_CURSOR_FLAGS_MARKER)
            )

            for spec in cursor_specs:
                cursor_name = str(spec.get("cursor_name", ""))
                flag_name = f"WS-{cursor_name}-FLAG"
                not_eoc_name = f"{cursor_name}-NOT-EOC"
                eoc_name = f"{cursor_name}-EOC"

                lines.append(
                    f"01  {flag_name:<30} PIC X VALUE 'N'."
                )
                lines.append(
                    f"    88  {not_eoc_name:<26} VALUE 'N'."
                )
                lines.append(
                    f"    88  {eoc_name:<26} VALUE 'Y'."
                )

            lines.append("")
            lines.extend(
                self._comment_block(DB2_CURSOR_DECLARATIONS_MARKER)
            )

            for spec in cursor_specs:
                lines.extend(
                    self._cursor_declaration(spec)
                )
                lines.append("")

        return "\n".join(lines).rstrip() + "\n"

    def _cursor_declaration(
        self,
        spec: dict[str, object],
    ) -> list[str]:
        cursor_name = str(spec.get("cursor_name", ""))
        table_name = NameNormalizer.normalize(
            str(spec.get("table_name", ""))
        )

        select_columns = [
            NameNormalizer.normalize(str(column))
            for column in list(spec.get("select_columns", []))
            if NameNormalizer.normalize(str(column))
        ]

        where_conditions = [
            str(condition or "").strip()
            for condition in list(spec.get("where_conditions", []))
            if str(condition or "").strip()
        ]

        order_by_columns = [
            str(column or "").strip()
            for column in list(spec.get("order_by_columns", []))
            if str(column or "").strip()
        ]

        if not cursor_name:
            return [
                "* DB2 WARNING: Unable to declare cursor; missing cursor name."
            ]

        if not table_name:
            return [
                f"* DB2 WARNING: Unable to declare cursor {cursor_name}; missing DB2 table mapping."
            ]

        if not select_columns:
            select_columns = ["*"]

        lines: list[str] = [
            "EXEC SQL",
            f"    DECLARE {cursor_name} CURSOR WITH HOLD FOR",
            "    SELECT",
        ]

        lines.extend(
            self._select_lines(
                columns=select_columns,
            )
        )

        lines.append(
            f"    FROM {table_name}"
        )

        if where_conditions:
            lines.append("    WHERE")
            lines.extend(
                self._and_lines(
                    items=where_conditions,
                    indent="       ",
                )
            )

        if order_by_columns:
            lines.append("    ORDER BY")
            lines.extend(
                self._comma_lines(
                    items=order_by_columns,
                    indent="       ",
                )
            )

        lines.append("    FOR READ ONLY")
        lines.append("END-EXEC.")

        return lines

    def _where_conditions_from_relationship(
        self,
        conditions,
    ) -> list[str]:
        output: list[str] = []

        for condition in conditions or []:
            child_column = NameNormalizer.normalize(condition.child_column)
            parent_host = str(condition.parent_host_reference or "").strip()

            if not child_column or not parent_host:
                continue

            output.append(
                f"{child_column} = {parent_host}"
            )

        return output

    def _select_lines(
        self,
        columns: list[str],
    ) -> list[str]:
        clean_columns = [
            NameNormalizer.normalize(column)
            for column in columns
            if NameNormalizer.normalize(column)
        ]

        output: list[str] = []

        for index, column in enumerate(clean_columns):
            if index == 0:
                output.append(f"        {column}")
            else:
                output.append(f"       , {column}")

        return output

    def _include_lines(
        self,
        include_names: list[str],
    ) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()

        for include_name in include_names:
            normalized = self._normalize_include_name(include_name)

            if not normalized:
                continue

            if normalized in seen:
                continue

            seen.add(normalized)

            output.extend(
                [
                    "EXEC SQL",
                    f"    INCLUDE {normalized}",
                    "END-EXEC.",
                ]
            )

        return output

    def _ensure_dclgen_initialization(
        self,
        text: str,
        include_names: list[str],
    ) -> str:
        clean_include_names = [
            self._normalize_include_name(include_name)
            for include_name in include_names
            if self._normalize_include_name(include_name)
        ]

        if not clean_include_names:
            return text

        missing_initializes = []

        for include_name in clean_include_names:
            group_name = "DCL" + NameNormalizer.to_cobol(include_name)

            if re.search(
                rf"\bINITIALIZE\s+{re.escape(group_name)}\b",
                text,
                flags=re.IGNORECASE,
            ):
                continue

            missing_initializes.append(group_name)

        if not missing_initializes:
            return text

        initialize_lines = [
            "* DB2: Initialize generated DCLGEN host groups."
        ]

        for group_name in missing_initializes:
            initialize_lines.append(
                f"INITIALIZE {group_name}."
            )

        block = "\n".join(initialize_lines)

        return self._insert_after_procedure_division(
            text=text,
            block=block,
        )

    def _insert_after_procedure_division(
        self,
        text: str,
        block: str,
    ) -> str:
        lines = str(text or "").splitlines()
        output: list[str] = []
        inserted = False

        for line in lines:
            output.append(line)

            if inserted:
                continue

            logical = self._logical_line(line)

            if self.PROCEDURE_DIVISION_PATTERN.match(logical):
                output.append(block)
                inserted = True

        if inserted:
            return "\n".join(output).rstrip() + "\n"

        return str(text or "").rstrip() + "\n\n" + block + "\n"

    def _insert_in_data_division(
        self,
        text: str,
        block: str,
    ) -> str:
        for pattern in [
            self.LINKAGE_SECTION_PATTERN,
            self.PROCEDURE_DIVISION_PATTERN,
        ]:
            match = pattern.search(text)

            if match:
                return (
                    text[: match.start()].rstrip()
                    + "\n\n"
                    + block.rstrip()
                    + "\n\n"
                    + text[match.start():].lstrip()
                ).rstrip() + "\n"

        working_storage_match = self.WORKING_STORAGE_PATTERN.search(text)

        if working_storage_match:
            return (
                text[: working_storage_match.end()].rstrip()
                + "\n\n"
                + block.rstrip()
                + "\n\n"
                + text[working_storage_match.end():].lstrip()
            ).rstrip() + "\n"

        data_division_match = self.DATA_DIVISION_PATTERN.search(text)

        if data_division_match:
            return (
                text[: data_division_match.end()].rstrip()
                + "\n\n"
                + "WORKING-STORAGE SECTION."
                + "\n\n"
                + block.rstrip()
                + "\n\n"
                + text[data_division_match.end():].lstrip()
            ).rstrip() + "\n"

        return block.rstrip() + "\n\n" + text.rstrip() + "\n"

    def _cursor_paragraph_spec(
        self,
        cursor_order: int,
        table_name: str,
    ) -> dict[str, str]:
        if hasattr(self.cursor_name_resolver, "cursor_spec"):
            return self.cursor_name_resolver.cursor_spec(
                cursor_order=cursor_order,
                table_name=table_name,
            )

        cursor_name = self.cursor_name_resolver.cursor_name_from_table(
            table_name
        )

        base = 710 + ((cursor_order - 1) * 100)

        return {
            "cursor_name": cursor_name,
            "open_paragraph": f"{base}-OPEN-{cursor_name}",
            "fetch_paragraph": f"{base + 10}-FETCH-{cursor_name}",
            "close_paragraph": f"{base + 20}-CLOSE-{cursor_name}",
        }

    def _cursor_spec_messages(
        self,
        cursor_specs: list[dict[str, object]],
    ) -> list[str]:
        messages: list[str] = []

        for spec in cursor_specs:
            cursor_name = str(spec.get("cursor_name", ""))
            record_name = str(spec.get("record_name", ""))
            table_name = str(spec.get("table_name", ""))
            select_columns = list(spec.get("select_columns", []))
            host_variables = list(spec.get("host_variables", []))

            if not table_name:
                messages.append(
                    f"DB2 infrastructure: cursor {cursor_name} has no resolved DB2 table for record {record_name}."
                )

            if not select_columns:
                messages.append(
                    f"DB2 infrastructure: cursor {cursor_name} has no resolved SELECT columns for record {record_name}."
                )

            if not host_variables:
                messages.append(
                    f"DB2 infrastructure: cursor {cursor_name} has no resolved FETCH host variables for record {record_name}."
                )

        return messages

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

    def _comment_block(
        self,
        title: str,
    ) -> list[str]:
        return [
            f"* {title:<62}*",
        ]

    def _normalize_include_name(
        self,
        value: str,
    ) -> str:
        text = NameNormalizer.normalize(value)

        if not text:
            return ""

        return text

    def _logical_line(
        self,
        line: str,
    ) -> str:
        text = str(line or "").rstrip()

        if len(text) >= 80:
            left = text[:6]
            body = text[7:72]

            if left.strip().isdigit():
                return body.strip()

        if len(text) > 6 and text[:6].strip().isdigit():
            return text[6:].strip()

        return text.strip()