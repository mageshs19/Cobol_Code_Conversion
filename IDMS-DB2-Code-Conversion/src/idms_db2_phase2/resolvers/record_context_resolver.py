from idms_db2_phase2.repositories.dclgen_repository import DclgenRepository
from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.services.name_normalizer import NameNormalizer


class RecordContextResolver:
    """
    Resolves active source record context.

    This helper is used by transformers and field rewriters to avoid guessing
    the active record directly inside transformation logic.
    """

    def __init__(
        self,
        mapping_repository: MappingRepository,
        dclgen_repository: DclgenRepository,
    ) -> None:
        self.mapping_repository = mapping_repository
        self.dclgen_repository = dclgen_repository

    def known_records(
        self,
    ) -> list[str]:
        return self.mapping_repository.records()

    def record_from_text(
        self,
        text: str,
    ) -> str:
        normalized_text = NameNormalizer.normalize(text)

        if not normalized_text:
            return ""

        for record in self.known_records():
            if record and record in normalized_text:
                return record

        return ""

    def record_from_paragraph_name(
        self,
        paragraph_name: str,
    ) -> str:
        return self.record_from_text(paragraph_name)

    def record_from_move_target(
        self,
        move_target: str,
    ) -> str:
        return self.record_from_text(move_target)

    def record_from_initialize_target(
        self,
        initialize_target: str,
    ) -> str:
        text = NameNormalizer.normalize(initialize_target)

        if not text:
            return ""

        if text.startswith("DCL"):
            table = text[3:]
            return self.record_from_table(table)

        return self.record_from_text(text)

    def record_from_table(
        self,
        table_name: str,
    ) -> str:
        table = NameNormalizer.normalize(table_name)

        if not table:
            return ""

        for record in self.known_records():
            record_table = self.mapping_repository.db2_table_for_record(record)

            if NameNormalizer.normalize(record_table) == table:
                return record

        return ""

    def record_from_dclgen_group(
        self,
        group_name: str,
    ) -> str:
        text = NameNormalizer.normalize(group_name)

        if not text:
            return ""

        if text.startswith("DCL"):
            return self.record_from_table(text[3:])

        return ""

    def context_strength(
        self,
        record_name: str,
    ) -> int:
        if not record_name:
            return 0

        if self.mapping_repository.has_record(record_name):
            return 100

        return 0