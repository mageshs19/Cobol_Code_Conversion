from idms_db2_phase2.analyzers.field_usage_analyzer import FieldUsageAnalysis
from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.column_name_resolver import ColumnNameResolver
from idms_db2_phase2.resolvers.relationship_resolver import RelationshipResolver
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from rules.timestamp_audit_rules import AUDIT_COLUMN_PREFIXES


class CursorColumnResolver:
    """
    Resolves minimal cursor SELECT and ORDER BY columns generically.

    SELECT priority:
    1. DCLGEN host fields used in procedure logic.
    2. Fields used in procedure conditions.
    3. Fields used as MOVE sources for output writes.
    4. Parent key columns required by child cursor relationships.
    5. Child order key columns.
    6. Fallback to mapped non-audit columns only if usage is unavailable.

    ORDER BY rule:
    - Parent/root cursors do not get ORDER BY unless explicit order metadata
      exists in Sheet Mapping.
    - Child cursors may order by non-FK primary/sequence key.
    - DESC is added for child sequence/order key where metadata indicates
      sequence/event/latest-first semantics.
    """

    ORDER_HINT_WORDS = (
        "ORDER",
        "ORDERBY",
        "SORT",
        "SORTKEY",
        "RANK",
    )

    DESC_HINT_WORDS = (
        "SEQ",
        "SEQUENCE",
        "IDMSKEY",
        "IDENTIFIERSEQ",
        "IDENTIFIERSEQSPECIAL",
        "EVENT",
        "EVPR",
        "EVEF",
        "AUTO",
        "INCREMENT",
    )

    def __init__(
        self,
        mapping_repository: MappingRepository,
        table_name_resolver: TableNameResolver,
        column_name_resolver: ColumnNameResolver,
        relationship_resolver: RelationshipResolver,
    ) -> None:
        self.mapping_repository = mapping_repository
        self.table_name_resolver = table_name_resolver
        self.column_name_resolver = column_name_resolver
        self.relationship_resolver = relationship_resolver

    def select_columns_for_record(
        self,
        record_name: str,
        field_usage_analysis: FieldUsageAnalysis | None = None,
    ) -> list[str]:
        record = NameNormalizer.normalize(record_name)

        if not record:
            return []

        selected: list[str] = []

        selected.extend(
            self._columns_from_field_usage(
                record_name=record,
                field_usage_analysis=field_usage_analysis,
            )
        )

        selected.extend(
            self.relationship_resolver.parent_key_columns_required_by_children(record)
        )

        if self.relationship_resolver.has_foreign_keys(record):
            selected.extend(
                self._order_by_base_columns_for_record(record)
            )

        selected = self._valid_non_audit_columns(
            record_name=record,
            columns=selected,
        )

        if selected:
            return selected

        fallback = self.column_name_resolver.columns_for_record(record)

        return self._valid_non_audit_columns(
            record_name=record,
            columns=fallback,
        )

    def order_by_columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        record = NameNormalizer.normalize(record_name)

        if not record:
            return []

        is_child = self.relationship_resolver.has_foreign_keys(record)

        if not is_child:
            return self._explicit_parent_order_columns(record)

        order_columns = self._order_by_base_columns_for_record(record)

        output: list[str] = []

        for column in order_columns:
            expression = column

            if self._should_order_desc(
                record_name=record,
                column_name=column,
            ):
                expression = f"{column} DESC"

            output.append(expression)

        return self._unique(output)

    def _explicit_parent_order_columns(
        self,
        record_name: str,
    ) -> list[str]:
        """
        Parent/root cursor gets ORDER BY only if Sheet Mapping explicitly
        indicates order/sort/rank semantics.

        This prevents automatic ORDER BY on normal parent PK columns.
        """

        rows = self.mapping_repository.rows_for_record(record_name)
        output: list[str] = []

        for row in rows:
            text = " ".join(
                [
                    str(getattr(row, "remarks", "") or ""),
                    str(getattr(row, "hopex_expression_type_remark", "") or ""),
                    str(getattr(row, "relation", "") or ""),
                    str(getattr(row, "basetype", "") or ""),
                ]
            ).upper()

            if not any(word in text for word in self.ORDER_HINT_WORDS):
                continue

            column = NameNormalizer.normalize(
                getattr(row, "new_db2_field_name", "")
            )

            if not column:
                continue

            if not self._column_exists_for_record(record_name, column):
                continue

            if self._is_audit_column(column):
                continue

            output.append(column)

        return self._unique(output)

    def _order_by_base_columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        return self.relationship_resolver.order_by_columns_for_record(record_name)

    def _should_order_desc(
        self,
        record_name: str,
        column_name: str,
    ) -> bool:
        record = NameNormalizer.normalize(record_name)
        column = NameNormalizer.normalize(column_name)

        rows = self.mapping_repository.rows_for_record(record)

        for row in rows:
            row_column = NameNormalizer.normalize(
                getattr(row, "new_db2_field_name", "")
            )

            if row_column != column:
                continue

            combined_text = " ".join(
                [
                    str(getattr(row, "db2_key", "") or ""),
                    str(getattr(row, "hopex_expression_type_remark", "") or ""),
                    str(getattr(row, "remarks", "") or ""),
                    str(getattr(row, "new_db2_data_type", "") or ""),
                    str(getattr(row, "basetype", "") or ""),
                    column,
                ]
            ).upper()

            if any(word in combined_text for word in self.DESC_HINT_WORDS):
                return True

        return False

    def _columns_from_field_usage(
        self,
        record_name: str,
        field_usage_analysis: FieldUsageAnalysis | None,
    ) -> list[str]:
        if field_usage_analysis is None:
            return []

        usage = field_usage_analysis.usage_by_record.get(
            NameNormalizer.normalize(record_name)
        )

        if usage is None:
            return []

        output: list[str] = []

        for field_name in usage.all_fields:
            column = self._column_for_source_or_host_field(
                record_name=record_name,
                source_or_host_field=field_name,
            )

            if column:
                output.append(column)

        return self._unique(output)

    def _column_for_source_or_host_field(
        self,
        record_name: str,
        source_or_host_field: str,
    ) -> str:
        record = NameNormalizer.normalize(record_name)
        source = NameNormalizer.normalize(source_or_host_field)

        if not record or not source:
            return ""

        rows = self.mapping_repository.rows_for_record(record)

        for row in rows:
            target_column = NameNormalizer.normalize(
                getattr(row, "new_db2_field_name", "")
                or getattr(row, "cross_application_db2_field_name", "")
            )

            if not target_column:
                continue

            source_candidates = {
                NameNormalizer.normalize(
                    self._extract_source_field(getattr(row, "cobol_zone", ""))
                ),
                NameNormalizer.normalize(
                    self._extract_source_field(
                        getattr(row, "reference_field_name_copybook", "")
                    )
                ),
                target_column,
                NameNormalizer.normalize(NameNormalizer.to_cobol(target_column)),
            }

            source_candidates = {
                candidate
                for candidate in source_candidates
                if candidate
            }

            if source in source_candidates:
                return target_column

        return ""

    def _valid_non_audit_columns(
        self,
        record_name: str,
        columns: list[str],
    ) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()

        for column in columns:
            normalized = NameNormalizer.normalize(column)

            if not normalized:
                continue

            if normalized in seen:
                continue

            if self._is_audit_column(normalized):
                continue

            if not self._column_exists_for_record(record_name, normalized):
                continue

            seen.add(normalized)
            output.append(normalized)

        return output

    def _column_exists_for_record(
        self,
        record_name: str,
        column_name: str,
    ) -> bool:
        table = self.table_name_resolver.table_for_record(record_name)

        if not table:
            return False

        return self.column_name_resolver.has_column(
            table_name=table,
            column_name=column_name,
        )

    def _extract_source_field(
        self,
        value: str,
    ) -> str:
        text = str(value or "").strip()

        if not text:
            return ""

        text = text.replace(".", " ")

        tokens = text.split()

        if tokens and tokens[0].isdigit() and len(tokens) > 1:
            return tokens[1]

        if tokens:
            return tokens[0]

        return ""

    def _is_audit_column(
        self,
        column_name: str,
    ) -> bool:
        column = NameNormalizer.normalize(column_name)

        return any(
            column.startswith(prefix)
            for prefix in AUDIT_COLUMN_PREFIXES
        )

    def _unique(
        self,
        values: list[str],
    ) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()

        for value in values:
            normalized = str(value or "").strip()

            if not normalized:
                continue

            key = NameNormalizer.normalize(normalized)

            if key in seen:
                continue

            seen.add(key)
            output.append(normalized)

        return output