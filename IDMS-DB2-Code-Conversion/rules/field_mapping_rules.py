"""
Field mapping rules.

These constants describe authority and rewrite behavior for IDMS-to-DB2 field
mapping. No regex or runtime logic belongs in this file.
"""

FIELD_MAPPING_RULES = [
    "Sheet Mapping is the authority for DB2 column names.",
    "DCLGEN is the authority for COBOL host variable spelling.",
    "Do not invent DB2 field names.",
    "Do not use IDMS record names in final DB2 procedure logic when a Sheet Mapping and DCLGEN mapping exists.",
    "Rewrite only safe qualified references unless strong context exists.",
]

QUALIFIED_REFERENCE_REWRITE_RULES = [
    "Rewrite FIELD OF IDMS-RECORD when a Sheet Mapping and DCLGEN mapping exists.",
    "Rewrite FIELD IN IDMS-RECORD when a Sheet Mapping and DCLGEN mapping exists.",
    "Do not rewrite bare words globally.",
    "When mapping metadata is missing, leave a clear conversion-skipped comment.",
]