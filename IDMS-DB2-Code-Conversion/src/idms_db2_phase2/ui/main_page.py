import re
from pathlib import Path

import streamlit as st

from idms_db2_phase2.analyzers.metadata_service import MetadataService
from idms_db2_phase2.domain.models import ConversionInput
from idms_db2_phase2.infrastructure.file_loader import FileLoader
from idms_db2_phase2.orchestration.conversion_service import ConversionService
from idms_db2_phase2.parsers.copybook_parser import CopybookParser
from idms_db2_phase2.parsers.dclgen_parser import DclgenParser
from idms_db2_phase2.parsers.sheet_mapping_parser import SheetMappingParser


def initialize_session_state() -> None:
    defaults = {
        "sheet_mapping_rows": [],
        "dclgen_columns": [],
        "copybook_fields": [],
        "idms_cobol_text": "",
        "idms_cobol_source_name": "",
        "converted_cobol": "",
        "converted_cobol_file_name": "converted_db2_cobol.cbl",
        "validation_messages": [],
        "operations": [],
        "generated": False,
        "loaded": False,
        "diagnostics": [],
        "uploaded_file_names": {},
        "auto_fix_pic_length_mismatches": False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_main_page() -> None:
    initialize_session_state()

    tabs = st.tabs(
        [
            "Main",
            "Metadata Overview",
            "Column Names",
            "Sets",
            "Sheet Mapping Rows",
            "Generated DB2 COBOL",
            "Validation",
            "Diagnostics",
        ]
    )

    with tabs[0]:
        render_main_tab()

    with tabs[1]:
        render_metadata_overview_tab()

    with tabs[2]:
        render_column_names_tab()

    with tabs[3]:
        render_sets_tab()

    with tabs[4]:
        render_sheet_mapping_rows_tab()

    with tabs[5]:
        render_generated_cobol_tab()

    with tabs[6]:
        render_validation_tab()

    with tabs[7]:
        render_diagnostics_tab()


def render_main_tab() -> None:
    st.markdown("## Upload Inputs")

    st.info(
        "Upload Sheet Mapping, one or more DCLGEN files, optional Copybook files, "
        "and the IDMS COBOL source text file to generate DB2 embedded SQL COBOL."
    )

    col1, col2 = st.columns(2)

    with col1:
        sheet_mapping_file = st.file_uploader(
            "Sheet Mapping Excel or CSV",
            type=["xlsx", "csv"],
            key="sheet_mapping_file",
            help=(
                "Upload Sheet Mapping as .xlsx or .csv. "
                "If your file is .xls, save it as .xlsx or .csv first."
            ),
        )

        dclgen_files = st.file_uploader(
            "DCLGEN text file or files",
            type=["txt", "cbl", "cpy"],
            accept_multiple_files=True,
            key="dclgen_files",
        )

    with col2:
        copybook_files = st.file_uploader(
            "Optional Copybook text file or files",
            type=["txt", "cbl", "cpy"],
            accept_multiple_files=True,
            key="copybook_files",
        )

        idms_cobol_source_file = st.file_uploader(
            "IDMS COBOL source code",
            type=["txt", "cbl", "cob"],
            key="idms_cobol_source_file",
        )

    st.session_state.auto_fix_pic_length_mismatches = st.checkbox(
        "Auto-fix PIC length mismatches",
        value=st.session_state.auto_fix_pic_length_mismatches,
        help="If enabled, the converter can expand generated target PIC lengths when needed.",
    )

    target_program_id = st.text_input(
        "Target PROGRAM-ID",
        value="",
        help="Optional. If provided, the generated COBOL PROGRAM-ID will be replaced.",
    )

    col_load, col_generate = st.columns(2)

    with col_load:
        if st.button("Load and Analyze Inputs", type="primary"):
            load_and_analyze_inputs(
                sheet_mapping_file=sheet_mapping_file,
                dclgen_files=dclgen_files,
                copybook_files=copybook_files,
                idms_cobol_source_file=idms_cobol_source_file,
            )

    with col_generate:
        if st.button("Generate DB2 COBOL"):
            generate_db2_cobol(target_program_id=target_program_id)

    render_current_status()


def load_and_analyze_inputs(
    sheet_mapping_file,
    dclgen_files,
    copybook_files,
    idms_cobol_source_file,
) -> None:
    diagnostics = []
    uploaded_file_names = {}

    file_loader = FileLoader()
    sheet_mapping_parser = SheetMappingParser()
    dclgen_parser = DclgenParser()
    copybook_parser = CopybookParser()

    sheet_rows = []
    dclgen_columns = []
    copybook_fields = []

    if sheet_mapping_file is None:
        diagnostics.append("Sheet Mapping file not uploaded.")
    else:
        uploaded_file_names["sheet_mapping_file"] = str(sheet_mapping_file.name or "")

        try:
            sheet_rows = sheet_mapping_parser.parse(sheet_mapping_file)
            diagnostics.append(f"Sheet Mapping uploaded: {sheet_mapping_file.name}")
            diagnostics.append(f"Sheet Mapping parsed rows: {len(sheet_rows)}")
        except Exception as exc:
            diagnostics.append(f"Sheet Mapping parse failed: {exc}")
            sheet_rows = []

    dclgen_file_names = []

    if not dclgen_files:
        diagnostics.append("DCLGEN file not uploaded.")
    else:
        dclgen_text_parts = []

        for file in dclgen_files:
            file_name = str(file.name or "")
            dclgen_file_names.append(file_name)

            try:
                text = file_loader.read_uploaded_text(file)
                diagnostics.append(f"DCLGEN uploaded: {file_name}")
                diagnostics.append(f"DCLGEN text length for {file_name}: {len(text)}")
                dclgen_text_parts.append(text)
            except Exception as exc:
                diagnostics.append(f"DCLGEN read failed for {file_name}: {exc}")

        uploaded_file_names["dclgen_files"] = dclgen_file_names

        dclgen_text = "\n".join(dclgen_text_parts)

        try:
            dclgen_columns = dclgen_parser.parse(dclgen_text)
            diagnostics.append(f"DCLGEN parsed columns: {len(dclgen_columns)}")
        except Exception as exc:
            diagnostics.append(f"DCLGEN parse failed: {exc}")
            dclgen_columns = []

    copybook_file_names = []

    if not copybook_files:
        diagnostics.append("Copybook file not uploaded. Continuing without copybook.")
    else:
        copybook_text_parts = []

        for file in copybook_files:
            file_name = str(file.name or "")
            copybook_file_names.append(file_name)

            try:
                text = file_loader.read_uploaded_text(file)
                diagnostics.append(f"Copybook uploaded: {file_name}")
                diagnostics.append(f"Copybook text length for {file_name}: {len(text)}")
                copybook_text_parts.append(text)
            except Exception as exc:
                diagnostics.append(f"Copybook read failed for {file_name}: {exc}")

        uploaded_file_names["copybook_files"] = copybook_file_names

        copybook_text = "\n".join(copybook_text_parts)

        try:
            copybook_fields = copybook_parser.parse(copybook_text)
            diagnostics.append(f"Copybook parsed fields: {len(copybook_fields)}")
        except Exception as exc:
            diagnostics.append(f"Copybook parse failed: {exc}")
            copybook_fields = []

    idms_cobol_text = ""
    idms_cobol_source_name = ""

    if idms_cobol_source_file is None:
        diagnostics.append("IDMS COBOL source file not uploaded.")
    else:
        idms_cobol_source_name = str(idms_cobol_source_file.name or "")
        uploaded_file_names["idms_cobol_source_file"] = idms_cobol_source_name

        try:
            idms_cobol_text = file_loader.read_uploaded_text(idms_cobol_source_file)
            diagnostics.append(f"IDMS COBOL source uploaded: {idms_cobol_source_name}")
            diagnostics.append(f"IDMS COBOL source text length: {len(idms_cobol_text)}")
        except Exception as exc:
            diagnostics.append(f"IDMS COBOL source read failed: {exc}")
            idms_cobol_text = ""

    st.session_state.sheet_mapping_rows = sheet_rows
    st.session_state.dclgen_columns = dclgen_columns
    st.session_state.copybook_fields = copybook_fields
    st.session_state.idms_cobol_text = idms_cobol_text
    st.session_state.idms_cobol_source_name = idms_cobol_source_name
    st.session_state.converted_cobol = ""
    st.session_state.converted_cobol_file_name = "converted_db2_cobol.cbl"
    st.session_state.validation_messages = []
    st.session_state.operations = []
    st.session_state.generated = False
    st.session_state.loaded = True
    st.session_state.diagnostics = diagnostics
    st.session_state.uploaded_file_names = uploaded_file_names

    st.success("Inputs loaded and analyzed.")


def generate_db2_cobol(target_program_id: str) -> None:
    if not st.session_state.loaded:
        st.warning("Load and analyze inputs before generating DB2 COBOL.")
        return

    service = ConversionService()

    result = service.convert(
        ConversionInput(
            sheet_mapping_rows=st.session_state.sheet_mapping_rows,
            dclgen_columns=st.session_state.dclgen_columns,
            copybook_fields=st.session_state.copybook_fields,
            idms_cobol_text=st.session_state.idms_cobol_text,
            target_program_id=target_program_id,
            auto_fix_pic_length_mismatches=st.session_state.auto_fix_pic_length_mismatches,
        )
    )

    st.session_state.converted_cobol = result.converted_cobol
    st.session_state.validation_messages = result.validation_messages
    st.session_state.operations = result.operations
    st.session_state.converted_cobol_file_name = build_converted_cobol_file_name(
        target_program_id=target_program_id,
        source_file_name=st.session_state.idms_cobol_source_name,
    )
    st.session_state.generated = True

    st.success("DB2 COBOL generation completed.")


def build_converted_cobol_file_name(
    target_program_id: str,
    source_file_name: str,
) -> str:
    target = sanitize_file_stem(target_program_id)

    if target:
        return f"{target}.cbl"

    source_stem = ""

    if source_file_name:
        source_stem = Path(source_file_name).stem
        source_stem = sanitize_file_stem(source_stem)

    if source_stem:
        return f"{source_stem}_db2.cbl"

    return "converted_db2_cobol.cbl"


def sanitize_file_stem(value: str) -> str:
    text = str(value or "").strip()

    if not text:
        return ""

    text = re.sub(r"[^A-Za-z0-9_-]+", "_", text)
    text = re.sub(r"_+", "_", text)

    return text.strip("_")


def render_current_status() -> None:
    st.markdown("## Current Status")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Sheet Mapping Rows", len(st.session_state.sheet_mapping_rows))

    with col2:
        st.metric("DCLGEN Columns", len(st.session_state.dclgen_columns))

    with col3:
        st.metric("Copybook Fields", len(st.session_state.copybook_fields))

    with col4:
        st.metric("IDMS COBOL Length", len(st.session_state.idms_cobol_text))

    if st.session_state.loaded:
        st.success("Inputs loaded. Review metadata and diagnostics before generating.")

    if st.session_state.generated:
        st.success("DB2 COBOL generated. Open the Generated DB2 COBOL tab to download.")


def render_metadata_overview_tab() -> None:
    st.markdown("## Metadata Overview")

    metadata_service = MetadataService()

    summaries = metadata_service.record_summaries(
        st.session_state.sheet_mapping_rows,
    )

    if summaries:
        st.dataframe(
            summaries,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No metadata available. Upload Sheet Mapping first.")


def render_column_names_tab() -> None:
    st.markdown("## Column Names")

    metadata_service = MetadataService()

    rows = metadata_service.column_rows(
        st.session_state.sheet_mapping_rows,
    )

    if rows:
        st.dataframe(
            rows,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No column rows available. Upload Sheet Mapping first.")


def render_sets_tab() -> None:
    st.markdown("## Sets")

    metadata_service = MetadataService()

    rows = metadata_service.relationship_summaries(
        st.session_state.sheet_mapping_rows,
    )

    if rows:
        st.dataframe(
            rows,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No relationship rows available. Upload Sheet Mapping first.")


def render_sheet_mapping_rows_tab() -> None:
    st.markdown("## Sheet Mapping Rows")

    metadata_service = MetadataService()

    rows = metadata_service.mapping_preview_rows(
        st.session_state.sheet_mapping_rows,
    )

    if rows:
        st.dataframe(
            rows,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No Sheet Mapping rows available. Upload Excel or CSV first.")


def render_generated_cobol_tab() -> None:
    st.markdown("## Generated DB2 COBOL")

    if not st.session_state.converted_cobol:
        st.info("Generate DB2 COBOL from the Main tab.")
        return

    st.caption(
        f"Output file name: `{st.session_state.converted_cobol_file_name}`"
    )

    st.download_button(
        label="Download Generated COBOL",
        data=st.session_state.converted_cobol,
        file_name=st.session_state.converted_cobol_file_name,
        mime="text/plain",
        type="primary",
    )

    st.text_area(
        "Final DB2 COBOL Code",
        value=st.session_state.converted_cobol,
        height=760,
    )


def render_validation_tab() -> None:
    st.markdown("## Validation")

    if not st.session_state.validation_messages:
        st.success("No validation messages.")
        return

    for message in st.session_state.validation_messages:
        st.warning(message)


def render_diagnostics_tab() -> None:
    st.markdown("## Diagnostics")

    st.markdown("### Uploaded Files")
    st.json(st.session_state.uploaded_file_names)

    st.markdown("### Parser Diagnostics")

    diagnostics = st.session_state.diagnostics or []

    if not diagnostics:
        st.info("No diagnostics available. Click Load and Analyze Inputs first.")
        return

    st.code(
        "\n".join(diagnostics),
        language="text",
    )