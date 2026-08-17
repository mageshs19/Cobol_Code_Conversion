from idms_db2_phase2.repositories.dclgen_repository import DclgenRepository
from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
from rules.validation_rules import MAPPING_VALIDATION_MESSAGES


class MappingValidator:
    """
    Validates Sheet Mapping and DCLGEN consistency.

    This validator checks metadata availability and resolver alignment.
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

    def validate(
        self,
    ) -> list[str]:
        messages: list[str] = []

        if self.mapping_repository.count() == 0:
            messages.append(
                MAPPING_VALIDATION_MESSAGES["missing_mapping_rows"]
            )

        if self.dclgen_repository.count() == 0:
            messages.append(
                MAPPING_VALIDATION_MESSAGES["missing_dclgen_columns"]
            )

        messages.extend(self._validate_record_table_resolution())
        messages.extend(self._validate_table_column_resolution())

        return messages

    def _validate_record_table_resolution(
        self,
    ) -> list[str]:
        messages: list[str] = []

        for record in self.mapping_repository.records():
            table = self.table_name_resolver.table_for_record(record)

            if table:
                continue

            messages.append(
                f"{MAPPING_VALIDATION_MESSAGES['missing_record_mapping']} Record={record}"
            )

        return messages

    def _validate_table_column_resolution(
        self,
    ) -> list[str]:
        messages: list[str] = []

        for table in self.mapping_repository.tables():
            resolved_table = self.table_name_resolver.resolve_table(table)

            if not resolved_table:
                continue

            columns = self.mapping_repository.db2_columns_for_table(table)

            if columns:
                continue

            messages.append(
                f"{MAPPING_VALIDATION_MESSAGES['missing_column_mapping']} Table={resolved_table}"
            )

        return messages