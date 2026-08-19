"""
Final feedback fix rules.

This module contains constants and rule values only.

No regex.
No parser logic.
No service logic.
No hardcoded business names.
"""

from __future__ import annotations


FINAL_FEEDBACK_FIX_RULES = [
    "Fix Procedure Division executable statements to begin in Area B.",
    "Synchronize PROGRAM-NAME from final PROGRAM-ID only in safe MOVE statements.",
    "Use configurable DB2 date external format for generated date conversion.",
    "Remove ORDER-BY-only columns from cursor SELECT and FETCH when safe.",
    "Do not hardcode program names, DB2 tables, columns, DCLGEN groups, or host variables.",
    "Do not remove existing business logic or already fixed feedback functionality.",
]

AREA_A_BODY_INDENT = ""
AREA_B_BODY_INDENT = "    "
SQL_BODY_INDENT = "    "

SUPPORTED_DB2_DATE_FORMATS = {
    "YYYY-MM-DD",
    "DD.MM.YYYY",
    "YYYYMMDD",
}

DATE_FORMAT_ALIASES = {
    "ISO": "YYYY-MM-DD",
    "YYYY-MM-DD": "YYYY-MM-DD",
    "EUR": "DD.MM.YYYY",
    "EUROPEAN": "DD.MM.YYYY",
    "DD.MM.YYYY": "DD.MM.YYYY",
    "DD.MM.CCYY": "DD.MM.YYYY",
    "NUMERIC": "YYYYMMDD",
    "YYYYMMDD": "YYYYMMDD",
    "CCYYMMDD": "YYYYMMDD",
}

# Preserve current generated behavior unless the caller explicitly configures
# a different site/DCLGEN date external format.
DEFAULT_DB2_DATE_EXTERNAL_FORMAT = "DD.MM.YYYY"

DB2_DATE_HELPER_BY_FORMAT = {
    "DD.MM.YYYY": "DA-DD-MM-CCYY",
    "YYYY-MM-DD": "DA-YYYY-MM-DD",
    "YYYYMMDD": "DA-YYYYMMDD",
}

DB2_DATE_LOW_LITERAL_BY_FORMAT = {
    "DD.MM.YYYY": "'01.01.0001'",
    "YYYY-MM-DD": "'0001-01-01'",
    "YYYYMMDD": "'00010101'",
}

DB2_DATE_HIGH_LITERAL_BY_FORMAT = {
    "DD.MM.YYYY": "'31.12.9999'",
    "YYYY-MM-DD": "'9999-12-31'",
    "YYYYMMDD": "'99991231'",
}

ORDER_BY_COLUMNS_IN_SELECT_DEFAULT = False