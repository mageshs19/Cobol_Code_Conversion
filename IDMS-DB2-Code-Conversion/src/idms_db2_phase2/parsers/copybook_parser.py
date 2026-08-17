from idms_db2_phase2.domain.models import CopybookField
from idms_db2_phase2.parsers.base_text_parser import BaseTextParser
from patterns.copybook_patterns import (
    COPYBOOK_COMMENT_OR_SKIP_PATTERN,
    COPYBOOK_FIELD_PATTERN,
    COPYBOOK_OCCURS_PATTERN,
    COPYBOOK_PIC_PATTERN,
    COPYBOOK_USAGE_PATTERN,
)


class CopybookParser(BaseTextParser):
    """
    Parses COBOL copybook fields.

    This parser contains parsing logic only. Regex patterns live in
    patterns/copybook_patterns.py.
    """

    def parse(
        self,
        text: str,
    ) -> list[CopybookField]:
        if not str(text or "").strip():
            return []

        output: list[CopybookField] = []
        logical_lines = self._logical_lines(text)

        for line in logical_lines:
            match = COPYBOOK_FIELD_PATTERN.search(line)

            if not match:
                continue

            name = str(match.group("name") or "").strip().upper()
            rest = str(match.group("rest") or "")

            if not name:
                continue

            if name == "FILLER":
                continue

            output.append(
                CopybookField(
                    level=str(match.group("level") or "").strip(),
                    name=name,
                    picture=self._picture(rest),
                    usage=self._usage(rest),
                    occurs=self._occurs(rest),
                )
            )

        return output

    def _picture(
        self,
        text: str,
    ) -> str:
        match = COPYBOOK_PIC_PATTERN.search(str(text or ""))

        if not match:
            return ""

        return str(match.group("pic") or "").strip().upper()

    def _usage(
        self,
        text: str,
    ) -> str:
        match = COPYBOOK_USAGE_PATTERN.search(str(text or ""))

        if not match:
            return ""

        return str(match.group("usage") or "").strip().upper()

    def _occurs(
        self,
        text: str,
    ) -> str:
        match = COPYBOOK_OCCURS_PATTERN.search(str(text or ""))

        if not match:
            return ""

        return str(match.group("occurs") or "").strip()

    def _logical_lines(
        self,
        text: str,
    ) -> list[str]:
        output: list[str] = []
        buffer = ""

        for raw_line in str(text or "").splitlines():
            line = self.strip_sequence_area(raw_line).rstrip()

            if not line.strip():
                continue

            if COPYBOOK_COMMENT_OR_SKIP_PATTERN.search(line):
                continue

            if buffer:
                buffer = f"{buffer} {line.strip()}"
            else:
                buffer = line.strip()

            if "." in line:
                parts = buffer.split(".")

                for part in parts[:-1]:
                    clean = part.strip()

                    if clean:
                        output.append(clean + ".")

                buffer = parts[-1].strip()

        if buffer.strip():
            output.append(buffer.strip())

        return output