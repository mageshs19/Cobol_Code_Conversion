from catalogs.db2_naming_catalog import DB2_HOST_REFERENCE_PREFIX
from idms_db2_phase2.repositories.dclgen_repository import DclgenRepository
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
from idms_db2_phase2.services.name_normalizer import NameNormalizer


class HostVariableResolver:
    """
    Resolves DCLGEN host variables.

    Authority:
    - DCLGEN determines COBOL host-variable spelling.
    - DCLGEN determines group names.
    """

    def __init__(
        self,
        dclgen_repository: DclgenRepository,
        table_name_resolver: TableNameResolver,
    ) -> None:
        self.dclgen_repository = dclgen_repository
        self.table_name_resolver = table_name_resolver

    def host_for_column(
        self,
        table_name: str,
        column_name: str,
    ) -> str:
        resolved_table = self.table_name_resolver.resolve_table(table_name)

        if not resolved_table:
            return ""

        return self.dclgen_repository.host_for_column(
            table_name=resolved_table,
            column_name=column_name,
        )

    def group_for_table(
        self,
        table_name: str,
    ) -> str:
        resolved_table = self.table_name_resolver.resolve_table(table_name)

        if not resolved_table:
            return ""

        return self.dclgen_repository.group_for_table(resolved_table)

    def host_reference_for_column(
        self,
        table_name: str,
        column_name: str,
    ) -> str:
        group = self.group_for_table(table_name)
        host = self.host_for_column(
            table_name=table_name,
            column_name=column_name,
        )

        if not group or not host:
            return ""

        return self.normalize_host_reference(
            f"{DB2_HOST_REFERENCE_PREFIX}{host} OF {group}"
        )

    def host_references_for_columns(
        self,
        table_name: str,
        columns: list[str],
    ) -> list[str]:
        output: list[str] = []

        for column in columns:
            reference = self.host_reference_for_column(
                table_name=table_name,
                column_name=column,
            )

            if reference:
                output.append(reference)

        return output

    def normalize_host_reference(
        self,
        value: str,
    ) -> str:
        text = str(value or "").strip()

        while text.startswith(f"{DB2_HOST_REFERENCE_PREFIX}{DB2_HOST_REFERENCE_PREFIX}"):
            text = text[1:].strip()

        if not text:
            return ""

        if text.startswith(DB2_HOST_REFERENCE_PREFIX):
            return text

        return f"{DB2_HOST_REFERENCE_PREFIX}{text}"

    def valid_host_references(
        self,
    ) -> set[str]:
        return self.dclgen_repository.valid_host_references()

    def has_host_for_column(
        self,
        table_name: str,
        column_name: str,
    ) -> bool:
        return bool(
            self.host_for_column(
                table_name=table_name,
                column_name=column_name,
            )
        )

    def host_reference_key(
        self,
        table_name: str,
        column_name: str,
    ) -> str:
        group = self.group_for_table(table_name)
        host = self.host_for_column(
            table_name=table_name,
            column_name=column_name,
        )

        if not group or not host:
            return ""

        return f"{NameNormalizer.to_cobol(group)}.{NameNormalizer.to_cobol(host)}"