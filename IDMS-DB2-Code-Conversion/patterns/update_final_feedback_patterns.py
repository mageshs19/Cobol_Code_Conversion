"""
Update final feedback regex patterns.

This module contains regex patterns only.

No business rules.
No service logic.
No hardcoded program names, record names, DB2 table names, DB2 column names,
DCLGEN names, or host variable names.
"""

from __future__ import annotations

import re


EXEC_SQL_START_PATTERN = re.compile(
    r"^EXEC\s+SQL\b",
    flags=re.IGNORECASE,
)

EXEC_SQL_END_PATTERN = re.compile(
    r"^END-EXEC\.?$",
    flags=re.IGNORECASE,
)

UPDATE_STATEMENT_PATTERN = re.compile(
    r"^UPDATE\s+(?P<table>[A-Z0-9_]+)\b",
    flags=re.IGNORECASE,
)

FROM_STATEMENT_PATTERN = re.compile(
    r"^FROM\s+(?P<table>[A-Z0-9_]+)\b",
    flags=re.IGNORECASE,
)

SET_KEYWORD_PATTERN = re.compile(
    r"^SET$",
    flags=re.IGNORECASE,
)

WHERE_KEYWORD_PATTERN = re.compile(
    r"^WHERE$",
    flags=re.IGNORECASE,
)

SQL_SET_ASSIGNMENT_PATTERN = re.compile(
    r"^(?P<column>[A-Z][A-Z0-9_]+)\s*=\s*:"
    r"(?P<group>DCL[A-Z0-9]+)\."
    r"(?P<host>[A-Z][A-Z0-9-]*)"
    r"(?P<comma>,?)$",
    flags=re.IGNORECASE,
)

NON_SQL_DCL_DOT_REFERENCE_PATTERN = re.compile(
    r"\b(?P<group>DCL[A-Z0-9]+)\."
    r"(?P<host>[A-Z][A-Z0-9-]*)\b",
    flags=re.IGNORECASE,
)

DCLGEN_OF_REFERENCE_PATTERN = re.compile(
    r"\b(?P<host>[A-Z][A-Z0-9-]*)\s+OF\s+"
    r"(?P<group>DCL[A-Z0-9]+)\b",
    flags=re.IGNORECASE,
)

MOVE_TO_DCL_OF_REFERENCE_PATTERN = re.compile(
    r"^MOVE\s+(?P<source>.+?)\s+TO\s+"
    r"(?P<host>[A-Z][A-Z0-9-]*)\s+OF\s+"
    r"(?P<group>DCL[A-Z0-9]+)\.?$",
    flags=re.IGNORECASE,
)

MOVE_TO_BARE_RECORD_PATTERN = re.compile(
    r"^MOVE\s+(?P<source>SPACES?|SPACE)\s+TO\s+"
    r"(?P<target>[A-Z][A-Z0-9-]*)\.?$",
    flags=re.IGNORECASE,
)

INITIALIZE_DCL_PATTERN = re.compile(
    r"^INITIALIZE\s+(?P<group>DCL[A-Z0-9]+)\.?$",
    flags=re.IGNORECASE,
)

SQL_LOCATION_DB_OPERATION_PATTERN = re.compile(
    r"^MOVE\s+'(?P<operation>SELECT|UPDATE|INSERT|DELETE)-"
    r"(?P<label>[A-Z0-9-]+)'\s+TO\s+SQL-LOCATION\.?$",
    flags=re.IGNORECASE,
)

CONVERTED_DB2_OPERATION_COMMENT_PATTERN = re.compile(
    r"^(?P<prefix>\*?\s*DB2:\s+Converted\s+"
    r"(?P<operation>OBTAIN\s+CALC|MODIFY|STORE|ERASE|FIND|OBTAIN)"
    r"\s+for\s+)"
    r"(?P<label>[A-Z0-9-]+)"
    r"(?P<suffix>\.?\s*)$",
    flags=re.IGNORECASE,
)