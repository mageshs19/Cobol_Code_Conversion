class CobolFormatter:
    """
    Preserve-first COBOL formatter.

    This formatter intentionally does NOT re-indent or restructure the full
    COBOL program.

    Reason:
    - The original IDMS COBOL source is the authority for manual style.
    - The converter must preserve existing indentation, comments, sequence-like
      lines, paragraph spacing, and business-flow layout.
    - Only generated DB2 blocks should be inserted or normalized by generators
      and composers.

    This class therefore performs only safe text cleanup:
    - Normalize Windows/Unix line endings.
    - Remove trailing spaces.
    - Limit excessive blank lines.
    - Ensure one final newline.

    It must not:
    - Strip sequence numbers.
    - Re-indent PROCEDURE DIVISION.
    - Reformat original business logic.
    - Move paragraphs.
    - Add or remove periods.
    - Change field references.
    """

    def format(
        self,
        text: str,
    ) -> str:
        if not text:
            return ""

        normalized = self._normalize_line_endings(text)
        normalized = self._rstrip_lines(normalized)
        normalized = self._normalize_excess_blank_lines(normalized)

        return normalized.rstrip() + "\n"

    def _normalize_line_endings(
        self,
        text: str,
    ) -> str:
        return str(text or "").replace("\r\n", "\n").replace("\r", "\n")

    def _rstrip_lines(
        self,
        text: str,
    ) -> str:
        return "\n".join(
            line.rstrip()
            for line in str(text or "").splitlines()
        )

    def _normalize_excess_blank_lines(
        self,
        text: str,
    ) -> str:
        output = str(text or "")

        while "\n\n\n\n" in output:
            output = output.replace("\n\n\n\n", "\n\n\n")

        return output