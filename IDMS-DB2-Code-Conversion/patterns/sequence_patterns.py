"""
Manual COBOL sequence number patterns.

The converter must support both:
- unsequenced COBOL
- manual-style sequenced COBOL:
  000010 COBOL STATEMENT 00010000
"""

import re


LEFT_SEQUENCE_PATTERN = re.compile(
    r"^\s*\d{6}\s+(?P<body>.*)$",
    flags=re.IGNORECASE,
)


RIGHT_SEQUENCE_PATTERN = re.compile(
    r"(?P<body>.*?)(?:\s+(?P<right>\d{8}))\s*$",
    flags=re.IGNORECASE,
)


FULL_SEQUENCE_PATTERN = re.compile(
    r"^\s*(?P<left>\d{6})\s+(?P<body>.*?)(?:\s+(?P<right>\d{8}))?\s*$",
    flags=re.IGNORECASE,
)


SEQUENCE_ONLY_PATTERN = re.compile(
    r"^\s*(\d{6}|\d{8})\s*$",
    flags=re.IGNORECASE,
)


def strip_sequence_numbers(
    line: str,
) -> str:
    text = str(line or "").rstrip()

    right_match = RIGHT_SEQUENCE_PATTERN.match(text)

    if right_match:
        text = right_match.group("body").rstrip()

    left_match = LEFT_SEQUENCE_PATTERN.match(text)

    if left_match:
        text = left_match.group("body")

    return text.strip()


def compose_manual_sequence_line(
    left_sequence: str,
    body: str,
    right_sequence: str,
) -> str:
    clean_body = str(body or "")

    if not clean_body:
        return f"{left_sequence} {right_sequence}"

    if len(clean_body) >= 64:
        return f"{left_sequence} {clean_body} {right_sequence}"

    return f"{left_sequence} {clean_body:<64} {right_sequence}"