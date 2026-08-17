from catalogs.db2_naming_catalog import DB2_TABLE_SUFFIX_EQUIVALENTS
from idms_db2_phase2.repositories.dclgen_repository import DclgenRepository
from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.services.name_normalizer import NameNormalizer


class TableNameResolver:
    """
    Resolves DB2 table names.

    Authority:
    - Sheet Mapping provides intended DB2 table names.
    - DCLGEN provides the final available DB2 table name.
    - If Sheet Mapping says TB but DCLGEN has TV, resolve to DCLGEN TV.

    Example:
    - Sheet Mapping: DZBFARTB
    - DCLGEN table: DZBFARTV
    - Final SQL table: DZBFARTV
    """

    def __init__(
        self,
        mapping_repository: MappingRepository,
        dclgen_repository: DclgenRepository,
    ) -> None:
        self.mapping_repository = mapping_repository
        self.dclgen_repository = dclgen_repository

    def resolve_table(
        self,
        table_name: str,
    ) -> str:
        normalized = NameNormalizer.normalize(table_name)

        if not normalized:
            return ""

        for candidate in self.table_candidates(normalized):
            if self.dclgen_repository.has_table(candidate):
                return candidate

        return normalized

    def table_for_record(
        self,
        record_name: str,
    ) -> str:
        mapped_table = self.mapping_repository.db2_table_for_record(record_name)

        if not mapped_table:
            return ""

        return self.resolve_table(mapped_table)

    def table_candidates(
        self,
        table_name: str,
    ) -> list[str]:
        normalized = NameNormalizer.normalize(table_name)

        if not normalized:
            return []

        output: list[str] = [normalized]

        for source_suffix, target_suffix in DB2_TABLE_SUFFIX_EQUIVALENTS:
            if normalized.endswith(source_suffix):
                output.append(
                    normalized[: -len(source_suffix)] + target_suffix
                )

        cobol_name = NameNormalizer.to_cobol(normalized)
        compact_name = NameNormalizer.compact(normalized)

        if cobol_name:
            output.append(cobol_name)

        if compact_name:
            output.append(compact_name)

        final: list[str] = []

        for item in output:
            normalized_item = NameNormalizer.normalize(item)

            if not normalized_item:
                continue

            if normalized_item in final:
                continue

            final.append(normalized_item)

        return final

    def known_dclgen_tables(
        self,
    ) -> list[str]:
        return self.dclgen_repository.tables()

    def known_mapping_tables(
        self,
    ) -> list[str]:
        return self.mapping_repository.tables()

    def has_resolved_table(
        self,
        table_name: str,
    ) -> bool:
        resolved = self.resolve_table(table_name)

        if not resolved:
            return False

        return self.dclgen_repository.has_table(resolved)

    def context_strength(
        self,
        record_name: str,
    ) -> int:
        if not record_name:
            return 0

        if self.mapping_repository.has_record(record_name):
            return 100

        return 0