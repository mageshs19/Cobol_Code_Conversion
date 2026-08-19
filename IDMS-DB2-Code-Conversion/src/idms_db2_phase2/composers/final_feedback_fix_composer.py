"""
Final feedback fix composer.

Orchestrates the final generic fixes only.

No regex.
No business rules.
No hardcoded program names, table names, columns, DCLGEN names, or host vars.
"""

from __future__ import annotations

from dataclasses import dataclass

from rules.final_feedback_fix_rules import (
    DEFAULT_DB2_DATE_EXTERNAL_FORMAT,
    ORDER_BY_COLUMNS_IN_SELECT_DEFAULT,
)
from idms_db2_phase2.services.cobol_area_alignment_service import (
    CobolAreaAlignmentService,
)
from idms_db2_phase2.services.cursor_select_minimizer_service import (
    CursorSelectMinimizerService,
)
from idms_db2_phase2.services.db2_date_format_service import (
    Db2DateFormatService,
)
from idms_db2_phase2.services.final_sequence_resequencer_service import (
    FinalSequenceResequencerService,
)
from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)
from idms_db2_phase2.services.program_name_sync_service import (
    ProgramNameSyncService,
)
from idms_db2_phase2.services.update_final_feedback_service import (
    UpdateFinalFeedbackService,
)


@dataclass(frozen=True)
class FinalFeedbackFixComposerConfig:
    """
    Configuration for final generic feedback fixes.
    """

    db2_date_external_format: str = DEFAULT_DB2_DATE_EXTERNAL_FORMAT
    require_order_by_columns_in_select: bool = ORDER_BY_COLUMNS_IN_SELECT_DEFAULT
    resequence_final_output: bool = True


class FinalFeedbackFixComposer:
    """
    Applies only the remaining generic feedback fixes:

    1. Program-name synchronization.
    2. DB2 date format correction.
    3. Cursor SELECT/FETCH minimization.
    4. Update-program final cleanup.
    5. Procedure Division Area B alignment.
    6. Final manual-style resequencing.

    This composer does not hardcode business names or rewrite business logic.
    """

    def __init__(
        self,
        config: FinalFeedbackFixComposerConfig | None = None,
        fixed_format: FixedFormatLineService | None = None,
    ) -> None:
        self.config = config or FinalFeedbackFixComposerConfig()
        self.fixed_format = fixed_format or FixedFormatLineService()

        self.program_name_sync = ProgramNameSyncService()
        self.date_format_service = Db2DateFormatService(
            date_external_format=self.config.db2_date_external_format,
        )
        self.cursor_select_minimizer = CursorSelectMinimizerService(
            fixed_format=self.fixed_format,
            require_order_by_columns_in_select=(
                self.config.require_order_by_columns_in_select
            ),
        )
        self.update_final_feedback = UpdateFinalFeedbackService(
            fixed_format=self.fixed_format,
        )
        self.area_alignment = CobolAreaAlignmentService(
            fixed_format=self.fixed_format,
        )
        self.sequence_resequencer = FinalSequenceResequencerService()

    def compose(self, text: str) -> str:
        output = str(text or "")

        if not output:
            return ""

        output = self.program_name_sync.sync(output)
        output = self.date_format_service.apply(output)
        output = self.cursor_select_minimizer.minimize(output)
        output = self.update_final_feedback.apply(output)
        output = self.area_alignment.align(output)

        if self.config.resequence_final_output:
            output = self.sequence_resequencer.resequence(output)

        return output.rstrip() + "\n"


def apply_final_feedback_fixes(
    text: str,
    db2_date_external_format: str = DEFAULT_DB2_DATE_EXTERNAL_FORMAT,
    require_order_by_columns_in_select: bool = ORDER_BY_COLUMNS_IN_SELECT_DEFAULT,
    resequence_final_output: bool = True,
) -> str:
    """
    Convenience wrapper for pipeline integration.
    """

    composer = FinalFeedbackFixComposer(
        config=FinalFeedbackFixComposerConfig(
            db2_date_external_format=db2_date_external_format,
            require_order_by_columns_in_select=require_order_by_columns_in_select,
            resequence_final_output=resequence_final_output,
        )
    )

    return composer.compose(text)