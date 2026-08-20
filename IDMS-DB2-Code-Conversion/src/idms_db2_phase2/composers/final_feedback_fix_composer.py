from __future__ import annotations

import re
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
    6. STRING block manual-style formatting.
    7. Final manual-style resequencing.

    This composer does not hardcode business names, DB2 tables, columns,
    DCLGEN groups, host variables, or program names.
    """

    STRING_START_PATTERN = re.compile(
        r"^STRING\b",
        flags=re.IGNORECASE,
    )

    STRING_END_PATTERN = re.compile(
        r"^END-STRING\.?$",
        flags=re.IGNORECASE,
    )

    STRING_INTO_PATTERN = re.compile(
        r"^INTO\b",
        flags=re.IGNORECASE,
    )

    STRING_START_BODY_INDENT = "    "
    STRING_CONTINUATION_BODY_INDENT = "           "
    STRING_INTO_BODY_INDENT = "      "

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

    def compose(
        self,
        text: str,
    ) -> str:
        output = str(text or "")

        if not output:
            return ""

        output = self.program_name_sync.sync(output)
        output = self.date_format_service.apply(output)
        output = self.cursor_select_minimizer.minimize(output)
        output = self.update_final_feedback.apply(output)
        output = self.area_alignment.align(output)

        # Important:
        # Area alignment normalizes Procedure Division executable statements.
        # Therefore STRING block formatting must run AFTER area alignment.
        output = self._format_string_blocks(output)

        if self.config.resequence_final_output:
            output = self.sequence_resequencer.resequence(output)

        return output.rstrip() + "\n"

    def _format_string_blocks(
        self,
        text: str,
    ) -> str:
        """
        Reformat COBOL STRING blocks after final Area B alignment.

        Generic rule:
        - The first STRING line starts in Area B.
        - Literal/source continuation lines are indented under STRING.
        - INTO line is indented separately.
        - END-STRING returns to Area B.
        - No business names, tables, columns, or host variables are hardcoded.

        Example output:

            STRING DATE-YMD8(7:2) DELIMITED BY SIZE
                   '.' DELIMITED BY SIZE
                   DATE-YMD8(5:2) DELIMITED BY SIZE
                   '.' DELIMITED BY SIZE
                   DATE-YMD8(1:4) DELIMITED BY SIZE
              INTO DA-INFSDGD-479BFAR OF DCLDZBFARTV
            END-STRING.
        """

        if not text:
            return ""

        lines = str(text or "").splitlines()
        output: list[str] = []
        inside_string = False

        for line in lines:
            logical = self.fixed_format.logical(line)
            stripped = str(logical or "").strip()

            if not stripped:
                output.append(line)
                continue

            if self.fixed_format.is_comment_or_control_line(line):
                output.append(line)
                continue

            if self.STRING_START_PATTERN.match(stripped):
                inside_string = True
                output.append(
                    self._replace_body_preserving_fixed_format(
                        line=line,
                        body=self.STRING_START_BODY_INDENT + stripped,
                    )
                )
                continue

            if inside_string and self.STRING_END_PATTERN.match(stripped):
                inside_string = False
                output.append(
                    self._replace_body_preserving_fixed_format(
                        line=line,
                        body=self.STRING_START_BODY_INDENT + stripped,
                    )
                )
                continue

            if inside_string and self.STRING_INTO_PATTERN.match(stripped):
                output.append(
                    self._replace_body_preserving_fixed_format(
                        line=line,
                        body=self.STRING_INTO_BODY_INDENT + stripped,
                    )
                )
                continue

            if inside_string:
                output.append(
                    self._replace_body_preserving_fixed_format(
                        line=line,
                        body=self.STRING_CONTINUATION_BODY_INDENT + stripped,
                    )
                )
                continue

            output.append(line)

        return "\n".join(output).rstrip() + "\n"

    def _replace_body_preserving_fixed_format(
        self,
        line: str,
        body: str,
    ) -> str:
        """
        Replace only the COBOL body area.

        If the line is already fixed-format, preserve sequence columns and
        indicator. If not, return the body as a normal text line.
        """

        clean_body = str(body or "").rstrip()

        if not self.fixed_format.is_fixed_line(line):
            return clean_body

        if len(clean_body) > self.fixed_format.BODY_WIDTH:
            clean_body = clean_body[: self.fixed_format.BODY_WIDTH]

        return self.fixed_format.replace_body(
            line,
            clean_body,
        )


def apply_final_feedback_fixes(
    text: str,
    db2_date_external_format: str | None = None,
    require_order_by_columns_in_select: bool = ORDER_BY_COLUMNS_IN_SELECT_DEFAULT,
    resequence_final_output: bool = True,
) -> str:
    composer = FinalFeedbackFixComposer(
        config=FinalFeedbackFixComposerConfig(
            db2_date_external_format=(
                db2_date_external_format or DEFAULT_DB2_DATE_EXTERNAL_FORMAT
            ),
            require_order_by_columns_in_select=require_order_by_columns_in_select,
            resequence_final_output=resequence_final_output,
        )
    )

    return composer.compose(text)