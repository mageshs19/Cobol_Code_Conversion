from idms_db2_phase2.composers.final_feedback_fix_composer import (
    FinalFeedbackFixComposer,
    FinalFeedbackFixComposerConfig,
)


def test_program_name_sync_uses_final_program_id():
    source = (
        "000040 PROGRAM-ID. VMDZ4420.                                            00040000\n"
        "002420     MOVE 'VM4BD420' TO PROGRAM-NAME.                             02420000\n"
    )

    composer = FinalFeedbackFixComposer()
    updated = composer.compose(source)

    assert "MOVE 'VMDZ4420' TO PROGRAM-NAME" in updated
    assert "MOVE 'VM4BD420' TO PROGRAM-NAME" not in updated


def test_procedure_statement_starts_in_area_b_column_12():
    source = (
        "002040 PROCEDURE DIVISION USING PARAM-DATONLY.                          02040000\n"
        "002060  INITIALIZE DCLDZBEFFTV.                                         02060000\n"
    )

    composer = FinalFeedbackFixComposer()
    updated = composer.compose(source)
    line = updated.splitlines()[1]

    assert line[11] == "I"
    assert len(line) == 80
    assert line[72:80].isdigit()


def test_date_format_can_be_configured_to_iso():
    source = (
        "003150     MOVE DA-CREVTPD-479EVEF OF DCLDZEVEFTV TO DA-DD-MM-CCYY      03150000\n"
        "003170      WHEN DA-DD-MM-CCYY = '01.01.0001'                           03170000\n"
        "003190      WHEN DA-DD-MM-CCYY = '31.12.9999'                           03190000\n"
    )

    composer = FinalFeedbackFixComposer(
        config=FinalFeedbackFixComposerConfig(
            db2_date_external_format="YYYY-MM-DD",
        )
    )
    updated = composer.compose(source)

    assert "DA-YYYY-MM-DD" in updated
    assert "'0001-01-01'" in updated
    assert "'9999-12-31'" in updated


def test_order_by_only_column_removed_from_select_and_fetch():
    source = (
        "000010 PROCEDURE DIVISION.                                             00010000\n"
        "000020  EXEC SQL                                                       00020000\n"
        "000030     DECLARE C1 CURSOR WITH HOLD FOR                             00030000\n"
        "000040     SELECT                                                      00040000\n"
        "000050         COL_A                                                   00050000\n"
        "000060        , COL_B                                                   00060000\n"
        "000070     FROM TAB1                                                   00070000\n"
        "000080     ORDER BY                                                    00080000\n"
        "000090        COL_B DESC                                               00090000\n"
        "000100     FOR READ ONLY                                               00100000\n"
        "000110  END-EXEC.                                                      00110000\n"
        "000120  EXEC SQL                                                       00120000\n"
        "000130     FETCH C1                                                    00130000\n"
        "000140     INTO                                                        00140000\n"
        "000150         :DCLTAB1.COL-A,                                         00150000\n"
        "000160         :DCLTAB1.COL-B                                          00160000\n"
        "000170  END-EXEC.                                                      00170000\n"
        "000180     DISPLAY COL-A.                                              00180000\n"
    )

    composer = FinalFeedbackFixComposer()
    updated = composer.compose(source)

    assert ", COL_B" not in updated
    assert ":DCLTAB1.COL-B" not in updated
    assert "ORDER BY" in updated
    assert "COL_B DESC" in updated