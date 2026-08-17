from idms_db2_phase2.repositories.dclgen_repository import DclgenRepository
from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
from idms_db2_phase2.services.name_normalizer import NameNormalizer


class ColumnNameResolver:
    """
    Resolves DB2 column names.

    Authority:
    - Sheet Mapping provides DB2 column names.
    - DCLGEN validates whether a column exists for the resolved table.
    """

    def __init__(
        self,
        mapping_repository: MappingRepository,
        dclgen_repository: DclgenRepository,
        table_name_resolver: TableNameResolver,
    ) -> None:
        self.mapping_repository = mapping_repository
        self.dclgen_repository = dclgen_repository
        self.table_name_resolver = table_name_resolver

    def columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        table_name = self.table_name_resolver.table_for_record(record_name)

        if not table_name:
            return []

        mapped_columns = self.mapping_repository.db2_columns_for_table(table_name)

        if not mapped_columns:
            mapped_table = self.mapping_repository.db2_table_for_record(record_name)
            mapped_columns = self.mapping_repository.db2_columns_for_table(mapped_table)

        return self._filter_to_existing_dclgen_columns(
            table_name=table_name,
            columns=mapped_columns,
        )

    def columns_for_table(
        self,
        table_name: str,
    ) -> list[str]:
        resolved_table = self.table_name_resolver.resolve_table(table_name)

        if not resolved_table:
            return []

        mapped_columns = self.mapping_repository.db2_columns_for_table(table_name)

        if mapped_columns:
            return self._filter_to_existing_dclgen_columns(
                table_name=resolved_table,
                columns=mapped_columns,
            )

        return self.dclgen_repository.column_names_for_table(resolved_table)

    def key_columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        table_name = self.table_name_resolver.table_for_record(record_name)

        if not table_name:
            return []

        mapped_keys = self.mapping_repository.key_columns_for_record(record_name)

        return self._filter_to_existing_dclgen_columns(
            table_name=table_name,
            columns=mapped_keys,
        )

    def has_column(
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
            return self._unique(columns)

        output: list[str] = []

        for column in columns:
            normalized = NameNormalizer.normalize(column)

            if not normalized:
                continue

            if normalized not in dclgen_columns:
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