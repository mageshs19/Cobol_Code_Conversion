@echo off
setlocal enabledelayedexpansion

set PROJECT_ROOT=IDMS-DB2-Code-Conversion

echo Creating clean production architecture: %PROJECT_ROOT%

mkdir "%PROJECT_ROOT%"
mkdir "%PROJECT_ROOT%\logs"
mkdir "%PROJECT_ROOT%\config"
mkdir "%PROJECT_ROOT%\catalogs"
mkdir "%PROJECT_ROOT%\rules"
mkdir "%PROJECT_ROOT%\patterns"
mkdir "%PROJECT_ROOT%\src"
mkdir "%PROJECT_ROOT%\src\idms_db2_phase2"

mkdir "%PROJECT_ROOT%\src\idms_db2_phase2\domain"
mkdir "%PROJECT_ROOT%\src\idms_db2_phase2\infrastructure"
mkdir "%PROJECT_ROOT%\src\idms_db2_phase2\parsers"
mkdir "%PROJECT_ROOT%\src\idms_db2_phase2\repositories"
mkdir "%PROJECT_ROOT%\src\idms_db2_phase2\resolvers"
mkdir "%PROJECT_ROOT%\src\idms_db2_phase2\generators"
mkdir "%PROJECT_ROOT%\src\idms_db2_phase2\transformers"
mkdir "%PROJECT_ROOT%\src\idms_db2_phase2\validators"
mkdir "%PROJECT_ROOT%\src\idms_db2_phase2\composers"
mkdir "%PROJECT_ROOT%\src\idms_db2_phase2\analyzers"
mkdir "%PROJECT_ROOT%\src\idms_db2_phase2\orchestration"
mkdir "%PROJECT_ROOT%\src\idms_db2_phase2\testing"
mkdir "%PROJECT_ROOT%\src\idms_db2_phase2\ui"

mkdir "%PROJECT_ROOT%\tests"

type nul > "%PROJECT_ROOT%\main.py"
type nul > "%PROJECT_ROOT%\pyproject.toml"
type nul > "%PROJECT_ROOT%\README.md"
type nul > "%PROJECT_ROOT%\logs\.gitkeep"

type nul > "%PROJECT_ROOT%\config\__init__.py"
type nul > "%PROJECT_ROOT%\config\app_settings.py"
type nul > "%PROJECT_ROOT%\config\path_settings.py"
type nul > "%PROJECT_ROOT%\config\logging_settings.py"

type nul > "%PROJECT_ROOT%\catalogs\__init__.py"
type nul > "%PROJECT_ROOT%\catalogs\input_file_roles.py"
type nul > "%PROJECT_ROOT%\catalogs\sheet_mapping_schema.py"
type nul > "%PROJECT_ROOT%\catalogs\dclgen_schema.py"
type nul > "%PROJECT_ROOT%\catalogs\copybook_schema.py"
type nul > "%PROJECT_ROOT%\catalogs\db2_sql_types.py"
type nul > "%PROJECT_ROOT%\catalogs\cobol_reserved_words.py"
type nul > "%PROJECT_ROOT%\catalogs\output_sections.py"

type nul > "%PROJECT_ROOT%\rules\__init__.py"
type nul > "%PROJECT_ROOT%\rules\authority_rules.py"
type nul > "%PROJECT_ROOT%\rules\business_flow_rules.py"
type nul > "%PROJECT_ROOT%\rules\conversion_rules.py"
type nul > "%PROJECT_ROOT%\rules\cursor_rules.py"
type nul > "%PROJECT_ROOT%\rules\db2_infrastructure_rules.py"
type nul > "%PROJECT_ROOT%\rules\field_mapping_rules.py"
type nul > "%PROJECT_ROOT%\rules\sql_generation_rules.py"
type nul > "%PROJECT_ROOT%\rules×tamp_audit_rules.py"
type nul > "%PROJECT_ROOT%\rules\validation_rules.py"
type nul > "%PROJECT_ROOT%\rules\manual_layout_rules.py"

type nul > "%PROJECT_ROOT%\patterns\__init__.py"
type nul > "%PROJECT_ROOT%\patterns\cobol_patterns.py"
type nul > "%PROJECT_ROOT%\patterns\copybook_patterns.py"
type nul > "%PROJECT_ROOT%\patterns\dclgen_patterns.py"
type nul > "%PROJECT_ROOT%\patterns\db2_patterns.py"
type nul > "%PROJECT_ROOT%\patterns\idms_patterns.py"
type nul > "%PROJECT_ROOT%\patterns\naming_patterns.py"
type nul > "%PROJECT_ROOT%\patterns\sequence_patterns.py"
type nul > "%PROJECT_ROOT%\patterns\sheet_mapping_patterns.py"
type nul > "%PROJECT_ROOT%\patterns\sql_patterns.py"

type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\__init__.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\app.py"

type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\domain\__init__.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\domain\models.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\domain\enums.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\domain\result_models.py"

type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\infrastructure\__init__.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\infrastructure\file_loader.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\infrastructure\local_uploaded_file.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\infrastructure\logger_factory.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\infrastructure\runtime_context.py"

type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\parsers\__init__.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\parsers\base_text_parser.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\parsers\cobol_parser.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\parsers\copybook_parser.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\parsers\dclgen_parser.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\parsers\sheet_mapping_parser.py"

type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\repositories\__init__.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\repositories\mapping_repository.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\repositories\dclgen_repository.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\repositories\copybook_repository.py"

type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\resolvers\__init__.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\resolvers\table_name_resolver.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\resolvers\column_name_resolver.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\resolvers\host_variable_resolver.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\resolvers\cursor_name_resolver.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\resolvers\record_context_resolver.py"

type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\generators\__init__.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\generators\db2_infrastructure_generator.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\generators\sql_generator.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\generators\cursor_paragraph_generator.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\generators×tamp_generator.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\generators\sql_error_generator.py"

type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\transformers\__init__.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\transformers\cobol_transformer.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\transformers\idms_statement_transformer.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\transformers\field_reference_rewriter.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\transformers\pic_length_auto_fixer.py"

type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\validators\__init__.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\validators\input_validator.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\validators\production_validator.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\validators\mapping_validator.py"

type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\composers\__init__.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\composers\cobol_formatter.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\composers\fixed_format_composer.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\composers\manual_layout_composer.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\composers\manual_style_preserver.py"

type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\analyzers\__init__.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\analyzers\program_flow_analyzer.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\analyzers\metadata_service.py"

type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\orchestration\__init__.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\orchestration\conversion_service.py"

type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\testing\__init__.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\testing\run_retrieval.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\testing\run_update.py"

type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\ui\__init__.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\ui\main_page.py"

type nul > "%PROJECT_ROOT%\tests\__init__.py"
type nul > "%PROJECT_ROOT%\tests\test_patterns.py"
type nul > "%PROJECT_ROOT%\tests\test_rules.py"
type nul > "%PROJECT_ROOT%\tests\test_sheet_mapping_parser.py"
type nul > "%PROJECT_ROOT%\tests\test_dclgen_parser.py"
type nul > "%PROJECT_ROOT%\tests\test_copybook_parser.py"
type nul > "%PROJECT_ROOT%\tests\test_table_name_resolver.py"
type nul > "%PROJECT_ROOT%\tests\test_name_normalizer.py"

echo.
echo Clean production architecture created successfully.
echo.
echo Next:
echo cd %PROJECT_ROOT%
echo.

endlocal
pause