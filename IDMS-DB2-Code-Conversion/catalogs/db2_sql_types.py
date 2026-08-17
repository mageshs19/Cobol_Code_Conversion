"""
DB2 SQL type catalog.

DCLGEN parsing logic must import SQL type starters from here.
"""


DB2_SQL_TYPE_STARTERS = {
    "CHAR",
    "CHARACTER",
    "VARCHAR",
    "LONG",
    "GRAPHIC",
    "VARGRAPHIC",
    "SMALLINT",
    "INTEGER",
    "INT",
    "BIGINT",
    "DECIMAL",
    "DEC",
    "NUMERIC",
    "NUM",
    "FLOAT",
    "REAL",
    "DOUBLE",
    "DATE",
    "TIME",
    "TIMESTAMP",
    "BLOB",
    "CLOB",
    "DBCLOB",
    "XML",
}


DB2_SQL_SKIP_WORDS = {
    "EXEC",
    "SQL",
    "DECLARE",
    "TABLE",
    "END-EXEC",
    "END",
    "NOT",
    "NULL",
    "WITH",
    "DEFAULT",
    "PRIMARY",
    "FOREIGN",
    "KEY",
    "CONSTRAINT",
    "UNIQUE",
    "CHECK",
    "REFERENCES",
    "CREATE",
    "IN",
    "IS",
    "THE",
    "DCLGEN",
    "COMMAND",
    "THAT",
    "MADE",
    "FOLLOWING",
    "STATEMENTS",
}