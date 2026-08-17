"""
DB2 infrastructure and generated block patterns.

DB2 infrastructure generators, validators, and composers must import these
patterns instead of defining DB2 regex internally.
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
    r"^\s*(?:\d{6}\s+)?(SQL-ERROR|SQLERROR)\.\s*(?:\d{8})?\s*$",
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


REQUIRED_DB2_TOKENS = (
    "EXEC SQL",
    "SQLCA",
    "END-EXEC",
)