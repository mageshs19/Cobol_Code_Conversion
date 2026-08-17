from dataclasses import dataclass

from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.host_variable_resolver import HostVariableResolver
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
from idms_db2_phase2.services.name_normalizer import NameNormalizer


@dataclass
class RelationshipCondition:
    child_record: str
    child_table: str
    child_column: str
    parent_record: str
    parent_table: str
    parent_column: str
    parent_host_reference: str


@dataclass
class RelationshipResolution:
    child_record: str
    parent_record: str = ""
    child_table: str = ""
    parent_table: str = ""
    conditions: list[RelationshipCondition] = None
    diagnostics: list[str] = None

    def __post_init__(self) -> None:
        if self.conditions is None:
            self.conditions = []
        if self.diagnostics is None:
            self.diagnostics = []


class RelationshipResolver:
    """
    Resolves parent-child DB2 relationships using Sheet Mapping metadata.

    Generic rule:
    - Child FK columns come from rows marked FOREIGN KEY.
    - Parent columns are resolved by matching those FK columns against
      another record's primary key columns.
    - If Cross Application DB2 table/field is present, it is preferred.
    """

    def __init__(
        self,
        mapping_repository: MappingRepository,
        table_name_resolver: TableNameResolver,
        host_variable_resolver: HostVariableResolver,
    ) -> None:
        self.mapping_repository = mapping_repository
        self.table_name_resolver = table_name_resolver
        self.host_variable_resolver = host_variable_resolver

    def resolve_for_child_record(
        self,
        child_record: str,
    ) -> RelationshipResolution:
        child = NameNormalizer.normalize(child_record)
        result = RelationshipResolution(child_record=child)

        if not child:
            result.diagnostics.append("Relationship resolver: child record is empty.")
            return result

        child_table = self.table_name_resolver.table_for_record(child)
        result.child_table = child_table

        rows = self.mapping_repository.rows_for_record(child)

        fk_rows = [
            row
            for row in rows
            if self._is_foreign_key_row(row)
        ]

        if not fk_rows:
            result.diagnostics.append(
                f"Relationship resolver: no foreign-key rows for child record {child}."
            )
            return result

        parent_record = self._infer_parent_record(
            child_record=child,
            fk_rows=fk_rows,
        )

        parent_table = ""

        if parent_record:
            parent_table = self.table_name_resolver.table_for_record(parent_record)

        result.parent_record = parent_record
        result.parent_table = parent_table

        for row in fk_rows:
            child_column = NameNormalizer.normalize(
                getattr(row, "new_db2_field_name", "")
                or getattr(row, "cross_application_db2_field_name", "")
            )

            if not child_column:
                continue

            explicit_parent_table = self.table_name_resolver.resolve_table(
                getattr(row, "cross_application_db2_table", "")
            )

            explicit_parent_column = NameNormalizer.normalize(
                getattr(row, "cross_application_db2_field_name", "")
            )

            effective_parent_table = explicit_parent_table or parent_table
            effective_parent_column = explicit_parent_column or child_column

            if not effective_parent_table:
                effective_parent_table = self._find_parent_table_by_column(
                    child_record=child,
                    child_column=child_column,
                )

            if not effective_parent_table:
                result.diagnostics.append(
                    f"Relationship resolver: no parent table found for {child}.{child_column}."
                )
                continue

            if not parent_record:
                parent_record = self._record_for_table(effective_parent_table)
                result.parent_record = parent_record

            if not result.parent_table:
                result.parent_table = effective_parent_table

            parent_host = self.host_variable_resolver.host_reference_for_column(
                table_name=effective_parent_table,
                column_name=effective_parent_column,
            )

            if not parent_host:
                result.diagnostics.append(
                    "Relationship resolver: missing parent host for "
                    f"child={child}, child_column={child_column}, "
                    f"parent_table={effective_parent_table}, "
                    f"parent_column={effective_parent_column}."
                )
                continue

            result.conditions.append(
                RelationshipCondition(
                    child_record=child,
                    child_table=child_table,
                    child_column=child_column,
                    parent_record=parent_record,
                    parent_table=effective_parent_table,
                    parent_column=effective_parent_column,
                    parent_host_reference=parent_host,
                )
            )

        result.diagnostics.append(
            "Relationship resolver: "
            f"child={child}, parent={result.parent_record}, "
            f"conditions={len(result.conditions)}"
        )

        return result

    def foreign_key_columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        record = NameNormalizer.normalize(record_name)
        rows = self.mapping_repository.rows_for_record(record)
        output: list[str] = []
        seen: set[str] = set()

        for row in rows:
            if not self._is_foreign_key_row(row):
                continue

            column = NameNormalizer.normalize(
                getattr(row, "new_db2_field_name", "")
                or getattr(row, "cross_application_db2_field_name", "")
            )

            if not column or column in seen:
                continue

            seen.add(column)
            output.append(column)

        return output

    def primary_key_columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        record = NameNormalizer.normalize(record_name)
        rows = self.mapping_repository.rows_for_record(record)
        output: list[str] = []
        seen: set[str] = set()

        for row in rows:
            if not self._is_primary_key_row(row):
                continue

            column = NameNormalizer.normalize(
                getattr(row, "new_db2_field_name", "")
            )

            if not column or column in seen:
                continue

            seen.add(column)
            output.append(column)

        return output

    def parent_key_columns_required_by_children(
        self,
        parent_record: str,
    ) -> list[str]:
        parent = NameNormalizer.normalize(parent_record)
        output: list[str] = []
        seen: set[str] = set()

        for child in self.mapping_repository.records():
            child = NameNormalizer.normalize(child)

            if child == parent:
                continue

            relation = self.resolve_for_child_record(child)

            if relation.parent_record != parent:
                continue

            for condition in relation.conditions:
                column = NameNormalizer.normalize(condition.parent_column)

                if not column or column in seen:
                    continue

                seen.add(column)
                output.append(column)

        return output

    def order_by_columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        record = NameNormalizer.normalize(record_name)
        primary_keys = self.primary_key_columns_for_record(record)
        foreign_keys = set(self.foreign_key_columns_for_record(record))
        output: list[str] = []

        for column in primary_keys:
            normalized = NameNormalizer.normalize(column)

            if not normalized:
                continue

            if normalized in foreign_keys:
                continue

            if normalized not in output:
                output.append(normalized)

        return output

    def has_foreign_keys(
        self,
        record_name: str,
    ) -> bool:
        return bool(self.foreign_key_columns_for_record(record_name))

    def _is_primary_key_row(
        self,
        row,
    ) -> bool:
        db2_key = NameNormalizer.normalize(getattr(row, "db2_key", ""))
        idms_key = NameNormalizer.normalize(getattr(row, "idms_key", ""))

        return (
            "PRIMARY" in db2_key
            or db2_key == "KEY"
            or "CALC" in idms_key
        )

    def _is_foreign_key_row(
        self,
        row,
    ) -> bool:
        db2_key = NameNormalizer.normalize(getattr(row, "db2_key", ""))
        relation = NameNormalizer.normalize(getattr(row, "relation", ""))

        return (
            "FOREIGN" in db2_key
            or "FK" in db2_key
            or "FOREIGN" in relation
        )

    def _infer_parent_record(
        self,
        child_record: str,
        fk_rows: list,
    ) -> str:
        for row in fk_rows:
            parent_table = self.table_name_resolver.resolve_table(
                getattr(row, "cross_application_db2_table", "")
            )

            if parent_table:
                record = self._record_for_table(parent_table)
                if record:
                    return record

        best_record = ""
        best_count = 0

        for record in self.mapping_repository.records():
            record = NameNormalizer.normalize(record)

            if record == child_record:
                continue

            parent_keys = set(self.primary_key_columns_for_record(record))

            if not parent_keys:
                continue

            child_fk_columns = {
                NameNormalizer.normalize(
                    getattr(row, "new_db2_field_name", "")
                    or getattr(row, "cross_application_db2_field_name", "")
                )
                for row in fk_rows
            }

            match_count = len(parent_keys.intersection(child_fk_columns))

            if match_count > best_count:
                best_count = match_count
                best_record = record

        return best_record

    def _find_parent_table_by_column(
        self,
        child_record: str,
        child_column: str,
    ) -> str:
        column = NameNormalizer.normalize(child_column)

        if not column:
            return ""

        child_table = self.table_name_resolver.table_for_record(child_record)

        for record in self.mapping_repository.records():
            normalized_record = NameNormalizer.normalize(record)

            if normalized_record == child_record:
                continue

            table = self.table_name_resolver.table_for_record(normalized_record)

            if not table:
                continue

            if table == child_table:
                continue

            if column in self.primary_key_columns_for_record(normalized_record):
                return table

        return ""

    def _record_for_table(
        self,
        table_name: str,
    ) -> str:
        table = self.table_name_resolver.resolve_table(table_name)

        if not table:
            return ""

        for record in self.mapping_repository.records():
            record_table = self.table_name_resolver.table_for_record(record)

            if record_table == table:
                return NameNormalizer.normalize(record)

        return ""