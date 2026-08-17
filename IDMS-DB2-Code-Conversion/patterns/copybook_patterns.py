"""
Copybook regex patterns.

Copybook parser logic must import these patterns instead of defining regex
directly inside parser classes.
"""

import re


COPYBOOK_FIELD_PATTERN = re.compile(
    r"^\s*(?P<level>0[1-9]|[1-4][0-9]|66|77|88)\s+"
    r"(?P<name>[A-Z0-9-]+)"
    r"(?P<rest>.*)$",
    flags=re.IGNORECASE,
)


COPYBOOK_PIC_PATTERN = re.compile(
    r"\bPIC(?:TURE)?\s+"
    r"(?P<pic>[SXA9VZ0-9\(\)\+\-\.,/]+)",
    flags=re.IGNORECASE,
)


COPYBOOK_USAGE_PATTERN = re.compile(
    r"\b(?:USAGE\s+IS\s+|USAGE\s+)?"
    r"(?P<usage>COMP-3|COMPUTATIONAL-3|COMP|COMPUTATIONAL|BINARY|DISPLAY|PACKED-DECIMAL)\b",
    flags=re.IGNORECASE,
)


COPYBOOK_OCCURS_PATTERN = re.compile(
    r"\bOCCURS\s+(?P<occurs>[0-9]+)\s+(?:TIMES\b)?",
    flags=re.IGNORECASE,
)


COPYBOOK_COMMENT_OR_SKIP_PATTERN = re.compile(
    r"^\s*(?:\*|/|EJECT\b|SKIP[0-9]*\b)",
    flags=re.IGNORECASE,
)