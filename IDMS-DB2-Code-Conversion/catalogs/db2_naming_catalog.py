"""
DB2 naming catalog.

This file owns DB2 naming conventions so resolvers and generators do not
hardcode table suffixes or cursor suffix rules.
"""


DB2_TABLE_SUFFIX_EQUIVALENTS = [
    ("_TB", "_TV"),
    ("_TV", "_TB"),
    ("TB", "TV"),
    ("TV", "TB"),
]


DB2_CURSOR_SUFFIX = "C1"


DB2_DEFAULT_CURSOR_NAME = "DB2CURC1"


DB2_HOST_REFERENCE_PREFIX = ":"