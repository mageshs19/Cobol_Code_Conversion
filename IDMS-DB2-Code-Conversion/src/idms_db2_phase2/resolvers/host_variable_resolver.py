import re

from catalogs.db2_naming_catalog import DB2_HOST_REFERENCE_PREFIX
from idms_db2_phase2.repositories.dclgen_repository import DclgenRepository
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
from idms_db2_phase2.services.name_normalizer import NameNormalizer


class HostVariableResolver:
    """
    Resolves DCLGEN host variables.

    Authority:
    - DCLGEN determines COBOL host-variable spelling.
    - DCLGEN determines DCLGEN group names.
    - Final DB2 embedded SQL host reference format is:

        :DCLGROUP.HOST-FIELD

      Example:

        :DCLDZBEFFTV.NR-IDSTOCK-479BEFF

    This resolver also normalizes older generated forms:

        :HOST-FIELD OF DCLGROUP
        HOST-FIELD OF DCLGROUP
        :DCLGROUP.HOST-FIELD
        DCLGROUP.HOST-FIELD

    into the canonical DB2 style:

        :DCLGROUP.HOST-FIELD
    """

    HOST_OF_GROUP_PATTERN = re.compile(
        r"^:?\s*"
        r"(?P<host>[A-Z][A-Z0-9-]*)"
        r"\s+OF\s+"
        r"(?P<group>DCL[A-Z0-9-]+)"
        r"\s*$",
        flags=re.IGNORECASE,
    )

    GROUP_DOT_HOST_PATTERN = re.compile(
        r"^:?\s*"
        r"(?P<group>DCL[A-Z0-9-]+)"
        r"\s*\.\s*"
        r"(?P<host>[A-Z][A-Z0-9-]*)"
        r"\s*$",
        flags=re.IGNORECASE,
    )

    DOUBLE_COLON_PATTERN = re.compile(
        r"^:+",
        flags=re.IGNORECASE,
    )

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

        group = self.dclgen_repository.group_for_table(resolved_table)

        if group:
            return NameNormalizer.to_cobol(group)

        return "DCL" + NameNormalizer.to_cobol(resolved_table)

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
            f"{DB2_HOST_REFERENCE_PREFIX}{group}.{host}"
        )

    def host_references_for_columns(
        self,
        table_name: str,
        columns: list[str],
    ) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()

        for column in columns:
            reference = self.host_reference_for_column(
                table_name=table_name,
                column_name=column,
            )

            if not reference:
                continue

            key = reference.upper()

            if key in seen:
                continue

            seen.add(key)
            output.append(reference)

        return output

    def normalize_host_reference(
        self,
        value: str,
    ) -> str:
        text = str(value or "").strip()

        if not text:
            return ""

        text = text.replace("::", ":")
        text = self.DOUBLE_COLON_PATTERN.sub(":", text)

        of_match = self.HOST_OF_GROUP_PATTERN.match(text)

        if of_match:
            group = NameNormalizer.to_cobol(of_match.group("group"))
            host = NameNormalizer.to_cobol(of_match.group("host"))

            if not group or not host:
                return ""

            return f"{DB2_HOST_REFERENCE_PREFIX}{group}.{host}"

        dot_match = self.GROUP_DOT_HOST_PATTERN.match(text)

        if dot_match:
            group = NameNormalizer.to_cobol(dot_match.group("group"))
            host = NameNormalizer.to_cobol(dot_match.group("host"))

            if not group or not host:
                return ""

            return f"{DB2_HOST_REFERENCE_PREFIX}{group}.{host}"

        if text.startswith(DB2_HOST_REFERENCE_PREFIX):
            text = text[1:].strip()

        if "." in text:
            parts = text.split(".", 1)
            group = NameNormalizer.to_cobol(parts[0])
            host = NameNormalizer.to_cobol(parts[1])

            if group and host and group.upper().startswith("DCL"):
                return f"{DB2_HOST_REFERENCE_PREFIX}{group}.{host}"

        if text.upper().startswith("DCL") and " " in text:
            parts = text.split()

            if len(parts) >= 2:
                group = NameNormalizer.to_cobol(parts[0])
                host = NameNormalizer.to_cobol(parts[1])

                if group and host:
                    return f"{DB2_HOST_REFERENCE_PREFIX}{group}.{host}"

        if text.upper().startswith("DCL"):
            return f"{DB2_HOST_REFERENCE_PREFIX}{NameNormalizer.to_cobol(text)}"

        return f"{DB2_HOST_REFERENCE_PREFIX}{NameNormalizer.to_cobol(text)}"

    def valid_host_references(
        self,
    ) -> set[str]:
        output: set[str] = set()

        for reference in self.dclgen_repository.valid_host_references():
            normalized = self.normalize_host_reference(reference)

            if normalized:
                output.add(normalized)
                output.add(normalized[1:])

        return output

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
        reference = self.host_reference_for_column(
            table_name=table_name,
            column_name=column_name,
        )

        if not reference:
            return ""

        return reference[1:]