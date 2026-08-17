import re


QUALIFIED_REFERENCE_PATTERN = re.compile(
    r"\b(?P<field>[A-Z][A-Z0-9-]*)\s+"
    r"(?P<qualifier>OF|IN)\s+"
    r"(?P<record>[A-Z][A-Z0-9-]*)\b",
    flags=re.IGNORECASE,
)

REDEFINES_PATTERN = re.compile(
    r"\b(?P<alias>[A-Z][A-Z0-9-]*)\s+REDEFINES\s+"
    r"(?P<base>[A-Z][A-Z0-9-]*)\b",
    flags=re.IGNORECASE,
)

STRING_LITERAL_PATTERN = re.compile(
    r"'[^']*'|\"[^\"]*\"",
    flags=re.IGNORECASE,
)