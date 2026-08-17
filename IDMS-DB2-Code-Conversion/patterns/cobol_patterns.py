"""
COBOL regex patterns.

These patterns are shared by parsers, analyzers, transformers, composers,
and formatters. Keep regex definitions centralized here so runtime modules
do not define their own duplicate COBOL patterns.
"""

import re


PROGRAM_ID_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s+)?PROGRAM-ID\.\s*([A-Z0-9-]+)\.?\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)


DIVISION_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s+)?"
    r"(IDENTIFICATION|ENVIRONMENT|DATA|PROCEDURE)"
    r"\s+DIVISION\b.*\.?\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE,
)


IDENTIFICATION_DIVISION_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s+)?IDENTIFICATION\s+DIVISION\b.*\.?\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)


ENVIRONMENT_DIVISION_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s+)?ENVIRONMENT\s+DIVISION\b.*\.?\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)


DATA_DIVISION_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s+)?DATA\s+DIVISION\b.*\.?\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)


PROCEDURE_DIVISION_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s+)?PROCEDURE\s+DIVISION\b.*\.?\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)


WORKING_STORAGE_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s+)?WORKING-STORAGE\s+SECTION\.\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)


LINKAGE_SECTION_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s+)?LINKAGE\s+SECTION\.\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)


SECTION_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s+)?[A-Z0-9][A-Z0-9-]*\s+SECTION\.\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE,
)


PARAGRAPH_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s+)?(?P<name>[A-Z0-9][A-Z0-9-]*)\.\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE,
)


END_PROGRAM_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s+)?END\s+PROGRAM\b.*\.?\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)


STOP_RUN_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s+)?STOP\s+RUN\.?\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE,
)


GOBACK_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s+)?GOBACK\.?\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE,
)


COMMENT_OR_SKIP_PATTERN = re.compile(
    r"^\s*(\*|/|EJECT\b|SKIP[0-9]*\b)",
    flags=re.IGNORECASE,
)


COMMENT_PATTERN = re.compile(
    r"^\s*\*",
    flags=re.IGNORECASE,
)


PAGE_EJECT_PATTERN = re.compile(
    r"^\s*/\s*$",
    flags=re.IGNORECASE,
)


SEQUENCE_ONLY_PATTERN = re.compile(
    r"^\s*(\d{6}|\d{8})\s*$",
    flags=re.IGNORECASE,
)


LEFT_SEQUENCE_PATTERN = re.compile(
    r"^\s*(?P<seq>\d{6})(?P<body>\s+.*)$",
    flags=re.IGNORECASE,
)


RIGHT_SEQUENCE_PATTERN = re.compile(
    r"(?P<body>.*?)\s+(?P<right>\d{8})\s*$",
    flags=re.IGNORECASE,
)


DATA_ENTRY_START_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s+)?"
    r"(?P<level>0[1-9]|[1-4][0-9]|66|77|88)"
    r"\s+(?P<name>[A-Z0-9][A-Z0-9-]*)\b"
    r"(?P<rest>.*)$",
    flags=re.IGNORECASE,
)


FILE_DESCRIPTOR_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s+)?(FD|SD)\s+",
    flags=re.IGNORECASE,
)


SELECT_FILE_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s+)?SELECT\s+",
    flags=re.IGNORECASE,
)


SQL_ERROR_PARAGRAPH_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s+)?(SQL-ERROR|SQLERROR)\.\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)


SQL_ERROR_DOT_PATTERN = re.compile(
    r"\bPERFORM\s+(SQL-ERROR|SQLERROR)\s*\.?",
    flags=re.IGNORECASE,
)


DB2_INFRASTRUCTURE_MARKER_PATTERN = re.compile(
    r"DB2 SQLCA, SQL ERROR WORKING STORAGE, DCLGEN INCLUDES, AND CURSOR FLAGS",
    flags=re.IGNORECASE,
)


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
    "END-IF",
    "END-EVALUATE",
    "END-PERFORM",
    "END-READ",
    "END-STRING",
    "END-UNSTRING",
    "END-WRITE",
    "END-EXEC",
    "EJECT",
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
