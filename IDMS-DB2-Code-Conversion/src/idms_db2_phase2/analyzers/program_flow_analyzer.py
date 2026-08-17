from dataclasses import dataclass, field

from idms_db2_phase2.domain.models import DclgenColumn, IdmsOperation, SheetMappingRow
from idms_db2_phase2.resolvers.cursor_name_resolver import CursorNameResolver
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from patterns.cobol_patterns import PARAGRAPH_PATTERN, PROCEDURE_DIVISION_PATTERN
from patterns.sequence_patterns import strip_sequence_numbers


@dataclass
class ParagraphSpan:
    name: str
    start_line: int
    end_line: int
    lines: list[str] = field(default_factory=list)


@dataclass
class CursorLoop:
    record_name: str = ""
    set_name: str = ""
    operation: str = ""
    operation_line: int = 0
    process_paragraph: str = ""
    perform_line: int = 0
    until_line: int = 0
    loop_type: str = "unknown"
    cursor_name: str = ""
    open_paragraph: str = ""
    fetch_paragraph: str = ""
    close_paragraph: str = ""


@dataclass
class OutputWrite:
    output_record: str = ""
    paragraph_name: str = ""
    write_line: int = 0
    move_lines: list[str] = field(default_factory=list)


@dataclass
class DateUsage:
    host_field: str = ""
    dclgen_group: str = ""
    idms_record: str = ""
    line_number: int = 0
    line_text: str = ""
    usage_type: str = ""


@dataclass
class ProgramFlowAnalysis:
    paragraphs: list[ParagraphSpan] = field(default_factory=list)
    cursor_loops: list[CursorLoop] = field(default_factory=list)
    output_writes: list[OutputWrite] = field(default_factory=list)
    date_usages: list[DateUsage] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)

    def process_paragraph_for_cursor(
        self,
        cursor_name: str,
    ) -> str:
        cursor = NameNormalizer.to_cobol(NameNormalizer.normalize(cursor_name))

        for loop in self.cursor_loops:
            if NameNormalizer.to_cobol(NameNormalizer.normalize(loop.cursor_name)) == cursor:
                return loop.process_paragraph

        return ""

    def loop_for_set(
        self,
        set_name: str,
    ) -> CursorLoop | None:
        target = NameNormalizer.normalize(set_name)

        for loop in self.cursor_loops:
            if NameNormalizer.normalize(loop.set_name) == target:
                return loop

        return None

    def loop_for_record(
        self,
        record_name: str,
    ) -> CursorLoop | None:
        target = NameNormalizer.normalize(record_name)

        for loop in self.cursor_loops:
            if NameNormalizer.normalize(loop.record_name) == target:
                return loop

        return None


