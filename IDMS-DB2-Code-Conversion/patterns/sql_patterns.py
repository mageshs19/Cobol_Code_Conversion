"""
SQL regex patterns and formatting keyword groups.

SQL generators, formatters, validators, and timestamp/audit components must
import SQL patterns from here instead of defining regex internally.
"""

import re


EXEC_SQL_PATTERN = re.compile(
    r"^\s*EXEC\s+SQL\b",
    flags=re.IGNORECASE,
)


END_EXEC_PATTERN = re.compile(
    r"^\s*END-EXEC\.?\s*$",
    flags=re.IGNORECASE,
)


INCLUDE_PATTERN = re.compile(
    r"\bINCLUDE\s+(?P<table>[A-Z][A-Z0-9_]*)\b",
    flags=re.IGNORECASE,
)


SELECT_SQL_PATTERN = re.compile(
    r"\bSELECT\b",
    flags=re.IGNORECASE,
)


FROM_SQL_PATTERN = re.compile(
    r"\bFROM\s+(?P<table>[A-Z][A-Z0-9_]*)\b",
    flags=re.IGNORECASE,
)


WHERE_SQL_PATTERN = re.compile(
    r"\bWHERE\b",
    flags=re.IGNORECASE,
)


UPDATE_SQL_PATTERN = re.compile(
    r"\bUPDATE\s+(?P<table>[A-Z][A-Z0-9_]*)\b",
    flags=re.IGNORECASE,
)


INSERT_SQL_PATTERN = re.compile(
    r"\bINSERT\s+INTO\s+(?P<table>[A-Z][A-Z0-9_]*)\b",
    flags=re.IGNORECASE,
)


DELETE_SQL_PATTERN = re.compile(
    r"\bDELETE\s+FROM\s+(?P<table>[A-Z][A-Z0-9_]*)\b",
    flags=re.IGNORECASE,
)


OPEN_CURSOR_PATTERN = re.compile(
    r"\bOPEN\s+(?P<cursor>[A-Z][A-Z0-9-]*)\b",
    flags=re.IGNORECASE,
)


FETCH_CURSOR_PATTERN = re.compile(
    r"\bFETCH\s+(?P<cursor>[A-Z][A-Z0-9-]*)\b",
    flags=re.IGNORECASE,
)


CLOSE_CURSOR_PATTERN = re.compile(
    r"\bCLOSE\s+(?P<cursor>[A-Z][A-Z0-9-]*)\b",
    flags=re.IGNORECASE,
)


HOST_REFERENCE_PATTERN = re.compile(
    r":\s*(?P<group>DCL[A-Z0-9-]+)\s*\.\s*(?P<field>[A-Z][A-Z0-9-]*)",
    flags=re.IGNORECASE,
)


SQL_KEYWORDS_ZERO_INDENT = (
    "EXEC SQL",
    "END-EXEC",
)


SQL_KEYWORDS_LEVEL_1 = (
    "INCLUDE ",
    "DECLARE ",
    "SELECT",
    "INTO",
    "FROM ",
    "WHERE",
    "ORDER BY",
    "GROUP BY",
    "HAVING",
    "FETCH ",
    "OPEN ",
    "CLOSE ",
    "COMMIT",
    "ROLLBACK",
    "INSERT ",
    "UPDATE ",
    "DELETE ",
    "SET ",
    "VALUES",
    "FOR READ ONLY",
)


SQL_KEYWORDS_LEVEL_2 = (
    "AND ",
    "OR ",
)