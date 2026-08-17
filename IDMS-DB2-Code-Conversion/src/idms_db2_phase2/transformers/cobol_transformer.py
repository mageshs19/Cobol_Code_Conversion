import re

from idms_db2_phase2.domain.models import IdmsOperation
from idms_db2_phase2.parsers.cobol_parser import CobolParser
from idms_db2_phase2.transformers.idms_statement_transformer import (
    IdmsStatementTransformer,
)
from patterns.cobol_patterns import DIVISION_PATTERN, PROGRAM_ID_PATTERN
from patterns.db2_patterns import SQL_ERROR_PARAGRAPH_PATTERN


class CobolTransformer:
    """
    Converts IDMS COBOL statements to DB2-compatible COBOL.

    Responsibilities:
    - Preserve original COBOL business flow.
    - Convert CBL compiler option line to DB2-compatible option.
    - Replace target PROGRAM-ID.
    - Remove residual IDMS declarative/control lines.
    - Remove or convert residual IDMS executable lines.
    - Preserve sequence/spacing for one-line DB condition replacements.
    - Remove orphan IDMS-ABORT paragraph after PERFORM IDMS-ABORT is removed.
    """

    IDMS_DECLARATIVE_PATTERNS = [
        re.compile(
            r"^IDMS-CONTROL\s+SECTION\.?$",
            flags=re.IGNORECASE,
        ),
        re.compile(
            r"^PROTOCOL\b.*$",
            flags=re.IGNORECASE,
        ),
        re.compile(
            r"^IDMS-RECORDS\s+WITHIN\s+WORKING-STORAGE\s+SECTION\.?$",
            flags=re.IGNORECASE,
        ),
        re.compile(
            r"^SCHEMA\s+SECTION\.?$",
            flags=re.IGNORECASE,
        ),
        re.compile(
            r"^DB\s+[A-Z0-9-]+\s+WITHIN\s+[A-Z0-9-]+\.?$",
            flags=re.IGNORECASE,
        ),
        re.compile(
            r"^COPY\s+IDMS\b.*$",
            flags=re.IGNORECASE,
        ),
    ]

    IDMS_EXECUTABLE_PATTERNS = [
        re.compile(
            r"^BIND\b.*$",
            flags=re.IGNORECASE,
        ),
        re.compile(
            r"^FIND\s+CURRENT\b.*$",
            flags=re.IGNORECASE,
        ),
        re.compile(
            r"^FINISH\.?$",
            flags=re.IGNORECASE,
        ),
    ]

    IDMS_ABORT_PARAGRAPH_PATTERN = re.compile(
        r"^IDMS-ABORT\.?$",
        flags=re.IGNORECASE,
    )

    EXIT_LINE_PATTERN = re.compile(
        r"^EXIT\.?$",
        flags=re.IGNORECASE,
    )

    GENERATED_LINE_PREFIXES = (
        "* DB2:",
        "EXEC SQL",
        "END-EXEC",
        "MOVE '",
        "PERFORM ",
        "END-IF",
        "CONTINUE",
        "SELECT",
        "INSERT",
        "UPDATE",
        "DELETE",
        "COMMIT",
        "ROLLBACK",
    )

    def __init__(
        self,
        idms_statement_transformer: IdmsStatementTransformer,
    ) -> None:
        self.idms_statement_transformer = idms_statement_transformer
        self.parser = CobolParser()

    def transform(
        self,
        cobol_text: str,
        target_program_id: str = "",
    ) -> tuple[str, list[str], list[IdmsOperation]]:
        operations = self.parser.analyze(cobol_text)

        validation_messages: list[str] = []
        output_lines: list[str] = []
        current_division = ""
        sql_error_paragraph = self._detect_sql_error_paragraph(cobol_text)
        skip_orphan_idms_abort_exit = False

        for raw_line in str(cobol_text or "").splitlines():
            line = raw_line.rstrip()
            logical = self._logical_line(line)
            logical_stripped = logical.strip()

            if skip_orphan_idms_abort_exit:
                if self._is_exit_line(logical_stripped):
                    skip_orphan_idms_abort_exit = False
                    continue

                skip_orphan_idms_abort_exit = False

            if not logical_stripped:
                output_lines.append(line)
                continue

            if self._is_cbl_line(logical_stripped):
                output_lines.append(
                    self._replace_logical_body(
                        original_line=line,
                        replacement_body="CBL ARITH(EXTEND)",
                    )
                )
                continue

            if self._is_idms_abort_paragraph(logical_stripped):
                output_lines.append(
                    "* DB2: Removed orphan IDMS-ABORT paragraph."
                )
                skip_orphan_idms_abort_exit = True
                continue

            program_id_line = self._program_id_replacement(
                original_line=line,
                logical_line=logical_stripped,
                target_program_id=target_program_id,
            )

            if program_id_line is not None:
                output_lines.append(program_id_line)
                continue

            division_match = DIVISION_PATTERN.match(logical_stripped)

            if division_match:
                current_division = division_match.group(1).upper()
                output_lines.append(line)
                continue

            if self._is_idms_declarative_or_control(logical_stripped):
                output_lines.extend(
                    self._removed_declarative_lines(logical_stripped)
                )
                continue

            if self._is_idms_executable_cleanup(logical_stripped):
                output_lines.extend(
                    self._removed_executable_lines(
                        logical_line=logical_stripped,
                        current_division=current_division,
                    )
                )
                continue

            transformed_lines, messages = (
                self.idms_statement_transformer.transform_line(
                    line=logical_stripped,
                    current_division=current_division,
                    sql_error_paragraph=sql_error_paragraph,
                )
            )

            validation_messages.extend(messages)

            if self._transformer_changed_line(
                original_logical=logical_stripped,
                transformed_lines=transformed_lines,
            ):
                output_lines.extend(
                    self._merge_transformed_lines_with_original_style(
                        original_line=line,
                        original_logical=logical_stripped,
                        transformed_lines=transformed_lines,
                    )
                )
            else:
                output_lines.append(line)

        converted_text = "\n".join(output_lines).rstrip() + "\n"

        converted_text = self._fix_program_id_period(
            text=converted_text,
            target_program_id=target_program_id,
        )

        return converted_text, validation_messages, operations

    def _merge_transformed_lines_with_original_style(
        self,
        original_line: str,
        original_logical: str,
        transformed_lines: list[str],
    ) -> list[str]:
        if not transformed_lines:
            return [original_line]

        if len(transformed_lines) == 1:
            transformed = str(transformed_lines[0] or "").strip()

            if self._is_single_line_token_replacement(
                original_logical=original_logical,
                transformed_line=transformed,
            ):
                return [
                    self._replace_logical_body(
                        original_line=original_line,
                        replacement_body=transformed,
                    )
                ]

            return [transformed]

        return transformed_lines

    def _is_single_line_token_replacement(
        self,
        original_logical: str,
        transformed_line: str,
    ) -> bool:
        original = str(original_logical or "").strip()
        transformed = str(transformed_line or "").strip()
        transformed_upper = transformed.upper()

        if not original or not transformed:
            return False

        if "SQLCODE = 100" in transformed_upper:
            return True

        if "SQLCODE NOT = 100" in transformed_upper:
            return True

        if "SQLCODE NOT = 0" in transformed_upper:
            return True

        if transformed_upper.startswith(self.GENERATED_LINE_PREFIXES):
            return False

        if transformed.startswith("*"):
            return False

        return False

    def _program_id_replacement(
        self,
        original_line: str,
        logical_line: str,
        target_program_id: str,
    ) -> str | None:
        if not target_program_id:
            return None

        if not PROGRAM_ID_PATTERN.search(logical_line):
            return None

        program_id = str(target_program_id or "").strip().upper()

        if not program_id:
            return None

        replacement_body = f"PROGRAM-ID. {program_id}."

        return self._replace_logical_body(
            original_line=original_line,
            replacement_body=replacement_body,
        )

    def _fix_program_id_period(
        self,
        text: str,
        target_program_id: str,
    ) -> str:
        program_id = str(target_program_id or "").strip().upper()

        if program_id:
            pattern = re.compile(
                rf"PROGRAM-ID\.\s*{re.escape(program_id)}\.?",
                flags=re.IGNORECASE,
            )

            return pattern.sub(
                f"PROGRAM-ID. {program_id}.",
                text,
                count=1,
            )

        return re.sub(
            r"(PROGRAM-ID\.\s*[A-Z0-9-]+)\s*$",
            r"\1.",
            text,
            count=1,
            flags=re.IGNORECASE | re.MULTILINE,
        )

    def _is_cbl_line(
        self,
        logical_line: str,
    ) -> bool:
        return str(logical_line or "").strip().upper().startswith("CBL ")

    def _is_idms_declarative_or_control(
        self,
        logical_line: str,
    ) -> bool:
        statement = str(logical_line or "").strip().rstrip(".")

        for pattern in self.IDMS_DECLARATIVE_PATTERNS:
            if pattern.search(statement):
                return True

        return False

    def _is_idms_executable_cleanup(
        self,
        logical_line: str,
    ) -> bool:
        statement = str(logical_line or "").strip().rstrip(".")

        for pattern in self.IDMS_EXECUTABLE_PATTERNS:
            if pattern.search(statement):
                return True

        return False

    def _is_idms_abort_paragraph(
        self,
        logical_line: str,
    ) -> bool:
        statement = str(logical_line or "").strip()

        return bool(self.IDMS_ABORT_PARAGRAPH_PATTERN.match(statement))

    def _is_exit_line(
        self,
        logical_line: str,
    ) -> bool:
        statement = str(logical_line or "").strip()

        return bool(self.EXIT_LINE_PATTERN.match(statement))

    def _removed_declarative_lines(
        self,
        logical_line: str,
    ) -> list[str]:
        return [
            f"* DB2: Removed residual IDMS control statement: {logical_line}",
        ]

    def _removed_executable_lines(
        self,
        logical_line: str,
        current_division: str,
    ) -> list[str]:
        statement = str(logical_line or "").strip()

        if re.search(
            r"^FINISH\.?$",
            statement,
            flags=re.IGNORECASE,
        ):
            if current_division == "PROCEDURE":
                return [
                    "* DB2: IDMS FINISH converted to COMMIT.",
                    "MOVE 'COMMIT' TO SQL-LOCATION.",
                    "EXEC SQL",
                    "    COMMIT",
                    "END-EXEC.",
                ]

            return [
                f"* DB2: Removed IDMS FINISH outside PROCEDURE DIVISION: {statement}",
            ]

        if re.search(
            r"^BIND\b",
            statement,
            flags=re.IGNORECASE,
        ):
            return self._procedure_safe_removal(
                message=f"* DB2: Removed IDMS BIND statement: {statement}",
                current_division=current_division,
            )

        if re.search(
            r"^FIND\s+CURRENT\b",
            statement,
            flags=re.IGNORECASE,
        ):
            return self._procedure_safe_removal(
                message=f"* DB2: Removed IDMS FIND CURRENT statement: {statement}",
                current_division=current_division,
            )

        return self._procedure_safe_removal(
            message=f"* DB2: Removed residual IDMS executable statement: {statement}",
            current_division=current_division,
        )

    def _procedure_safe_removal(
        self,
        message: str,
        current_division: str,
    ) -> list[str]:
        if current_division == "PROCEDURE":
            return [
                message,
                "CONTINUE.",
            ]

        return [
            message,
        ]

    def _transformer_changed_line(
        self,
        original_logical: str,
        transformed_lines: list[str],
    ) -> bool:
        if not transformed_lines:
            return False

        if len(transformed_lines) != 1:
            return True

        transformed = str(transformed_lines[0] or "").strip()
        original = str(original_logical or "").strip()

        return transformed != original

    def _logical_line(
        self,
        line: str,
    ) -> str:
        text = str(line or "").rstrip()

        text = self._remove_right_sequence(text)
        text = self._remove_left_sequence(text)

        return text.strip()

    def _remove_left_sequence(
        self,
        line: str,
    ) -> str:
        text = str(line or "")

        if len(text) >= 6 and text[:6].strip().isdigit():
            return text[6:].strip()

        return text

    def _remove_right_sequence(
        self,
        line: str,
    ) -> str:
        text = str(line or "").rstrip()

        match = re.match(
            r"^(?P<body>.*?)(?:\s+(?P<right>\d{8}))\s*$",
            text,
            flags=re.IGNORECASE,
        )

        if match:
            return match.group("body").rstrip()

        return text

    def _replace_logical_body(
        self,
        original_line: str,
        replacement_body: str,
    ) -> str:
        text = str(original_line or "").rstrip()

        left_sequence = ""
        body_with_possible_right = text

        left_match = re.match(
            r"^(?P<left>\s*\d{6}\s+)(?P<body>.*)$",
            body_with_possible_right,
        )

        if left_match:
            left_sequence = left_match.group("left")
            body_with_possible_right = left_match.group("body")

        right_match = re.match(
            r"^(?P<body>.*?)(?P<spaces>\s+)(?P<right>\d{8})\s*$",
            body_with_possible_right,
        )

        if right_match:
            original_body = right_match.group("body")
            original_spaces = right_match.group("spaces")
            right_sequence = right_match.group("right")

            original_body_area_width = len(original_body) + len(original_spaces)

            replacement = str(replacement_body or "")

            if len(replacement) >= original_body_area_width:
                formatted_body = replacement + " "
            else:
                formatted_body = replacement.ljust(original_body_area_width)

            return f"{left_sequence}{formatted_body}{right_sequence}"

        if left_sequence:
            return f"{left_sequence}{replacement_body}"

        return str(replacement_body or "")

    def _detect_sql_error_paragraph(
        self,
        cobol_text: str,
    ) -> str:
        match = SQL_ERROR_PARAGRAPH_PATTERN.search(str(cobol_text or ""))

        if not match:
            return "SQL-ERROR"

        return match.group(1).upper()