"""
DB2 date comparison regex patterns.

These patterns support conservative DB2 date realignment before comparing
DB2 date host fields with COBOL numeric date fields like PARMDATE.
"""

import re


DB2_DATE_COMPARISON_PATTERN = re.compile(
    r"^(?P<indent>\s*)IF\s+"
    r"(?P<field>(?:DA|DT)-[A-Z0-9-]+)"
    r"\s+OF\s+"
    r"(?P<group>DCL[A-Z0-9-]+)"
    r"\s+"
    r"(?P<condition>.+\bPARMDATE\b.*)$",
    flags=re.IGNORECASE,
)


WORKING_STORAGE_SECTION_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s+)?WORKING-STORAGE\s+SECTION\.\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE,
)


LINKAGE_SECTION_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s+)?LINKAGE\s+SECTION\.\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE,
)


PROCEDURE_DIVISION_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s+)?PROCEDURE\s+DIVISION\b.*\.?\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE,
)


DATE_HELPER_FIELD_PATTERN = re.compile(
    r"\bHELP-(?:DA|DT)-[A-Z0-9-]+\b",
    flags=re.IGNORECASE,
)


DATE_WORKING_STORAGE_MARKER_PATTERN = re.compile(
    r"DB2 DATE COMPARISON WORKING STORAGE",
    flags=re.IGNORECASE,
)