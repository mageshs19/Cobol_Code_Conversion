"""
Fixed-format COBOL body formatter.

Responsibilities:
- Decide Area A vs Area B.
- Preserve original indentation wherever possible.
- Keep original business COBOL indentation.
- Normalize generated SQL and generated procedure statements.
"""

from __future__ import annotations

import re


try:
    from patterns.fixed_format_patterns import (
        AREA_A_PREFIX_PATTERN,
        DATA_LEVEL_PATTERN,
        DIVISION_PATTERN,
        EXEC_SQL_END_PATTERN,
        EXEC_SQL_START_PATTERN,
        PARAGRAPH_PATTERN,
        SECTION_PATTERN,
    )
except Exception:
    AREA_A_PREFIX_PATTERN = re.compile(
        r"^(PROGRAM-ID\.|AUTHOR\.|INSTALLATION\.|DATE-WRITTEN\.|DATE-COMPILED\.|SECURITY\.)",
        flags=re.IGNORECASE,
    )

    DATA_LEVEL_PATTERN = re.compile(
        r"^(0[1-9]|[1-4][0-9]|66|77|88)\s+",
        flags=re.IGNORECASE,
    )

    DIVISION_PATTERN = re.compile(
        r"^(IDENTIFICATION|ENVIRONMENT|DATA|PROCEDURE)\s+DIVISION\b",
        flags=re.IGNORECASE,
    )

    EXEC_SQL_START_PATTERN = re.compile(
        r"^EXEC\s+SQL\b",
        flags=re.IGNORECASE,
    )

    EXEC_SQL_END_PATTERN = re.compile(
        r"^END-EXEC\.?$",
        flags=re.IGNORECASE,
    )

    PARAGRAPH_PATTERN = re.compile(
        r"^[A-Z0-9][A-Z0-9-]*\.\s*$",
        flags=re.IGNORECASE,
    )

    SECTION_PATTERN = re.compile(
        r"^[A-Z0-9-]+\s+SECTION\.?$",
        flags=re.IGNORECASE,
    )


try:
    from rules.cobol_statement_rules import (
        NON_PARAGRAPH_WORDS,
        PROCEDURE_VERBS,
        SQL_LEVEL_1_KEYWORDS,
        SQL_LEVEL_2_KEYWORDS,
    )
except Exception:
    NON_PARAGRAPH_WORDS = {
        "ACCEPT",
        "ADD",
        "CALL",
        "CLOSE",
        "COMPUTE",
        "CONTINUE",
        "DISPLAY",
        "ELSE",
        "END-IF",
        "EVALUATE",
        "EXEC",
        "EXIT",
        "GO",
        "GOBACK",
        "IF",
        "INITIALIZE",
        "MOVE",
        "OPEN",
        "PERFORM",
        "READ",
        "SET",
        "STOP",
        "WHEN",
        "WRITE",
    }

    PROCEDURE_VERBS = (
        "ACCEPT ",
        "ADD ",
        "CALL ",
        "CLOSE ",
        "COMPUTE ",
        "CONTINUE",
        "DISPLAY ",
        "ELSE",
        "END-IF",
        "EVALUATE ",
        "EXEC SQL",
        "EXIT",
        "GO ",
        "GOBACK",
        "IF ",
        "INITIALIZE ",
        "MOVE ",
        "OPEN ",
        "PERFORM ",
        "READ ",
        "SET ",
        "STOP ",
        "WHEN ",
        "WRITE ",
    )

    SQL_LEVEL_1_KEYWORDS = (
        "SELECT ",
        "INTO ",
        "FROM ",
        "WHERE ",
        "ORDER BY ",
        "GROUP BY ",
        "HAVING ",
        "FETCH ",
        "OPEN ",
        "CLOSE ",
        "COMMIT",
        "ROLLBACK",
        "INSERT ",
        "UPDATE ",
        "DELETE ",
        "SET ",
        "VALUES ",
        "FOR READ ONLY",
        "QUERYNO ",
    )

    SQL_LEVEL_2_KEYWORDS = (
        "AND ",
        "OR ",
    )


try:
    from rules.fixed_format_rules import (
        AREA_A_DATA_LEVELS,
        AREA_B_INDENT,
        COMMENT_INDICATOR,
        DEBUG_INDICATOR,
        PAGE_INDICATOR,
        SPACE_INDICATOR,
        SQL_INDENT,
    )
