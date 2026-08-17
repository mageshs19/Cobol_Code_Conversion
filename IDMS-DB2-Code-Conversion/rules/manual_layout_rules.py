"""
Manual-style COBOL layout rules.

These constants describe final manual-style sequencing behavior.
No regex or runtime logic belongs in this file.
"""

MANUAL_LAYOUT_RULES = [
    "Final COBOL should be manual-style sequenced.",
    "Columns 1-6 contain the left sequence number.",
    "Columns 8-72 contain the COBOL body.",
    "Columns 73-80 contain the right sequence number.",
    "Generated output must preserve COBOL headers and division structure.",
]