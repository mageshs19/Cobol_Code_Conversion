"""
DB2 date conversion rules.

This file contains reusable templates for DB2 date comparison conversion.

No program name is hardcoded.
No table name is hardcoded.
No DCLGEN group name is hardcoded.
No business field name is hardcoded.

The composer supplies dynamic values such as:
- field_name
- group_name
- helper
- condition
- indent
"""


DB2_DATE_COMPARISON_RULES = [
    "DB2 DATE values must be realigned before numeric comparison.",
    "Generate date conversion only when a DA-/DT- DCLGEN host field is compared with PARMDATE.",
    "Generated helper field names are derived from the detected DB2 host field name.",
    "Date conversion logic must not hardcode program names, table names, record names, or business fields.",
    "Initialize generated date helper fields before moving converted date values into them.",
]


DB2_DATE_COMPARISON_WS_MARKER = "DB2 DATE CONVERSION WORKING STORAGE"


DB2_DATE_BASE_WORKING_STORAGE_LINES = [
    f"* {DB2_DATE_COMPARISON_WS_MARKER}",
    "01  WS-DATUMVELDEN.",
    "    03  DA-CCYYMMDD.",
    "        05  CC                    PIC 99       VALUE ZERO.",
    "        05  YY                    PIC 99       VALUE ZERO.",
    "        05  MM                    PIC 99       VALUE ZERO.",
    "        05  DD                    PIC 99       VALUE ZERO.",
    "    03  DA-CCYYMMDD-R REDEFINES DA-CCYYMMDD.",
    "        05  CCYY                  PIC 9999.",
    "        05  MM                    PIC 99.",
    "        05  DD                    PIC 99.",
    "    03  DA-DD-MM-CCYY.",
    "        05  DD                    PIC 9(02).",
    "        05  TE-MARKER5            PIC X        VALUE '.'.",
    "        05  MM                    PIC 9(02).",
    "        05  TE-MARKER6            PIC X        VALUE '.'.",
    "        05  CCYY                  PIC 9(04).",
]


DB2_DATE_HELPER_FIELD_TEMPLATE = (
    "    02  {helper:<30} PIC 9(8)     VALUE ZEROES."
)


DB2_DATE_LOW_VALUE_LITERAL = "01.01.0001"
DB2_DATE_HIGH_VALUE_LITERAL = "31.12.9999"
DB2_DATE_HIGH_NUMERIC_LITERAL = "99999999"


DB2_DATE_CONVERSION_LINE_TEMPLATES = [
    "{indent}MOVE ZEROES TO DA-CCYYMMDD",
    "{indent}MOVE ZEROES TO {helper}",
    "{indent}MOVE {field_name} OF {group_name} TO DA-DD-MM-CCYY",
    "{indent}EVALUATE TRUE",
    "{indent} WHEN DA-DD-MM-CCYY = '{low_value}'",
    "{indent}      MOVE ZEROES TO DA-CCYYMMDD-R",
    "{indent} WHEN DA-DD-MM-CCYY = '{high_value}'",
    "{indent}      MOVE '{high_numeric}' TO DA-CCYYMMDD-R",
    "{indent} WHEN OTHER",
    "{indent}      MOVE CCYY OF DA-DD-MM-CCYY TO CCYY OF DA-CCYYMMDD-R",
    "{indent}      MOVE MM   OF DA-DD-MM-CCYY TO MM   OF DA-CCYYMMDD-R",
    "{indent}      MOVE DD   OF DA-DD-MM-CCYY TO DD   OF DA-CCYYMMDD-R",
    "{indent}END-EVALUATE",
    "{indent}MOVE DA-CCYYMMDD-R TO {helper}",
]


DB2_DATE_IF_REPLACEMENT_TEMPLATE = "{indent}IF {helper} {condition}"