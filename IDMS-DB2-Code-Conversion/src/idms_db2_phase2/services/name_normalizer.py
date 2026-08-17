from patterns.naming_patterns import (
    FOUR_DIGIT_RECORD_SUFFIX_PATTERN,
    MULTIPLE_UNDERSCORE_PATTERN,
    NON_COMPACT_NAME_CHARACTER_PATTERN,
    NON_DB2_NAME_CHARACTER_PATTERN,
)


class NameNormalizer:
    """
    Generic name normalization helper.

    This service contains name transformation logic only.
    Regex patterns are stored in patterns/naming_patterns.py.
    """

    @staticmethod
    def normalize(
        value: str | None,
    ) -> str:
        if value is None:
            return ""

        text = str(value).strip().upper()

        if not text:
            return ""

        text = text.replace("-", "_")
        text = text.replace(" ", "_")
        text = NON_DB2_NAME_CHARACTER_PATTERN.sub("_", text)
        text = MULTIPLE_UNDERSCORE_PATTERN.sub("_", text)

        return text.strip("_")

    @staticmethod
    def to_cobol(
        value: str | None,
    ) -> str:
        return NameNormalizer.normalize(value).replace("_", "-")

    @staticmethod
    def compact(
        value: str | None,
    ) -> str:
        text = NameNormalizer.normalize(value)

        return NON_COMPACT_NAME_CHARACTER_PATTERN.sub("", text)

    @staticmethod
    def remove_record_suffix(
        value: str | None,
    ) -> str:
        text = NameNormalizer.normalize(value)

        if not text:
            return ""

        return FOUR_DIGIT_RECORD_SUFFIX_PATTERN.sub("", text)