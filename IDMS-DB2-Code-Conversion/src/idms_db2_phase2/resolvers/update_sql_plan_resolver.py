from dataclasses import dataclass, field

from idms_db2_phase2.repositories.dclgen_repository import DclgenRepository
from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.host_variable_resolver import HostVariableResolver
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
from idms_db2_phase2.services.name_normalizer import NameNormalizer


@dataclass
class UpdateSqlPlan:
    record_name: str = ""
    table_name: str = ""
    key_columns: list[str] = field(default_factory=list)
    update_columns: list[str] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        return bool(
            self.record_name
            and self.table_name
            and self.key_columns
            and self.update_columns
        )


class UpdateSqlPlanResolver:
    """
    Resolves conservative UPDATE SQL plans.

    Generic rules:
    - Sheet Mapping decides DB2 table and column names.
    - DCLGEN decides whether host variables exist.
    - DB2 PRIMARY KEY metadata decides WHERE columns.
    - Composite primary keys are supported by returning all PK columns.
    - FOREIGN KEY / relationship columns must not be included in WHERE.
    - UPDATE columns come only from changed source fields and update audit fields.
    """

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

    def resolve(
        self,
        record_name: str,
        changed_source_fields: list[str] | None = None,
    ) -> UpdateSqlPlan:
        record = NameNormalizer.normalize(record_name)
        plan = UpdateSqlPlan(record_name=record)

        if not record:
            plan.diagnostics.append("Update SQL plan: record name is empty.")
            return plan

        mapped_table = self.mapping_repository.db2_table_for_record(record)
        resolved_table = self.table_name_resolver.resolve_table(mapped_table)

        if not resolved_table:
            plan.diagnostics.append(
                f"Update SQL plan: no resolved DB2 table for record {record}."
            )
            return plan

        plan.table_name = resolved_table

        key_columns = self._primary_key_columns_for_record(record)
        key_columns = self._filter_to_dclgen_columns(
            table_name=resolved_table,
            columns=key_columns,
        )

        if not key_columns:
            plan.diagnostics.append(
                f"Update SQL plan: no valid primary key columns resolved for record {record}."
            )

        update_columns = self.mapping_repository.update_candidate_columns_for_record(
            record_name=record,
            changed_source_fields=changed_source_fields or [],
        )
        update_columns = self._filter_to_dclgen_columns(
            table_name=resolved_table,
            columns=update_columns,
        )

        if not update_columns:
            plan.diagnostics.append(
                f"Update SQL plan: no conservative update columns resolved for record {record}."
            )

        plan.key_columns = self._unique(key_columns)
        plan.update_columns = self._unique(update_columns)

        return plan

    def _primary_key_columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        """
        Return DB2 primary-key columns only.

        This intentionally does not use key_columns_for_record(), because that
        method can include broader IDMS CALC/key metadata.

        WHERE clause rule:
        - Include PRIMARY / KEY columns.
        - Exclude FOREIGN KEY columns.
        - Exclude relationship columns.
        - If multiple PK columns exist, keep all of them for composite PK WHERE.
        """
        if not hasattr(self.mapping_repository, "primary_key_columns_for_record"):
            return []

        return self.mapping_repository.primary_key_columns_for_record(record_name)

    def _filter_to_dclgen_columns(
        self,
        table_name: str,
        columns: list[str],
    ) -> list[str]:
        dclgen_columns = set(
            self.dclgen_repository.column_names_for_table(table_name)
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

            if not self.host_variable_resolver.has_host_for_column(
                table_name=table_name,
                column_name=normalized,
            ):
                continue

            output.append(normalized)

        return self._unique(output)

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