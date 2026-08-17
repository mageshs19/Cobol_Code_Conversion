def test_core_imports():
    from idms_db2_phase2.domain.models import ConversionInput
    from idms_db2_phase2.orchestration.conversion_service import ConversionService
    from idms_db2_phase2.parsers.sheet_mapping_parser import SheetMappingParser
    from idms_db2_phase2.parsers.dclgen_parser import DclgenParser
    from idms_db2_phase2.parsers.copybook_parser import CopybookParser
    from idms_db2_phase2.parsers.cobol_parser import CobolParser

    assert ConversionInput is not None
    assert ConversionService is not None
    assert SheetMappingParser is not None
    assert DclgenParser is not None
    assert CopybookParser is not None
    assert CobolParser is not None


def test_clean_architecture_imports():
    from catalogs.sheet_mapping_schema import SHEET_MAPPING_MODEL_FIELD_MAP
    from patterns.idms_patterns import OBTAIN_CALC_PATTERN
    from rules.authority_rules import INPUT_AUTHORITY_RULES

    assert SHEET_MAPPING_MODEL_FIELD_MAP
    assert OBTAIN_CALC_PATTERN
    assert INPUT_AUTHORITY_RULES


def test_layer_imports():
    from idms_db2_phase2.repositories.mapping_repository import MappingRepository
    from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
    from idms_db2_phase2.generators.sql_generator import SqlGenerator
    from idms_db2_phase2.transformers.cobol_transformer import CobolTransformer
    from idms_db2_phase2.validators.production_validator import ProductionValidator
    from idms_db2_phase2.composers.cobol_formatter import CobolFormatter

    assert MappingRepository is not None
    assert TableNameResolver is not None
    assert SqlGenerator is not None
    assert CobolTransformer is not None
    assert ProductionValidator is not None
    assert CobolFormatter is not None