"""
Qualified IDMS field reference transformer.

Rewrites safe qualified references only:

- FIELD OF IDMS-RECORD
- FIELD IN IDMS-RECORD

Bare words are not globally rewritten.
"""

from patterns.field_usage_patterns import QUALIFIED_REFERENCE_PATTERN
from rules.field_mapping_rules import QUALIFIED_REFERENCE_REWRITE_RULES


class QualifiedReferenceTransformer:
    """
    Rewrites qualified IDMS field references to DB2 DCLGEN host references when
    mapping metadata exists.
    """

    def __init__(
        self,
        mapping_repository,
        dclgen_repository,
    ) -> None:
        self.mapping_repository = mapping_repository
        self.dclgen_repository = dclgen_repository

    def transform_line(
        self,
        line: str,
    ) -> str:
        if not line:
            return ""

        return QUALIFIED_REFERENCE_PATTERN.sub(
            self._replace_reference,
            line,
        )

    def _replace_reference(
        self,
        match,
    ) -> str:
        field_name = match.group("field")
        record_name = match.group("record")

        mapped_column = self.mapping_repository.find_column_mapping(
            record_name=record_name,
            idms_field_name=field_name,
        )

        if not mapped_column:
            return match.group(0)

        host_reference = self.dclgen_repository.find_host_reference(
            table_name=mapped_column.db2_table_name,
            column_name=mapped_column.db2_column_name,
        )

        if not host_reference:
            return match.group(0)

        return host_reference