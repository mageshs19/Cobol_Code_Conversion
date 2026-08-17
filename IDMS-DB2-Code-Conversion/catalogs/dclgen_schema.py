"""
DCLGEN schema catalog.

This file owns DCLGEN-related static names and conventions.
Parser and service classes must import from here instead of hardcoding
DCLGEN names internally.
"""


DCLGEN_GROUP_PREFIX = "DCL"


DCLGEN_COLUMN_FIELDS = [
    "table_name",
    "column_name",
    "db2_type",
    "cobol_host_name",
    "cobol_picture",
    "cobol_usage",
    "nullable",
]


DCLGEN_HOST_FIELD_SUFFIXES_TO_IGNORE = [
    "-NULL",
    "-LEN",
    "-TEXT",
]