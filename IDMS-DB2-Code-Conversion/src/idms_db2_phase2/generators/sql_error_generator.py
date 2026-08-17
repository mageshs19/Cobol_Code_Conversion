import re

from patterns.db2_patterns import END_PROGRAM_PATTERN


class SqlErrorGenerator:
    """
    Generates and ensures SQLERROR paragraph.

    Feedback rule:
    - Use SQLERROR, not SQL-ERROR.
    - Generated DB2 cursor paragraphs and SQL blocks must perform SQLERROR.
    """

    DEFAULT_PARAGRAPH_NAME = "SQLERROR"

    SQLERROR_PARAGRAPH_PATTERN = re.compile(
        r"^\s*(?:\d{6}\s+)?(SQLERROR|SQL-ERROR)\.\s*(?:\d{8})?\s*$",
        flags=re.IGNORECASE | re.MULTILINE,
    )

    SQLERROR_PERFORM_PATTERN = re.compile(
        r"\bPERFORM\s+(SQLERROR|SQL-ERROR)\s*\.?",
        flags=re.IGNORECASE,
    )

    def paragraph_name(
        self,
        cobol_text: str,
    ) -> str:
        return self.DEFAULT_PARAGRAPH_NAME

    def has_sql_error_paragraph(
        self,
        cobol_text: str,
    ) -> bool:
        return bool(
            self.SQLERROR_PARAGRAPH_PATTERN.search(cobol_text or "")
        )

    def paragraph_block(
        self,
        paragraph_name: str = DEFAULT_PARAGRAPH_NAME,
    ) -> str:
        clean_name = self.DEFAULT_PARAGRAPH_NAME

        return "\n".join(
            [
                f"{clean_name}.",
                "    DISPLAY 'DB2 SQL ERROR SQLCODE=' SQLCODE.",
                "    DISPLAY 'DB2 SQL ERROR LOCATION=' SQL-LOCATION.",
                "    CONTINUE.",
            ]
        )

    def ensure_sql_error_paragraph(
        self,
        cobol_text: str,
    ) -> str:
        text = str(cobol_text or "")

        if not text:
            return ""

        text = self.normalize_sql_error_references(text)

        if self._has_sqlerror_paragraph(text):
            return text.rstrip() + "\n"

        block = self.paragraph_block()

        end_program_match = END_PROGRAM_PATTERN.search(text)

        if end_program_match:
            return (
                text[: end_program_match.start()].rstrip()
                + "\n\n"
                + block
                + "\n\n"
                + text[end_program_match.start():].lstrip()
            ).rstrip() + "\n"

        return text.rstrip() + "\n\n" + block + "\n"

    def normalize_sql_error_references(
        self,
        text: str,
    ) -> str:
        updated = str(text or "")

        updated = re.sub(
            r"\bPERFORM\s+SQL-ERROR\s*\.?",
            "PERFORM SQLERROR.",
            updated,
            flags=re.IGNORECASE,
        )

        updated = re.sub(
            r"\bPERFORM\s+SQLERROR\s*\.?",
            "PERFORM SQLERROR.",
            updated,
            flags=re.IGNORECASE,
        )

        updated = re.sub(
            r"(?m)^(\s*)(?:\d{6}\s+)?SQL-ERROR\.\s*(?:\d{8})?\s*$",
            r"\1SQLERROR.",
            updated,
            flags=re.IGNORECASE,
        )

        return updated

    def _has_sqlerror_paragraph(
        self,
        text: str,
    ) -> bool:
        return bool(
            re.search(
                r"^\s*(?:\d{6}\s+)?SQLERROR\.\s*(?:\d{8})?\s*$",
                text or "",
                flags=re.IGNORECASE | re.MULTILINE,
            )
        )