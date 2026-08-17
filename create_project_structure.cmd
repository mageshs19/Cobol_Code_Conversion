@echo off
setlocal enabledelayedexpansion

set PROJECT_ROOT=IDMS-DB2-Code-Conversion

echo Creating project root: %PROJECT_ROOT%

mkdir "%PROJECT_ROOT%"

mkdir "%PROJECT_ROOT%\logs"

mkdir "%PROJECT_ROOT%\rules"
mkdir "%PROJECT_ROOT%\patterns"

mkdir "%PROJECT_ROOT%\src"
mkdir "%PROJECT_ROOT%\src\idms_db2_phase2"

mkdir "%PROJECT_ROOT%\src\idms_db2_phase2\config"
mkdir "%PROJECT_ROOT%\src\idms_db2_phase2\domain"
mkdir "%PROJECT_ROOT%\src\idms_db2_phase2\logging_utils"
mkdir "%PROJECT_ROOT%\src\idms_db2_phase2\parsers"
mkdir "%PROJECT_ROOT%\src\idms_db2_phase2\services"
mkdir "%PROJECT_ROOT%\src\idms_db2_phase2\testing"
mkdir "%PROJECT_ROOT%\src\idms_db2_phase2\ui"

mkdir "%PROJECT_ROOT%\tests"

echo Creating root files...

type nul > "%PROJECT_ROOT%\main.py"
type nul > "%PROJECT_ROOT%\pyproject.toml"
type nul > "%PROJECT_ROOT%\README.md"
type nul > "%PROJECT_ROOT%\logs\.gitkeep"

echo Creating rules files...

type nul > "%PROJECT_ROOT%\rules\__init__.py"
type nul > "%PROJECT_ROOT%\rules\business_rules.py"
type nul > "%PROJECT_ROOT%\rules\conversion_rules.py"
type nul > "%PROJECT_ROOT%\rules\cursor_rules.py"
type nul > "%PROJECT_ROOT%\rules\db2_infrastructure_rules.py"
type nul > "%PROJECT_ROOT%\rules\field_mapping_rules.py"
type nul > "%PROJECT_ROOT%\rules\manual_layout_rules.py"
type nul > "%PROJECT_ROOT%\rules\sql_generation_rules.py"
type nul > "%PROJECT_ROOT%\rules×tamp_audit_rules.py"

echo Creating patterns files...

type nul > "%PROJECT_ROOT%\patterns\__init__.py"
type nul > "%PROJECT_ROOT%\patterns\cobol_patterns.py"
type nul > "%PROJECT_ROOT%\patterns\db2_patterns.py"
type nul > "%PROJECT_ROOT%\patterns\idms_patterns.py"
type nul > "%PROJECT_ROOT%\patterns\naming_patterns.py"
type nul > "%PROJECT_ROOT%\patterns\sequence_patterns.py"
type nul > "%PROJECT_ROOT%\patterns\sql_patterns.py"

echo Creating src package files...

type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\__init__.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\app.py"

echo Creating config files...

type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\config\__init__.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\config\app_config.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\config\path_config.py"

echo Creating domain files...

type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\domain\__init__.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\domain\models.py"

echo Creating logging utility files...

type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\logging_utils\__init__.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\logging_utils\logger_factory.py"

echo Creating parser files...

type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\parsers\__init__.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\parsers\cobol_parser.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\parsers\copybook_parser.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\parsers\dclgen_parser.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\parsers\sheet_mapping_parser.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\parsers\text_loader.py"

echo Creating service files...

type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\services\__init__.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\services\cobol_fixed_format_composer.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\services\cobol_formatter.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\services\cobol_transformer.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\services\conversion_service.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\services\db2_cursor_paragraph_generator.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\services\db2_infrastructure_generator.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\services\field_reference_rewriter.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\services\manual_layout_composer.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\services\metadata_service.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\services\name_normalizer.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\services\pic_length_auto_fixer.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\services\production_validator.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\services\program_flow_analyzer.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\services\sql_generator.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\services×tamp_generator.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\services\validation_service.py"

echo Creating testing files...

type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\testing\__init__.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\testing\run_retrieval.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\testing\run_update.py"

echo Creating UI files...

type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\ui\__init__.py"
type nul > "%PROJECT_ROOT%\src\idms_db2_phase2\ui\main_page.py"

echo Creating test files...

type nul > "%PROJECT_ROOT%\tests\__init__.py"
type nul > "%PROJECT_ROOT%\tests\test_name_normalizer.py"
type nul > "%PROJECT_ROOT%\tests\test_rules.py"
type nul > "%PROJECT_ROOT%\tests\test_patterns.py"

echo.
echo Project structure created successfully.
echo.
echo Next command:
echo cd %PROJECT_ROOT%
echo.

endlocal
pause