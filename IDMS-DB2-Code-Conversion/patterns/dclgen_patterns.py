"""
DCLGEN regex patterns.

Parser classes must import these patterns instead of defining regex inside
parser classes.
"""

import re


DECLARE_TABLE_PATTERN = re.compile(
    r"EXEC\s+SQL\s+DECLARE\s+([A-Z0-9_. #$@]+)\s+TABLE",
    flags=re.IGNORECASE,
)


DECLARE_TABLE_ALT_PATTERN = re.compile(
    r"\bDECLARE\s+([A-Z0-9_. #$@]+)\s+TABLE\b",
    flags=re.IGNORECASE,
)


DCLGEN_TABLE_COMMENT_PATTERN = re.compile(
    r"\bDCLGEN\s+TABLE\s*$\s*([A-Z0-9_. #$@]+)\s*$",
    flags=re.IGNORECASE,
)


COBOL_GROUP_PATTERN = re.compile(
    r"^\s*\*?\s*01\s+(DCL[A-Z0-9-]+)\.?\s*$",
    flags=re.IGNORECASE,
)


COBOL_FIELD_PATTERN = re.compile(
    r"^\s*(0[2-9]|[1-4][0-9]|77)\s+"
    r"([A-Z][A-Z0-9-]*)\b(?P<body>.*)$",
    flags=re.IGNORECASE,
)


DCLGEN_PIC_PATTERN = re.compile(
    r"\bPIC(?:TURE)?\s+(?:IS\s+)?"
    r"(?P<pic>[A-Z0-9SV() .,+\-]+)",
    flags=re.IGNORECASE,
)


DCLGEN_USAGE_PATTERN = re.compile(
    r"\b(?:USAGE\s+(?:IS\s+)?)?"
    r"(COMP-3|COMP|COMP-1|COMP-2|COMP-4|COMP-5|BINARY|PACKED-DECIMAL|DISPLAY)\b",
    flags=re.IGNORECASE,
)


SQL_NAME_CLEANUP_PATTERN = re.compile(
    r"[^A-Z0-9_#$@]+",
    flags=re.IGNORECASE,
)


MULTIPLE_UNDERSCORE_PATTERN = re.compile(
    r"_+",
    flags=re.IGNORECASE,
)


VALID_SQL_COLUMN_NAME_PATTERN = re.compile(
    r"^[A-Z][A-Z0-9_#$@]*$",
    flags=re.IGNORECASE,
)