except Exception:
    AREA_A_DATA_LEVELS = {
        "01",
        "66",
        "77",
    }
    AREA_B_INDENT = "    "
    COMMENT_INDICATOR = "*"
    DEBUG_INDICATOR = "D"
    PAGE_INDICATOR = "/"
    SPACE_INDICATOR = " "
    SQL_INDENT = " "


class FixedFormatBodyFormatter:
    def area_body(
        self,
        body: str,
        logical: str,
        current_division: str,
        inside_exec_sql: bool,
        indicator: str,
        previous_procedure_indent: str,
    ) -> str:
        original = str(body or "").rstrip()
        clean_statement = str(logical or "").strip()

        if indicator in {
            COMMENT_INDICATOR,
            PAGE_INDICATOR,
            DEBUG_INDICATOR,
            "-",
        }:
            return original

        if not clean_statement:
            return ""

        if original.startswith(" "):
            return original

        if self.is_area_a_statement(clean_statement):
            return clean_statement

        if inside_exec_sql:
            return self.sql_area_body(clean_statement)

        if current_division == "PROCEDURE":
            return self.procedure_area_b_body(
                clean_statement=clean_statement,
                previous_procedure_indent=previous_procedure_indent,
            )

        if DATA_LEVEL_PATTERN.match(clean_statement):
            return self.data_area_body(clean_statement)

        return clean_statement

    def procedure_area_b_body(
        self,
        clean_statement: str,
        previous_procedure_indent: str,
    ) -> str:
        upper = clean_statement.upper()

        if self.is_area_a_statement(clean_statement):
            return clean_statement

        if upper.startswith(PROCEDURE_VERBS):
            return AREA_B_INDENT + clean_statement

        if previous_procedure_indent:
            return previous_procedure_indent + clean_statement

        return AREA_B_INDENT + clean_statement

    def data_area_body(
        self,
        clean_statement: str,
    ) -> str:
        parts = clean_statement.split(maxsplit=1)

        if not parts:
            return clean_statement

        level = parts[0]

        if level in AREA_A_DATA_LEVELS:
            return clean_statement

        return AREA_B_INDENT + clean_statement

    def sql_area_body(
        self,
        clean_statement: str,
    ) -> str:
        upper = clean_statement.upper()

        if EXEC_SQL_START_PATTERN.match(clean_statement):
            return AREA_B_INDENT + clean_statement

        if EXEC_SQL_END_PATTERN.match(clean_statement):
            return AREA_B_INDENT + clean_statement

        if upper.startswith(SQL_LEVEL_1_KEYWORDS):
            return SQL_INDENT + clean_statement

        if upper.startswith(SQL_LEVEL_2_KEYWORDS):
            return SQL_INDENT + clean_statement

        return SQL_INDENT + clean_statement

    def is_area_a_statement(
        self,
        statement: str,
    ) -> bool:
        clean_statement = str(statement or "").strip()

        if not clean_statement:
            return False

        if DIVISION_PATTERN.match(clean_statement):
            return True

        if SECTION_PATTERN.match(clean_statement):
            return True

        if AREA_A_PREFIX_PATTERN.match(clean_statement):
            return True

        if DATA_LEVEL_PATTERN.match(clean_statement):
            first_word = clean_statement.split(maxsplit=1)[0]
            return first_word in AREA_A_DATA_LEVELS

        if not PARAGRAPH_PATTERN.match(clean_statement):
            return False

        paragraph_name = clean_statement.rstrip(".").strip().upper()

        if paragraph_name in NON_PARAGRAPH_WORDS:
            return False

        return True

    def is_exec_sql_start(
        self,
        statement: str,
    ) -> bool:
        return bool(
            EXEC_SQL_START_PATTERN.match(
                str(statement or "").strip(),
            )
        )

    def is_exec_sql_end(
        self,
        statement: str,
    ) -> bool:
        return bool(
            EXEC_SQL_END_PATTERN.match(
                str(statement or "").strip(),
            )
        )

    def leading_spaces(
        self,
        text: str,
        default: str = "",
    ) -> str:
        value = str(text or "")

        if not value:
            return default

        count = len(value) - len(value.lstrip(" "))

        if count <= 0:
            return default

        return value[:count]