"""
Fixed-format COBOL layout rules.
These constants define final physical COBOL layout:
- Columns 1-6 : left sequence number
- Column 7 : indicator area
- Columns 8-72 : COBOL body
- Columns 73-80 : right sequence number
This file contains rules/constants only.
No regex should be defined here.
"""
TOTAL_WIDTH = 80
BODY_WIDTH = 65
LEFT_SEQUENCE_WIDTH = 6
INDICATOR_WIDTH = 1
RIGHT_SEQUENCE_WIDTH = 8
DEFAULT_LEFT_START = 10
DEFAULT_LEFT_STEP = 10
# Generic fallback for manual-style COBOL when input has no valid
# manual right sequence, or when input has old/small right sequence.
#
# Example:
# left 000010 -> right 00010000
# left 000020 -> right 00020000
#
# This is not program-specific hardcoding.
# It is a layout fallback rule.
DEFAULT_RIGHT_START = 10000
DEFAULT_RIGHT_STEP = 10000
AREA_A_INDENT = ""
AREA_B_INDENT = " "
SQL_INDENT = " "
SQL_CONTINUATION_INDENT = " "
SPACE_INDICATOR = " "
COMMENT_INDICATOR = "*"
PAGE_INDICATOR = "/"
DEBUG_INDICATOR = "D"
CONTINUATION_INDICATOR = "-"
VALID_INDICATORS = {
SPACE_INDICATOR,
COMMENT_INDICATOR,
PAGE_INDICATOR,
DEBUG_INDICATOR,
"d",
CONTINUATION_INDICATOR,
}
NON_PARAGRAPH_WORDS = {
"ACCEPT",
"ADD",
"ALTER",
"CALL",
"CANCEL",
"CLOSE",
"COMMIT",
"COMPUTE",
"CONTINUE",
"DELETE",
"DISPLAY",
"DIVIDE",
"ELSE",
"END-ADD",
"END-CALL",
"END-DELETE",
"END-DIVIDE",
"END-EVALUATE",
"END-EXEC",
"END-IF",
"END-MULTIPLY",
"END-PERFORM",
"END-READ",
"END-RETURN",
"END-REWRITE",
"END-SEARCH",
"END-START",
"END-STRING",
"END-SUBTRACT",
"END-UNSTRING",
"END-WRITE",
"EVALUATE",
"EXEC",
"EXIT",
"FETCH",
"GOBACK",
"IF",
"INITIALIZE",
"INSPECT",
"MOVE",
"MULTIPLY",
"NEXT",
"OPEN",
"PERFORM",
"READ",
"RETURN",
"REWRITE",
"ROLLBACK",
"SEARCH",
"SET",
"SKIP1",
"SKIP2",
"SKIP3",
"SORT",
"SPACE",
"SPACES",
"START",
"STOP",
"STRING",
"SUBTRACT",
"UNSTRING",
"WHEN",
"WRITE",
}
PROCEDURE_VERBS = (
"ACCEPT ",
"ADD ",
"ALTER ",
"CALL ",
"CANCEL ",
"CLOSE ",
"COMMIT",
"COMPUTE ",
"CONTINUE",
"DELETE ",
"DISPLAY ",
"DIVIDE ",
"ELSE",
"END-ADD",
"END-CALL",
"END-DELETE",
"END-DIVIDE",
"END-EVALUATE",
"END-EXEC",
"END-IF",
"END-MULTIPLY",
"END-PERFORM",
"END-READ",
"END-RETURN",
"END-REWRITE",
"END-SEARCH",
"END-START",
"END-STRING",
"END-SUBTRACT",
"END-UNSTRING",
"END-WRITE",
"EVALUATE ",
"EXEC SQL",
"EXIT",
"FETCH ",
"GOBACK",
"IF ",
"INITIALIZE ",
"INSPECT ",
"MOVE ",
"MULTIPLY ",
"NEXT ",
"OPEN ",
"PERFORM ",
"READ ",
"RETURN ",
"REWRITE ",
"ROLLBACK",
"SEARCH ",
"SET ",
"SORT ",
"START ",
"STOP ",
"STRING ",
"SUBTRACT ",
"UNSTRING ",
"WHEN ",
"WRITE ",
)
SQL_LEVEL_1_KEYWORDS = (
"SELECT ",
"INTO ",
"FROM ",
"WHERE ",
"ORDER BY ",
"GROUP BY ",
"HAVING ",
"FETCH ",
"OPEN ",
"CLOSE ",
"COMMIT",
"ROLLBACK",
"INSERT ",
"UPDATE ",
"DELETE ",
"SET ",
"VALUES ",
"FOR READ ONLY",
"QUERYNO ",
)
SQL_LEVEL_2_KEYWORDS = (
"AND ",
"OR ",
",",
)
AREA_A_HEADER_PREFIXES = (
"PROGRAM-ID.",
"AUTHOR.",
"INSTALLATION.",
"DATE-WRITTEN.",
"DATE-COMPILED.",
"SECURITY.",
)
AREA_A_DATA_LEVELS = {
"01",
"66",
"77",
}
AREA_B_DATA_LEVELS = {
"02",
"03",
"04",
"05",
"06",
"07",
"08",
"09",
"10",
"11",
"12",
"13",
"14",
"15",
"16",
"17",
"18",
"19",
"20",
"21",
"22",
"23",
"24",
"25",
"26",
"27",
"28",
"29",
"30",
"31",
"32",
"33",
"34",
"35",
"36",
"37",
"38",
"39",
"40",
"41",
"42",
"43",
"44",
"45",
"46",
"47",
"48",
"49",
"88",
}
