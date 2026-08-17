"""
PIC and MOVE regex patterns.

PIC length auto-fixer and production validators must import these patterns
instead of defining regex internally.
"""

import re


DATA_ENTRY_START_PATTERN = re.compile(
    r"^\s*(?P<level>0[1-9]|[1-4][0-9]|77)\s+"
    r"(?P<name>[A-Z][A-Z0-9-]*)\b"
    r"(?P<rest>.*)$",
    flags=re.IGNORECASE,
)


NUMERIC_PIC_PATTERN = re.compile(
    r"\bPIC(?:TURE)?\s+(?:IS\s+)?"
    r"(?P<pic>S?9(?:$(?P<len>\d+)$)?)"
    r"(?P<trailing>[^.\n]*)"
    r"(?P<dot>\.)?",
    flags=re.IGNORECASE,
)


MOVE_PATTERN = re.compile(
    r"\bMOVE\s+"
    r"(?P<source>[A-Z][A-Z0-9-]*(?:\.[A-Z][A-Z0-9-]*)?)"
    r"(?:\s+OF\s+[A-Z][A-Z0-9-]*)?"
    r"\s+TO\s+"
    r"(?P<target>[A-Z][A-Z0-9-]*(?:\.[A-Z][A-Z0-9-]*)?)\b",
    flags=re.IGNORECASE,
)