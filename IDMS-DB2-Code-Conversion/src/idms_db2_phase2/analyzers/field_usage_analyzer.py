import re
from dataclasses import dataclass, field

from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from patterns.sequence_patterns import strip_sequence_numbers


@dataclass
class FieldUsage:
    record_name: str
    condition_fields: set[str] = field(default_factory=set)
    output_fields: set[str] = field(default_factory=set)
    move_source_fields: set[str] = field(default_factory=set)
    move_target_fields: set[str] = field(default_factory=set)
    dclgen_host_fields: set[str] = field(default_factory=set)
    all_fields: set[str] = field(default_factory=set)


@dataclass
class FieldUsageAnalysis:
    usage_by_record: dict[str, FieldUsage] = field(default_factory=dict)
    diagnostics: list[str] = field(default_factory=list)


class FieldUsageAnalyzer:
    """
    Generic COBOL field-usage analyzer.

    Detects:
    - IDMS qualified references: FIELD OF RECORD / FIELD IN RECORD
    - DCLGEN qualified references: FIELD OF DCLGROUP
    - DB2 host references: :DCLGROUP.FIELD / :FIELD OF DCLGROUP
    - MOVE source fields used for output
    - condition fields in IF / WHEN / UNTIL / EVALUATE

    This analyzer does not rewrite COBOL.
    """

    QUALIFIED_REFERENCE_PATTERN = re.compile(
        r"\b(?P<field>[A-Z][A-Z0-9-]*)\s+(?:OF|IN)\s+"
        r"(?P<record>[A-Z][A-Z0-9-]*)\b",
        flags=re.IGNORECASE,
    )

    DCLGEN_OF_PATTERN = re.compile(
        r":?\s*(?P<field>[A-Z][A-Z0-9-]*)\s+OF\s+"
        r"(?P<group>DCL[A-Z0-9-]+)",
        flags=re.IGNORECASE,
    )

    DCLGEN_DOT_PATTERN = re.compile(
        r":?\s*(?P<group>DCL[A-Z0-9-]+)\.(?P<field>[A-Z][A-Z0-9-]*)",
        flags=re.IGNORECASE,
    )

    MOVE_PATTERN = re.compile(
        r"\bMOVE\s+(?P<source>.+?)\s+TO\s+(?P<target>.+?)(?:\.|$)",
        flags=re.IGNORECASE,
    )

    CONDITION_PATTERN = re.compile(
        r"^\s*(IF|WHEN|UNTIL|EVALUATE)\b",
        flags=re.IGNORECASE,
    )

    DIVISION_PATTERN = re.compile(
        r"^\s*(IDENTIFICATION|ENVIRONMENT|DATA|PROCEDURE)\s+DIVISION\b",
        flags=re.IGNORECASE,
    )

    COMMENT_PATTERN = re.compile(
        r"^\s*[\*/]",
        flags=re.IGNORECASE,
    )

    def __init__(
        self,
        mapping_repository: MappingRepository,
        table_name_resolver: TableNameResolver,
    ) -> None:
        self.mapping_repository = mapping_repository
        self.table_name_resolver = table_name_resolver
        self.group_to_record = self._build_group_to_record_map()

    def analyze(
        self,
        cobol_text: str,
    ) -> FieldUsageAnalysis:
        result = FieldUsageAnalysis()
        inside_procedure = False
        inside_exec_sql = False

        for line_number, raw_line in enumerate(
            str(cobol_text or "").splitlines(),
            start=1,
        ):
            logical = strip_sequence_numbers(raw_line).strip()

            if not logical:
                continue

            if self.COMMENT_PATTERN.match(logical):
                continue

            division_match = self.DIVISION_PATTERN.match(logical)

            if division_match:
                inside_procedure = division_match.group(1).upper() == "PROCEDURE"
                continue

            if logical.upper().startswith("EXEC SQL"):
                inside_exec_sql = True

            if inside_exec_sql:
                self._capture_dclgen_references(
                    logical=logical,
                    result=result,
                    is_condition=False,
                    is_output=False,
                )

                if logical.upper().startswith("END-EXEC"):
                    inside_exec_sql = False

                continue

            if not inside_procedure:
                continue

            is_condition = bool(self.CONDITION_PATTERN.match(logical))

            self._capture_idms_qualified_references(
                logical=logical,
                result=result,
                is_condition=is_condition,
            )

            self._capture_dclgen_references(
                logical=logical,
                result=result,
                is_condition=is_condition,
                is_output=False,
            )

            self._capture_move_usage(
                logical=logical,
                result=result,
            )

        for usage in result.usage_by_record.values():
            usage.all_fields.update(usage.condition_fields)
            usage.all_fields.update(usage.output_fields)
            usage.all_fields.update(usage.move_source_fields)
            usage.all_fields.update(usage.move_target_fields)
            usage.all_fields.update(usage.dclgen_host_fields)

        result.diagnostics.append(
            f"Field usage analyzer: records with usage detected: {len(result.usage_by_record)}"
        )

        for record_name, usage in sorted(result.usage_by_record.items()):
            result.diagnostics.append(
                "Field usage analyzer: "
                f"record={record_name}, "
                f"condition={len(usage.condition_fields)}, "
                f"output={len(usage.output_fields)}, "
                f"move_source={len(usage.move_source_fields)}, "
                f"move_target={len(usage.move_target_fields)}, "
                f"dclgen={len(usage.dclgen_host_fields)}"
            )

        return result

    def _capture_idms_qualified_references(
        self,
        logical: str,
        result: FieldUsageAnalysis,
        is_condition: bool,
    ) -> None:
        for match in self.QUALIFIED_REFERENCE_PATTERN.finditer(logical):
            field_name = NameNormalizer.to_cobol(match.group("field"))
            record_name = NameNormalizer.normalize(match.group("record"))

            if not field_name or not record_name:
                continue

            if record_name.startswith("DCL"):
                continue

            if record_name not in self._mapping_records():
                continue

            usage = self._usage_for_record(result, record_name)
            usage.all_fields.add(field_name)

            if is_condition:
                usage.condition_fields.add(field_name)

    def _capture_dclgen_references(
        self,
        logical: str,
        result: FieldUsageAnalysis,
        is_condition: bool,
        is_output: bool,
    ) -> None:
        for match in self.DCLGEN_OF_PATTERN.finditer(logical):
            field_name = NameNormalizer.to_cobol(match.group("field"))
            group_name = NameNormalizer.normalize(match.group("group"))
            record_name = self.group_to_record.get(group_name, "")

            if not field_name or not record_name:
                continue

            usage = self._usage_for_record(result, record_name)
            usage.dclgen_host_fields.add(field_name)

            if is_condition:
                usage.condition_fields.add(field_name)

            if is_output:
                usage.output_fields.add(field_name)

        for match in self.DCLGEN_DOT_PATTERN.finditer(logical):
            field_name = NameNormalizer.to_cobol(match.group("field"))
            group_name = NameNormalizer.normalize(match.group("group"))
            record_name = self.group_to_record.get(group_name, "")

            if not field_name or not record_name:
                continue

            usage = self._usage_for_record(result, record_name)
            usage.dclgen_host_fields.add(field_name)

            if is_condition:
                usage.condition_fields.add(field_name)

            if is_output:
                usage.output_fields.add(field_name)

    def _capture_move_usage(
        self,
        logical: str,
        result: FieldUsageAnalysis,
    ) -> None:
        match = self.MOVE_PATTERN.search(logical)

        if not match:
            return

        source_text = match.group("source")
        target_text = match.group("target")
        is_output = "UIT-" in target_text.upper()

        for source_match in self.QUALIFIED_REFERENCE_PATTERN.finditer(source_text):
            field_name = NameNormalizer.to_cobol(source_match.group("field"))
            record_name = NameNormalizer.normalize(source_match.group("record"))

            if not field_name or not record_name:
                continue

            if record_name.startswith("DCL"):
                continue

            if record_name not in self._mapping_records():
                continue

            usage = self._usage_for_record(result, record_name)
            usage.move_source_fields.add(field_name)

            if is_output:
                usage.output_fields.add(field_name)

        self._capture_dclgen_references(
            logical=source_text,
            result=result,
            is_condition=False,
            is_output=is_output,
        )

        for target_match in self.QUALIFIED_REFERENCE_PATTERN.finditer(target_text):
            field_name = NameNormalizer.to_cobol(target_match.group("field"))
            record_name = NameNormalizer.normalize(target_match.group("record"))

            if not field_name or not record_name:
                continue

            if record_name.startswith("DCL"):
                continue

            if record_name not in self._mapping_records():
                continue

            usage = self._usage_for_record(result, record_name)
            usage.move_target_fields.add(field_name)

    def _usage_for_record(
        self,
        result: FieldUsageAnalysis,
        record_name: str,
    ) -> FieldUsage:
        record = NameNormalizer.normalize(record_name)

        if record not in result.usage_by_record:
            result.usage_by_record[record] = FieldUsage(record_name=record)

        return result.usage_by_record[record]

    def _build_group_to_record_map(
        self,
    ) -> dict[str, str]:
        output: dict[str, str] = {}

        for record in self._mapping_records():
            normalized_record = NameNormalizer.normalize(record)
            table = self.table_name_resolver.table_for_record(normalized_record)

            if not table:
                continue

            group = "DCL" + NameNormalizer.to_cobol(table)
            output[NameNormalizer.normalize(group)] = normalized_record

        return output

    def _mapping_records(
        self,
    ) -> set[str]:
        try:
            return {
                NameNormalizer.normalize(record)
                for record in self.mapping_repository.records()
                if NameNormalizer.normalize(record)
            }
        except Exception:
            return set()