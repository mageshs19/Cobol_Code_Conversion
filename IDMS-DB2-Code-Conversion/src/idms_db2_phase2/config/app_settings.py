"""
Application settings.

Keep app-level settings outside parser, transformer, generator, and service
logic.
"""


APP_NAME = "IDMS DB2 Phase 2 Converter"


APP_DESCRIPTION = (
    "Standalone Phase 2 project for converting IDMS COBOL programs "
    "into DB2 embedded SQL COBOL."
)


DEFAULT_STREAMLIT_PORT = 8502


DEFAULT_AUTO_FIX_PIC_LENGTH_MISMATCHES = False