import re

from patterns.db2_patterns import END_PROGRAM_PATTERN


class SqlErrorGenerator:
    """
    Generates and ensures SQLERROR paragraph.

    Generic rule:
    - Use SQLERROR, not SQL-ERROR.
    - Generated DB2 cursor paragraphs and SQL blocks perform SQLERROR.
    - SQLERROR paragraph wraps the standard DB2 SQLERROR include.

    Generated paragraph:

        SQLERROR.
            EXEC SQL
                INCLUDE SQLERROR
            END-EXEC.
    """

    DEFAULT_PARAGRAPH_NAME = "SQLERROR"

    SQLERROR_PARAGRAPH_PATTERN = re.compile(
        r"^\s*(?:\d{6}\s+)?(?:SQLERROR|SQL-ERROR)\.\s*(?:\d{8})?\s*$",
        flags=re.IGNORECASE | re.MULTILINE,
    )

    SQLERROR_PERFORM_PATTERN = re.compile(
        r"\bPERFORM\s+(?:SQLERROR|SQL-ERROR)\s*\.?",
        flags=re.IGNORECASE,
    )

    SQLERROR_INCLUDE_PATTERN = re.compile(
        r"\bINCLUDE\s+SQLERROR\b",
        flags=re.IGNORECASE,
    )

    CUSTOM_SQLERROR_DISPLAY_PATTERN = re.compile(
        r"DISPLAY\s+'DB2\s+SQL\s+ERROR",
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
                "    EXEC SQL",
                "        INCLUDE SQLERROR",
                "    END-EXEC.",
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
            text = self._replace_existing_sqlerror_paragraph(text)
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

    def _replace_existing_sqlerror_paragraph(
        self,
        text: str,
    ) -> str:
        lines = str(text or "").splitlines()

        output: list[str] = []
        index = 0
        replaced = False

        while index < len(lines):
            line = lines[index]

            if not self._is_sqlerror_paragraph_header(line):
                output.append(line)
                index += 1
                continue

            output.extend(self.paragraph_block().splitlines())
            replaced = True
            index += 1

            while index < len(lines):
                current = lines[index]

                if self._is_next_paragraph_or_program_boundary(current):
                    break

                if self._line_belongs_to_old_sqlerror_block(current):
                    index += 1
                    continue

                if not current.strip():
                    index += 1
                    continue

                break

            continue

        if not replaced:
            return text

        return "\n".join(output).rstrip() + "\n"

    def _is_sqlerror_paragraph_header(
        self,
        line: str,
    ) -> bool:
        logical = self._logical_line(line)

        return bool(
            re.fullmatch(
                r"(?:SQLERROR|SQL-ERROR)\.",
                logical,
                flags=re.IGNORECASE,
            )
        )

    def _is_next_paragraph_or_program_boundary(
        self,
        line: str,
    ) -> bool:
        logical = self._logical_line(line)

        if not logical:
            return False

        if re.match(
            r"END\s+PROGRAM\b",
            logical,
            flags=re.IGNORECASE,
        ):
            return True

        if re.fullmatch(
            r"[A-Z0-9][A-Z0-9-]*\.",
            logical,
            flags=re.IGNORECASE,
        ):
            return True

        return False

    def _line_belongs_to_old_sqlerror_block(
        self,
        line: str,
    ) -> bool:
        logical = self._logical_line(line)

        if not logical:
            return True

        if logical.upper().startswith("DISPLAY "):
            return True

        if logical.upper().startswith("CONTINUE"):
            return True

        if logical.upper().startswith("EXEC SQL"):
            return True

        if logical.upper().startswith("INCLUDE SQLERROR"):
            return True

        if logical.upper().startswith("END-EXEC"):
            return True

        return False

    def _logical_line(
        self,
        line: str,
    ) -> str:
        text = str(line or "").rstrip()

        if len(text) >= 80 and text[:6].isdigit() and text[72:80].isdigit():
            return text[7:72].strip()

        if len(text) > 6 and text[:6].isdigit():
            text = text[6:].strip()

        if len(text) >= 8 and text[-8:].isdigit():
            text = text[:-8].rstrip()

        return text.strip()