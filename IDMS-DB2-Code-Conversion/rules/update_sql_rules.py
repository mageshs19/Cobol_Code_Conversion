"""
Update SQL generation rules.

This file contains rules/constants only.
No parser, formatter, generator, resolver, or transformer logic belongs here.

The goal is to keep UPDATE generation conservative and manual-style:
- Do not update every DCLGEN column.
- Update only fields proven to be changed by the COBOL business flow.
- For update flows, include only update audit fields.
- For CALC-style IDMS records, use Sheet Mapping key metadata for WHERE.
"""

CONSERVATIVE_UPDATE_RULES = [
    "UPDATE generation is conservative/manual-style, not broad all-column update.",
    "Only columns changed by original COBOL business logic should be updated.",
    "UPDATE audit columns may be added only when present in Sheet Mapping and DCLGEN.",
    "For UPDATE flows, generate TS_UPDATE and USER-ID moves only.",
    "TS_CREATE is insert-only and must not be generated for update-only flows.",
    "For IDMS CALC records, WHERE clause must use Sheet Mapping key metadata only.",
    "Do not add relationship foreign keys to CALC-record WHERE clauses unless marked as key metadata.",
]

UPDATE_AUDIT_COLUMN_PREFIXES = [
    "TS_UPDATE",
    "ID_USERID",
    "NR_USERID",
    "ID_USER",
    "NR_USER",
]

INSERT_ONLY_AUDIT_COLUMN_PREFIXES = [
    "TS_CREATE",
]

KEY_TEXT_MARKERS = [
    "PRIMARY",
    "PRIMARY KEY",
    "KEY",
    "CALC",
]

DATE_COLUMN_PREFIXES = [
    "DA_",
    "DT_",
]