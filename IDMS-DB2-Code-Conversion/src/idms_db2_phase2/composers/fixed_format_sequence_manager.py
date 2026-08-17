"""
Fixed-format COBOL sequence manager.

Responsibilities:
- Detect left sequence start and step from input when available.
- Detect manual-style right sequence start and step from input when available.
- Reject old/generated right sequence styles like 00000010, 00000020.
- Provide generic fallback manual sequence values when source cannot provide them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


try:
    from patterns.fixed_format_patterns import (
        LEFT_SEQUENCE_PATTERN,
        RIGHT_SEQUENCE_PATTERN,
    )
except Exception:
    LEFT_SEQUENCE_PATTERN = re.compile(
        r"^\s*(?P<left>\d{6})\s+(?P<body>.*)$",
        flags=re.IGNORECASE,
    )

    RIGHT_SEQUENCE_PATTERN = re.compile(
        r"^(?P<body>.*?)(?P<right>\d{8})\s*$",
        flags=re.IGNORECASE,
    )


try:
    from rules.fixed_format_rules import (
        DEFAULT_LEFT_START,
        DEFAULT_LEFT_STEP,
        DEFAULT_RIGHT_START,
        DEFAULT_RIGHT_STEP,
        TOTAL_WIDTH,
    )
except Exception:
    DEFAULT_LEFT_START = 10
    DEFAULT_LEFT_STEP = 10
    DEFAULT_RIGHT_START = 10000
    DEFAULT_RIGHT_STEP = 10000
    TOTAL_WIDTH = 80


@dataclass
class FixedFormatSequenceState:
    left_current: int
    left_step: int
    right_current: int
    right_step: int

    def current_left(
        self,
    ) -> str:
        return f"{self.left_current:06d}"

    def current_right(
        self,
    ) -> str:
        return f"{self.right_current:08d}"

    def advance(
        self,
    ) -> None:
        self.left_current += self.left_step
        self.right_current += self.right_step


class FixedFormatSequenceManager:
    """
    Generic sequence manager.

    Manual right sequence style:
    - 00010000
    - 00020000
    - 00030000

    Old/generated right sequence style:
    - 00000010
    - 00000020

    The old style is intentionally not preserved.
    """

    MIN_MANUAL_RIGHT_SEQUENCE = 10000
    MIN_MANUAL_RIGHT_STEP = 10000

    def create_state(
        self,
        lines: list[str],
        left_start: int | None = None,
        left_step: int | None = None,
        right_start: int | None = None,
        right_step: int | None = None,
    ) -> FixedFormatSequenceState:
        detected_left_values = self._left_sequence_values(lines)
        detected_right_values = self._right_sequence_values(lines)

        effective_left_start = (
            left_start
            if left_start is not None
            else self._first_positive(
                detected_left_values,
                DEFAULT_LEFT_START,
            )
        )

        effective_left_step = (
            left_step
            if left_step is not None
            else self._detect_step(
                detected_left_values,
                DEFAULT_LEFT_STEP,
            )
        )

        effective_right_start = (
            right_start
            if right_start is not None
            else self._detect_manual_right_start(
                detected_right_values,
            )
        )

        effective_right_step = (
            right_step
            if right_step is not None
            else self._detect_manual_right_step(
                detected_right_values,
            )
        )

        return FixedFormatSequenceState(
            left_current=effective_left_start,
            left_step=effective_left_step,
            right_current=effective_right_start,
            right_step=effective_right_step,
        )

    def _left_sequence_values(
        self,
        lines: list[str],
    ) -> list[int]:
        values: list[int] = []

        for line in lines:
            text = str(line or "").rstrip()

            if len(text) >= TOTAL_WIDTH and text[:6].isdigit():
                values.append(int(text[:6]))
                continue

            match = LEFT_SEQUENCE_PATTERN.match(text)

            if match:
                left = str(match.group("left") or "")

                if left.isdigit():
                    values.append(int(left))

        return values

    def _right_sequence_values(
        self,
        lines: list[str],
    ) -> list[int]:
        values: list[int] = []

        for line in lines:
            text = str(line or "").rstrip()

            if len(text) >= TOTAL_WIDTH and text[72:80].isdigit():
                values.append(int(text[72:80]))
                continue

            match = RIGHT_SEQUENCE_PATTERN.match(text)

            if match:
                right = str(match.group("right") or "")

                if right.isdigit():
                    values.append(int(right))

        return values

    def _first_positive(
        self,
        values: list[int],
        default_value: int,
    ) -> int:
        for value in values:
            if value > 0:
                return value

        return default_value

    def _detect_step(
        self,
        values: list[int],
        default_step: int,
    ) -> int:
        differences = self._positive_differences(values)

        if not differences:
            return default_step

        return self._most_common_difference(
            differences,
            default_step,
        )

    def _detect_manual_right_start(
        self,
        values: list[int],
    ) -> int:
        manual_values = [
            value
            for value in values
            if value >= self.MIN_MANUAL_RIGHT_SEQUENCE
        ]

        if not manual_values:
            return DEFAULT_RIGHT_START

        return manual_values[0]

    def _detect_manual_right_step(
        self,
        values: list[int],
    ) -> int:
        manual_values = [
            value
            for value in values
            if value >= self.MIN_MANUAL_RIGHT_SEQUENCE
        ]

        differences = self._positive_differences(manual_values)

        if not differences:
            return DEFAULT_RIGHT_STEP

        step = self._most_common_difference(
            differences,
            DEFAULT_RIGHT_STEP,
        )

        if step < self.MIN_MANUAL_RIGHT_STEP:
            return DEFAULT_RIGHT_STEP

        return step

    def _positive_differences(
        self,
        values: list[int],
    ) -> list[int]:
        differences: list[int] = []

        for index in range(1, len(values)):
            difference = values[index] - values[index - 1]

            if difference > 0:
                differences.append(difference)

        return differences

    def _most_common_difference(
        self,
        differences: list[int],
        default_step: int,
    ) -> int:
        if not differences:
            return default_step

        counts: dict[int, int] = {}

        for difference in differences:
            counts[difference] = counts.get(difference, 0) + 1

        return sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0]),
        )[0][0]