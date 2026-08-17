from idms_db2_phase2.domain.models import DclgenColumn
from idms_db2_phase2.services.name_normalizer import NameNormalizer


class DclgenRepository:
    """
    Repository wrapper for DCLGEN columns.

    DCLGEN is the authority for COBOL host-variable spelling, group names,
    and PIC clauses.
    """

    def __init__(
        self,
        columns: list[DclgenColumn] | None = None,
    ) -> None:
        self.columns = columns or []

    def all(
        self,
    ) -> list[DclgenColumn]:
        return list(self.columns)

    def count(
        self,
    ) -> int:
        return len(self.columns)

    def tables(
        self,
    ) -> list[str]:
        values = {
            NameNormalizer.normalize(column.table_name)
            for column in self.columns
            if NameNormalizer.normalize(column.table_name)
        }

        return sorted(values)

    def columns_for_table(
        self,
        table_name: str,
    ) -> list[DclgenColumn]:
        target = NameNormalizer.normalize(table_name)

        if not target:
            return []

        return [
            column
            for column in self.columns
            if NameNormalizer.normalize(column.table_name) == target
        ]

    def column_names_for_table(
        self,
        table_name: str,
    ) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()

        for column in self.columns_for_table(table_name):
            name = NameNormalizer.normalize(column.column_name)

            if not name:
                continue

            if name in seen:
                continue

            seen.add(name)
            output.append(name)

        return output

    def has_table(
        self,
        table_name: str,
    ) -> bool:
        return bool(self.columns_for_table(table_name))

    def has_column(
        self,
        table_name: str,
        column_name: str,
    ) -> bool:
        target_column = NameNormalizer.normalize(column_name)

        if not target_column:
            return False

        return target_column in self.column_names_for_table(table_name)

    def host_for_column(
        self,
        table_name: str,
        column_name: str,
    ) -> str:
        target_column = NameNormalizer.normalize(column_name)

        if not target_column:
            return ""

        for column in self.columns_for_table(table_name):
            if NameNormalizer.normalize(column.column_name) == target_column:
                return NameNormalizer.to_cobol(
                    column.cobol_host_name or column.column_name
                )

        return ""

    def group_for_table(
        self,
        table_name: str,
    ) -> str:
        table = NameNormalizer.normalize(table_name)

        if not table:
            return ""

        return "DCL" + NameNormalizer.to_cobol(table)

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

        return f":{host} OF {group}"

    def valid_host_references(
        self,
    ) -> set[str]:
        output: set[str] = set()

        for column in self.columns:
            table = NameNormalizer.normalize(column.table_name)
            group = self.group_for_table(table)
            host = NameNormalizer.to_cobol(
                column.cobol_host_name or column.column_name
            )

            if group and host:
                output.add(f"{group}.{host}")
                output.add(f"{group} {host}")
                output.add(host)

        return output