"""
Business flow preservation rules.

These constants describe how original COBOL business logic should be preserved.
No regex or runtime logic belongs in this file.
"""

BUSINESS_FLOW_RULES = [
    "Preserve original COBOL business logic unless replacing IDMS database statements.",
    "Do not rewrite unrelated COBOL statements.",
    "Do not corrupt COBOL headers such as DATE-WRITTEN, AUTHOR, or PROGRAM-ID.",
    "Replace only IDMS database access logic with DB2 embedded SQL logic.",
    "Retain paragraph structure unless a database replacement requires a local block.",
]