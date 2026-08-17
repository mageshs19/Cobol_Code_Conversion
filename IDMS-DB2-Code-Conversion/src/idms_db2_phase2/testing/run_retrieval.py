from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path


CURRENT_FILE = Path(__file__).resolve()
SRC_DIR = CURRENT_FILE.parents[2]
PROJECT_ROOT = CURRENT_FILE.parents[3]

for path in [PROJECT_ROOT, SRC_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


from config.path_settings import (
    DEFAULT_COPYBOOK_CANDIDATE_PATHS,
    DEFAULT_DCLGEN_CANDIDATE_PATHS,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_RETRIEVAL_SOURCE_PATH,
    DEFAULT_SHEET_MAPPING_PATH,
)

from idms_db2_phase2.domain.models import ConversionInput
from idms_db2_phase2.infrastructure.file_loader import FileLoader
from idms_db2_phase2.infrastructure.local_uploaded_file import LocalUploadedFile
from idms_db2_phase2.orchestration.conversion_service import ConversionService
from idms_db2_phase2.parsers.copybook_parser import CopybookParser
from idms_db2_phase2.parsers.dclgen_parser import DclgenParser
from idms_db2_phase2.parsers.sheet_mapping_parser import SheetMappingParser


TARGET_PROGRAM_ID = "VMDZ4420"
AUTO_FIX_PIC_LENGTH_MISMATCHES = False

SHEET_MAPPING_PATH = DEFAULT_SHEET_MAPPING_PATH
IDMS_COBOL_SOURCE_PATH = DEFAULT_RETRIEVAL_SOURCE_PATH
OUTPUT_DIR = DEFAULT_OUTPUT_DIR

DCLGEN_PATHS = [
    path
    for path in DEFAULT_DCLGEN_CANDIDATE_PATHS
    if path.exists() and path.is_file()
]

COPYBOOK_PATHS = [
    path
    for path in DEFAULT_COPYBOOK_CANDIDATE_PATHS
    if path.exists() and path.is_file()
]


def validate_file_exists(
    file_path: Path,
    label: str,
) -> None:
    if not file_path.exists():
        raise FileNotFoundError(f"{label} file not found: {file_path}")

    if not file_path.is_file():
        raise FileNotFoundError(f"{label} path is not a file: {file_path}")


def validate_inputs() -> None:
    validate_file_exists(SHEET_MAPPING_PATH, "Sheet Mapping")
    validate_file_exists(IDMS_COBOL_SOURCE_PATH, "IDMS COBOL Source")

    if not DCLGEN_PATHS:
        searched = "\n".join(
            str(path)
            for path in DEFAULT_DCLGEN_CANDIDATE_PATHS
        )

        raise ValueError(
            "At least one DCLGEN file path is required. "
            "No DCLGEN candidate file was found. Searched:\n"
            f"{searched}"
        )

    for index, dclgen_path in enumerate(DCLGEN_PATHS, start=1):
        validate_file_exists(dclgen_path, f"DCLGEN {index}")

    for index, copybook_path in enumerate(COPYBOOK_PATHS, start=1):
        validate_file_exists(copybook_path, f"Copybook {index}")

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


def load_inputs() -> tuple[list, list, list, str, list[str]]:
    diagnostics: list[str] = []

    sheet_parser = SheetMappingParser()
    dclgen_parser = DclgenParser()
    copybook_parser = CopybookParser()
    file_loader = FileLoader()

    diagnostics.append("START LOAD INPUTS")

    sheet_file = LocalUploadedFile(SHEET_MAPPING_PATH)
    sheet_rows = sheet_parser.parse_uploaded_file(sheet_file)

    diagnostics.append(f"Sheet Mapping file: {SHEET_MAPPING_PATH}")
    diagnostics.append(f"Sheet Mapping rows: {len(sheet_rows)}")

    if hasattr(sheet_parser, "diagnostics"):
        diagnostics.extend(sheet_parser.diagnostics)

    dclgen_texts: list[str] = []

    diagnostics.append(f"DCLGEN file count: {len(DCLGEN_PATHS)}")

    for index, dclgen_path in enumerate(DCLGEN_PATHS, start=1):
        dclgen_file = LocalUploadedFile(dclgen_path)
        dclgen_text = file_loader.read_uploaded_text(dclgen_file)

        dclgen_texts.append(dclgen_text)

        diagnostics.append(f"DCLGEN {index}: {dclgen_path}")
        diagnostics.append(f"DCLGEN {index} text length: {len(dclgen_text)}")

    if hasattr(dclgen_parser, "parse_many_texts"):
        dclgen_columns = dclgen_parser.parse_many_texts(dclgen_texts)
    else:
        dclgen_columns = []

        for index, dclgen_text in enumerate(dclgen_texts, start=1):
            parsed_columns = dclgen_parser.parse(
                text=dclgen_text,
                source_label=f"DCLGEN file {index}",
            )
            dclgen_columns.extend(parsed_columns)

    diagnostics.append(f"DCLGEN total columns: {len(dclgen_columns)}")

    if hasattr(dclgen_parser, "diagnostics"):
        diagnostics.extend(dclgen_parser.diagnostics)

    copybook_text_parts: list[str] = []

    diagnostics.append(f"Copybook file count: {len(COPYBOOK_PATHS)}")

    for index, copybook_path in enumerate(COPYBOOK_PATHS, start=1):
        copybook_file = LocalUploadedFile(copybook_path)
        copybook_text = file_loader.read_uploaded_text(copybook_file)

        copybook_text_parts.append(copybook_text)

        diagnostics.append(f"Copybook {index}: {copybook_path}")
        diagnostics.append(f"Copybook {index} text length: {len(copybook_text)}")

    copybook_text = "\n".join(copybook_text_parts)

    if copybook_text.strip():
        try:
            copybook_fields = copybook_parser.parse(
                text=copybook_text,
                source_label="Copybook files",
            )
        except TypeError:
            copybook_fields = copybook_parser.parse(copybook_text)
    else:
        copybook_fields = []

    diagnostics.append(f"Copybook total fields: {len(copybook_fields)}")

    if hasattr(copybook_parser, "diagnostics"):
        diagnostics.extend(copybook_parser.diagnostics)

    source_file = LocalUploadedFile(IDMS_COBOL_SOURCE_PATH)
    idms_cobol_text = file_loader.read_uploaded_text(source_file)

    diagnostics.append(f"IDMS COBOL source file: {IDMS_COBOL_SOURCE_PATH}")
    diagnostics.append(f"IDMS COBOL source text length: {len(idms_cobol_text)}")

    return (
        sheet_rows,
        dclgen_columns,
        copybook_fields,
        idms_cobol_text,
        diagnostics,
    )


def run_conversion() -> None:
    validate_inputs()

    (
        sheet_rows,
        dclgen_columns,
        copybook_fields,
        idms_cobol_text,
        diagnostics,
    ) = load_inputs()

    service = ConversionService()

    result = service.convert(
        ConversionInput(
            sheet_mapping_rows=sheet_rows,
            dclgen_columns=dclgen_columns,
            copybook_fields=copybook_fields,
            idms_cobol_text=idms_cobol_text,
            target_program_id=TARGET_PROGRAM_ID,
            auto_fix_pic_length_mismatches=AUTO_FIX_PIC_LENGTH_MISMATCHES,
        )
    )

    date_time = datetime.now().strftime("%d-%m-%Y_%H%M%S")
    code_name = IDMS_COBOL_SOURCE_PATH.stem
    output_cobol_path = OUTPUT_DIR / f"{code_name}_{date_time}.cbl"

    output_cobol_path.write_text(
        result.converted_cobol or "",
        encoding="utf-8",
    )

    print("DB2 COBOL generation completed.")
    print(f"Output file created: {output_cobol_path}")
    print("")
    print("Input Summary")
    print("-------------")
    print(f"Project Root       : {PROJECT_ROOT}")
    print(f"SRC Directory      : {SRC_DIR}")
    print(f"Sheet Mapping Rows : {len(sheet_rows)}")
    print(f"DCLGEN Columns     : {len(dclgen_columns)}")
    print(f"Copybook Fields    : {len(copybook_fields)}")
    print(f"COBOL Text Length  : {len(idms_cobol_text)}")
    print(f"Target PROGRAM-ID  : {TARGET_PROGRAM_ID}")

    print("")
    print("Selected Input Files")
    print("--------------------")
    print(f"Sheet Mapping       : {SHEET_MAPPING_PATH}")
    print(f"IDMS COBOL Source   : {IDMS_COBOL_SOURCE_PATH}")

    print("DCLGEN Files:")
    for path in DCLGEN_PATHS:
        print(f" - {path}")

    if COPYBOOK_PATHS:
        print("Copybook Files:")
        for path in COPYBOOK_PATHS:
            print(f" - {path}")
    else:
        print("Copybook Files      : None")

    print("")
    print("Validation Messages")
    print("-------------------")

    if result.validation_messages:
        for message in result.validation_messages:
            print(f"- {message}")
    else:
        print("No validation messages.")

    print("")
    print("Diagnostics")
    print("-----------")

    for diagnostic in diagnostics:
        print(f"- {diagnostic}")


if __name__ == "__main__":
    run_conversion()