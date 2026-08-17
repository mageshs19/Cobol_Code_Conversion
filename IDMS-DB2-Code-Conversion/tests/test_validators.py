from idms_db2_phase2.domain.models import ConversionInput, DclgenColumn, SheetMappingRow
from idms_db2_phase2.repositories.dclgen_repository import DclgenRepository
from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
from idms_db2_phase2.validators.input_validator import InputValidator
from idms_db2_phase2.validators.mapping_validator import MappingValidator
from idms_db2_phase2.validators.production_validator import ProductionValidator


def test_input_validator_detects_missing_inputs():
    validator = InputValidator()

    messages = validator.validate(ConversionInput())

    assert "Sheet Mapping is required and must contain rows." in messages
    assert "At least one DCLGEN file is required." in messages
    assert "IDMS COBOL source text file is required and must contain readable COBOL code." in messages


def test_input_validator_passes_with_required_inputs():
    validator = InputValidator()

    messages = validator.validate(
        ConversionInput(
            sheet_mapping_rows=[SheetMappingRow(cobol_record_idms="REC")],
            dclgen_columns=[DclgenColumn(table_name="TABLE")],
            idms_cobol_text="IDENTIFICATION DIVISION.",
        )
    )

    assert messages == []


def test_mapping_validator_detects_missing_metadata():
    mapping_repository = MappingRepository([])
    dclgen_repository = DclgenRepository([])
    table_resolver = TableNameResolver(
        mapping_repository=mapping_repository,
        dclgen_repository=dclgen_repository,
    )

    validator = MappingValidator(
        mapping_repository=mapping_repository,
        dclgen_repository=dclgen_repository,
        table_name_resolver=table_resolver,
    )

    messages = validator.validate()

    assert "Mapping validation: Sheet Mapping rows are missing." in messages
    assert "Mapping validation: DCLGEN columns are missing." in messages


def test_mapping_validator_passes_basic_mapping():
    mapping_repository = MappingRepository(
        [
            SheetMappingRow(
                cobol_record_idms="VMB-FAR",
                new_db2_record="DZBFARTB",
                new_db2_field_name="NR_ID",
            )
        ]
    )
    dclgen_repository = DclgenRepository(
        [
            DclgenColumn(
                table_name="DZBFARTV",
                column_name="NR_ID",
                cobol_host_name="NR-ID",
            )
        ]
    )
    table_resolver = TableNameResolver(
        mapping_repository=mapping_repository,
        dclgen_repository=dclgen_repository,
    )

    validator = MappingValidator(
        mapping_repository=mapping_repository,
        dclgen_repository=dclgen_repository,
        table_name_resolver=table_resolver,
    )

    messages = validator.validate()

    assert "Mapping validation: Sheet Mapping rows are missing." not in messages
    assert "Mapping validation: DCLGEN columns are missing." not in messages


def test_production_validator_detects_missing_db2_tokens():
    dclgen_repository = DclgenRepository([])
    validator = ProductionValidator(dclgen_repository=dclgen_repository)

    messages = validator.validate("IDENTIFICATION DIVISION.")

    assert "Production validation: required DB2 token missing: EXEC SQL" in messages
    assert "Production validation: required DB2 token missing: SQLCA" in messages
    assert "Production validation: required DB2 token missing: END-EXEC" in messages


def test_production_validator_detects_residual_idms_statement():
    dclgen_repository = DclgenRepository([])
    validator = ProductionValidator(dclgen_repository=dclgen_repository)

    text = """
    EXEC SQL
        INCLUDE SQLCA
    END-EXEC.
    PROCEDURE DIVISION.
    OBTAIN VMB-FAR CALC.
    """

    messages = validator.validate(text)

    assert any("residual executable IDMS statement remains" in message for message in messages)


def test_production_validator_accepts_valid_host_reference():
    dclgen_repository = DclgenRepository(
        [
            DclgenColumn(
                table_name="DZBFARTV",
                column_name="NR_ID",
                cobol_host_name="NR-ID",
            )
        ]
    )
    validator = ProductionValidator(dclgen_repository=dclgen_repository)

    text = """
    EXEC SQL
        INCLUDE SQLCA
    END-EXEC.
    EXEC SQL
        SELECT NR_ID
        INTO :DCLDZBFARTV.NR-ID
        FROM DZBFARTV
    END-EXEC.
    """

    messages = validator.validate(text)

    assert not any("was not found in uploaded DCLGEN columns" in message for message in messages)