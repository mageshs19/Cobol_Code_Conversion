"""
Cursor generation rules.

This file contains cursor authority rules and paragraph numbering rules.

Rules belong in rules/, not patterns/.

No regex patterns should be defined here.
No parser, service, transformer, or generator logic should be placed here.
"""

CURSOR_AUTHORITY_RULES = [
    "Cursor names are derived from Sheet Mapping DB2 record/table names.",
    "Cursor names are not derived from IDMS set names.",
    "Generated cursor OPEN, FETCH, and CLOSE paragraphs are placed near the end.",
    "SQL-ERROR paragraph is required when cursor code performs SQL error handling.",
]

CURSOR_PARAGRAPH_NUMBERING = {
    1: {
        "open": 710,
        "fetch": 720,
        "close": 730,
    },
    2: {
        "open": 810,
        "fetch": 820,
        "close": 830,
    },
    3: {
        "open": 910,
        "fetch": 920,
        "close": 930,
    },
}


def cursor_paragraph_number(
    cursor_order: int,
    operation: str,
) -> int:
    operation_key = str(operation or "").strip().lower()

    if cursor_order not in CURSOR_PARAGRAPH_NUMBERING:
        raise ValueError(f"Unsupported cursor order: {cursor_order}")

    if operation_key not in CURSOR_PARAGRAPH_NUMBERING[cursor_order]:
        raise ValueError(f"Unsupported cursor operation: {operation}")

    return CURSOR_PARAGRAPH_NUMBERING[cursor_order][operation_key]