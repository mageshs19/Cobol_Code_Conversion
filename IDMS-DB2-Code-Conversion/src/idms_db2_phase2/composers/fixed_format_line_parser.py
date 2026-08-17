"""
Fixed-format COBOL line parser.

Responsibilities:
- Parse already sequenced 80-column COBOL lines.
- Parse unsequenced COBOL lines.
- Strip old left and right sequence numbers.
- Preserve COBOL body indentation.
- Detect indicator column values.

Important:
- A true left sequence number must start in column 1 and must be exactly
  six digits.
- COBOL level numbers such as 01, 03, 05, 10, 20, 77, and 88 must never be
  treated as sequence numbers.
- Old right sequence numbers may appear separated by spaces or accidentally
  attached to the COBOL body. Both cases are handled conservatively.
"""

from __future__ import annotations

import re


try:
    from patterns.fixed_format_patterns import DEBUG_LINE_PATTERN
except Exception:
    DEBUG_LINE_PATTERN = re.compile(
        r"^[Dd]\s+",
        flags=re.IGNORECASE,
    )


try:
    from rules.fixed_format_rules import (
        BODY_WIDTH,
        COMMENT_INDICATOR,
        DEBUG_INDICATOR,
        PAGE_INDICATOR,
        SPACE_INDICATOR,
        TOTAL_WIDTH,
        VALID_INDICATORS,
    )
except Exception:
    BODY_WIDTH = 65
    COMMENT_INDICATOR = "*"
    DEBUG_INDICATOR = "D"
    PAGE_INDICATOR = "/"
    SPACE_INDICATOR = " "
    TOTAL_WIDTH = 80
    VALID_INDICATORS = {
        SPACE_INDICATOR,
        COMMENT_INDICATOR,
        DEBUG_INDICATOR,
        DEBUG_INDICATOR.lower(),
        PAGE_INDICATOR,
        "-",
    }


