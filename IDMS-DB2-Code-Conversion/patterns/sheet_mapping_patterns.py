"""
Sheet Mapping regex patterns.

Sheet Mapping parser logic must import these patterns instead of defining
regex directly inside parser classes.
"""

import re


HEADER_NON_ALPHANUMERIC_PATTERN = re.compile(
    r"[^A-Z0-9]+",
    flags=re.IGNORECASE,
)


HEADER_WHITESPACE_PATTERN = re.compile(
    r"\s+",
    flags=re.IGNORECASE,
)


CELL_WHITESPACE_PATTERN = re.compile(
    r"[ \t]+",
    flags=re.IGNORECASE,
)