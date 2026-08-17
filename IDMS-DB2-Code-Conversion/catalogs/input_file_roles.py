"""
Input file role catalog.

Input labels are centralized here so UI, runners, validators, and diagnostics
do not hardcode file role names.
"""


INPUT_ROLE_SHEET_MAPPING = "Sheet Mapping"
INPUT_ROLE_DCLGEN = "DCLGEN"
INPUT_ROLE_COPYBOOK = "Copybook"
INPUT_ROLE_IDMS_COBOL_SOURCE = "IDMS COBOL Source"


REQUIRED_INPUT_ROLES = [
    INPUT_ROLE_SHEET_MAPPING,
    INPUT_ROLE_DCLGEN,
    INPUT_ROLE_IDMS_COBOL_SOURCE,
]


OPTIONAL_INPUT_ROLES = [
    INPUT_ROLE_COPYBOOK,
]