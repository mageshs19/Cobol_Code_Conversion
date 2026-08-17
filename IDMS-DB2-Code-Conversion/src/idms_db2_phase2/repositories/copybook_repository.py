from idms_db2_phase2.domain.models import CopybookField
from idms_db2_phase2.services.name_normalizer import NameNormalizer


class CopybookRepository:
    """
    Repository wrapper for optional copybook fields.
    """

    def __init__(
        self,
        fields: list[CopybookField] | None = None,
    ) -> None:
        self.fields = fields or []

    def all(
        self,
    ) -> list[CopybookField]:
        return list(self.fields)

    def count(
        self,
    ) -> int:
        return len(self.fields)

    def names(
        self,
    ) -> list[str]:
        values = {
            NameNormalizer.normalize(field.name)
            for field in self.fields
            if NameNormalizer.normalize(field.name)
        }

        return sorted(values)

    def find(
        self,
        field_name: str,
    ) -> CopybookField | None:
        target = NameNormalizer.normalize(field_name)

        if not target:
            return None

        for field in self.fields:
            if NameNormalizer.normalize(field.name) == target:
                return field

        return None

    def picture_for(
        self,
        field_name: str,
    ) -> str:
        field = self.find(field_name)

        if field is None:
            return ""

        return field.picture

    def usage_for(
        self,
        field_name: str,
    ) -> str:
        field = self.find(field_name)

        if field is None:
            return ""

        return field.usage

    def occurs_for(
        self,
        field_name: str,
    ) -> str:
        field = self.find(field_name)

        if field is None:
            return ""

        return field.occurs

    def has_field(
        self,
        field_name: str,
    ) -> bool:
        return self.find(field_name) is not None