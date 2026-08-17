import re
from difflib import SequenceMatcher

from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.host_variable_resolver import HostVariableResolver
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from patterns.field_reference_patterns import QUALIFIED_REFERENCE_PATTERN


class FieldReferenceRewriter:
    """
    Generic IDMS field reference to DB2 DCLGEN reference rewriter.

    No business names are hardcoded.

    Rules:
    - Qualified references are always eligible:
        FIELD OF RECORD
        FIELD IN RECORD

    - Bare references are eligible only when active record context is strong.

    - Date fields are protected only for bare references.
      Qualified references like DA-FIELD OF RECORD are eligible.
    """

    EXEC_SQL_PATTERN = re.compile(
        r"^\s*EXEC\s+SQL\b",
        flags=re.IGNORECASE,
    )

    END_EXEC_PATTERN = re.compile(
        r"^\s*END-EXEC\.?\s*$",
        flags=re.IGNORECASE,
    )

    DIVISION_PATTERN = re.compile(
        r"^\s*(IDENTIFICATION|ENVIRONMENT|DATA|PROCEDURE)\s+DIVISION\b",
        flags=re.IGNORECASE,
    )

    PARAGRAPH_PATTERN = re.compile(
        r"^\s*(?P<name>[A-Z0-9][A-Z0-9-]*)\.\s*$",
        flags=re.IGNORECASE,
    )

    STRING_PATTERN = re.compile(
        r"'[^']*'",
        flags=re.IGNORECASE,
    )

    HOST_REFERENCE_OF_PATTERN = re.compile(
        r":?\s*(?P<host>[A-Z][A-Z0-9-]*)\s+OF\s+(?P<group>DCL[A-Z0-9-]+)",
        flags=re.IGNORECASE,
    )

    HOST_REFERENCE_DOT_PATTERN = re.compile(
        r":?\s*(?P<group>DCL[A-Z0-9-]+)\.(?P<host>[A-Z][A-Z0-9-]*)",
        flags=re.IGNORECASE,
    )

    INITIALIZE_DCL_PATTERN = re.compile(
        r"\bINITIALIZE\s+(?P<group>DCL[A-Z0-9-]+)\b",
        flags=re.IGNORECASE,
    )

    GENERATED_OBTAIN_COMMENT_PATTERN = re.compile(
        r"CONVERTED\s+(?:OBTAIN|FIND)\s+(?:FIRST|NEXT|CALC)?\s*(?P<record>[A-Z][A-Z0-9-]*)",
        flags=re.IGNORECASE,
    )

    MOVE_SPACES_TO_RECORD_PATTERN = re.compile(
        r"\bMOVE\s+(?:SPACE|SPACES|ZEROES|ZEROS)\s+TO\s+(?P<record>[A-Z][A-Z0-9-]*)\b",
        flags=re.IGNORECASE,
    )

    PROTECTED_BARE_PREFIXES = (
        "WS-",
        "WK-",
        "W-",
        "SW-",
        "UIT-",
        "OUT-",
        "ES-",
        "D-",
        "DATE",
        "SQL",
        "DCL",
        "L-",
        "LS-",
        "PARAM",
        "ERROR-",
        "USER",
        "CS-",
        "TS-",
        "DA-",
        "HR-",
        "HELP-",
    )

    MIN_SIMILARITY_FOR_ALIAS = 0.94

    def __init__(
        self,
        mapping_repository: MappingRepository,
        table_name_resolver: TableNameResolver,
        host_variable_resolver: HostVariableResolver,
    ) -> None:
        self.mapping_repository = mapping_repository
        self.table_name_resolver = table_name_resolver
        self.host_variable_resolver = host_variable_resolver
        self.rewrite_messages: list[str] = []

        self.record_field_map: dict[str, dict[str, str]] = {}
        self.record_group_map: dict[str, str] = {}
        self.table_record_map: dict[str, str] = {}
        self.group_record_map: dict[str, str] = {}

    def rewrite(
        self,
        text: str,
    ) -> str:
        self.rewrite_messages = []

        if not text:
            return ""

        self._build_reference_maps()

        if not self.record_field_map:
            return str(text or "").rstrip() + "\n"

        output_lines: list[str] = []
        inside_exec_sql = False
        current_division = ""
        active_record = ""

        for raw_line in str(text or "").splitlines():
            line = raw_line.rstrip()
            logical = self._logical_line(line)

            division_match = self.DIVISION_PATTERN.match(logical)

            if division_match:
                current_division = division_match.group(1).upper()
                active_record = ""
                output_lines.append(line)
                continue

            detected_context = self._detect_active_record_from_line(
                logical_line=logical,
                current_active_record=active_record,
            )

            if detected_context:
                active_record = detected_context

            if self.EXEC_SQL_PATTERN.match(logical):
                inside_exec_sql = True
                output_lines.append(line)
                continue

            if inside_exec_sql:
                output_lines.append(line)

                if self.END_EXEC_PATTERN.match(logical):
                    inside_exec_sql = False

                continue

            output_lines.append(
                self._rewrite_line(
                    line=line,
                    current_division=current_division,
                    active_record=active_record,
                )
            )

        return "\n".join(output_lines).rstrip() + "\n"

    def _rewrite_line(
        self,
        line: str,
        current_division: str,
        active_record: str,
    ) -> str:
        if self._is_comment_or_blank(line):
            return line

        if current_division != "PROCEDURE":
            return line

        if self._has_existing_dclgen_reference(line):
            return line

        segments = self._split_string_segments(line)
        rewritten_segments: list[str] = []

        for segment, is_string in segments:
            if is_string:
                rewritten_segments.append(segment)
                continue

            rewritten = self._rewrite_qualified_references(segment)
            rewritten = self._rewrite_bare_references(
                text=rewritten,
                active_record=active_record,
            )

            rewritten_segments.append(rewritten)

        return "".join(rewritten_segments)

    def _rewrite_qualified_references(
        self,
        text: str,
    ) -> str:
        def repl(match):
            source_field = NameNormalizer.to_cobol(match.group("field"))
            source_record = NameNormalizer.normalize(match.group("record"))

            target = self._target_for_record_field(
                record_name=source_record,
                source_field=source_field,
            )

            if not target:
                return match.group(0)

            self.rewrite_messages.append(
                f"Qualified field rewrite: {source_field} OF "
                f"{NameNormalizer.to_cobol(source_record)} -> {target}"
            )

            return target

        return QUALIFIED_REFERENCE_PATTERN.sub(
            repl,
            text,
        )

    def _rewrite_bare_references(
        self,
        text: str,
        active_record: str,
    ) -> str:
        record = NameNormalizer.normalize(active_record)

        if not record:
            return text

        field_map = self.record_field_map.get(record, {})

        if not field_map:
            return text

        updated = str(text or "")

        for source_key, target_reference in sorted(
            field_map.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        ):
            source_name = NameNormalizer.to_cobol(source_key)

            if not source_name or not target_reference:
                continue

            if self._is_protected_bare_source_name(source_name):
                continue

            updated = self._replace_bare_identifier(
                text=updated,
                source_name=source_name,
                target_name=target_reference,
            )

        return updated

    def _replace_bare_identifier(
        self,
        text: str,
        source_name: str,
        target_name: str,
    ) -> str:
        source = NameNormalizer.to_cobol(source_name)
        target = str(target_name or "").strip()

        if not source or not target:
            return text

        pattern = re.compile(
            rf"(?<![A-Z0-9-]){re.escape(source)}(?![A-Z0-9-])",
            flags=re.IGNORECASE,
        )

        def repl(match):
            before_text = text[: match.start()]
            after_text = text[match.end():]

            if self._is_part_of_qualified_reference(
                before_text=before_text,
                after_text=after_text,
            ):
                return match.group(0)

            self.rewrite_messages.append(
                f"Bare field rewrite: {source} -> {target}"
            )

            return target

        return pattern.sub(
            repl,
            text,
        )

    def _target_for_record_field(
        self,
        record_name: str,
        source_field: str,
    ) -> str:
        record = NameNormalizer.normalize(record_name)
        field = self._field_key(source_field)

        if not record or not field:
            return ""

        return self.record_field_map.get(record, {}).get(field, "")

    def _build_reference_maps(
        self,
    ) -> None:
        self.record_field_map = {}
        self.record_group_map = {}
        self.table_record_map = {}
        self.group_record_map = {}

        records = self.mapping_repository.records()

        for record in records:
            normalized_record = NameNormalizer.normalize(record)

            if not normalized_record:
                continue

            resolved_table = self.table_name_resolver.table_for_record(
                normalized_record
            )

            if resolved_table:
                table_key = NameNormalizer.normalize(resolved_table)
                group_name = "DCL" + NameNormalizer.to_cobol(table_key)

                self.record_group_map[normalized_record] = group_name
                self.table_record_map[table_key] = normalized_record
                self.group_record_map[NameNormalizer.normalize(group_name)] = (
                    normalized_record
                )

            self.record_field_map[normalized_record] = (
                self._field_map_for_record(normalized_record)
            )

        self._add_redefines_aliases()
        self._add_strict_similarity_aliases()

    def _field_map_for_record(
        self,
        record_name: str,
    ) -> dict[str, str]:
        output: dict[str, str] = {}

        rows = self.mapping_repository.rows_for_record(record_name)

        for row in rows:
            source_candidates = self._source_candidates_from_row(row)

            if not source_candidates:
                continue

            target_table = self.table_name_resolver.resolve_table(
                self._first_non_empty(
                    getattr(row, "new_db2_record", ""),
                    getattr(row, "cross_application_db2_table", ""),
                )
            )

            target_column = NameNormalizer.normalize(
                self._first_non_empty(
                    getattr(row, "new_db2_field_name", ""),
                    getattr(row, "cross_application_db2_field_name", ""),
                )
            )

            if not target_table or not target_column:
                continue

            target_reference = self._dclgen_reference_for_column(
                table_name=target_table,
                column_name=target_column,
            )

            if not target_reference:
                continue

            for source_candidate in source_candidates:
                source_key = self._field_key(source_candidate)

                if not source_key:
                    continue

                if source_key not in output:
                    output[source_key] = target_reference

        return output

    def _source_candidates_from_row(
        self,
        row,
    ) -> list[str]:
        candidates: list[str] = []

        for value in [
            getattr(row, "cobol_zone", ""),
            getattr(row, "reference_field_name_copybook", ""),
        ]:
            field_name = self._extract_field_name(value)

            if not field_name:
                continue

            cobol_name = NameNormalizer.to_cobol(field_name)

            if not cobol_name:
                continue

            if cobol_name not in candidates:
                candidates.append(cobol_name)

            redefines_base = self._extract_redefines_base(value)

            if redefines_base:
                base_name = NameNormalizer.to_cobol(redefines_base)

                if base_name and base_name not in candidates:
                    candidates.append(base_name)

        return candidates

    def _add_redefines_aliases(
        self,
    ) -> None:
        for record in self.mapping_repository.records():
            normalized_record = NameNormalizer.normalize(record)
            rows = self.mapping_repository.rows_for_record(normalized_record)
            field_map = self.record_field_map.get(normalized_record, {})

            if not field_map:
                continue

            for row in rows:
                cobol_zone = getattr(row, "cobol_zone", "") or ""
                alias_name = self._extract_field_name(cobol_zone)
                base_name = self._extract_redefines_base(cobol_zone)

                if not alias_name or not base_name:
                    continue

                alias_key = self._field_key(alias_name)
                base_key = self._field_key(base_name)

                if not alias_key or not base_key:
                    continue

                if alias_key in field_map:
                    continue

                if base_key in field_map:
                    field_map[alias_key] = field_map[base_key]

    def _add_strict_similarity_aliases(
        self,
    ) -> None:
        for record, field_map in self.record_field_map.items():
            existing_keys = list(field_map.keys())

            rows = self.mapping_repository.rows_for_record(record)

            for row in rows:
                for source_candidate in self._source_candidates_from_row(row):
                    source_key = self._field_key(source_candidate)

                    if not source_key:
                        continue

                    if source_key in field_map:
                        continue

                    best_key = ""
                    best_score = 0.0

                    for existing_key in existing_keys:
                        score = self._similarity(source_key, existing_key)

                        if score > best_score:
                            best_score = score
                            best_key = existing_key

                    if (
                        best_key
                        and best_score >= self.MIN_SIMILARITY_FOR_ALIAS
                        and best_key in field_map
                    ):
                        field_map[source_key] = field_map[best_key]

    def _dclgen_reference_for_column(
        self,
        table_name: str,
        column_name: str,
    ) -> str:
        host_reference = self.host_variable_resolver.host_reference_for_column(
            table_name=table_name,
            column_name=column_name,
        )

        if not host_reference:
            return ""

        host_reference = str(host_reference or "").strip()

        of_match = self.HOST_REFERENCE_OF_PATTERN.search(host_reference)

        if of_match:
            host = NameNormalizer.to_cobol(of_match.group("host"))
            group = NameNormalizer.to_cobol(of_match.group("group"))
            return f"{host} OF {group}"

        dot_match = self.HOST_REFERENCE_DOT_PATTERN.search(host_reference)

        if dot_match:
            host = NameNormalizer.to_cobol(dot_match.group("host"))
            group = NameNormalizer.to_cobol(dot_match.group("group"))
            return f"{host} OF {group}"

        cleaned = host_reference.lstrip(":").strip()

        if " OF " in cleaned.upper():
            parts = re.split(
                r"\s+OF\s+",
                cleaned,
                flags=re.IGNORECASE,
            )
            if len(parts) == 2:
                host = NameNormalizer.to_cobol(parts[0])
                group = NameNormalizer.to_cobol(parts[1])
                return f"{host} OF {group}"

        return NameNormalizer.to_cobol(cleaned)

    def _detect_active_record_from_line(
        self,
        logical_line: str,
        current_active_record: str,
    ) -> str:
        logical = str(logical_line or "").strip()

        if not logical:
            return current_active_record

        paragraph_record = self._record_from_paragraph(logical)

        if paragraph_record:
            return paragraph_record

        initialize_record = self._record_from_initialize(logical)

        if initialize_record:
            return initialize_record

        generated_comment_record = self._record_from_generated_comment(logical)

        if generated_comment_record:
            return generated_comment_record

        move_target_record = self._record_from_move_target(logical)

        if move_target_record:
            return move_target_record

        qualified_record = self._record_from_qualified_reference(logical)

        if qualified_record:
            return qualified_record

        return current_active_record

    def _record_from_paragraph(
        self,
        logical_line: str,
    ) -> str:
        match = self.PARAGRAPH_PATTERN.match(logical_line)

        if not match:
            return ""

        paragraph = NameNormalizer.normalize(match.group("name"))

        for record in self.record_field_map:
            if record and record in paragraph:
                return record

        return ""

    def _record_from_initialize(
        self,
        logical_line: str,
    ) -> str:
        match = self.INITIALIZE_DCL_PATTERN.search(logical_line)

        if not match:
            return ""

        group = NameNormalizer.normalize(match.group("group"))

        return self.group_record_map.get(group, "")

    def _record_from_generated_comment(
        self,
        logical_line: str,
    ) -> str:
        match = self.GENERATED_OBTAIN_COMMENT_PATTERN.search(logical_line)

        if not match:
            return ""

        record = NameNormalizer.normalize(match.group("record"))

        if record in self.record_field_map:
            return record

        return ""

    def _record_from_move_target(
        self,
        logical_line: str,
    ) -> str:
        match = self.MOVE_SPACES_TO_RECORD_PATTERN.search(logical_line)

        if not match:
            return ""

        record = NameNormalizer.normalize(match.group("record"))

        if record in self.record_field_map:
            return record

        return ""

    def _record_from_qualified_reference(
        self,
        logical_line: str,
    ) -> str:
        match = QUALIFIED_REFERENCE_PATTERN.search(logical_line)

        if not match:
            return ""

        record = NameNormalizer.normalize(match.group("record"))

        if record in self.record_field_map:
            return record

        return ""

    def _extract_field_name(
        self,
        value: str,
    ) -> str:
        text = str(value or "").strip()

        if not text:
            return ""

        text = text.replace(".", " ")

        level_match = re.match(
            r"^\s*(0[1-9]|[1-4][0-9]|66|77|88)\s+([A-Z][A-Z0-9-]*)\b",
            text,
            flags=re.IGNORECASE,
        )

        if level_match:
            return level_match.group(2)

        redefines_match = re.match(
            r"^\s*([A-Z][A-Z0-9-]*)\s+REDEFINES\s+[A-Z][A-Z0-9-]*",
            text,
            flags=re.IGNORECASE,
        )

        if redefines_match:
            return redefines_match.group(1)

        tokens = re.findall(
            r"[A-Z][A-Z0-9-]*",
            text,
            flags=re.IGNORECASE,
        )

        if not tokens:
            return ""

        return tokens[0]

    def _extract_redefines_base(
        self,
        value: str,
    ) -> str:
        text = str(value or "")

        match = re.search(
            r"\bREDEFINES\s+([A-Z][A-Z0-9-]*)\b",
            text,
            flags=re.IGNORECASE,
        )

        if not match:
            return ""

        return match.group(1)

    def _field_key(
        self,
        value: str,
    ) -> str:
        return NameNormalizer.to_cobol(value)

    def _is_protected_bare_source_name(
        self,
        source_name: str,
    ) -> bool:
        source = NameNormalizer.to_cobol(source_name).upper()

        if not source:
            return True

        for prefix in self.PROTECTED_BARE_PREFIXES:
            if source.startswith(prefix):
                return True

        return False

    def _is_part_of_qualified_reference(
        self,
        before_text: str,
        after_text: str,
    ) -> bool:
        before = str(before_text or "").upper()
        after = str(after_text or "").upper()

        if re.search(r"\b(OF|IN)\s*$", before):
            return True

        if re.match(r"^\s+(OF|IN)\s+[A-Z0-9-]+", after):
            return True

        return False

    def _has_existing_dclgen_reference(
        self,
        line: str,
    ) -> bool:
        upper = str(line or "").upper()

        if " OF DCL" in upper:
            return True

        if re.search(
            r":\s*DCL[A-Z0-9-]+\.",
            upper,
        ):
            return True

        if re.search(
            r":\s*[A-Z0-9-]+\s+OF\s+DCL[A-Z0-9-]+",
            upper,
        ):
            return True

        return False

    def _split_string_segments(
        self,
        line: str,
    ) -> list[tuple[str, bool]]:
        text = str(line or "")
        output: list[tuple[str, bool]] = []
        last_index = 0

        for match in self.STRING_PATTERN.finditer(text):
            if match.start() > last_index:
                output.append(
                    (
                        text[last_index: match.start()],
                        False,
                    )
                )

            output.append(
                (
                    match.group(0),
                    True,
                )
            )

            last_index = match.end()

        if last_index < len(text):
            output.append(
                (
                    text[last_index:],
                    False,
                )
            )

        return output

    def _logical_line(
        self,
        line: str,
    ) -> str:
        text = str(line or "").rstrip()

        if len(text) >= 80:
            left = text[:6]
            indicator = text[6:7]
            body = text[7:72]

            if left.strip().isdigit():
                if indicator in {"*", "/"}:
                    return indicator + body.rstrip()

                return body.strip()

        if len(text) > 6 and text[:6].strip().isdigit():
            return text[6:].strip()

        return text.strip()

    def _is_comment_or_blank(
        self,
        line: str,
    ) -> bool:
        logical = self._logical_line(line)
        stripped = str(logical or "").strip()

        if not stripped:
            return True

        if stripped.startswith("*"):
            return True

        if stripped.startswith("/"):
            return True

        return False

    def _first_non_empty(
        self,
        *values: str,
    ) -> str:
        for value in values:
            text = str(value or "").strip()

            if text:
                return text

        return ""

    def _similarity(
        self,
        left: str,
        right: str,
    ) -> float:
        return SequenceMatcher(
            None,
            NameNormalizer.compact(left),
            NameNormalizer.compact(right),
        ).ratio()