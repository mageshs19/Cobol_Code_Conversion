import re


class FixedFormatComposer:
    """
    Final fixed-format COBOL composer.

    Enforces:
    - Columns 1-6   : left sequence number
    - Column 7      : indicator area
    - Columns 8-72  : COBOL body
    - Columns 73-80 : right sequence number

    Generic rules:
    - Preserve indentation of existing sequenced COBOL lines.
    - Do not truncate generated COBOL statements.
    - Split long MOVE statements safely.
    - Split long IF ... AND / IF ... OR statements safely.
    - Merge dangling boolean continuations before wrapping.
    - Keep comments in column 7.
    - Keep generated normal statements in Area B when inside PROCEDURE DIVISION.
    """

    TOTAL_WIDTH = 80
    BODY_WIDTH = 65

    DEFAULT_LEFT_START = 10
    DEFAULT_LEFT_STEP = 10
    DEFAULT_RIGHT_START = 10
    DEFAULT_RIGHT_STEP = 10

    LEFT_SEQUENCE_PATTERN = re.compile(
        r"^\s*(?P<left>\d{6})(?P<rest>.*)$",
        flags=re.IGNORECASE,
    )

    RIGHT_SEQUENCE_PATTERN = re.compile(
        r"^(?P<body>.*?)(?P<right>\d{8})\s*$",
        flags=re.IGNORECASE,
    )

    SEQUENCE_ONLY_PATTERN = re.compile(
        r"^\s*(\d{6}|\d{8})\s*$",
        flags=re.IGNORECASE,
    )

    DIVISION_PATTERN = re.compile(
        r"^(IDENTIFICATION|ENVIRONMENT|DATA|PROCEDURE)\s+DIVISION\b.*\.?$",
        flags=re.IGNORECASE,
    )

    SECTION_PATTERN = re.compile(
        r"^[A-Z0-9-]+\s+SECTION\.?$",
        flags=re.IGNORECASE,
    )

    PARAGRAPH_PATTERN = re.compile(
        r"^[A-Z0-9][A-Z0-9-]*\.?$",
        flags=re.IGNORECASE,
    )

    AREA_A_PREFIX_PATTERN = re.compile(
        r"^(PROGRAM-ID\.|AUTHOR\.|INSTALLATION\.|DATE-WRITTEN\.|DATE-COMPILED\.|SECURITY\.|FD\s+|SD\s+|01\s+)",
        flags=re.IGNORECASE,
    )

    EXEC_SQL_START_PATTERN = re.compile(
        r"^EXEC\s+SQL\b",
        flags=re.IGNORECASE,
    )

    EXEC_SQL_END_PATTERN = re.compile(
        r"^END-EXEC\.?$",
        flags=re.IGNORECASE,
    )

    NON_PARAGRAPH_WORDS = {
        "ACCEPT",
        "ADD",
        "CALL",
        "CLOSE",
        "COMMIT",
        "CONTINUE",
        "DISPLAY",
        "ELSE",
        "END-EXEC",
        "END-EVALUATE",
        "END-IF",
        "EXEC",
        "IF",
        "INITIALIZE",
        "MOVE",
        "OPEN",
        "PERFORM",
        "READ",
        "SET",
        "STOP",
        "WRITE",
        "WHEN",
    }

    PROCEDURE_VERBS = (
        "IF ",
        "MOVE ",
        "PERFORM ",
        "DISPLAY ",
        "SET ",
        "CONTINUE",
        "WHEN ",
        "EVALUATE ",
        "END-IF",
        "END-EVALUATE",
        "OPEN ",
        "CLOSE ",
        "READ ",
        "WRITE ",
        "ADD ",
        "CALL ",
    )

    def format(
        self,
        text: str,
        left_start: int | None = None,
        left_step: int | None = None,
        right_start: int | None = None,
        right_step: int | None = None,
        preserve_blank_lines: bool = True,
    ) -> str:
        if not text:
            return ""

        lines = self._normalize_line_endings(text).splitlines()
        lines = self._merge_dangling_boolean_lines(lines)

        current_left = (
            left_start
            if left_start is not None
            else self._detect_first_left_sequence(lines)
        )

        current_left_step = (
            left_step
            if left_step is not None
            else self._detect_left_sequence_step(lines)
        )

        current_right = (
            right_start
            if right_start is not None
            else self._detect_first_right_sequence(lines)
        )

        current_right_step = (
            right_step
            if right_step is not None
            else self._detect_right_sequence_step(lines)
        )

        output_lines: list[str] = []
        current_division = ""
        inside_exec_sql = False
        previous_procedure_indent = "    "

        for raw_line in lines:
            raw_text = str(raw_line or "").rstrip()

            if not raw_text.strip():
                if preserve_blank_lines:
                    output_lines.append("")
                continue

            if self.SEQUENCE_ONLY_PATTERN.match(raw_text.strip()):
                continue

            parsed = self._parse_line(raw_text)

            indicator = str(parsed["indicator"])
            body = str(parsed["body"])
            had_sequence = bool(parsed["had_sequence"])

            if not body.strip() and indicator == " ":
                if preserve_blank_lines:
                    output_lines.append("")
                continue

            logical = body.strip()

            division_match = self.DIVISION_PATTERN.match(logical)

            if division_match:
                current_division = division_match.group(1).upper()
                previous_procedure_indent = "    "

            if self.EXEC_SQL_START_PATTERN.match(logical):
                inside_exec_sql = True

            if had_sequence:
                area_body = self._preserve_existing_body(
                    body=body,
                    indicator=indicator,
                )
            else:
                area_body = self._generated_area_body(
                    body=body,
                    logical=logical,
                    current_division=current_division,
                    inside_exec_sql=inside_exec_sql,
                    indicator=indicator,
                    previous_procedure_indent=previous_procedure_indent,
                )

            if current_division == "PROCEDURE" and indicator == " ":
                area_body = self._repair_area_b_if_needed(
                    area_body=area_body,
                    previous_procedure_indent=previous_procedure_indent,
                )

            physical_bodies = self._wrap_body(
                body=area_body,
                indicator=indicator,
                inside_exec_sql=inside_exec_sql,
                current_division=current_division,
                previous_procedure_indent=previous_procedure_indent,
            )

            physical_bodies = self._repair_boolean_operator_only_lines(
                physical_bodies
            )

            for index, physical_body in enumerate(physical_bodies):
                physical_indicator = indicator

                if index > 0:
                    physical_indicator = self._continuation_indicator(indicator)

                output_lines.append(
                    self._compose_line(
                        left_seq=f"{current_left:06d}",
                        indicator=physical_indicator,
                        area_body=physical_body,
                        right_seq=f"{current_right:08d}",
                    )
                )

                current_left += current_left_step
                current_right += current_right_step

            if (
                current_division == "PROCEDURE"
                and indicator == " "
                and physical_bodies
                and not self._is_area_a_statement(logical)
            ):
                previous_procedure_indent = self._leading_spaces(
                    physical_bodies[0],
                    default=previous_procedure_indent or "    ",
                )

            if self.EXEC_SQL_END_PATTERN.match(logical):
                inside_exec_sql = False

        return "\n".join(output_lines).rstrip() + "\n"

    def _merge_dangling_boolean_lines(
        self,
        lines: list[str],
    ) -> list[str]:
        output: list[str] = []
        index = 0

        while index < len(lines):
            current = str(lines[index] or "").rstrip()

            if index + 1 >= len(lines):
                output.append(current)
                index += 1
                continue

            next_line = str(lines[index + 1] or "").rstrip()

            current_body = self._body_for_boolean_merge(current)
            next_body = self._body_for_boolean_merge(next_line)

            if not current_body.strip() or not next_body.strip():
                output.append(current)
                index += 1
                continue

            if self._is_comment_or_page_line(current_body):
                output.append(current)
                index += 1
                continue

            if self._is_comment_or_page_line(next_body):
                output.append(current)
                index += 1
                continue

            if self._ends_with_boolean_operator(current_body):
                merged_body = f"{current_body.rstrip()} {next_body.strip()}"

                output.append(
                    self._replace_body_preserving_sequence(
                        original_line=current,
                        new_body=merged_body,
                    )
                )

                index += 2
                continue

            output.append(current)
            index += 1

        return output

    def _body_for_boolean_merge(
        self,
        line: str,
    ) -> str:
        text = str(line or "").rstrip()

        fixed = self._parse_fixed_80_line(text)

        if fixed is not None:
            indicator = str(fixed.get("indicator", " "))
            body = str(fixed.get("body", ""))

            if indicator in {"*", "/"}:
                return indicator + body

            return body.rstrip()

        text_without_right = self._remove_loose_right_sequence(text)
        text_without_left = self._remove_loose_left_sequence(text_without_right)

        return text_without_left.rstrip()

    def _ends_with_boolean_operator(
        self,
        body: str,
    ) -> bool:
        return bool(
            re.search(
                r"\b(AND|OR)\s*$",
                str(body or "").strip(),
                flags=re.IGNORECASE,
            )
        )

    def _is_comment_or_page_line(
        self,
        logical: str,
    ) -> bool:
        stripped = str(logical or "").strip()

        return stripped.startswith("*") or stripped.startswith("/")

    def _replace_body_preserving_sequence(
        self,
        original_line: str,
        new_body: str,
    ) -> str:
        text = str(original_line or "").rstrip()

        fixed = self._parse_fixed_80_line(text)

        if fixed is not None:
            left = text[:6]
            indicator = text[6:7]
            right = text[72:80]

            if indicator not in {"*", "/"}:
                indicator = " "

            body = str(new_body or "").rstrip()

            return f"{left}{indicator}{body:<65}{right}"

        left_match = self.LEFT_SEQUENCE_PATTERN.match(text)

        if left_match:
            left = left_match.group("left")
            return f"{left} {new_body}"

        return str(new_body or "").rstrip()

    def _normalize_line_endings(
        self,
        text: str,
    ) -> str:
        return str(text or "").replace("\r\n", "\n").replace("\r", "\n")

    def _parse_line(
        self,
        line: str,
    ) -> dict[str, object]:
        text = str(line or "").rstrip()

        fixed = self._parse_fixed_80_line(text)

        if fixed is not None:
            return fixed

        stripped = text.lstrip()

        if stripped.startswith("*"):
            return {
                "indicator": "*",
                "body": stripped[1:].rstrip(),
                "had_sequence": False,
            }

        if stripped.startswith("/"):
            return {
                "indicator": "/",
                "body": stripped[1:].rstrip(),
                "had_sequence": False,
            }

        text_without_right = self._remove_loose_right_sequence(text)
        text_without_left = self._remove_loose_left_sequence(text_without_right)

        stripped_without_left = text_without_left.lstrip()

        if stripped_without_left.startswith("*"):
            return {
                "indicator": "*",
                "body": stripped_without_left[1:].rstrip(),
                "had_sequence": True,
            }

        if stripped_without_left.startswith("/"):
            return {
                "indicator": "/",
                "body": stripped_without_left[1:].rstrip(),
                "had_sequence": True,
            }

        had_sequence = text_without_left != text or text_without_right != text

        return {
            "indicator": " ",
            "body": text_without_left.rstrip(),
            "had_sequence": had_sequence,
        }

    def _parse_fixed_80_line(
        self,
        text: str,
    ) -> dict[str, object] | None:
        if len(text) < self.TOTAL_WIDTH:
            return None

        left = text[:6]
        indicator = text[6:7]
        body = text[7:72]
        right = text[72:80]

        if not left.isdigit():
            return None

        if not right.isdigit():
            return None

        if indicator not in {" ", "*", "/"}:
            indicator = " "

        return {
            "indicator": indicator,
            "body": body.rstrip(),
            "had_sequence": True,
        }

    def _remove_loose_left_sequence(
        self,
        text: str,
    ) -> str:
        match = self.LEFT_SEQUENCE_PATTERN.match(str(text or ""))

        if not match:
            return str(text or "")

        left_value = match.group("left")

        if not left_value.isdigit():
            return str(text or "")

        rest = match.group("rest")

        if rest.startswith(" "):
            rest = rest[1:]

        return rest.rstrip()

    def _remove_loose_right_sequence(
        self,
        text: str,
    ) -> str:
        value = str(text or "").rstrip()
        match = self.RIGHT_SEQUENCE_PATTERN.match(value)

        if not match:
            return value

        right_value = match.group("right")

        if not right_value.isdigit():
            return value

        return match.group("body").rstrip()

    def _preserve_existing_body(
        self,
        body: str,
        indicator: str,
    ) -> str:
        return str(body or "").rstrip()

    def _generated_area_body(
        self,
        body: str,
        logical: str,
        current_division: str,
        inside_exec_sql: bool,
        indicator: str,
        previous_procedure_indent: str,
    ) -> str:
        if indicator in {"*", "/"}:
            return str(body or "").rstrip()

        clean_statement = str(body or "").strip()

        if not clean_statement:
            return ""

        if inside_exec_sql:
            if self.EXEC_SQL_START_PATTERN.match(clean_statement):
                return clean_statement

            if self.EXEC_SQL_END_PATTERN.match(clean_statement):
                return clean_statement

            return "    " + clean_statement

        if self._is_area_a_statement(clean_statement):
            return clean_statement

        if current_division == "PROCEDURE":
            return previous_procedure_indent + clean_statement

        return clean_statement

    def _repair_area_b_if_needed(
        self,
        area_body: str,
        previous_procedure_indent: str,
    ) -> str:
        text = str(area_body or "").rstrip()
        stripped = text.strip()

        if not stripped:
            return text

        if self._is_area_a_statement(stripped):
            return text

        if text.startswith(" "):
            return text

        upper = stripped.upper()

        if upper.startswith(self.PROCEDURE_VERBS):
            return (previous_procedure_indent or "    ") + stripped

        return text

    def _wrap_body(
        self,
        body: str,
        indicator: str,
        inside_exec_sql: bool,
        current_division: str,
        previous_procedure_indent: str,
    ) -> list[str]:
        text = str(body or "").rstrip()

        if len(text) <= self.BODY_WIDTH:
            return [text]

        if indicator in {"*", "/"}:
            return self._wrap_comment_body(text)

        return self._wrap_cobol_body(
            text=text,
            inside_exec_sql=inside_exec_sql,
            current_division=current_division,
            previous_procedure_indent=previous_procedure_indent,
        )

    def _wrap_comment_body(
        self,
        text: str,
    ) -> list[str]:
        clean = str(text or "").strip()

        if not clean:
            return [""]

        words = clean.split()
        lines: list[str] = []
        current = ""

        for word in words:
            candidate = word if not current else current + " " + word

            if len(candidate) <= self.BODY_WIDTH:
                current = candidate
                continue

            if current:
                lines.append(current)

            current = word

        if current:
            lines.append(current)

        return lines or [clean[: self.BODY_WIDTH]]

    def _wrap_cobol_body(
        self,
        text: str,
        inside_exec_sql: bool,
        current_division: str,
        previous_procedure_indent: str,
    ) -> list[str]:
        stripped = str(text or "").rstrip()
        logical = stripped.strip()

        leading_spaces = self._leading_spaces(
            stripped,
            default=previous_procedure_indent if current_division == "PROCEDURE" else "",
        )

        if current_division == "PROCEDURE" and not leading_spaces:
            leading_spaces = previous_procedure_indent or "    "

        if_lines = self._wrap_if_statement(
            logical=logical,
            indent=leading_spaces,
        )

        if if_lines:
            return if_lines

        move_lines = self._wrap_move_statement(
            logical=logical,
            indent=leading_spaces,
        )

        if move_lines:
            return move_lines

        display_lines = self._wrap_display_statement(
            logical=logical,
            indent=leading_spaces,
        )

        if display_lines:
            return display_lines

        return self._wrap_by_words(
            text=leading_spaces + logical,
            continuation_indent=leading_spaces + "    ",
        )

    def _wrap_if_statement(
        self,
        logical: str,
        indent: str,
    ) -> list[str]:
        if not logical.upper().startswith("IF "):
            return []

        split_result = self._split_condition_on_boolean_operator(logical)

        if not split_result:
            return []

        left_part, operator, right_part = split_result

        left_part = left_part.rstrip()
        operator = operator.strip().upper()
        right_part = right_part.strip()

        if not left_part or not operator or not right_part:
            return []

        first_line = f"{indent}{left_part}"
        second_line = f"{indent}   {operator} {right_part}"

        return self._force_lines_to_body_width(
            lines=[
                first_line,
                second_line,
            ],
            continuation_indent=indent + "   ",
        )

    def _split_condition_on_boolean_operator(
        self,
        logical: str,
    ) -> tuple[str, str, str] | None:
        text = str(logical or "").strip()

        tokens = re.split(
            r"(\s+AND\s+|\s+OR\s+)",
            text,
            maxsplit=1,
            flags=re.IGNORECASE,
        )

        if len(tokens) < 3:
            return None

        left_part = tokens[0].rstrip()
        operator = tokens[1].strip().upper()
        right_part = tokens[2].strip()

        if not left_part or not operator or not right_part:
            return None

        return left_part, operator, right_part

    def _force_lines_to_body_width(
        self,
        lines: list[str],
        continuation_indent: str,
    ) -> list[str]:
        output: list[str] = []

        for line in lines:
            text = str(line or "").rstrip()

            if len(text) <= self.BODY_WIDTH:
                output.append(text)
                continue

            indent = self._leading_spaces(
                text,
                default=continuation_indent,
            )

            content = text.strip()
            available_width = self.BODY_WIDTH - len(indent)

            while content:
                part = content[:available_width].rstrip()
                output.append(indent + part)
                content = content[len(part):].strip()

        return self._repair_boolean_operator_only_lines(output)

    def _repair_boolean_operator_only_lines(
        self,
        lines: list[str],
    ) -> list[str]:
        output: list[str] = []
        index = 0

        while index < len(lines):
            current = str(lines[index] or "").rstrip()
            current_stripped = current.strip().upper()

            if current_stripped in {"AND", "OR"} and index + 1 < len(lines):
                next_line = str(lines[index + 1] or "").rstrip()
                next_stripped = next_line.strip()

                if next_stripped:
                    indent = self._leading_spaces(
                        current,
                        default="   ",
                    )

                    repaired = f"{indent}{current_stripped} {next_stripped}"

                    if len(repaired) <= self.BODY_WIDTH:
                        output.append(repaired)
                        index += 2
                        continue

            output.append(current)
            index += 1

        return output

    def _wrap_move_statement(
        self,
        logical: str,
        indent: str,
    ) -> list[str]:
        match = re.match(
            r"^MOVE\s+(?P<src>.+?)\s+TO\s+(?P<tgt>.+?\.?)$",
            logical,
            flags=re.IGNORECASE,
        )

        if not match:
            return []

        src = match.group("src").strip()
        tgt = match.group("tgt").strip()

        first = f"{indent}MOVE {src}"
        second = f"{indent}TO {tgt}"

        if len(first) <= self.BODY_WIDTH and len(second) <= self.BODY_WIDTH:
            return [
                first,
                second,
            ]

        return self._wrap_by_words(
            text=f"{indent}{logical}",
            continuation_indent=indent + "    ",
        )

    def _wrap_display_statement(
        self,
        logical: str,
        indent: str,
    ) -> list[str]:
        if not logical.upper().startswith("DISPLAY "):
            return []

        return self._wrap_by_words(
            text=f"{indent}{logical}",
            continuation_indent=indent + "    ",
        )

    def _wrap_by_words(
        self,
        text: str,
        continuation_indent: str,
    ) -> list[str]:
        raw = str(text or "").rstrip()

        if len(raw) <= self.BODY_WIDTH:
            return [raw]

        leading_indent = self._leading_spaces(
            raw,
            default="",
        )

        stripped_text = raw.strip()
        words = stripped_text.split()

        lines: list[str] = []
        current = leading_indent

        for word in words:
            if current.strip():
                candidate = current.rstrip() + " " + word
            else:
                candidate = leading_indent + word

            if len(candidate) <= self.BODY_WIDTH:
                current = candidate
                continue

            if current.strip():
                lines.append(current.rstrip())

            current = continuation_indent + word

        if current.strip():
            lines.append(current.rstrip())

        normalized: list[str] = []

        for line in lines:
            if len(line) <= self.BODY_WIDTH:
                normalized.append(line)
                continue

            line_indent = self._leading_spaces(
                line,
                default=continuation_indent,
            )

            available_width = self.BODY_WIDTH - len(line_indent)
            content = line.strip()

            while content:
                part = content[:available_width].rstrip()
                normalized.append(line_indent + part)
                content = content[len(part):].strip()

        return normalized

    def _leading_spaces(
        self,
        text: str,
        default: str = "",
    ) -> str:
        value = str(text or "")

        if not value:
            return default

        count = len(value) - len(value.lstrip(" "))

        if count <= 0:
            return default

        return value[:count]

    def _continuation_indicator(
        self,
        indicator: str,
    ) -> str:
        if indicator in {"*", "/"}:
            return "*"

        return " "

    def _is_area_a_statement(
        self,
        statement: str,
    ) -> bool:
        logical = str(statement or "").strip()

        if self.DIVISION_PATTERN.match(logical):
            return True

        if self.SECTION_PATTERN.match(logical):
            return True

        if self.AREA_A_PREFIX_PATTERN.match(logical):
            return True

        paragraph_match = self.PARAGRAPH_PATTERN.match(logical)

        if paragraph_match:
            first_word = logical.rstrip(".").split()[0].upper()

            if first_word not in self.NON_PARAGRAPH_WORDS:
                return True

        return False

    def _compose_line(
        self,
        left_seq: str,
        indicator: str,
        area_body: str,
        right_seq: str,
    ) -> str:
        safe_indicator = str(indicator or " ")[:1]

        if safe_indicator not in {"*", "/"}:
            safe_indicator = " "

        safe_body = str(area_body or "").rstrip()

        if len(safe_body) > self.BODY_WIDTH:
            safe_body = safe_body[: self.BODY_WIDTH]

        body_area = safe_body.ljust(self.BODY_WIDTH)

        line = f"{left_seq}{safe_indicator}{body_area}{right_seq}"

        if len(line) > self.TOTAL_WIDTH:
            return line[: self.TOTAL_WIDTH]

        if len(line) < self.TOTAL_WIDTH:
            return line.ljust(self.TOTAL_WIDTH)

        return line

    def _detect_first_left_sequence(
        self,
        lines: list[str],
    ) -> int:
        for line in lines:
            text = str(line or "")

            if len(text) >= 6 and text[:6].isdigit():
                value = int(text[:6])

                if value > 0:
                    return value

        return self.DEFAULT_LEFT_START

    def _detect_first_right_sequence(
        self,
        lines: list[str],
    ) -> int:
        for line in lines:
            fixed = self._parse_fixed_80_line(str(line or "").rstrip())

            if fixed is not None:
                right = str(line or "").rstrip()[72:80]

                if right.isdigit():
                    value = int(right)

                    if value > 0:
                        return value

            match = self.RIGHT_SEQUENCE_PATTERN.match(str(line or "").rstrip())

            if match:
                try:
                    value = int(match.group("right"))
                except ValueError:
                    continue

                if value > 0:
                    return value

        return self.DEFAULT_RIGHT_START

    def _detect_left_sequence_step(
        self,
        lines: list[str],
    ) -> int:
        values: list[int] = []

        for line in lines:
            text = str(line or "")

            if len(text) >= 6 and text[:6].isdigit():
                values.append(int(text[:6]))

            if len(values) >= 8:
                break

        return self._detect_step(values, self.DEFAULT_LEFT_STEP)

    def _detect_right_sequence_step(
        self,
        lines: list[str],
    ) -> int:
        values: list[int] = []

        for line in lines:
            text = str(line or "").rstrip()
            fixed = self._parse_fixed_80_line(text)

            if fixed is not None:
                right = text[72:80]

                if right.isdigit():
                    values.append(int(right))
                    continue

            match = self.RIGHT_SEQUENCE_PATTERN.match(text)

            if match:
                try:
                    values.append(int(match.group("right")))
                except ValueError:
                    continue

            if len(values) >= 8:
                break

        return self._detect_step(values, self.DEFAULT_RIGHT_STEP)

    def _detect_step(
        self,
        values: list[int],
        default_step: int,
    ) -> int:
        if len(values) < 2:
            return default_step

        differences: list[int] = []

        for index in range(1, len(values)):
            difference = values[index] - values[index - 1]

            if difference > 0:
                differences.append(difference)

        if not differences:
            return default_step

        if 10 in differences:
            return 10

        if 100 in differences:
            return 100

        return differences[0]