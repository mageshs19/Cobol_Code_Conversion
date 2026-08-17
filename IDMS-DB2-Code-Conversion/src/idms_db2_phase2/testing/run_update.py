from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from config.path_settings import (
    DEFAULT_COPYBOOK_CANDIDATE_PATHS,
    DEFAULT_DCLGEN_CANDIDATE_PATHS,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SHEET_MAPPING_PATH,
    DEFAULT_UPDATE_SOURCE_PATH,
    LOGS_DIR,
    PROJECT_ROOT,
    SRC_DIR,
)
from idms_db2_phase2.domain.models import ConversionInput
from idms_db2_phase2.infrastructure.file_loader import FileLoader
from idms_db2_phase2.infrastructure.local_uploaded_file import LocalUploadedFile
from idms_db2_phase2.infrastructure.logger_factory import LoggerFactory
from idms_db2_phase2.orchestration.conversion_service import ConversionService
from idms_db2_phase2.parsers.copybook_parser import CopybookParser
from idms_db2_phase2.parsers.dclgen_parser import DclgenParser
from idms_db2_phase2.parsers.sheet_mapping_parser import SheetMappingParser


if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


TARGET_PROGRAM_ID = "VMDZ1567"
AUTO_FIX_PIC_LENGTH_MISMATCHES = False


SHEET_MAPPING_PATH = DEFAULT_SHEET_MAPPING_PATH
IDMS_COBOL_SOURCE_PATH = DEFAULT_UPDATE_SOURCE_PATH
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
        searched = "\n".join(str(path) for path in DEFAULT_DCLGEN_CANDIDATE_PATHS)
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


def load_inputs(
    logger,
) -> tuple[list, list, list, str, list[str]]:
    diagnostics: list[str] = []

    sheet_parser = SheetMappingParser()
    dclgen_parser = DclgenParser()
    copybook_parser = CopybookParser()
    file_loader = FileLoader()

    diagnostics.append("START LOAD INPUTS")
    logger.info("START LOAD INPUTS")

    sheet_file = LocalUploadedFile(SHEET_MAPPING_PATH)
    sheet_rows = sheet_parser.parse_uploaded_file(sheet_file)
    diagnostics.append(f"Sheet Mapping file: {SHEET_MAPPING_PATH}")
    diagnostics.append(f"Sheet Mapping parsed rows: {len(sheet_rows)}")
    diagnostics.extend(sheet_parser.diagnostics)

    logger.info("Sheet Mapping parsed rows: %s", len(sheet_rows))

    dclgen_texts: list[str] = []
    diagnostics.append("DCLGEN files selected:")

    for dclgen_path in DCLGEN_PATHS:
        diagnostics.append(f" - {dclgen_path}")
        dclgen_file = LocalUploadedFile(dclgen_path)
        dclgen_text = file_loader.read_uploaded_text(dclgen_file)
        diagnostics.append(f"DCLGEN file: {dclgen_path}")
        diagnostics.append(f"DCLGEN text length: {len(dclgen_text)}")
        dclgen_texts.append(dclgen_text)

    dclgen_columns = dclgen_parser.parse_many_texts(dclgen_texts)
    diagnostics.append(f"DCLGEN parsed columns: {len(dclgen_columns)}")
    diagnostics.extend(dclgen_parser.diagnostics)

    logger.info("DCLGEN parsed columns: %s", len(dclgen_columns))

    copybook_text_parts: list[str] = []

    if COPYBOOK_PATHS:
        diagnostics.append("Copybook files selected:")

    for copybook_path in COPYBOOK_PATHS:
        diagnostics.append(f" - {copybook_path}")
        copybook_file = LocalUploadedFile(copybook_path)
        copybook_text = file_loader.read_uploaded_text(copybook_file)
        diagnostics.append(f"Copybook file: {copybook_path}")
        diagnostics.append(f"Copybook text length: {len(copybook_text)}")
        copybook_text_parts.append(copybook_text)

    copybook_text = "\n".join(copybook_text_parts)
    copybook_fields = copybook_parser.parse(copybook_text)
    diagnostics.append(f"Copybook parsed fields: {len(copybook_fields)}")

    logger.info("Copybook parsed fields: %s", len(copybook_fields))

    source_file = LocalUploadedFile(IDMS_COBOL_SOURCE_PATH)
    idms_cobol_text = file_loader.read_uploaded_text(source_file)
    diagnostics.append(f"IDMS COBOL source file: {IDMS_COBOL_SOURCE_PATH}")
    diagnostics.append(f"IDMS COBOL source text length: {len(idms_cobol_text)}")

    logger.info("IDMS COBOL source text length: %s", len(idms_cobol_text))

    return (
        sheet_rows,
        dclgen_columns,
        copybook_fields,
        idms_cobol_text,
        diagnostics,
    )


def run_conversion() -> None:
    logger = LoggerFactory.create_logger(
        name="run_update",
        logs_dir=LOGS_DIR,
    )

    logger.info("Update conversion started.")
    validate_inputs()

    (
        sheet_rows,
        dclgen_columns,
        copybook_fields,
        idms_cobol_text,
        diagnostics,
    ) = load_inputs(logger)

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

    logger.info("DB2 COBOL generation completed.")
    logger.info("Output file created: %s", output_cobol_path)

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
    print("Validation Messages")
    print("-------------------")

    if result.validation_messages:
        for message in result.validation_messages:
            print(f"- {message}")
            logger.warning(message)
    else:
        print("No validation messages.")

    print("")
    print("Diagnostics")
    print("-----------")

    for diagnostic in diagnostics:
        print(f"- {diagnostic}")
        logger.info(diagnostic)


if __name__ == "__main__":
    run_conversion()