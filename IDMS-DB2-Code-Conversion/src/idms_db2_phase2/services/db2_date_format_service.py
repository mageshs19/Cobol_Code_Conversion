"""
DB2 date format service.

Generic behavior:
- Does not hardcode program, table, field, or DCLGEN names.
- Keeps current European format unless configured otherwise.
- Adjusts generated DB2 date helper references and sentinel literals.
"""

from __future__ import annotations

from patterns.final_feedback_fix_patterns import (
    DATE_HELPER_EUR_PATTERN,
    DATE_HIGH_EUR_LITERAL_PATTERN,
    DATE_LOW_EUR_LITERAL_PATTERN,
)
from rules.final_feedback_fix_rules import (
    DATE_FORMAT_ALIASES,
    DB2_DATE_HELPER_BY_FORMAT,
    DB2_DATE_HIGH_LITERAL_BY_FORMAT,
    DB2_DATE_LOW_LITERAL_BY_FORMAT,
    DEFAULT_DB2_DATE_EXTERNAL_FORMAT,
)


class Db2DateFormatService:
    """
    Applies configured DB2 external date format to generated date conversion.

    This service intentionally does not infer business semantics. It only
    transforms generated generic date helper references when a site/DCLGEN
    external date format is provided.
    """

    def __init__(
        self,
        date_external_format: str | None = None,
    ) -> None:
        self.date_external_format = self.normalize_format(
            date_external_format or DEFAULT_DB2_DATE_EXTERNAL_FORMAT
        )

    def apply(self, text: str) -> str:
        source = str(text or "")

        if not source:
            return ""

        if self.date_external_format == "DD.MM.YYYY":
            return source

        target_helper = DB2_DATE_HELPER_BY_FORMAT[self.date_external_format]
        target_low = DB2_DATE_LOW_LITERAL_BY_FORMAT[self.date_external_format]
        target_high = DB2_DATE_HIGH_LITERAL_BY_FORMAT[self.date_external_format]

        updated = DATE_HELPER_EUR_PATTERN.sub(target_helper, source)
        updated = DATE_LOW_EUR_LITERAL_PATTERN.sub(target_low, updated)
        updated = DATE_HIGH_EUR_LITERAL_PATTERN.sub(target_high, updated)

        return updated

    def normalize_format(self, value: str) -> str:
        text = str(value or "").strip().upper()

        if not text:
            return DEFAULT_DB2_DATE_EXTERNAL_FORMAT

        return DATE_FORMAT_ALIASES.get(
            text,
            DEFAULT_DB2_DATE_EXTERNAL_FORMAT,
        )