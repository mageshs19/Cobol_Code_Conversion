from idms_db2_phase2.domain.models import DclgenColumn, IdmsOperation, SheetMappingRow
from idms_db2_phase2.generators.cursor_paragraph_generator import CursorParagraphGenerator
from idms_db2_phase2.generators.db2_infrastructure_generator import Db2InfrastructureGenerator
from idms_db2_phase2.generators.sql_error_generator import SqlErrorGenerator
from idms_db2_phase2.generators.sql_generator import SqlGenerator
from idms_db2_phase2.repositories.dclgen_repository import DclgenRepository
from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.column_name_resolver import ColumnNameResolver
from idms_db2_phase2.resolvers.cursor_name_resolver import CursorNameResolver
from idms_db2_phase2.resolvers.host_variable_resolver import HostVariableResolver
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver


def build_generator_context():
    mapping_repository = MappingRepository(
        [
            SheetMappingRow(
                cobol_record_idms="VMB-FAR",
                idms_key="CALC",
                db2_key="PRIMARY KEY",
                new_db2_record="DZBFARTB",
                new_db2_field_name="NR_ID",
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

    cursor_resolver = CursorNameResolver()

    return {
        "mapping_repository": mapping_repository,
        "dclgen_repository": dclgen_repository,
        "table_resolver": table_resolver,
        "column_resolver": column_resolver,
        "host_resolver": host_resolver,
        "cursor_resolver": cursor_resolver,
    }


def test_sql_error_generator_adds_paragraph_before_end_program():
    generator = SqlErrorGenerator()

    text = "IDENTIFICATION DIVISION.\nPROGRAM-ID. TEST.\nEND PROGRAM TEST.\n"

    result = generator.ensure_sql_error_paragraph(text)

    assert "SQL-ERROR." in result
    assert "DISPLAY 'DB2 SQL ERROR SQLCODE='" in result
    assert result.index("SQL-ERROR.") < result.index("END PROGRAM")


def test_sql_generator_select_by_key_uses_resolved_tv_table():
    context = build_generator_context()

    generator = SqlGenerator(
        mapping_repository=context["mapping_repository"],
        dclgen_repository=context["dclgen_repository"],
        table_name_resolver=context["table_resolver"],
        column_name_resolver=context["column_resolver"],
        host_variable_resolver=context["host_resolver"],
    )

    lines = generator.select_by_key("VMB-FAR")
    text = "\n".join(lines)

    assert "FROM DZBFARTV" in text
    assert ":NR-ID OF DCLDZBFARTV" in text


def test_sql_generator_insert_uses_resolved_tv_table():
    context = build_generator_context()

    generator = SqlGenerator(
        mapping_repository=context["mapping_repository"],
        dclgen_repository=context["dclgen_repository"],
        table_name_resolver=context["table_resolver"],
        column_name_resolver=context["column_resolver"],
        host_variable_resolver=context["host_resolver"],
    )

    lines = generator.insert("VMB-FAR")
    text = "\n".join(lines)

    assert "INSERT INTO DZBFARTV" in text
    assert ":NR-ID OF DCLDZBFARTV" in text


def test_sql_generator_update_uses_resolved_tv_table():
    context = build_generator_context()

    generator = SqlGenerator(
        mapping_repository=context["mapping_repository"],
        dclgen_repository=context["dclgen_repository"],
        table_name_resolver=context["table_resolver"],
        column_name_resolver=context["column_resolver"],
        host_variable_resolver=context["host_resolver"],
    )

    lines = generator.update("VMB-FAR")
    text = "\n".join(lines)

    assert "UPDATE DZBFARTV" in text
    assert "WHERE" in text


def test_db2_infrastructure_generator_inserts_sqlca_and_dclgen_include():
    context = build_generator_context()

    generator = Db2InfrastructureGenerator(
        table_name_resolver=context["table_resolver"],
        column_name_resolver=context["column_resolver"],
        host_variable_resolver=context["host_resolver"],
        cursor_name_resolver=context["cursor_resolver"],
    )

    cobol = "IDENTIFICATION DIVISION.\nPROGRAM-ID. TEST.\nDATA DIVISION.\nPROCEDURE DIVISION.\nEND PROGRAM TEST.\n"

    updated, messages = generator.apply(
        cobol_text=cobol,
        operations=[
            IdmsOperation(
                operation="OBTAIN_FIRST",
                record_name="VMB-FAR",
                set_name="AR-VMB-FAR",
            )
        ],
    )

    assert "INCLUDE SQLCA" in updated
    assert "INCLUDE SQLERRWS" in updated
    assert "INCLUDE DZBFARTV" in updated
    assert "SQL-LOCATION" in updated
    assert messages


def test_cursor_paragraph_generator_creates_open_fetch_close():
    context = build_generator_context()

    db2_generator = Db2InfrastructureGenerator(
        table_name_resolver=context["table_resolver"],
        column_name_resolver=context["column_resolver"],
        host_variable_resolver=context["host_resolver"],
        cursor_name_resolver=context["cursor_resolver"],
    )

    generator = CursorParagraphGenerator(
        db2_infrastructure_generator=db2_generator,
        host_variable_resolver=context["host_resolver"],
        sql_error_generator=SqlErrorGenerator(),
    )

    cobol = "IDENTIFICATION DIVISION.\nPROGRAM-ID. TEST.\nPROCEDURE DIVISION.\nEND PROGRAM TEST.\n"

    updated, messages = generator.apply(
        cobol_text=cobol,
        operations=[
            IdmsOperation(
                operation="OBTAIN_FIRST",
                record_name="VMB-FAR",
                set_name="AR-VMB-FAR",
            )
        ],
    )

    assert "710-OPEN-DZBFARC1." in updated
    assert "720-FETCH-DZBFARC1." in updated
    assert "730-CLOSE-DZBFARC1." in updated
    assert "FETCH DZBFARC1" in updated
    assert messages