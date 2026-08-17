"""
COBOL statement classification rules.

This file contains COBOL statement rule constants only.

Rules belong in rules/, not patterns/.

No regex patterns should be defined here.
No parser, service, transformer, generator, validator, or composer logic
should be placed here.

Use this file for generic COBOL statement classification values that are
shared by formatters, composers, parsers, transformers, or validators.
"""

NON_PARAGRAPH_SINGLE_WORDS = {
    "ACCEPT",
    "ADD",
    "ALTER",
    "CALL",
    "CANCEL",
    "CLOSE",
    "COMMIT",
    "COMPUTE",
    "CONTINUE",
    "DELETE",
    "DISPLAY",
    "DIVIDE",
    "ELSE",
    "END-ADD",
    "END-CALL",
    "END-DELETE",
    "END-DIVIDE",
    "END-EVALUATE",
    "END-EXEC",
    "END-IF",
    "END-MULTIPLY",
    "END-PERFORM",
    "END-READ",
    "END-RETURN",
    "END-REWRITE",
    "END-SEARCH",
    "END-START",
    "END-STRING",
    "END-SUBTRACT",
    "END-UNSTRING",
    "END-WRITE",
    "EJECT",
    "EVALUATE",
    "EXEC",
    "FETCH",
    "EXIT",
    "GOBACK",
    "IF",
    "INITIALIZE",
    "INSPECT",
    "MOVE",
    "MULTIPLY",
    "NEXT",
    "OPEN",
    "PERFORM",
    "READ",
    "RETURN",
    "REWRITE",
    "ROLLBACK",
    "SEARCH",
    "SET",
    "SKIP1",
    "SKIP2",
    "SKIP3",
    "SORT",
    "SPACE",
    "SPACES",
    "START",
    "STOP",
    "STRING",
    "SUBTRACT",
    "UNSTRING",
    "WHEN",
    "WRITE",
}

NON_PARAGRAPH_WORDS = NON_PARAGRAPH_SINGLE_WORDS

PROCEDURE_VERBS = (
    "ACCEPT ",
    "ADD ",
    "ALTER ",
    "CALL ",
    "CANCEL ",
    "CLOSE ",
    "COMMIT",
    "COMPUTE ",
    "CONTINUE",
    "DELETE ",
    "DISPLAY ",
    "DIVIDE ",
    "ELSE",
    "END-ADD",
    "END-CALL",
    "END-DELETE",
    "END-DIVIDE",
    "END-EVALUATE",
    "END-EXEC",
    "END-IF",
    "END-MULTIPLY",
    "END-PERFORM",
    "END-READ",
    "END-RETURN",
    "END-REWRITE",
    "END-SEARCH",
    "END-START",
    "END-STRING",
    "END-SUBTRACT",
    "END-UNSTRING",
    "END-WRITE",
    "EVALUATE ",
    "EXEC SQL",
    "EXIT",
    "FETCH ",
    "GOBACK",
    "IF ",
    "INITIALIZE ",
    "INSPECT ",
    "MOVE ",
    "MULTIPLY ",
    "NEXT ",
    "OPEN ",
    "PERFORM ",
    "READ ",
    "RETURN ",
    "REWRITE ",
    "ROLLBACK",
    "SEARCH ",
    "SET ",
    "SORT ",
    "START ",
    "STOP ",
    "STRING ",
    "SUBTRACT ",
    "UNSTRING ",
    "WHEN ",
    "WRITE ",
)

SQL_LEVEL_1_KEYWORDS = (
    "SELECT ",
    "INTO ",
    "FROM ",
    "WHERE",
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


def is_non_paragraph_word(
    word: str,
) -> bool:
    """
    Return True when the supplied word is a COBOL verb or keyword that should
    not be treated as a paragraph name.
    """
    clean_word = str(word or "").strip().upper()
    return clean_word in NON_PARAGRAPH_WORDS


def starts_with_procedure_verb(
    statement: str,
) -> bool:
    """
    Return True when the statement starts with a known PROCEDURE DIVISION verb.
    """
    clean_statement = str(statement or "").strip().upper()

    if not clean_statement:
        return False

    return clean_statement.startswith(PROCEDURE_VERBS)


def starts_with_sql_level_1_keyword(
    statement: str,
) -> bool:
    """
    Return True when the SQL statement starts with a level-1 SQL keyword.
    """
    clean_statement = str(statement or "").strip().upper()

    if not clean_statement:
        return False

    return clean_statement.startswith(SQL_LEVEL_1_KEYWORDS)


def starts_with_sql_level_2_keyword(
    statement: str,
) -> bool:
    """
    Return True when the SQL statement starts with a level-2 SQL keyword.
    """
    clean_statement = str(statement or "").strip().upper()

    if not clean_statement:
        return False

    return clean_statement.startswith(SQL_LEVEL_2_KEYWORDS)