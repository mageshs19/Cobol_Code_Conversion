"""
IDMS regex patterns.

COBOL parser and IDMS transformers must import these patterns instead of
defining IDMS operation regex inside parser or transformer classes.
"""

import re


OBTAIN_CALC_PATTERN = re.compile(
    r"\bOBTAIN\s+(?:KEEP\s+)?(?P<record>[A-Z0-9-]+)\s+CALC\b",
    flags=re.IGNORECASE,
)


OBTAIN_CALC_REVERSED_PATTERN = re.compile(
    r"\bOBTAIN\s+(?:KEEP\s+)?CALC\s+(?P<record>[A-Z0-9-]+)\b",
    flags=re.IGNORECASE,
)


OBTAIN_FIRST_NEXT_PATTERN = re.compile(
    r"\bOBTAIN\s+(?:KEEP\s+)?(?P<mode>FIRST|NEXT)\s+"
    r"(?P<record>[A-Z0-9-]+)\s+WITHIN\s+(?P<set>[A-Z0-9-]+)\b",
    flags=re.IGNORECASE,
)


OBTAIN_OWNER_PATTERN = re.compile(
    r"\bOBTAIN\s+OWNER\s+WITHIN\s+(?P<set>[A-Z0-9-]+)\b",
    flags=re.IGNORECASE,
)


FIND_FIRST_PATTERN = re.compile(
    r"\bFIND\s+FIRST\s+(?P<record>[A-Z0-9-]+)?\s*WITHIN\s+(?P<set>[A-Z0-9-]+)\b",
    flags=re.IGNORECASE,
)


STORE_PATTERN = re.compile(
    r"\bSTORE\s+(?P<record>[A-Z0-9-]+)\b",
    flags=re.IGNORECASE,
)


MODIFY_PATTERN = re.compile(
    r"\bMODIFY\s+(?P<record>[A-Z0-9-]+)\b",
    flags=re.IGNORECASE,
)


ERASE_PATTERN = re.compile(
    r"\bERASE\s+(?P<record>[A-Z0-9-]+)\b",
    flags=re.IGNORECASE,
)


READY_PATTERN = re.compile(
    r"^\s*READY\b",
    flags=re.IGNORECASE,
)


READY_UPDATE_PATTERN = re.compile(
    r"\bREADY\s+AREA\s+(?P<record>[A-Z0-9-]+).*UPDATE\b",
    flags=re.IGNORECASE,
)


FINISH_PATTERN = re.compile(
    r"^\s*FINISH\b",
    flags=re.IGNORECASE,
)


COMMIT_PATTERN = re.compile(
    r"^\s*COMMIT\b",
    flags=re.IGNORECASE,
)


BIND_STATEMENT_PATTERN = re.compile(
    r"^\s*BIND\b",
    flags=re.IGNORECASE,
)


FIND_CURRENT_PATTERN = re.compile(
    r"^\s*FIND\s+CURRENT\b",
    flags=re.IGNORECASE,
)


CONNECT_STATEMENT_PATTERN = re.compile(
    r"^\s*CONNECT\b",
    flags=re.IGNORECASE,
)


DISCONNECT_STATEMENT_PATTERN = re.compile(
    r"^\s*DISCONNECT\b",
    flags=re.IGNORECASE,
)


USAGE_MODE_PATTERN = re.compile(
    r"\bUSAGE-MODE\s+IS\s+(UPDATE|RETRIEVAL)\b",
    flags=re.IGNORECASE,
)


IDMS_STATUS_PERFORM_PATTERN = re.compile(
    r"\bPERFORM\b.*\bIDMS-STATUS\b",
    flags=re.IGNORECASE,
)


IDMS_ABORT_PERFORM_PATTERN = re.compile(
    r"\bPERFORM\b.*\bIDMS-ABORT\b",
    flags=re.IGNORECASE,
)


DB_REC_NOT_FOUND_TOKEN_PATTERN = re.compile(
    r"\bDB-REC-NOT-FOUND\b",
    flags=re.IGNORECASE,
)


DB_END_OF_SET_TOKEN_PATTERN = re.compile(
    r"\bDB-END-OF-SET\b",
    flags=re.IGNORECASE,
)


ON_DB_REC_NOT_FOUND_PATTERN = re.compile(
    r"^\s*ON\s+DB-REC-NOT-FOUND\s+(?P<statement>.+?)\.?\s*$",
    flags=re.IGNORECASE,
)


IDMS_DECLARATIVE_OR_CONTROL_PATTERNS = [
    re.compile(r"^\s*IDMS-CONTROL\s+SECTION\b", flags=re.IGNORECASE),
    re.compile(r"^\s*PROTOCOL\b", flags=re.IGNORECASE),
    re.compile(r"^\s*IDMS-RECORDS\s+WITHIN\b", flags=re.IGNORECASE),
    re.compile(r"^\s*SCHEMA\s+SECTION\b", flags=re.IGNORECASE),
    re.compile(r"^\s*DB\s+[A-Z0-9-]+\s+WITHIN\s+[A-Z0-9-]+\b", flags=re.IGNORECASE),
    re.compile(r"^\s*COPY\s+IDMS\b", flags=re.IGNORECASE),
]