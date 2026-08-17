$ProjectRoot = "IDMS-DB2-Code-Conversion"

Write-Host "Creating project root: $ProjectRoot"

New-Item -ItemType Directory -Force -Path $ProjectRoot | Out-Null

$Directories = @(
    "$ProjectRoot/logs",
    "$ProjectRoot/rules",
    "$ProjectRoot/patterns",
    "$ProjectRoot/src",
    "$ProjectRoot/src/idms_db2_phase2",
    "$ProjectRoot/src/idms_db2_phase2/config",
    "$ProjectRoot/src/idms_db2_phase2/domain",
    "$ProjectRoot/src/idms_db2_phase2/logging_utils",
    "$ProjectRoot/src/idms_db2_phase2/parsers",
    "$ProjectRoot/src/idms_db2_phase2/services",
    "$ProjectRoot/src/idms_db2_phase2/testing",
    "$ProjectRoot/src/idms_db2_phase2/ui",
    "$ProjectRoot/tests"
)

foreach ($Directory in $Directories) {
    New-Item -ItemType Directory -Force -Path $Directory | Out-Null
    Write-Host "Created directory: $Directory"
}

$Files = @(
    "$ProjectRoot/main.py",
    "$ProjectRoot/pyproject.toml",
    "$ProjectRoot/README.md",
    "$ProjectRoot/logs/.gitkeep",

    "$ProjectRoot/rules/__init__.py",
    "$ProjectRoot/rules/business_rules.py",
    "$ProjectRoot/rules/conversion_rules.py",
    "$ProjectRoot/rules/cursor_rules.py",
    "$ProjectRoot/rules/db2_infrastructure_rules.py",
    "$ProjectRoot/rules/field_mapping_rules.py",
    "$ProjectRoot/rules/manual_layout_rules.py",
    "$ProjectRoot/rules/sql_generation_rules.py",
    "$ProjectRoot/rules/timestamp_audit_rules.py",

    "$ProjectRoot/patterns/__init__.py",
    "$ProjectRoot/patterns/cobol_patterns.py",
    "$ProjectRoot/patterns/db2_patterns.py",
    "$ProjectRoot/patterns/idms_patterns.py",
    "$ProjectRoot/patterns/naming_patterns.py",
    "$ProjectRoot/patterns/sequence_patterns.py",
    "$ProjectRoot/patterns/sql_patterns.py",

    "$ProjectRoot/src/idms_db2_phase2/__init__.py",
    "$ProjectRoot/src/idms_db2_phase2/app.py",

    "$ProjectRoot/src/idms_db2_phase2/config/__init__.py",
    "$ProjectRoot/src/idms_db2_phase2/config/app_config.py",
    "$ProjectRoot/src/idms_db2_phase2/config/path_config.py",

    "$ProjectRoot/src/idms_db2_phase2/domain/__init__.py",
    "$ProjectRoot/src/idms_db2_phase2/domain/models.py",

    "$ProjectRoot/src/idms_db2_phase2/logging_utils/__init__.py",
    "$ProjectRoot/src/idms_db2_phase2/logging_utils/logger_factory.py",

    "$ProjectRoot/src/idms_db2_phase2/parsers/__init__.py",
    "$ProjectRoot/src/idms_db2_phase2/parsers/cobol_parser.py",
    "$ProjectRoot/src/idms_db2_phase2/parsers/copybook_parser.py",
    "$ProjectRoot/src/idms_db2_phase2/parsers/dclgen_parser.py",
    "$ProjectRoot/src/idms_db2_phase2/parsers/sheet_mapping_parser.py",
    "$ProjectRoot/src/idms_db2_phase2/parsers/text_loader.py",

    "$ProjectRoot/src/idms_db2_phase2/services/__init__.py",
    "$ProjectRoot/src/idms_db2_phase2/services/cobol_fixed_format_composer.py",
    "$ProjectRoot/src/idms_db2_phase2/services/cobol_formatter.py",
    "$ProjectRoot/src/idms_db2_phase2/services/cobol_transformer.py",
    "$ProjectRoot/src/idms_db2_phase2/services/conversion_service.py",
    "$ProjectRoot/src/idms_db2_phase2/services/db2_cursor_paragraph_generator.py",
    "$ProjectRoot/src/idms_db2_phase2/services/db2_infrastructure_generator.py",
    "$ProjectRoot/src/idms_db2_phase2/services/field_reference_rewriter.py",
    "$ProjectRoot/src/idms_db2_phase2/services/manual_layout_composer.py",
    "$ProjectRoot/src/idms_db2_phase2/services/metadata_service.py",
    "$ProjectRoot/src/idms_db2_phase2/services/name_normalizer.py",
    "$ProjectRoot/src/idms_db2_phase2/services/pic_length_auto_fixer.py",
    "$ProjectRoot/src/idms_db2_phase2/services/production_validator.py",
    "$ProjectRoot/src/idms_db2_phase2/services/program_flow_analyzer.py",
    "$ProjectRoot/src/idms_db2_phase2/services/sql_generator.py",
    "$ProjectRoot/src/idms_db2_phase2/services/timestamp_generator.py",
    "$ProjectRoot/src/idms_db2_phase2/services/validation_service.py",

    "$ProjectRoot/src/idms_db2_phase2/testing/__init__.py",
    "$ProjectRoot/src/idms_db2_phase2/testing/run_retrieval.py",
    "$ProjectRoot/src/idms_db2_phase2/testing/run_update.py",

    "$ProjectRoot/src/idms_db2_phase2/ui/__init__.py",
    "$ProjectRoot/src/idms_db2_phase2/ui/main_page.py",

    "$ProjectRoot/tests/__init__.py",
    "$ProjectRoot/tests/test_name_normalizer.py",
    "$ProjectRoot/tests/test_rules.py",
    "$ProjectRoot/tests/test_patterns.py"
)

foreach ($File in $Files) {
    if (!(Test-Path $File)) {
        New-Item -ItemType File -Force -Path $File | Out-Null
        Write-Host "Created file: $File"
    }
    else {
        Write-Host "File already exists: $File"
    }
}

Write-Host ""
Write-Host "Project structure created successfully."
Write-Host "Next step: open the folder and start adding code file by file."