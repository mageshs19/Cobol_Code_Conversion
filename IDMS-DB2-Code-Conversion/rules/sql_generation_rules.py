"""
SQL generation rules.

SQL services and generators must import these rules instead of embedding
business rules directly in generator classes.
"""


SQL_GENERATION_RULES = [
    "Sheet Mapping is the authority for DB2 record/table names.",
    "Sheet Mapping is the authority for DB2 column names.",
    "DCLGEN is the authority for COBOL host variable spelling and group names.",
    "If Sheet Mapping uses TB but uploaded DCLGEN uses TV, generated SQL uses TV.",
    "UPDATE generation is conservative/manual-style, not broad all-column update.",
]


TABLE_RESOLUTION_RULES = [
    "If DZBFARTB is found in Sheet Mapping but DCLGEN has DZBFARTV, resolve to DZBFARTV.",
    "Generated SELECT FROM table name must match resolved DCLGEN table name.",
    "Generated UPDATE table name must match resolved DCLGEN table name.",
]