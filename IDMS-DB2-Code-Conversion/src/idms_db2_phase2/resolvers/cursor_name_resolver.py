from catalogs.db2_naming_catalog import DB2_CURSOR_SUFFIX, DB2_DEFAULT_CURSOR_NAME
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from rules.cursor_rules import cursor_paragraph_number


class CursorNameResolver:
    """
    Resolves cursor names and cursor paragraph names.

    Authority:
    - Cursor names are derived from DB2 table or record names.
    - Cursor names are not derived from IDMS set names.
    """

    def cursor_name_from_table(
        self,
        table_name: str,
    ) -> str:
        table = NameNormalizer.normalize(table_name)

        if not table:
            return DB2_DEFAULT_CURSOR_NAME

        base = self._remove_table_suffix(table)

        if not base:
            return DB2_DEFAULT_CURSOR_NAME

        return NameNormalizer.to_cobol(base + DB2_CURSOR_SUFFIX)

    def paragraph_names(
        self,
        cursor_order: int,
        cursor_name: str,
    ) -> dict[str, str]:
        clean_cursor = NameNormalizer.to_cobol(cursor_name)

        return {
            "open": f"{cursor_paragraph_number(cursor_order, 'open')}-OPEN-{clean_cursor}",
            "fetch": f"{cursor_paragraph_number(cursor_order, 'fetch')}-FETCH-{clean_cursor}",
            "close": f"{cursor_paragraph_number(cursor_order, 'close')}-CLOSE-{clean_cursor}",
        }

    def paragraph_numbers(
        self,
        cursor_order: int,
    ) -> dict[str, int]:
        return {
            "open": cursor_paragraph_number(cursor_order, "open"),
            "fetch": cursor_paragraph_number(cursor_order, "fetch"),
            "close": cursor_paragraph_number(cursor_order, "close"),
        }

    def cursor_spec(
        self,
        cursor_order: int,
        table_name: str,
    ) -> dict[str, str | int]:
        cursor_name = self.cursor_name_from_table(table_name)
        paragraph_names = self.paragraph_names(
            cursor_order=cursor_order,
            cursor_name=cursor_name,
        )
        paragraph_numbers = self.paragraph_numbers(cursor_order)

        return {
            "cursor_name": cursor_name,
            "open_paragraph": paragraph_names["open"],
            "fetch_paragraph": paragraph_names["fetch"],
            "close_paragraph": paragraph_names["close"],
            "open_number": paragraph_numbers["open"],
            "fetch_number": paragraph_numbers["fetch"],
            "close_number": paragraph_numbers["close"],
        }

    def _remove_table_suffix(
        self,
        table_name: str,
    ) -> str:
        table = NameNormalizer.normalize(table_name)

        if table.endswith("_TV") or table.endswith("_TB"):
            return table[:-3] + "_"

        if table.endswith("TV") or table.endswith("TB"):
            return table[:-2]

        return table + "_"