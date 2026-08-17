"""
DB2 infrastructure and generated block regex patterns.

DB2 infrastructure generators, validators, transformers, and composers
must import these patterns instead of defining DB2 regex internally.

This file must contain regex patterns only.

Do not place validation token lists, business rules, conversion rules,
or layout constants in this file.
"""

import re

SQLCA_TOKEN_PATTERN = re.compile(
    r"\bSQLCA\b",
    flags=re.IGNORECASE,
)

SQLERRWS_TOKEN_PATTERN = re.compile(
    r"\bSQLERRWS\b",
    flags=re.IGNORECASE,
)

SQL_LOCATION_PATTERN = re.compile(
    r"\bSQL-LOCATION\b",
    flags=re.IGNORECASE,
)

SQL_ERROR_PARAGRAPH_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s+)?(SQL-ERROR|SQLERROR)\s*\.\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)

SQL_ERROR_PERFORM_PATTERN = re.compile(
    r"\bPERFORM\s+(SQL-ERROR|SQLERROR)\s*\.?",
    flags=re.IGNORECASE,
)

DB2_CURSOR_BLOCK_MARKER_PATTERN = re.compile(
    r"DB2 GENERATED CURSOR OPEN FETCH CLOSE PARAGRAPHS",
    flags=re.IGNORECASE,
)

DB2_INFRASTRUCTURE_MARKER_PATTERN = re.compile(
    r"DB2 SQLCA, SQL ERROR WORKING STORAGE, DCLGEN INCLUDES, AND CURSOR FLAGS",
    flags=re.IGNORECASE,
)

DB2_CURSOR_DECLARATIONS_MARKER_PATTERN = re.compile(
    r"DB2 GENERATED CURSOR DECLARATIONS",
    flags=re.IGNORECASE,
)

DB2_CURSOR_FLAGS_MARKER_PATTERN = re.compile(
    r"DB2 GENERATED CURSOR FLAGS",
    flags=re.IGNORECASE,
)

DB2_SQL_ERROR_LOCATION_MARKER_PATTERN = re.compile(
    r"DB2 GENERATED SQL ERROR LOCATION",
    flags=re.IGNORECASE,
)

PROCEDURE_DIVISION_PATTERN = re.compile(
    r"(^\s*(?:\d{6}\s+)?PROCEDURE\s+DIVISION\b.*\.?\s*(?:\d{8})?\s*$)",
    flags=re.IGNORECASE | re.MULTILINE,
)

LINKAGE_SECTION_PATTERN = re.compile(
    r"(^\s*(?:\d{6}\s+)?LINKAGE\s+SECTION\.\s*(?:\d{8})?\s*$)",
    flags=re.IGNORECASE | re.MULTILINE,
)

WORKING_STORAGE_PATTERN = re.compile(
    r"(^\s*(?:\d{6}\s+)?WORKING-STORAGE\s+SECTION\.\s*(?:\d{8})?\s*$)",
    flags=re.IGNORECASE | re.MULTILINE,
)

DATA_DIVISION_PATTERN = re.compile(
    r"(^\s*(?:\d{6}\s+)?DATA\s+DIVISION\.\s*(?:\d{8})?\s*$)",
    flags=re.IGNORECASE | re.MULTILINE,
)

END_PROGRAM_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s+)?END\s+PROGRAM\b.*$",
    flags=re.IGNORECASE | re.MULTILINE,
)

EXEC_SQL_START_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s+)?EXEC\s+SQL\b",
    flags=re.IGNORECASE,
)

EXEC_SQL_END_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s+)?END-EXEC\.?\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE,
)

SQL_INCLUDE_PATTERN = re.compile(
    r"\bINCLUDE\s+(?P<include_name>[A-Z0-9_-]+)\b",
    flags=re.IGNORECASE,
)

SQLCA_INCLUDE_PATTERN = re.compile(
    r"\bINCLUDE\s+SQLCA\b",
    flags=re.IGNORECASE,
)

SQLERRWS_INCLUDE_PATTERN = re.compile(
    r"\bINCLUDE\s+SQLERRWS\b",
    flags=re.IGNORECASE,
)

DECLARE_CURSOR_PATTERN = re.compile(
    r"\bDECLARE\s+(?P<cursor_name>[A-Z0-9_-]+)\s+CURSOR\b",
    flags=re.IGNORECASE,
)

OPEN_CURSOR_PATTERN = re.compile(
    r"\bOPEN\s+(?P<cursor_name>[A-Z0-9_-]+)\b",
    flags=re.IGNORECASE,
)

FETCH_CURSOR_PATTERN = re.compile(
    r"\bFETCH\s+(?P<cursor_name>[A-Z0-9_-]+)\b",
    flags=re.IGNORECASE,
)

CLOSE_CURSOR_PATTERN = re.compile(
    r"\bCLOSE\s+(?P<cursor_name>[A-Z0-9_-]+)\b",
    flags=re.IGNORECASE,
)

SQLCODE_PATTERN = re.compile(
    r"\bSQLCODE\b",
    flags=re.IGNORECASE,
)

SQLCODE_SUCCESS_PATTERN = re.compile(
    r"\bSQLCODE\s*=\s*0\b",
    flags=re.IGNORECASE,
)

SQLCODE_NOT_FOUND_PATTERN = re.compile(
    r"\bSQLCODE\s*=\s*100\b",
    flags=re.IGNORECASE,
)

SQLCODE_ERROR_PATTERN = re.compile(
    r"\bSQLCODE\s*(?:NOT\s*=\s*0|<\s*0|>\s*0)\b",
    flags=re.IGNORECASE,
)

COMMIT_PATTERN = re.compile(
    r"\bCOMMIT\b",
    flags=re.IGNORECASE,
)

ROLLBACK_PATTERN = re.compile(
    r"\bROLLBACK\b",
    flags=re.IGNORECASE,
)