class FixedFormatLineParser:
    """
    Parses fixed-format and loose COBOL lines safely.
    """

    TRUE_LEFT_SEQUENCE_PATTERN = re.compile(
        r"^(?P<left>\d{6})(?P<body>\s+.*)$",
        flags=re.IGNORECASE,
    )

    RIGHT_SEQUENCE_WITH_SPACES_PATTERN = re.compile(
        r"^(?P<body>.*?)(?P<spaces>\s+)(?P<right>\d{8})\s*$",
        flags=re.IGNORECASE,
    )

    TRAILING_TIGHT_RIGHT_SEQUENCE_PATTERN = re.compile(
        r"^(?P<body>.*\S)(?P<right>\d{8})\s*$",
        flags=re.IGNORECASE,
    )

    COBOL_STATEMENT_STARTERS = (
        "ACCEPT ",
        "ADD ",
        "CALL ",
        "CLOSE ",
        "COMPUTE ",
        "CONTINUE",
        "DISPLAY ",
        "ELSE",
        "END-",
        "EVALUATE ",
        "EXEC ",
        "EXIT",
        "IF ",
        "INITIALIZE ",
        "MOVE ",
        "OPEN ",
        "PERFORM ",
        "READ ",
        "SET ",
        "STOP ",
        "TO ",
        "WHEN ",
        "WRITE ",
    )

    def parse_line(
        self,
        line: str,
    ) -> dict[str, str | bool]:
        text = str(line or "").rstrip()

        fixed = self.parse_fixed_80_line(text)

        if fixed is not None:
            return fixed

        body = self.remove_loose_sequence_numbers(text)
        indicator = self.indicator_for_body(body)
        body = self.strip_inline_indicator(
            body=body,
            indicator=indicator,
        )

        return {
            "left_sequence": "",
            "indicator": indicator,
            "body": body,
            "right_sequence": "",
            "is_fixed_format": False,
        }

    def parse_fixed_80_line(
        self,
        line: str,
    ) -> dict[str, str | bool] | None:
        text = str(line or "")

        if not self._is_fixed_format_line(text):
            return None

        left_seq = text[:6]
        indicator = text[6:7]
        body = text[7:72].rstrip()
        right_seq = text[72:80]

        if indicator not in VALID_INDICATORS:
            indicator = SPACE_INDICATOR

        return {
            "left_sequence": left_seq,
            "indicator": indicator,
            "body": body,
            "right_sequence": right_seq,
            "is_fixed_format": True,
        }

    def body_for_boolean_merge(
        self,
        line: str,
    ) -> str:
        parsed = self.parse_line(line)
        return str(parsed.get("body", ""))

    def remove_loose_sequence_numbers(
        self,
        line: str,
    ) -> str:
        text = str(line or "").rstrip()
        text = self.remove_loose_right_sequence(text)
        text = self.remove_loose_left_sequence(text)
        return text.rstrip()

    def remove_loose_left_sequence(
        self,
        line: str,
    ) -> str:
        text = str(line or "")
        match = self.TRUE_LEFT_SEQUENCE_PATTERN.match(text)

        if not match:
            return text

        left = str(match.group("left") or "")
        body = str(match.group("body") or "")

        if not left.isdigit() or len(left) != 6:
            return text

        return body.lstrip()

    def remove_loose_right_sequence(
        self,
        line: str,
    ) -> str:
        text = str(line or "").rstrip()

        spaced = self.RIGHT_SEQUENCE_WITH_SPACES_PATTERN.match(text)

        if spaced:
            body = str(spaced.group("body") or "").rstrip()
            spaces = str(spaced.group("spaces") or "")
            right = str(spaced.group("right") or "")

            if self._looks_like_spaced_right_sequence(
                body=body,
                spaces=spaces,
                right=right,
                original=text,
            ):
                return body

        tight = self.TRAILING_TIGHT_RIGHT_SEQUENCE_PATTERN.match(text)

        if tight:
            body = str(tight.group("body") or "").rstrip()
            right = str(tight.group("right") or "")

            if self._looks_like_tight_right_sequence(
                body=body,
                right=right,
                original=text,
            ):
                return body

        return text

    def _looks_like_spaced_right_sequence(
        self,
        body: str,
        spaces: str,
        right: str,
        original: str,
    ) -> bool:
        if not self._is_eight_digit_sequence(right):
            return False

        if not body:
            return False

        if len(original) >= TOTAL_WIDTH:
            return True

        if len(spaces) >= 2:
            return True

        return False

    def _looks_like_tight_right_sequence(
        self,
        body: str,
        right: str,
        original: str,
    ) -> bool:
        if not self._is_eight_digit_sequence(right):
            return False

        if not body:
            return False

        if len(original) >= TOTAL_WIDTH and original[72:80].isdigit():
            return True

        body_upper = body.strip().upper()

        if not body_upper:
            return False

        if body_upper.startswith(self.COBOL_STATEMENT_STARTERS):
            return True

        if right.startswith("0000") and self._body_ends_like_cobol_identifier(body):
            return True

        return False

    def _is_eight_digit_sequence(
        self,
        value: str,
    ) -> bool:
        text = str(value or "")
        return len(text) == 8 and text.isdigit()

    def _body_ends_like_cobol_identifier(
        self,
        body: str,
    ) -> bool:
        text = str(body or "").rstrip()

        if not text:
            return False

        if text[-1].isdigit():
            return False

        if text[-1] in {"'", '"'}:
            return False

        last_token = text.split()[-1]

        return bool(
            re.fullmatch(
                r"[A-Z][A-Z0-9-]*",
                last_token,
                flags=re.IGNORECASE,
            )
        )

    def indicator_for_body(
        self,
        body: str,
    ) -> str:
        text = str(body or "")

        if not text:
            return SPACE_INDICATOR

        stripped = text.lstrip()

        if stripped.startswith(COMMENT_INDICATOR):
            return COMMENT_INDICATOR

        if stripped.startswith(PAGE_INDICATOR):
            return PAGE_INDICATOR

        if DEBUG_LINE_PATTERN.match(text):
            return DEBUG_INDICATOR

        return SPACE_INDICATOR

    def strip_inline_indicator(
        self,
        body: str,
        indicator: str,
    ) -> str:
        text = str(body or "")

        if indicator in {COMMENT_INDICATOR, PAGE_INDICATOR}:
            stripped = text.lstrip()

            if stripped.startswith(indicator):
                return stripped[1:].lstrip()

        if indicator == DEBUG_INDICATOR and DEBUG_LINE_PATTERN.match(text):
            stripped = text.lstrip()

            if stripped[:1].upper() == DEBUG_INDICATOR:
                return stripped[1:].lstrip()

        return text.rstrip()

    def replace_body_preserving_sequence(
        self,
        original_line: str,
        new_body: str,
    ) -> str:
        text = str(original_line or "").rstrip()
        parsed = self.parse_line(text)

        if bool(parsed.get("is_fixed_format")):
            left = str(parsed.get("left_sequence") or "").zfill(6)[-6:]
            indicator = str(parsed.get("indicator") or SPACE_INDICATOR)[:1]
            right = str(parsed.get("right_sequence") or "").zfill(8)[-8:]

            if indicator not in VALID_INDICATORS:
                indicator = SPACE_INDICATOR

            body = str(new_body or "").rstrip()
            return f"{left}{indicator}{body[:BODY_WIDTH].ljust(BODY_WIDTH)}{right}"

        match = self.TRUE_LEFT_SEQUENCE_PATTERN.match(text)

        if match:
            left = str(match.group("left") or "").zfill(6)[-6:]
            return f"{left} {new_body}"

        return str(new_body or "").rstrip()

    def is_debug_line(
        self,
        stripped: str,
    ) -> bool:
        return bool(DEBUG_LINE_PATTERN.match(str(stripped or "")))

    def _is_fixed_format_line(
        self,
        line: str,
    ) -> bool:
        text = str(line or "")

        if len(text) < TOTAL_WIDTH:
            return False

        if not text[:6].isdigit():
            return False

        if not text[72:80].isdigit():
            return False

        return True