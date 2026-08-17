"""
DB2 validation rules.

This file contains DB2 validation constants only.

Rules belong in rules/, not patterns/.

No regex patterns should be defined here.
No parser, service, transformer, generator, validator, or composer logic
should be placed here.

Use this file for DB2 validation rule values that are shared by validators
or other runtime modules.
"""

REQUIRED_DB2_TOKENS = (
    "EXEC SQL",
    "SQLCA",
    "END-EXEC",
)