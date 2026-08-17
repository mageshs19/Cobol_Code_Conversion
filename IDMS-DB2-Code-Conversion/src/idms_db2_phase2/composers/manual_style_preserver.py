class ManualStylePreserver:
    """
    Preserves manual COBOL style by avoiding broad formatting changes.

    Requirement:
    - Output should remain close to original IDMS COBOL style.
    - Only DB2 conversion changes should be carried out.
    - Existing comments should remain where possible.
    """

    def preserve(
        self,
        original_text: str,
        converted_text: str,
    ) -> str:
        if not converted_text:
            return ""

        text = self._preserve_comment_density(converted_text)
        text = self._normalize_excess_blank_lines(text)

        return text.rstrip() + "\n"

    def _preserve_comment_density(
        self,
        text: str,
    ) -> str:
        output_lines: list[str] = []

        for line in str(text or "").splitlines():
            output_lines.append(line.rstrip())

        return "\n".join(output_lines)

    def _normalize_excess_blank_lines(
        self,
        text: str,
    ) -> str:
        while "\n\n\n\n" in text:
            text = text.replace("\n\n\n\n", "\n\n\n")

        return text