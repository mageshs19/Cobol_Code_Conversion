class BaseTextParser:
    """
    Shared parser helper methods.

    This base class intentionally avoids business rules, schema names, and
    regex definitions. It contains only generic text cleanup utilities.
    """

    def normalize_line_endings(
        self,
        text: str,
    ) -> str:
        return str(text or "").replace("\r\n", "\n").replace("\r", "\n")

    def normalize_spaces(
        self,
        text: str,
    ) -> str:
        output = str(text or "").replace("\t", " ")
        output = output.replace("\u00a0", " ")

        while "  " in output:
            output = output.replace("  ", " ")

        return output

    def clean_text(
        self,
        text: str,
    ) -> str:
        output = self.normalize_line_endings(text)
        output = self.normalize_spaces(output)
        output = output.replace("“", '"').replace("”", '"')
        output = output.replace("‘", "'").replace("’", "'")

        return output

    def clean_cell(
        self,
        value,
    ) -> str:
        if value is None:
            return ""

        text = str(value)
        text = text.replace("\ufeff", "")
        text = text.replace("\xa0", " ")
        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")
        text = self.normalize_spaces(text)

        return text.strip()

    def strip_sequence_area(
        self,
        line: str,
    ) -> str:
        text = str(line or "").rstrip()

        if len(text) > 6:
            indicator = text[6:7]

            if indicator in ("*", "/"):
                return indicator

            if text[:6].strip().isdigit():
                return text[6:]

        return text