from idms_db2_phase2.domain.models import ConversionInput, DclgenColumn, SheetMappingRow
from idms_db2_phase2.orchestration.conversion_service import ConversionService


def test_conversion_service_returns_empty_when_source_missing():
    service = ConversionService()

    result = service.convert(ConversionInput())

    assert result.converted_cobol == ""
    assert result.validation_messages
    assert result.operations == []


def test_conversion_service_generates_db2_infrastructure_and_sql_error():
    service = ConversionService()

    conversion_input = ConversionInput(
        sheet_mapping_rows=[
            SheetMappingRow(
                cobol_record_idms="VMB-FAR",
                cobol_zone="NR-ID",
                idms_key="CALC",
                db2_key="PRIMARY KEY",
                new_db2_record="DZBFARTB",
                new_db2_field_name="NR_ID",
            ),
            SheetMappingRow(
                cobol_record_idms="VMB-FAR",
                cobol_zone="CD-NAME",
                new_db2_record="DZBFARTB",
                new_db2_field_name="CD_NAME",
            ),
        ],
        dclgen_columns=[
            DclgenColumn(
                table_name="DZBFARTV",
                column_name="NR_ID",
                cobol_host_name="NR-ID",
            ),
            DclgenColumn(
                table_name="DZBFARTV",
                column_name="CD_NAME",
                cobol_host_name="CD-NAME",
            ),
        ],
        idms_cobol_text="""
IDENTIFICATION DIVISION.
PROGRAM-ID. OLDPROG.
DATA DIVISION.
WORKING-STORAGE SECTION.
PROCEDURE DIVISION.
OBTAIN VMB-FAR CALC.
STORE VMB-FAR.
END PROGRAM OLDPROG.
""",
        target_program_id="NEWPROG",
    )

    result = service.convert(conversion_input)
    text = result.converted_cobol

    assert "PROGRAM-ID. NEWPROG." in text
    assert "EXEC SQL" in text
    assert "INCLUDE SQLCA" in text
    assert "SQL-ERROR." in text
    assert "FROM DZBFARTV" in text
    assert "INSERT INTO DZBFARTV" in text
    assert result.operations