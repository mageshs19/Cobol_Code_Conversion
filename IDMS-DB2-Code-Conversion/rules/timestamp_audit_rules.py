"""
Timestamp and audit rules.
"""


TIMESTAMP_AUDIT_RULES = [
    "Sheet Mapping decides DB2 table and column names.",
    "DCLGEN supplies COBOL host variable spelling and group names.",
    "DCLGEN must not introduce audit fields absent from Sheet Mapping.",
    "For UPDATE flows, generate TS_UPDATE and USER-ID moves only.",
    "TS_CREATE is insert-only and is not generated for update-only flows.",
    "Timestamp paragraph must be a safe paragraph with a terminating boundary.",
]


AUDIT_COLUMN_PREFIXES = [
    "TS_CREATE",
    "TS_UPDATE",
    "ID_USERID",
    "NR_USERID",
    "ID_USER",
    "NR_USER",
    "NS_IDMSKEY",
]


UPDATE_AUDIT_COLUMN_PREFIXES = [
    "TS_UPDATE",
    "ID_USERID",
    "NR_USERID",
    "ID_USER",
    "NR_USER",
]


INSERT_EXCLUDE_AUDIT_PREFIXES = [
    "TS_UPDATE",
]


DATE_COLUMN_PREFIXES = [
    "DA_",
    "DT_",
]