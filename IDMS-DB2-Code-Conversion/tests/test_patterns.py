from patterns.cobol_patterns import PROGRAM_ID_PATTERN
from patterns.dclgen_patterns import DECLARE_TABLE_PATTERN
from patterns.idms_patterns import OBTAIN_CALC_PATTERN, STORE_PATTERN
from patterns.sql_patterns import EXEC_SQL_PATTERN, UPDATE_SQL_PATTERN
from patterns.validation_patterns import TODO_DB2_PATTERN


def test_program_id_pattern_matches():
    assert PROGRAM_ID_PATTERN.search("PROGRAM-ID. VMDZ1567.")


def test_dclgen_declare_table_pattern_matches():
    text = "EXEC SQL DECLARE DZBFARTV TABLE"

    match = DECLARE_TABLE_PATTERN.search(text)

    assert match
    assert match.group(1).strip() == "DZBFARTV"


def test_obtain_calc_pattern_matches():
    match = OBTAIN_CALC_PATTERN.search("OBTAIN VMB-FAR CALC.")

    assert match
    assert match.group("record") == "VMB-FAR"


def test_store_pattern_matches():
    match = STORE_PATTERN.search("STORE VMB-FAR.")

    assert match
    assert match.group("record") == "VMB-FAR"


def test_exec_sql_pattern_matches():
    assert EXEC_SQL_PATTERN.match("EXEC SQL")


def test_update_sql_pattern_matches_table():
    match = UPDATE_SQL_PATTERN.search("UPDATE DZBFARTV")

    assert match
    assert match.group("table") == "DZBFARTV"


def test_todo_db2_validation_pattern_matches():
    assert TODO_DB2_PATTERN.search("TODO DB2 mapping missing")