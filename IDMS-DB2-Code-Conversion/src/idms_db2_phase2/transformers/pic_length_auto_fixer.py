from idms_db2_phase2.services.name_normalizer import NameNormalizer
from patterns.pic_patterns import (
    DATA_ENTRY_START_PATTERN,
    MOVE_PATTERN,
    NUMERIC_PIC_PATTERN,
)


class PicLengthAutoFixer:
    """
    Auto-fixes target COBOL PIC lengths when a MOVE source has more numeric
    digits than the MOVE target.

    This transformer is generic and does not hardcode business fields.
    """

    def __init__(self) -> None:
        self.messages: list[str] = []

    def fix(
        self,
        source_cobol_text: str,
        converted_cobol_text: str,
    ) -> str:
        self.messages = []

        if not converted_cobol_text:
            return converted_cobol_text

        combined_text = "\n".join(
            [
                source_cobol_text or "",
                converted_cobol_text or "",
            ]
        )

        pic_lengths = self._parse_numeric_pic_lengths(combined_text)

        if not pic_lengths:
            self.messages.append("Auto-fix PIC: no numeric PIC fields found.")
            return converted_cobol_text

        move_pairs = self._parse_move_pairs(converted_cobol_text)

        if not move_pairs:
            self.messages.append("Auto-fix PIC: no MOVE source/target pairs found.")
            return converted_cobol_text

        fixes: dict[str, int] = {}

        for source_name, target_name in move_pairs:
            source_key = self._normalize_move_identifier(source_name)
            target_key = self._normalize_move_identifier(target_name)

            source_digits = pic_lengths.get(source_key)
            target_digits = pic_lengths.get(target_key)

            if not source_digits or not target_digits:
                continue

            if source_digits > target_digits:
                fixes[target_key] = max(
                    fixes.get(target_key, 0),
                    source_digits,
                )

        if not fixes:
            self.messages.append("Auto-fix PIC: no target PIC expansion required.")
            return converted_cobol_text

        updated = self._apply_fixes(
            converted_cobol_text=converted_cobol_text,
            fixes=fixes,
        )

        return updated

    def _parse_numeric_pic_lengths(
        self,
        text: str,
    ) -> dict[str, int]:
        output: dict[str, int] = {}

        for line in str(text or "").splitlines():
            match = DATA_ENTRY_START_PATTERN.match(line)

            if not match:
                continue

            name = self._normalize_move_identifier(match.group("name"))
            rest = match.group("rest") or ""

            digits = self._numeric_pic_digits(rest)

            if name and digits:
                output[name] = digits

        return output

    def _parse_move_pairs(
        self,
        text: str,
    ) -> list[tuple[str, str]]:
        output: list[tuple[str, str]] = []

        for match in MOVE_PATTERN.finditer(str(text or "")):
            source = str(match.group("source") or "")
            target = str(match.group("target") or "")

            if source and target:
                output.append((source, target))

        return output

    def _numeric_pic_digits(
        self,
        text: str,
    ) -> int | None:
        match = NUMERIC_PIC_PATTERN.search(str(text or ""))

        if not match:
            return None

        explicit_length = match.group("len")
        pic = match.group("pic") or ""

        if explicit_length:
            try:
                return int(explicit_length)
            except ValueError:
                return None

        return pic.upper().count("9")

    def _apply_fixes(
        self,
        converted_cobol_text: str,
        fixes: dict[str, int],
    ) -> str:
        output_lines: list[str] = []

        for line in converted_cobol_text.splitlines():
            match = DATA_ENTRY_START_PATTERN.match(line)

            if not match:
                output_lines.append(line)
                continue

            field_name = self._normalize_move_identifier(match.group("name"))
            required_digits = fixes.get(field_name)

            if not required_digits:
                output_lines.append(line)
                continue

            updated_line = self._replace_pic_digits(
                line=line,
                required_digits=required_digits,
            )

            if updated_line != line:
                self.messages.append(
                    f"Auto-fix PIC: expanded {field_name} to 9({required_digits})."
                )

            output_lines.append(updated_line)

        return "\n".join(output_lines).rstrip() + "\n"

    def _replace_pic_digits(
        self,
        line: str,
        required_digits: int,
    ) -> str:
        def repl(match) -> str:
            pic = match.group("pic") or ""
            trailing = match.group("trailing") or ""
            dot = match.group("dot") or ""
            sign_prefix = "S" if pic.upper().startswith("S") else ""
            new_pic = f"{sign_prefix}9({required_digits})"

            return f"PIC {new_pic}{trailing}{dot}"

        return NUMERIC_PIC_PATTERN.sub(
            repl,
            line,
            count=1,
        )

    def _normalize_move_identifier(
        self,
        value: str,
    ) -> str:
        text = str(value or "").strip()

        if "." in text:
            text = text.split(".")[-1]

        return NameNormalizer.to_cobol(text)