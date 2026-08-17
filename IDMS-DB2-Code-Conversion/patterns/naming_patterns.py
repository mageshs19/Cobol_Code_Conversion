"""
Naming patterns and naming helpers.

Name normalization logic must use these patterns instead of repeating
regex cleanup expressions across services.
"""

import re


NON_DB2_NAME_CHARACTER_PATTERN = re.compile(
    r"[^A-Z0-9_]+",
    flags=re.IGNORECASE,
)


NON_COMPACT_NAME_CHARACTER_PATTERN = re.compile(
    r"[^A-Z0-9]+",
    flags=re.IGNORECASE,
)


MULTIPLE_UNDERSCORE_PATTERN = re.compile(
    r"_+",
    flags=re.IGNORECASE,
)


DCL_PREFIX_PATTERN = re.compile(
    r"^DCL_?",
    flags=re.IGNORECASE,
)


FOUR_DIGIT_RECORD_SUFFIX_PATTERN = re.compile(
    r"_[0-9]{4}$",
    flags=re.IGNORECASE,
)