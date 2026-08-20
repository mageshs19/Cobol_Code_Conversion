"""
DB2 output date conversion rules.

This file contains reusable output-date conversion templates only.
No parser, service, transformer, composer, or generator logic belongs here.

Purpose:
- Convert DB2 date host fields into the output-file numeric date format
  before writing output records.
- Keep conversion rules centralized and generic.

No program name is hardcoded.
No table name is hardcoded.
No DCLGEN group name is hardcoded.
No business field name is hardcoded.

The composer supplies dynamic values:
- indent
- field_name
- group_name
- target_name
"""

DB2_OUTPUT_DATE_CONVERSION_RULES = [
    "DB2 date values must be realigned before moving to output date fields.",
    "Generate output date conversion only when a DA-/DT- DCLGEN host field is moved to an output date field.",
    "Initialize shared DB2 date work fields before date realignment.",
    "Clear the output date target before moving the converted date value.",
    "Do not hardcode program names, table names, DCLGEN group names, or business field names.",
    "Use shared date work fields when already generated in WORKING-STORAGE.",
]

DB2_OUTPUT_DATE_LOW_VALUE_LITERAL = "01.01.0001"
DB2_OUTPUT_DATE_HIGH_VALUE_LITERAL = "31.12.9999"
DB2_OUTPUT_DATE_HIGH_NUMERIC_LITERAL = "99999999"

DB2_OUTPUT_DATE_CONVERSION_LINE_TEMPLATES = [
    "{indent}MOVE ZEROES TO DA-CCYYMMDD",
    "{indent}MOVE SPACES TO {target_name}",
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
    "{indent}MOVE DA-CCYYMMDD-R TO {target_name}",
]