class ProgramFlowAnalyzer:
    """
    Generic flow analyzer for diagnostics.

    This analyzer does not rewrite COBOL. It detects:
    - procedure paragraphs
    - cursor-like operations from parsed IDMS operations
    - output write statements
    - basic date usage hints
    """

    CURSOR_OPERATIONS = {
        "OBTAIN_FIRST",
        "OBTAIN_NEXT",
        "FIND_FIRST",
    }

    WRITE_TOKENS = {
        "WRITE",
        "STORE",
        "MODIFY",
        "ERASE",
    }

    DATE_TOKENS = {
        "DATE",
        "TIME",
        "TIMESTAMP",
        "TS-",
    }

    def __init__(
        self,
        mapping_rows: list[SheetMappingRow] | None = None,
        dclgen_columns: list[DclgenColumn] | None = None,
    ) -> None:
        self.mapping_rows = mapping_rows or []
        self.dclgen_columns = dclgen_columns or []
        self.cursor_name_resolver = CursorNameResolver()

    def analyze(
        self,
        cobol_text: str,
        operations: list[IdmsOperation] | None = None,
    ) -> ProgramFlowAnalysis:
        diagnostics: list[str] = []

        if not str(cobol_text or "").strip():
            return ProgramFlowAnalysis(
                diagnostics=["Program flow analyzer: COBOL text is empty."]
            )

        logical_lines = self._logical_lines_with_numbers(cobol_text)
        paragraphs = self._paragraph_spans(logical_lines)
        cursor_loops = self._cursor_loops(operations or [])
        output_writes = self._output_writes(logical_lines, paragraphs)
        date_usages = self._date_usages(logical_lines)

        diagnostics.append(
            f"Program flow analyzer: Sheet Mapping rows received: {len(self.mapping_rows)}"
        )
        diagnostics.append(
            f"Program flow analyzer: DCLGEN columns received: {len(self.dclgen_columns)}"
        )
        diagnostics.append(
            f"Program flow analyzer: paragraphs detected: {len(paragraphs)}"
        )
        diagnostics.append(
            f"Program flow analyzer: cursor loops detected: {len(cursor_loops)}"
        )
        diagnostics.append(
            f"Program flow analyzer: output writes detected: {len(output_writes)}"
        )
        diagnostics.append(
            f"Program flow analyzer: DB2 date usages detected: {len(date_usages)}"
        )

        for loop in cursor_loops[:5]:
            diagnostics.append(
                "Program flow analyzer: loop sample: "
                f"record={loop.record_name}, set={loop.set_name}, "
                f"type={loop.loop_type}, cursor={loop.cursor_name}"
            )

        return ProgramFlowAnalysis(
            paragraphs=paragraphs,
            cursor_loops=cursor_loops,
            output_writes=output_writes,
            date_usages=date_usages,
            diagnostics=diagnostics,
        )

    def _logical_lines_with_numbers(
        self,
        cobol_text: str,
    ) -> list[tuple[int, str, str]]:
        output: list[tuple[int, str, str]] = []

        for line_number, raw_line in enumerate(cobol_text.splitlines(), start=1):
            logical = strip_sequence_numbers(raw_line)
            output.append((line_number, logical, raw_line.rstrip()))

        return output

    def _paragraph_spans(
        self,
        logical_lines: list[tuple[int, str, str]],
    ) -> list[ParagraphSpan]:
        paragraphs: list[ParagraphSpan] = []
        current: ParagraphSpan | None = None
        inside_procedure = False

        for line_number, logical, raw_line in logical_lines:
            if PROCEDURE_DIVISION_PATTERN.match(logical):
                inside_procedure = True

            if not inside_procedure:
                continue

            match = PARAGRAPH_PATTERN.match(logical.strip())

            if match:
                if current is not None:
                    current.end_line = line_number - 1
                    paragraphs.append(current)

                current = ParagraphSpan(
                    name=match.group("name").upper(),
                    start_line=line_number,
                    end_line=line_number,
                    lines=[raw_line],
                )
                continue

            if current is not None:
                current.lines.append(raw_line)
                current.end_line = line_number

        if current is not None:
            paragraphs.append(current)

        return paragraphs

    def _cursor_loops(
        self,
        operations: list[IdmsOperation],
    ) -> list[CursorLoop]:
        output: list[CursorLoop] = []
        cursor_order_by_name: dict[str, int] = {}

        for operation in operations:
            operation_name = str(operation.operation or "").upper()

            if operation_name not in self.CURSOR_OPERATIONS:
                continue

            record_name = NameNormalizer.normalize(operation.record_name)
            set_name = NameNormalizer.normalize(operation.set_name)

            if not record_name:
                continue

            cursor_name = self.cursor_name_resolver.cursor_name_from_table(record_name)

            if cursor_name not in cursor_order_by_name:
                cursor_order_by_name[cursor_name] = len(cursor_order_by_name) + 1

            paragraph_spec = self.cursor_name_resolver.paragraph_names(
                cursor_order=cursor_order_by_name[cursor_name],
                cursor_name=cursor_name,
            )

            output.append(
                CursorLoop(
                    record_name=record_name,
                    set_name=set_name,
                    operation=operation_name,
                    operation_line=operation.line_number,
                    loop_type="cursor",
                    cursor_name=cursor_name,
                    open_paragraph=paragraph_spec["open"],
                    fetch_paragraph=paragraph_spec["fetch"],
                    close_paragraph=paragraph_spec["close"],
                )
            )

        return output

    def _output_writes(
        self,
        logical_lines: list[tuple[int, str, str]],
        paragraphs: list[ParagraphSpan],
    ) -> list[OutputWrite]:
        output: list[OutputWrite] = []
        paragraph_by_line = self._paragraph_name_by_line(paragraphs)

        for line_number, logical, _raw_line in logical_lines:
            upper = logical.strip().upper()

            if not any(upper.startswith(token) for token in self.WRITE_TOKENS):
                continue

            output.append(
                OutputWrite(
                    output_record=self._first_word_after_operation(upper),
                    paragraph_name=paragraph_by_line.get(line_number, ""),
                    write_line=line_number,
                )
            )

        return output

    def _date_usages(
        self,
        logical_lines: list[tuple[int, str, str]],
    ) -> list[DateUsage]:
        output: list[DateUsage] = []

        for line_number, logical, raw_line in logical_lines:
            upper = logical.upper()

            if not any(token in upper for token in self.DATE_TOKENS):
                continue

            output.append(
                DateUsage(
                    line_number=line_number,
                    line_text=raw_line,
                    usage_type="date-token",
                )
            )

        return output

    def _paragraph_name_by_line(
        self,
        paragraphs: list[ParagraphSpan],
    ) -> dict[int, str]:
        output: dict[int, str] = {}

        for paragraph in paragraphs:
            for line_number in range(paragraph.start_line, paragraph.end_line + 1):
                output[line_number] = paragraph.name

        return output

    def _first_word_after_operation(
        self,
        upper_line: str,
    ) -> str:
        parts = upper_line.split()

        if len(parts) < 2:
            return ""

        return NameNormalizer.normalize(parts[1].rstrip("."))