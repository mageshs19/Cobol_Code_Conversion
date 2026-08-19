from idms_db2_phase2.composers.feedback_cleanup_composer import (
    FeedbackCleanupComposer,
)
from idms_db2_phase2.domain.models import DclgenColumn, SheetMappingRow
from idms_db2_phase2.generators.sql_generator import SqlGenerator
from idms_db2_phase2.repositories.dclgen_repository import DclgenRepository
from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.column_name_resolver import ColumnNameResolver
from idms_db2_phase2.resolvers.host_variable_resolver import HostVariableResolver
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver


def build_context():
    mapping_repository = MappingRepository(
        [
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
                cobol_zone="DA-INFSD-GDIFAR",
                new_db2_record="DZBFARTB",
                new_db2_field_name="DA_INFSDGD_479BFAR",
            ),
            SheetMappingRow(
                cobol_record_idms="VMB-FAR",
                new_db2_record="DZBFARTB",
                new_db2_field_name="TS_UPDATE_479BFAR",
            ),
            SheetMappingRow(
                cobol_record_idms="VMB-FAR",
                new_db2_record="DZBFARTB",
                new_db2_field_name="ID_USERID_479BFAR",
            ),
            SheetMappingRow(
                cobol_record_idms="VMB-FAR",
                new_db2_record="DZBFARTB",
                new_db2_field_name="CD_NAME",
            ),
        ]
    )

    dclgen_repository = DclgenRepository(
        [
            DclgenColumn(
                table_name="DZBFARTV",
                column_name="NR_ID",
                cobol_host_name="NR-ID",
            ),
            DclgenColumn(
                table_name="DZBFARTV",
                column_name="DA_INFSDGD_479BFAR",
                cobol_host_name="DA-INFSDGD-479BFAR",
            ),
            DclgenColumn(
                table_name="DZBFARTV",
                column_name="TS_UPDATE_479BFAR",
                cobol_host_name="TS-UPDATE-479BFAR",
            ),
            DclgenColumn(
                table_name="DZBFARTV",
                column_name="ID_USERID_479BFAR",
                cobol_host_name="ID-USERID-479BFAR",
            ),
            DclgenColumn(
                table_name="DZBFARTV",
                column_name="CD_NAME",
                cobol_host_name="CD-NAME",
            ),
        ]
    )

    table_resolver = TableNameResolver(
        mapping_repository=mapping_repository,
        dclgen_repository=dclgen_repository,
    )

    column_resolver = ColumnNameResolver(
        mapping_repository=mapping_repository,
        dclgen_repository=dclgen_repository,
        table_name_resolver=table_resolver,
    )

    host_resolver = HostVariableResolver(
        dclgen_repository=dclgen_repository,
        table_name_resolver=table_resolver,
    )

    sql_generator = SqlGenerator(
        mapping_repository=mapping_repository,
        dclgen_repository=dclgen_repository,
        table_name_resolver=table_resolver,
        column_name_resolver=column_resolver,
        host_variable_resolver=host_resolver,
    )

    return {
        "mapping_repository": mapping_repository,
        "dclgen_repository": dclgen_repository,
        "sql_generator": sql_generator,
    }


def test_update_is_conservative_and_key_only():
    context = build_context()
    sql_generator = context["sql_generator"]

    lines = sql_generator.update(
        "VMB-FAR",
        changed_source_fields=["DA-INFSD-GDIFAR"],
    )

    text = "\n".join(lines)

    assert "UPDATE DZBFARTV" in text
    assert "DA_INFSDGD_479BFAR" in text
    assert "TS_UPDATE_479BFAR" in text
    assert "ID_USERID_479BFAR" in text
    assert "CD_NAME" not in text
    assert "WHERE" in text
    assert "NR_ID" in text


def test_select_by_key_is_minimal():
    context = build_context()
    sql_generator = context["sql_generator"]

    lines = sql_generator.select_by_key("VMB-FAR")
    text = "\n".join(lines)

    assert "FROM DZBFARTV" in text
    assert "NR_ID" in text
    assert "CD_NAME" not in text


def test_changed_field_move_resolves_to_dclgen_host():
    context = build_context()
    sql_generator = context["sql_generator"]

    lines = sql_generator.changed_field_move(
        record_name="VMB-FAR",
        source_value="DATE-YMD8",
        target_source_field="DA-INFSD-GDIFAR",
    )

    text = "\n".join(lines)

    assert "DATE-YMD8" in text
    assert "DA-INFSDGD-479BFAR" in text
    assert "DCLDZBFARTV" in text


def test_feedback_cleanup_adds_missing_include():
    context = build_context()
    dclgen_repository = context["dclgen_repository"]

    composer = FeedbackCleanupComposer(
        dclgen_repository=dclgen_repository,
    )

    source = """
WORKING-STORAGE SECTION.
EXEC SQL
   INCLUDE SQLCA
END-EXEC.
PROCEDURE DIVISION.
MOVE 1 TO DCLDZBFARTV.NR-ID.
"""

    updated = composer.compose(source)

    assert "INCLUDE DZBFARTV" in updated


def test_feedback_cleanup_replaces_error_status_when_flag_exists():
    context = build_context()
    dclgen_repository = context["dclgen_repository"]

    composer = FeedbackCleanupComposer(
        dclgen_repository=dclgen_repository,
    )

    source = """
WORKING-STORAGE SECTION.
01 SW-STATUS-D PIC X.
PROCEDURE DIVISION.
MOVE '0307' TO ERROR-STATUS
"""

    updated = composer.compose(source)

    assert "MOVE 'Y' TO SW-STATUS-D" in updated
    assert "ERROR-STATUS" not in updated


def test_feedback_cleanup_adds_initialize_before_write():
    context = build_context()
    dclgen_repository = context["dclgen_repository"]

    composer = FeedbackCleanupComposer(
        dclgen_repository=dclgen_repository,
    )

    source = """
PROCEDURE DIVISION.
MOVE A TO UIT-A
WRITE UITRECORD
"""

    updated = composer.compose(source)

    assert "INITIALIZE UITRECORD" in updated
    assert "WRITE UITRECORD" in updated