"""
Fixed-format COBOL line helper service.

No regex.
No business hardcoding.

Purpose:
- Preserve existing left sequence, indicator, body, and right sequence layout.
- Allow services to update only the COBOL body area safely.
"""

from __future__ import annotations


class FixedFormatLineService:
    """
    Utility for fixed-format COBOL lines.

    Physical layout:
    - Columns 1-6   : left sequence
    - Column 7      : indicator
    - Columns 8-72  : COBOL body
    - Columns 73-80 : right sequence
    """

    LEFT_SEQUENCE_START = 0
    LEFT_SEQUENCE_END = 6
    INDICATOR_INDEX = 6
    BODY_START = 7
    BODY_END = 72
    RIGHT_SEQUENCE_START = 72
    RIGHT_SEQUENCE_END = 80
    BODY_WIDTH = 65

    def is_fixed_line(self, line: str) -> bool:
        text = str(line or "").rstrip("\n")

        return (
            len(text) >= self.RIGHT_SEQUENCE_END
            and text[self.LEFT_SEQUENCE_START:self.LEFT_SEQUENCE_END].isdigit()
            and text[self.RIGHT_SEQUENCE_START:self.RIGHT_SEQUENCE_END].isdigit()
        )

    def split(self, line: str) -> tuple[str, str, str, str]:
        text = str(line or "").rstrip("\n")

        if self.is_fixed_line(text):
            left = text[self.LEFT_SEQUENCE_START:self.LEFT_SEQUENCE_END]
            indicator = text[self.INDICATOR_INDEX]
            body = text[self.BODY_START:self.BODY_END]
            right = text[self.RIGHT_SEQUENCE_START:self.RIGHT_SEQUENCE_END]
            return left, indicator, body, right

        return "", "", text, ""

    def body(self, line: str) -> str:
        return self.split(line)[2]

    def logical(self, line: str) -> str:
        return self.body(line).strip()

    def replace_body(self, line: str, new_body: str) -> str:
        left, indicator, _old_body, right = self.split(line)
        return self.build(left, indicator, new_body, right)

    def build(
        self,
        left_sequence: str,
        indicator: str,
        body: str,
        right_sequence: str,
    ) -> str:
        if left_sequence and right_sequence:
            safe_body = str(body or "")[: self.BODY_WIDTH].ljust(self.BODY_WIDTH)
            return f"{left_sequence}{indicator}{safe_body}{right_sequence}"

        return str(body or "")

    def is_comment_or_control_line(self, line: str) -> bool:
        _left, indicator, _body, _right = self.split(line)
        return indicator in {"*", "/", "D", "d"}

    def leading_body_spaces(self, line: str, default: str = "") -> str:
        body = self.body(line)
        count = len(body) - len(body.lstrip(" "))

        if count <= 0:
            return default

        return body[:count]