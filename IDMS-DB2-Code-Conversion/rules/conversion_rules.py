"""
General IDMS to DB2 conversion rules.
"""


CONVERSION_RULES = [
    "Preserve original COBOL business flow.",
    "Replace IDMS database operations with DB2-compatible SQL logic.",
    "Do not fabricate DB2 SQL when Sheet Mapping metadata is missing.",
    "When mapping metadata is missing, generate a clear DB2 conversion-skipped comment.",
    "When removing executable PROCEDURE DIVISION IDMS code, add CONTINUE.",
]


MISSING_MAPPING_RULES = [
    "FFRECAB conversion requires Sheet Mapping and DCLGEN metadata.",
    "If Sheet Mapping entry is missing, conversion must be skipped with a clear comment.",
    "Missing Sheet Mapping metadata is an input-data blocker, not a Python logic failure.",
]