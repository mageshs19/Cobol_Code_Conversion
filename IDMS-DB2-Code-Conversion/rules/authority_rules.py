"""
Authority rules.

These are the central project authority rules confirmed by the existing
conversion service comments.
"""


INPUT_AUTHORITY_RULES = [
    "Sheet Mapping is the authority for DB2 record/table names.",
    "Sheet Mapping is the authority for DB2 column names.",
    "DCLGEN is the authority for COBOL host variable names and PIC clauses.",
    "Original COBOL is the authority for business flow.",
    "Final output is resequenced in manual-style COBOL format.",
]


NO_HARDCODE_RULES = [
    "Do not hardcode business records in services.",
    "Do not hardcode DB2 tables in services.",
    "Do not hardcode DB2 columns in services.",
    "Do not hardcode DCLGEN names in services.",
    "Do not hardcode host variables in services.",
    "Do not hardcode parser column aliases inside parser classes.",
    "Do not hardcode regex patterns inside parser or service classes.",
]