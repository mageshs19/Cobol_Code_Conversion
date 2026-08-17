from idms_db2_phase2.parsers.cobol_parser import CobolParser
from idms_db2_phase2.parsers.copybook_parser import CopybookParser
from idms_db2_phase2.parsers.dclgen_parser import DclgenParser
from idms_db2_phase2.parsers.sheet_mapping_parser import SheetMappingParser


def test_cobol_parser_detects_program_id():
    parser = CobolParser()

    assert parser.program_id("PROGRAM-ID. VMDZ1567.") == "VMDZ1567"


def test_cobol_parser_detects_obtain_calc():
    parser = CobolParser()

    operations = parser.analyze("OBTAIN VMB-FAR CALC.")

    assert len(operations) == 1
    assert operations[0].operation == "OBTAIN_CALC"
    assert operations[0].record_name == "VMB-FAR"


def test_cobol_parser_detects_store():
    parser = CobolParser()

    operations = parser.analyze("STORE VMB-FAR.")

    assert len(operations) == 1
    assert operations[0].operation == "STORE"
    assert operations[0].record_name == "VMB-FAR"


def test_copybook_parser_parses_field():
    parser = CopybookParser()

    fields = parser.parse(
        """
        10 NR-ID PIC 9(8).
        """
    )

    assert len(fields) == 1
    assert fields[0].name == "NR-ID"
    assert fields[0].picture == "9(8)"


def test_dclgen_parser_parses_inline_sql_declare():
    parser = DclgenParser()

    columns = parser.parse(
        """
        EXEC SQL DECLARE DZBFARTV TABLE
        (
            NR_ID DECIMAL(8,0) NOT NULL,
            CD_NAME CHAR(4)
        )
        END-EXEC.

        01 DCLDZBFARTV.
           10 NR-ID PIC S9(8) COMP-3.
           10 CD-NAME PIC X(4).
        """,
        source_label="unit-test",
    )

    assert len(columns) == 2
    assert columns[0].table_name == "DZBFARTV"
    assert columns[0].column_name == "NR_ID"
    assert columns[0].cobol_host_name == "NR-ID"


def test_sheet_mapping_parser_parses_csv_text():
    parser = SheetMappingParser()

    rows = parser.parse_csv_text(
        "Cobol Record IDMS,Cobol Zone,IDMS Key,DB2 Key,New DB2 Record,New DB2 Field name\n"
        "VMB-FAR,NR-ID,CALC,PRIMARY KEY,DZBFARTB,NR_ID\n"
    )

    assert len(rows) == 1
    assert rows[0].cobol_record_idms == "VMB-FAR"
    assert rows[0].new_db2_record == "DZBFARTB"
    assert rows[0].new_db2_field_name == "NR_ID"