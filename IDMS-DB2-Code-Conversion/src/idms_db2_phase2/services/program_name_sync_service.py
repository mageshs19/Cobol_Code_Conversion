"""
Program name synchronization service.

Generic behavior:
- Read final PROGRAM-ID.
- Rewrite only safe MOVE literal TO PROGRAM-NAME statements.
- Do not globally replace program names.
"""

from __future__ import annotations

from patterns.final_feedback_fix_patterns import (
    MOVE_TO_PROGRAM_NAME_PATTERN,
    PROGRAM_ID_PATTERN,
)


class ProgramNameSyncService:
    """
    Synchronizes PROGRAM-NAME from final PROGRAM-ID.

    No program name is hardcoded.
    """

    def sync(self, text: str) -> str:
        source = str(text or "")

        program_match = PROGRAM_ID_PATTERN.search(source)
        if not program_match:
            return source

        final_program_id = program_match.group("program").upper()

        def replace_program_name(match) -> str:
            return (
                match.group("prefix")
                + final_program_id
                + match.group("suffix")
            )

        return MOVE_TO_PROGRAM_NAME_PATTERN.sub(replace_program_name, source)