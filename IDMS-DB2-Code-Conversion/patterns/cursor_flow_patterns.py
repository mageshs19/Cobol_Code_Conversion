"""
Cursor flow regex patterns.
"""

import re


PERFORM_CURSOR_PARAGRAPH_PATTERN = re.compile(
    r"^\s*PERFORM\s+"
    r"(?P<number>\d{3})-"
    r"(?P<operation>OPEN|FETCH|CLOSE)-"
    r"(?P<cursor>[A-Z0-9-]+)"
    r"\.?\s*$",
    flags=re.IGNORECASE,
)


PERFORM_BUSINESS_PARAGRAPH_PATTERN = re.compile(
    r"^\s*PERFORM\s+"
    r"(?P<paragraph>[A-Z0-9][A-Z0-9-]*)"
    r"\.?\s*$",
    flags=re.IGNORECASE,
)


UNTIL_SQLCODE_100_PATTERN = re.compile(
    r"^\s*UNTIL\s+SQLCODE\s*=\s*100\.?\s*$",
    flags=re.IGNORECASE,
)


CURSOR_PARAGRAPH_HEADER_PATTERN = re.compile(
    r"^\s*"
    r"(?P<number>\d{3})-"
    r"(?P<operation>OPEN|FETCH|CLOSE)-"
    r"(?P<cursor>[A-Z0-9-]+)"
    r"\.\s*$",
    flags=re.IGNORECASE,
)


ANY_PARAGRAPH_HEADER_PATTERN = re.compile(
    r"^\s*[A-Z0-9][A-Z0-9-]*\.\s*$",
    flags=re.IGNORECASE,
)


WHEN_ZERO_PATTERN = re.compile(
    r"^\s*WHEN\s+ZERO\s*$",
    flags=re.IGNORECASE,
)


CONTINUE_PATTERN = re.compile(
    r"^\s*CONTINUE\.?\s*$",
    flags=re.IGNORECASE,
)