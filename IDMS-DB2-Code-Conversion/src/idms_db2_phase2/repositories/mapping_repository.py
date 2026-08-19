from __future__ import annotations

from difflib import SequenceMatcher

from idms_db2_phase2.domain.models import SheetMappingRow
from idms_db2_phase2.services.name_normalizer import NameNormalizer


class MappingRepository:
    """
    Repository wrapper for Sheet Mapping rows.

    Authority:
    - Sheet Mapping provides DB2 record/table names.
    - Sheet Mapping provides DB2 column names.
    - Sheet Mapping source-field metadata is used to resolve IDMS/copybook
      fields to DB2 columns.

    This repository does not hardcode program, record, table, or field names.
    """

    MIN_SOURCE_FIELD_SIMILARITY = 0.86

    INSERT_ONLY_AUDIT_PREFIXES = (
        "TS_CREATE",
    )

    UPDATE_AUDIT_PREFIXES = (
        "TS_UPDATE",
        "ID_USERID",
        "NR_USERID",
        "ID_USER",
        "NR_USER",
    )

    def __init__(
        self,
        rows: list[SheetMappingRow] | None = None,
    ) -> None:
        self.rows = rows or []

    def all(
        self,
    ) -> list[SheetMappingRow]:
        return list(self.rows)

    def count(
        self,
    ) -> int:
        return len(self.rows)

    def records(
        self,
    ) -> list[str]:
        values = {
            NameNormalizer.normalize(row.cobol_record_idms)
            for row in self.rows
            if NameNormalizer.normalize(row.cobol_record_idms)
        }
        return sorted(values)

    def tables(
        self,
    ) -> list[str]:
        values = {
            NameNormalizer.normalize(
                row.new_db2_record or row.cross_application_db2_table
            )
            for row in self.rows
            if NameNormalizer.normalize(
                row.new_db2_record or row.cross_application_db2_table
            )
        }
        return sorted(values)

    def rows_for_record(
        self,
        record_name: str,
    ) -> list[SheetMappingRow]:
        target = NameNormalizer.normalize(record_name)

        if not target:
            return []

        return [
            row
            for row in self.rows
            if NameNormalizer.normalize(row.cobol_record_idms) == target
        ]

    def rows_for_table(
        self,
        table_name: str,
    ) -> list[SheetMappingRow]:
        target = NameNormalizer.normalize(table_name)

        if not target:
            return []

        return [
            row
            for row in self.rows
            if NameNormalizer.normalize(row.new_db2_record) == target
            or NameNormalizer.normalize(row.cross_application_db2_table) == target
        ]

    def db2_columns_for_table(
        self,
        table_name: str,
    ) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()

        for row in self.rows_for_table(table_name):
            column = NameNormalizer.normalize(
                row.new_db2_field_name or row.cross_application_db2_field_name
            )

            if not column:
                continue
            if column in seen:
                continue

            seen.add(column)
            output.append(column)

        return output

    def db2_table_for_record(
        self,
        record_name: str,
    ) -> str:
        rows = self.rows_for_record(record_name)

        for row in rows:
            table = NameNormalizer.normalize(row.new_db2_record)

            if table:
                return table

        for row in rows:
            table = NameNormalizer.normalize(row.cross_application_db2_table)

            if table:
                return table

        return ""

    def key_columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        """
        Return key columns based on Sheet Mapping key metadata.

        This keeps older behavior by allowing IDMS CALC metadata as a fallback.
        For strict DB2 primary-key-only handling, use
        primary_key_columns_for_record().
        """
        output: list[str] = []
        seen: set[str] = set()

        for row in self.rows_for_record(record_name):
            key_text = " ".join(
                [
                    str(row.idms_key or ""),
                    str(row.db2_key or ""),
                ]
            ).upper()

            if (
                "KEY" not in key_text
                and "PRIMARY" not in key_text
                and "CALC" not in key_text
            ):
                continue

            column = NameNormalizer.normalize(row.new_db2_field_name)

            if not column:
                continue
            if column in seen:
                continue

            seen.add(column)
            output.append(column)

        return output

    def primary_key_columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        """
        Return DB2 primary-key columns only.

        This is stricter than key_columns_for_record and is used when feedback
        requires DB2 primary-key-only WHERE clauses.
        """
        output: list[str] = []
        seen: set[str] = set()

        for row in self.rows_for_record(record_name):
            db2_key = NameNormalizer.normalize(row.db2_key)
            relation = NameNormalizer.normalize(row.relation)

            if "FOREIGN" in relation:
                continue

            if "FOREIGN" in db2_key:
                continue

            if "PRIMARY" not in db2_key and db2_key != "KEY":
                continue

            column = NameNormalizer.normalize(row.new_db2_field_name)

            if not column:
                continue
            if column in seen:
                continue

            seen.add(column)
            output.append(column)

        return output

    def non_key_columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        key_columns = set(self.key_columns_for_record(record_name))
        output: list[str] = []
        seen: set[str] = set()

        for row in self.rows_for_record(record_name):
            column = NameNormalizer.normalize(row.new_db2_field_name)

            if not column:
                continue
            if column in key_columns:
                continue
            if column in seen:
                continue

            seen.add(column)
            output.append(column)

        return output

    def update_audit_columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()

        for row in self.rows_for_record(record_name):
            column = NameNormalizer.normalize(row.new_db2_field_name)

            if not column:
                continue
            if column.startswith(self.INSERT_ONLY_AUDIT_PREFIXES):
                continue
            if not column.startswith(self.UPDATE_AUDIT_PREFIXES):
                continue
            if column in seen:
                continue

            seen.add(column)
            output.append(column)

        return output

    def update_candidate_columns_for_record(
        self,
        record_name: str,
        changed_source_fields: list[str] | None = None,
    ) -> list[str]:
        """
        Return conservative UPDATE candidate columns.

        Generic rule:
        - If changed_source_fields are supplied, resolve them through Sheet
          Mapping to DB2 columns.
        - Exclude DB2 key columns from SET.
        - Add update audit columns only if present in Sheet Mapping.
        - Do not add TS_CREATE because it is insert-only.
        - Do not invent DB2 columns.

        This method is required by UpdateSqlPlanResolver.
        """
        output: list[str] = []
        seen: set[str] = set()
        key_columns = set(self.key_columns_for_record(record_name))

        for source_field in changed_source_fields or []:
            column = self.column_for_source_field(
                record_name=record_name,
                source_field_name=source_field,
            )
            column = NameNormalizer.normalize(column)

            if not column:
                continue
            if column in key_columns:
                continue
            if column.startswith(self.INSERT_ONLY_AUDIT_PREFIXES):
                continue
            if column in seen:
                continue

            seen.add(column)
            output.append(column)

        for column in self.update_audit_columns_for_record(record_name):
            column = NameNormalizer.normalize(column)

            if not column:
                continue
            if column in seen:
                continue

            seen.add(column)
            output.append(column)

        return output

    def column_for_source_field(
        self,
        record_name: str,
        source_field_name: str,
    ) -> str:
        """
        Resolve an IDMS/copybook source field to a DB2 column.

        Matching order:
        1. Exact normalized source metadata match.
        2. Compact source metadata match.
        3. DB2 suffix-insensitive match.
        4. Similarity fallback.

        This is generic and avoids hardcoded business fields.
        """
        record = NameNormalizer.normalize(record_name)
        source = NameNormalizer.normalize(source_field_name)

        if not record or not source:
            return ""

        rows = self.rows_for_record(record)

        exact = self._column_for_source_exact(
            rows=rows,
            source=source,
        )
        if exact:
            return exact

        compact = self._column_for_source_compact(
            rows=rows,
            source=source,
        )
        if compact:
            return compact

        similar = self._column_for_source_similarity(
            rows=rows,
            source=source,
        )
        if similar:
            return similar

        return ""

    def has_record(
        self,
        record_name: str,
    ) -> bool:
        return bool(self.rows_for_record(record_name))

    def has_table(
        self,
        table_name: str,
    ) -> bool:
        return bool(self.rows_for_table(table_name))

    def _column_for_source_exact(
        self,
        rows: list[SheetMappingRow],
        source: str,
    ) -> str:
        for row in rows:
            column = NameNormalizer.normalize(row.new_db2_field_name)

            if not column:
                continue

            for candidate in self._source_candidates(row):
                if NameNormalizer.normalize(candidate) == source:
                    return column

        return ""

    def _column_for_source_compact(
        self,
        rows: list[SheetMappingRow],
        source: str,
    ) -> str:
        compact_source = self._compact_for_compare(source)

        if not compact_source:
            return ""

        for row in rows:
            column = NameNormalizer.normalize(row.new_db2_field_name)

            if not column:
                continue

            candidates = self._source_candidates(row)
            candidates.append(column)

            for candidate in candidates:
                compact_candidate = self._compact_for_compare(candidate)

                if not compact_candidate:
                    continue

                if compact_candidate == compact_source:
                    return column

                if compact_candidate.startswith(compact_source):
                    return column

                if compact_source.startswith(compact_candidate):
                    return column

        return ""

    def _column_for_source_similarity(
        self,
        rows: list[SheetMappingRow],
        source: str,
    ) -> str:
        compact_source = self._compact_for_compare(source)

        if not compact_source:
            return ""

        best_column = ""
        best_score = 0.0

        for row in rows:
            column = NameNormalizer.normalize(row.new_db2_field_name)

            if not column:
                continue

            candidates = self._source_candidates(row)
            candidates.append(column)

            for candidate in candidates:
                compact_candidate = self._compact_for_compare(candidate)

                if not compact_candidate:
                    continue

                score = SequenceMatcher(
                    None,
                    compact_source,
                    compact_candidate,
                ).ratio()

                if score > best_score:
                    best_score = score
                    best_column = column

        if best_score >= self.MIN_SOURCE_FIELD_SIMILARITY:
            return best_column

        return ""

    def _source_candidates(
        self,
        row: SheetMappingRow,
    ) -> list[str]:
        return [
            str(row.cobol_zone or ""),
            str(row.reference_field_name_copybook or ""),
            str(row.new_db2_field_name or ""),
            str(row.cross_application_db2_field_name or ""),
        ]

    def _compact_for_compare(
        self,
        value: str,
    ) -> str:
        text = NameNormalizer.compact(value)
        return self._remove_db2_record_suffix(text)

    def _remove_db2_record_suffix(
        self,
        value: str,
    ) -> str:
        text = str(value or "").upper()

        if len(text) <= 7:
            return text

        for index, char in enumerate(text):
            if not char.isdigit():
                continue

            suffix = text[index:]

            if len(suffix) >= 4 and any(item.isalpha() for item in suffix):
                return text[:index]

        return text