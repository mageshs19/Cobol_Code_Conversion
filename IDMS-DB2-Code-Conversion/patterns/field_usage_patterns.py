"""
Field usage regex patterns.

This module contains regex patterns only.

Runtime analyzers, transformers, validators, composers, and services must
import these patterns instead of defining duplicate regex internally.

Rules:
- No business rules in this file.
- No service logic in this file.
- No parsing orchestration in this file.
- Regex patterns only.
"""

import re


QUALIFIED_REFERENCE_PATTERN = re.compile(
    r"\b(?P<field>[A-Z][A-Z0-9-]*)\s+(?:OF|IN)\s+"
    r"(?P<record>[A-Z][A-Z0-9-]*)\b",
    flags=re.IGNORECASE,
)

DCLGEN_OF_PATTERN = re.compile(
    r":?\s*(?P<field>[A-Z][A-Z0-9-]*)\s+OF\s+"
    r"(?P<group>DCL[A-Z0-9-]+)",
    flags=re.IGNORECASE,
)

DCLGEN_DOT_PATTERN = re.compile(
    r":\s*(?P<group>DCL[A-Z0-9-]+)\.(?P<field>[A-Z][A-Z0-9-]*)",
    flags=re.IGNORECASE,
)

MOVE_STATEMENT_PATTERN = re.compile(
    r"^\s*MOVE\s+(?P<source>.+?)\s+TO\s+(?P<target>.+?)(?:\.|\s*)$",
    flags=re.IGNORECASE,
)

CONDITION_STATEMENT_PATTERN = re.compile(
    r"^\s*(IF|WHEN|UNTIL|EVALUATE)\b",
    flags=re.IGNORECASE,
)

OUTPUT_STATEMENT_PATTERN = re.compile(
    r"^\s*(DISPLAY|WRITE|REWRITE|RETURN|GOBACK|EXIT|CALL)\b",
    flags=re.IGNORECASE,
)

COMMENT_OR_BLANK_PATTERN = re.compile(
    r"^\s*(?:$|\*)",
    flags=re.IGNORECASE,
)

EXEC_SQL_START_PATTERN = re.compile(
    r"^\s*EXEC\s+SQL\b",
    flags=re.IGNORECASE,
)

EXEC_SQL_END_PATTERN = re.compile(
    r"^\s*END-EXEC\.?\s*$",
    flags=re.IGNORECASE,
)