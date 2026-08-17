"""
SQLCODE wrapper cleanup composer.

This composer removes contradictory SQLCODE wrappers left after redundant
OBTAIN NEXT cursor calls have been removed.

It targets this generated pattern:

    IF NOT SQLCODE = 100
        * DB2: Removed redundant OBTAIN NEXT after cursor EOC loop.
        CONTINUE.
        IF SQLCODE = 100
            ...
        END-IF
    END-IF.

and rewrites it to:

    * DB2: Removed redundant SQLCODE wrapper after cursor EOC loop.
    IF WS-STATUS = 'C'
        ...
    END-IF

It also wraps MOVE statements inside the recovered block:

    MOVE SOURCE OF DCLGROUP TO TARGET

into:

    MOVE SOURCE OF DCLGROUP
    TO TARGET
"""

import re

from patterns.sequence_patterns import strip_sequence_numbers


class SqlcodeWrapperCleanupComposer:
    OUTER_IF_TEXT = "IF NOT SQLCODE = 100"
    INNER_IF_TEXT = "IF SQLCODE = 100"
    REMOVED_OBTAIN_NEXT_TEXT = (
        "DB2: REMOVED REDUNDANT OBTAIN NEXT AFTER CURSOR EOC LOOP"
    )
    CLEANUP_COMMENT_TEXT = (
        "DB2: Removed redundant SQLCODE wrapper after cursor EOC loop."
    )

    BASE_INDENT = "    "
    CHILD_INDENT = "        "
    BODY_WIDTH = 65

    MOVE_TO_PATTERN = re.compile(
        r"^MOVE\s+(?P<source>.+?)\s+TO\s+(?P<target>.+?\.?)$",
        flags=re.IGNORECASE,
    )

    def compose(
        self,
        text: str,
    ) -> str:
        if not text:
            return ""

        lines = self._normalize_line_endings(text).splitlines()

        output: list[str] = []
        index = 0

        while index < len(lines):
            logical = self._logical(lines[index]).upper()

            if self.OUTER_IF_TEXT not in logical:
                output.append(lines[index])
                index += 1
                continue

            block = self._try_extract_redundant_wrapper_block(
                lines=lines,
                start_index=index,
            )

            if block is None:
                output.append(lines[index])
                index += 1
                continue

            replacement_lines, next_index = block

            output.extend(replacement_lines)
            index = next_index

        return "\n".join(output).rstrip() + "\n"

    def _normalize_line_endings(
        self,
        text: str,
    ) -> str:
        return str(text or "").replace("\r\n", "\n").replace("\r", "\n")

    def _logical(
        self,
        line: str,
    ) -> str:
        return strip_sequence_numbers(str(line or "")).strip()

    def _try_extract_redundant_wrapper_block(
        self,
        lines: list[str],
        start_index: int,
    ) -> tuple[list[str], int] | None:
        outer_line = lines[start_index]

        marker_index = self._find_marker_after_outer_if(
            lines=lines,
            start_index=start_index + 1,
        )

        if marker_index < 0:
            return None

        inner_if_index = self._find_inner_if_sqlcode_100(
            lines=lines,
            start_index=marker_index + 1,
        )

        if inner_if_index < 0:
            return None

        inner_end_index = self._find_matching_end_if(
            lines=lines,
            if_index=inner_if_index,
        )

        if inner_end_index < 0:
            return None

        outer_end_index = self._find_matching_end_if(
            lines=lines,
            if_index=start_index,
        )

        if outer_end_index < 0:
            return None

        if outer_end_index <= inner_end_index:
            return None

        inner_body = lines[inner_if_index + 1 : inner_end_index]

        normalized_inner_body = self._normalize_inner_body(
            lines=inner_body,
        )

        replacement: list[str] = [
            self._format_comment_like_line(
                reference_line=outer_line,
                comment_text=self.CLEANUP_COMMENT_TEXT,
            )
        ]

        replacement.extend(normalized_inner_body)

        return replacement, outer_end_index + 1

    def _find_marker_after_outer_if(
        self,
        lines: list[str],
        start_index: int,
    ) -> int:
        end_index = min(
            len(lines),
            start_index + 8,
        )

        for index in range(start_index, end_index):
            logical = self._logical(lines[index]).upper()

            if self.REMOVED_OBTAIN_NEXT_TEXT in logical:
                return index

        return -1

    def _find_inner_if_sqlcode_100(
        self,
        lines: list[str],
        start_index: int,
    ) -> int:
        end_index = min(
            len(lines),
            start_index + 12,
        )

        for index in range(start_index, end_index):
            logical = self._logical(lines[index]).upper()

            if logical.startswith(self.INNER_IF_TEXT):
                return index

        return -1

    def _find_matching_end_if(
        self,
        lines: list[str],
        if_index: int,
    ) -> int:
        depth = 0

        for index in range(if_index, len(lines)):
            logical = self._logical(lines[index]).upper().rstrip(".")

            if logical.startswith("IF "):
                depth += 1
                continue

            if logical == "END-IF":
                depth -= 1

                if depth == 0:
                    return index

        return -1

    def _normalize_inner_body(
        self,
        lines: list[str],
    ) -> list[str]:
        output: list[str] = []
        first_content_seen = False

        for line in lines:
            logical = self._logical(line)

            if not logical:
                output.append(line)
                continue

            if logical.startswith("*") or logical.startswith("/"):
                output.append(line)
                continue

            if not first_content_seen:
                output.extend(
                    self._normalized_lines_for_logical(
                        original_line=line,
                        logical=logical,
                        indent=self.BASE_INDENT,
                    )
                )
                first_content_seen = True
                continue

            if logical.upper().rstrip(".") == "END-IF":
                output.extend(
                    self._normalized_lines_for_logical(
                        original_line=line,
                        logical="END-IF",
                        indent=self.BASE_INDENT,
                    )
                )
                continue

            output.extend(
                self._normalized_lines_for_logical(
                    original_line=line,
                    logical=logical,
                    indent=self.CHILD_INDENT,
                )
            )

        return output

    def _normalized_lines_for_logical(
        self,
        original_line: str,
        logical: str,
        indent: str,
    ) -> list[str]:
        wrapped_bodies = self._wrap_logical_body(
            logical=logical,
            indent=indent,
        )

        return [
            self._replace_body_part(
                original_line=original_line,
                new_body=body,
            )
            for body in wrapped_bodies
        ]

    def _wrap_logical_body(
        self,
        logical: str,
        indent: str,
    ) -> list[str]:
        text = str(logical or "").strip()

        if not text:
            return [indent.rstrip()]

        move_lines = self._wrap_move_statement(
            logical=text,
            indent=indent,
        )

        if move_lines:
            return move_lines

        body = indent + text

        if len(body) <= self.BODY_WIDTH:
            return [body]

        return self._wrap_by_words(
            body=body,
            continuation_indent=indent + "    ",
        )

    def _wrap_move_statement(
        self,
        logical: str,
        indent: str,
    ) -> list[str]:
        match = self.MOVE_TO_PATTERN.match(str(logical or "").strip())

        if not match:
            return []

        source = str(match.group("source") or "").strip()
        target = str(match.group("target") or "").strip()

        if not source or not target:
            return []

        force_split = " OF DCL" in source.upper()

        one_line = f"{indent}MOVE {source} TO {target}"

        if len(one_line) <= self.BODY_WIDTH and not force_split:
            return [one_line]

        first_line = f"{indent}MOVE {source}"
        second_line = f"{indent}TO {target}"

        output: list[str] = []

        if len(first_line) <= self.BODY_WIDTH:
            output.append(first_line)
        else:
            output.extend(
                self._wrap_by_words(
                    body=first_line,
                    continuation_indent=indent + "    ",
                )
            )

        if len(second_line) <= self.BODY_WIDTH:
            output.append(second_line)
        else:
            output.extend(
                self._wrap_by_words(
                    body=second_line,
                    continuation_indent=indent + "    ",
                )
            )

        return output

    def _wrap_by_words(
        self,
        body: str,
        continuation_indent: str,
    ) -> list[str]:
        text = str(body or "").rstrip()

        if len(text) <= self.BODY_WIDTH:
            return [text]

        words = text.strip().split()
        output: list[str] = []
        current = ""

        for word in words:
            candidate = word if not current else current.rstrip() + " " + word

            if len(candidate) <= self.BODY_WIDTH:
                current = candidate
                continue

            if current:
                if output:
                    output.append(continuation_indent + current.strip())
                else:
                    output.append(current.strip())

            current = word

        if current:
            if output:
                output.append(continuation_indent + current.strip())
            else:
                output.append(current.strip())

        if not output:
            return [text[: self.BODY_WIDTH]]

        normalized: list[str] = []

        for index, line in enumerate(output):
            if index == 0:
                normalized.append(line[: self.BODY_WIDTH])
                continue

            if line.startswith(continuation_indent):
                normalized.append(line[: self.BODY_WIDTH])
            else:
                normalized.append(
                    (continuation_indent + line.strip())[: self.BODY_WIDTH]
                )

        return normalized

    def _replace_body_part(
        self,
        original_line: str,
        new_body: str,
    ) -> str:
        line = str(original_line or "").rstrip()

        if self._is_fixed_format_line(line):
            left = line[:6]
            indicator = line[6]
            right = line[72:80]
            body = str(new_body or "").rstrip()[: self.BODY_WIDTH].ljust(
                self.BODY_WIDTH
            )

            return f"{left}{indicator}{body}{right}"

        return str(new_body or "").rstrip()

    def _format_comment_like_line(
        self,
        reference_line: str,
        comment_text: str,
    ) -> str:
        line = str(reference_line or "").rstrip()
        clean_comment = str(comment_text or "").strip()

        if not clean_comment.upper().startswith("DB2:"):
            clean_comment = f"DB2: {clean_comment}"

        body = f" {clean_comment}"

        if self._is_fixed_format_line(line):
            left = line[:6]
            right = line[72:80]
            body_area = body[: self.BODY_WIDTH].ljust(self.BODY_WIDTH)

            return f"{left}*{body_area}{right}"

        return f"*{body}"

    def _is_fixed_format_line(
        self,
        line: str,
    ) -> bool:
        text = str(line or "")

        if len(text) < 80:
            return False

        if not text[:6].isdigit():
            return False

        if not text[72:80].isdigit():
            return False

        return True