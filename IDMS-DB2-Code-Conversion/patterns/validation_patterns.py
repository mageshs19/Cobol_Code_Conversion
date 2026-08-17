"""
Validation regex patterns.

Validators must import these patterns instead of defining regex internally.
"""

import re


TODO_HOST_VARIABLE_PATTERN = re.compile(
    r":\s*TODO-HOST-VARIABLE",
    flags=re.IGNORECASE,
)


TODO_DB2_PATTERN = re.compile(
    r"TODO\s+DB2",
    flags=re.IGNORECASE,
)


ERROR_DB2_PATTERN = re.compile(
    r"ERROR\s+DB2\s*:",
    flags=re.IGNORECASE,
)


UNABLE_TO_DECLARE_CURSOR_PATTERN = re.compile(
    r"UNABLE\s+TO\s+DECLARE\s+CURSOR",
    flags=re.IGNORECASE,
)


NO_FETCH_HOST_VARIABLES_PATTERN = re.compile(
    r"NO\s+FETCH\s+HOST\s+VARIABLES\s+MAPPED",
    flags=re.IGNORECASE,
)


FORBIDDEN_EXECUTABLE_IDMS_PATTERNS = [
    re.compile(r"^BIND\b", flags=re.IGNORECASE),
    re.compile(r"^READY\b", flags=re.IGNORECASE),
    re.compile(r"^OBTAIN\b", flags=re.IGNORECASE),
    re.compile(r"^FIND\s+CURRENT\b", flags=re.IGNORECASE),
    re.compile(r"^FIND\s+FIRST\b", flags=re.IGNORECASE),
    re.compile(r"^STORE\b", flags=re.IGNORECASE),
    re.compile(r"^MODIFY\b", flags=re.IGNORECASE),
    re.compile(r"^ERASE\b", flags=re.IGNORECASE),
    re.compile(r"^CONNECT\b", flags=re.IGNORECASE),
    re.compile(r"^DISCONNECT\b", flags=re.IGNORECASE),
    re.compile(
        r"^PERFORM\s+[A-Z0-9-]*IDMS-STATUS\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"^PERFORM\s+[A-Z0-9-]*IDMS-ABORT\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\bUSAGE-MODE\s+IS\s+UPDATE\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\bUSAGE-MODE\s+IS\s+RETRIEVAL\b",
        flags=re.IGNORECASE,
    ),
]


FORBIDDEN_IDMS_DECLARATIVE_PATTERNS = [
    re.compile(
        r"^IDMS-CONTROL\s+SECTION\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"^PROTOCOL\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"^IDMS-RECORDS\s+WITHIN\s+WORKING-STORAGE\s+SECTION\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"^SCHEMA\s+SECTION\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"^DB[A-Z0-9-]+\s+WITHIN\s+[A-Z0-9-]+\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"^COPY\s+IDMS\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"^COPY\s+IDMS\s+IDMS-STATUS\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"^COPY\s+IDMS\s+SUBSCHEMA-BINDS\b",
        flags=re.IGNORECASE,
    ),
]