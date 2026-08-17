from idms_db2_phase2.domain.models import DclgenColumn, SheetMappingRow
from idms_db2_phase2.generators.sql_error_generator import SqlErrorGenerator
from idms_db2_phase2.generators.sql_generator import SqlGenerator
from idms_db2_phase2.repositories.dclgen_repository import DclgenRepository
from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.column_name_resolver import ColumnNameResolver
from idms_db2_phase2.resolvers.cursor_name_resolver import CursorNameResolver
from idms_db2_phase2.resolvers.host_variable_resolver import HostVariableResolver
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
from idms_db2_phase2.transformers.cobol_transformer import CobolTransformer
from idms_db2_phase2.transformers.field_reference_rewriter import FieldReferenceRewriter
from idms_db2_phase2.transformers.idms_statement_transformer import IdmsStatementTransformer
from idms_db2_phase2.transformers.pic_length_auto_fixer import PicLengthAutoFixer


def build_transformer_context():
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
                cobol_zone="CD-NAME",
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

    sql_generator = SqlGenerator(
        mapping_repository=mapping_repository,
        dclgen_repository=dclgen_repository,
        table_name_resolver=table_resolver,
        column_name_resolver=column_resolver,
        host_variable_resolver=host_resolver,
    )

    statement_transformer = IdmsStatementTransformer(
        sql_generator=sql_generator,
        sql_error_generator=SqlErrorGenerator(),
        table_name_resolver=table_resolver,
        cursor_name_resolver=cursor_resolver,
    )

    return {
        "mapping_repository": mapping_repository,
        "dclgen_repository": dclgen_repository,
        "table_resolver": table_resolver,
        "host_resolver": host_resolver,
        "statement_transformer": statement_transformer,
    }


def test_idms_statement_transformer_converts_obtain_calc():
    context = build_transformer_context()

    lines, _opened_set = context["statement_transformer"].transform_line(
        line="OBTAIN VMB-FAR CALC.",
        current_division="PROCEDURE",
        sql_error_paragraph="SQL-ERROR",
    )

    text = "\n".join(lines)

    assert "Converted OBTAIN CALC" in text
    assert "SELECT" in text
    assert "FROM DZBFARTV" in text


def test_idms_statement_transformer_converts_store_to_insert():
    context = build_transformer_context()

    lines, _opened_set = context["statement_transformer"].transform_line(
        line="STORE VMB-FAR.",
        current_division="PROCEDURE",
        sql_error_paragraph="SQL-ERROR",
    )

    text = "\n".join(lines)

    assert "Converted STORE" in text
    assert "INSERT INTO DZBFARTV" in text


def test_idms_statement_transformer_removes_bind():
    context = build_transformer_context()

    lines, _opened_set = context["statement_transformer"].transform_line(
        line="BIND RUN-UNIT.",
        current_division="PROCEDURE",
        sql_error_paragraph="SQL-ERROR",
    )

    text = "\n".join(lines)

    assert "Removed IDMS BIND statement" in text
    assert "CONTINUE." in text


def test_cobol_transformer_converts_program_id_and_idms_statement():
    context = build_transformer_context()

    transformer = CobolTransformer(
        idms_statement_transformer=context["statement_transformer"],
    )

    source = """
IDENTIFICATION DIVISION.
PROGRAM-ID. OLDPROG.
PROCEDURE DIVISION.
OBTAIN VMB-FAR CALC.
END PROGRAM OLDPROG.
"""

    converted, messages, operations = transformer.transform(
        cobol_text=source,
        target_program_id="NEWPROG",
    )

    assert "PROGRAM-ID. NEWPROG." in converted
    assert "Converted OBTAIN CALC" in converted
    assert len(operations) == 1
    assert messages == []


def test_field_reference_rewriter_rewrites_qualified_reference():
    context = build_transformer_context()

    rewriter = FieldReferenceRewriter(
        mapping_repository=context["mapping_repository"],
        table_name_resolver=context["table_resolver"],
        host_variable_resolver=context["host_resolver"],
    )

    result = rewriter.rewrite("MOVE NR-ID OF VMB-FAR TO WS-NR-ID.")

    assert ":NR-ID OF DCLDZBFARTV" in result


def test_pic_length_auto_fixer_expands_target_pic():
    fixer = PicLengthAutoFixer()

    source = """
01 WS-SOURCE PIC 9(8).
01 WS-TARGET PIC 9(6).
"""

    converted = """
01 WS-TARGET PIC 9(6).
PROCEDURE DIVISION.
MOVE WS-SOURCE TO WS-TARGET.
"""

    result = fixer.fix(
        source_cobol_text=source,
        converted_cobol_text=converted,
    )

    assert "PIC 9(8)" in result
    assert fixer.messages