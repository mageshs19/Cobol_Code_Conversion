from __future__ import annotations

from idms_db2_phase2.analyzers.program_flow_analyzer import ProgramFlowAnalyzer
from idms_db2_phase2.composers.cobol_formatter import CobolFormatter
from idms_db2_phase2.composers.cursor_flow_composer import CursorFlowComposer
from idms_db2_phase2.composers.cursor_order_cleanup_composer import (
    CursorOrderCleanupComposer,
)
from idms_db2_phase2.composers.db2_date_comparison_composer import (
    Db2DateComparisonComposer,
)
from idms_db2_phase2.composers.feedback_cleanup_composer import (
    FeedbackCleanupComposer,
)
from idms_db2_phase2.composers.final_feedback_fix_composer import (
    FinalFeedbackFixComposer,
    FinalFeedbackFixComposerConfig,
)
from idms_db2_phase2.composers.fixed_format_composer import FixedFormatComposer
from idms_db2_phase2.composers.manual_layout_composer import ManualLayoutComposer
from idms_db2_phase2.composers.manual_style_preserver import ManualStylePreserver
from idms_db2_phase2.composers.sqlcode_wrapper_cleanup_composer import (
    SqlcodeWrapperCleanupComposer,
)
from idms_db2_phase2.composers.update_program_feedback_composer import (
    UpdateProgramFeedbackComposer,
)
from idms_db2_phase2.composers.update_restart_skip_composer import (
    UpdateRestartSkipComposer,
)
from idms_db2_phase2.domain.models import ConversionInput, ConversionResult
from idms_db2_phase2.generators.cursor_paragraph_generator import (
    CursorParagraphGenerator,
)
from idms_db2_phase2.generators.db2_infrastructure_generator import (
    Db2InfrastructureGenerator,
)
from idms_db2_phase2.generators.sql_error_generator import SqlErrorGenerator
from idms_db2_phase2.generators.sql_generator import SqlGenerator
from idms_db2_phase2.generators.timestamp_generator import TimestampGenerator
from idms_db2_phase2.repositories.copybook_repository import CopybookRepository
from idms_db2_phase2.repositories.dclgen_repository import DclgenRepository
from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.column_name_resolver import ColumnNameResolver
from idms_db2_phase2.resolvers.cursor_name_resolver import CursorNameResolver
from idms_db2_phase2.resolvers.host_variable_resolver import HostVariableResolver
from idms_db2_phase2.resolvers.record_context_resolver import (
    RecordContextResolver,
)
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
from idms_db2_phase2.transformers.cobol_transformer import CobolTransformer
from idms_db2_phase2.transformers.field_reference_rewriter import (
    FieldReferenceRewriter,
)
from idms_db2_phase2.transformers.idms_statement_transformer import (
    IdmsStatementTransformer,
)
from idms_db2_phase2.transformers.pic_length_auto_fixer import (
    PicLengthAutoFixer,
)
from idms_db2_phase2.validators.input_validator import InputValidator
from idms_db2_phase2.validators.mapping_validator import MappingValidator
from idms_db2_phase2.validators.production_validator import ProductionValidator


class ConversionService:
    """
    Main orchestration service for IDMS COBOL to DB2 COBOL conversion.

    Responsibilities:
    - Validate required inputs.
    - Build repositories and resolvers.
    - Transform IDMS database logic into DB2 SQL logic.
    - Apply DB2 infrastructure generation.
    - Apply conservative feedback cleanup.
    - Apply final manual-style fixed-format output.
    - Run production validation.

    This service does not hardcode business records, DB2 tables, DB2 columns,
    DCLGEN groups, or host variables.
    """

    def convert(
        self,
        conversion_input: ConversionInput,
    ) -> ConversionResult:
        validation_messages: list[str] = []

        input_validator = InputValidator()
        input_messages = input_validator.validate(conversion_input)
        validation_messages.extend(input_messages)

        if input_messages:
            return ConversionResult(
                converted_cobol="",
                validation_messages=self._unique_messages(validation_messages),
                operations=[],
            )

        repositories = self._repositories(conversion_input)
        resolvers = self._resolvers(repositories)

        generators = self._generators(
            repositories=repositories,
            resolvers=resolvers,
        )

        transformers = self._transformers(
            repositories=repositories,
            resolvers=resolvers,
            generators=generators,
        )

        composers = self._composers(
            repositories=repositories,
            resolvers=resolvers,
        )

        mapping_validator = MappingValidator(
            mapping_repository=repositories["mapping"],
            dclgen_repository=repositories["dclgen"],
            table_name_resolver=resolvers["table_name"],
        )
        validation_messages.extend(mapping_validator.validate())

        converted_cobol, transform_messages, operations = transformers[
            "cobol"
        ].transform(
            cobol_text=conversion_input.idms_cobol_text,
            target_program_id=conversion_input.target_program_id,
        )
        validation_messages.extend(transform_messages)

        converted_cobol = composers["update_restart_skip"].compose(
            converted_cobol
        )
        validation_messages.extend(
            self._component_messages(composers["update_restart_skip"])
        )

        flow_analyzer = ProgramFlowAnalyzer(
            mapping_rows=conversion_input.sheet_mapping_rows,
            dclgen_columns=conversion_input.dclgen_columns,
        )
        flow_analysis = flow_analyzer.analyze(
            cobol_text=conversion_input.idms_cobol_text,
            operations=operations,
        )
        validation_messages.extend(flow_analysis.diagnostics)

        converted_cobol = transformers["field_reference"].rewrite(
            converted_cobol
        )
        validation_messages.extend(
            self._component_messages(transformers["field_reference"])
        )

        converted_cobol, infrastructure_messages = generators[
            "db2_infrastructure"
        ].apply(
            cobol_text=converted_cobol,
            operations=operations,
        )
        validation_messages.extend(infrastructure_messages)

        converted_cobol = composers["cursor_order_cleanup"].compose(
            converted_cobol
        )

        converted_cobol, cursor_messages = generators[
            "cursor_paragraph"
        ].apply(
            cobol_text=converted_cobol,
            operations=operations,
        )
        validation_messages.extend(cursor_messages)

        converted_cobol = composers["cursor_flow"].compose(converted_cobol)

        converted_cobol = composers["sqlcode_cleanup"].compose(
            converted_cobol
        )

        converted_cobol = composers["cursor_order_cleanup"].compose(
            converted_cobol
        )

        converted_cobol = composers["date_compare"].compose(converted_cobol)

        converted_cobol, timestamp_messages = generators["timestamp"].apply(
            cobol_text=converted_cobol,
            target_program_id=conversion_input.target_program_id,
        )
        validation_messages.extend(timestamp_messages)

        converted_cobol = generators["sql_error"].ensure_sql_error_paragraph(
            converted_cobol
        )

        if conversion_input.auto_fix_pic_length_mismatches:
            converted_cobol = transformers["pic_length"].fix(
                source_cobol_text=conversion_input.idms_cobol_text,
                converted_cobol_text=converted_cobol,
            )
            validation_messages.extend(
                self._component_messages(transformers["pic_length"])
            )

        converted_cobol = composers["feedback_cleanup"].compose(
            converted_cobol
        )
        validation_messages.extend(
            self._component_messages(composers["feedback_cleanup"])
        )

        converted_cobol = composers["update_restart_skip"].compose(
            converted_cobol
        )
        validation_messages.extend(
            self._component_messages(composers["update_restart_skip"])
        )

        converted_cobol = composers["update_program_feedback"].compose(
            converted_cobol
        )
        validation_messages.extend(
            self._component_messages(composers["update_program_feedback"])
        )

        converted_cobol = composers["formatter"].format(converted_cobol)

        converted_cobol = composers["manual_layout"].compose(converted_cobol)

        converted_cobol = composers["style_preserver"].preserve(
            original_text=conversion_input.idms_cobol_text,
            converted_text=converted_cobol,
        )

        converted_cobol = composers["fixed_format"].format(converted_cobol)

        converted_cobol = composers["cursor_flow"].compose(converted_cobol)

        converted_cobol = composers["sqlcode_cleanup"].compose(
            converted_cobol
        )

        converted_cobol = composers["cursor_order_cleanup"].compose(
            converted_cobol
        )

        converted_cobol = composers["date_compare"].compose(converted_cobol)

        converted_cobol = composers["feedback_cleanup"].compose(
            converted_cobol
        )
        validation_messages.extend(
            self._component_messages(composers["feedback_cleanup"])
        )

        converted_cobol = composers["update_restart_skip"].compose(
            converted_cobol
        )
        validation_messages.extend(
            self._component_messages(composers["update_restart_skip"])
        )

        converted_cobol = composers["update_program_feedback"].compose(
            converted_cobol
        )
        validation_messages.extend(
            self._component_messages(composers["update_program_feedback"])
        )

        converted_cobol = composers["fixed_format"].format(converted_cobol)

        converted_cobol = composers["final_feedback_fix"].compose(
            converted_cobol
        )

        production_validator = ProductionValidator(
            dclgen_repository=repositories["dclgen"],
        )
        validation_messages.extend(
            production_validator.validate(converted_cobol)
        )

        return ConversionResult(
            converted_cobol=converted_cobol,
            validation_messages=self._unique_messages(validation_messages),
            operations=operations,
        )

    def _repositories(
        self,
        conversion_input: ConversionInput,
    ) -> dict[str, object]:
        return {
            "mapping": MappingRepository(
                conversion_input.sheet_mapping_rows,
            ),
            "dclgen": DclgenRepository(
                conversion_input.dclgen_columns,
            ),
            "copybook": CopybookRepository(
                conversion_input.copybook_fields,
            ),
        }

    def _resolvers(
        self,
        repositories: dict[str, object],
    ) -> dict[str, object]:
        mapping_repository = repositories["mapping"]
        dclgen_repository = repositories["dclgen"]
        copybook_repository = repositories["copybook"]

        table_name_resolver = TableNameResolver(
            mapping_repository=mapping_repository,
            dclgen_repository=dclgen_repository,
        )

        column_name_resolver = ColumnNameResolver(
            mapping_repository=mapping_repository,
            dclgen_repository=dclgen_repository,
            table_name_resolver=table_name_resolver,
        )

        host_variable_resolver = HostVariableResolver(
            dclgen_repository=dclgen_repository,
            table_name_resolver=table_name_resolver,
        )

        cursor_name_resolver = CursorNameResolver()

        record_context_resolver = RecordContextResolver(
            mapping_repository=mapping_repository,
            dclgen_repository=dclgen_repository,
        )

        return {
            "table_name": table_name_resolver,
            "column_name": column_name_resolver,
            "host_variable": host_variable_resolver,
            "cursor_name": cursor_name_resolver,
            "record_context": record_context_resolver,
            "copybook": copybook_repository,
        }

    def _generators(
        self,
        repositories: dict[str, object],
        resolvers: dict[str, object],
    ) -> dict[str, object]:
        sql_error_generator = SqlErrorGenerator()

        sql_generator = SqlGenerator(
            mapping_repository=repositories["mapping"],
            dclgen_repository=repositories["dclgen"],
            table_name_resolver=resolvers["table_name"],
            column_name_resolver=resolvers["column_name"],
            host_variable_resolver=resolvers["host_variable"],
        )

        db2_infrastructure_generator = Db2InfrastructureGenerator(
            table_name_resolver=resolvers["table_name"],
            column_name_resolver=resolvers["column_name"],
            host_variable_resolver=resolvers["host_variable"],
            cursor_name_resolver=resolvers["cursor_name"],
        )

        cursor_paragraph_generator = CursorParagraphGenerator(
            db2_infrastructure_generator=db2_infrastructure_generator,
            host_variable_resolver=resolvers["host_variable"],
            sql_error_generator=sql_error_generator,
        )

        timestamp_generator = TimestampGenerator(
            mapping_repository=repositories["mapping"],
            table_name_resolver=resolvers["table_name"],
            host_variable_resolver=resolvers["host_variable"],
        )

        return {
            "sql": sql_generator,
            "sql_error": sql_error_generator,
            "db2_infrastructure": db2_infrastructure_generator,
            "cursor_paragraph": cursor_paragraph_generator,
            "timestamp": timestamp_generator,
        }

    def _transformers(
        self,
        repositories: dict[str, object],
        resolvers: dict[str, object],
        generators: dict[str, object],
    ) -> dict[str, object]:
        idms_statement_transformer = IdmsStatementTransformer(
            sql_generator=generators["sql"],
            sql_error_generator=generators["sql_error"],
            table_name_resolver=resolvers["table_name"],
            cursor_name_resolver=resolvers["cursor_name"],
        )

        cobol_transformer = CobolTransformer(
            idms_statement_transformer=idms_statement_transformer,
        )

        field_reference_rewriter = FieldReferenceRewriter(
            mapping_repository=repositories["mapping"],
            table_name_resolver=resolvers["table_name"],
            host_variable_resolver=resolvers["host_variable"],
        )

        pic_length_auto_fixer = PicLengthAutoFixer()

        return {
            "idms_statement": idms_statement_transformer,
            "cobol": cobol_transformer,
            "field_reference": field_reference_rewriter,
            "pic_length": pic_length_auto_fixer,
        }

    def _composers(
        self,
        repositories: dict[str, object],
        resolvers: dict[str, object],
    ) -> dict[str, object]:
        return {
            "formatter": CobolFormatter(),
            "cursor_flow": CursorFlowComposer(),
            "cursor_order_cleanup": CursorOrderCleanupComposer(),
            "date_compare": Db2DateComparisonComposer(),
            "feedback_cleanup": FeedbackCleanupComposer(
                dclgen_repository=repositories["dclgen"],
            ),
            "final_feedback_fix": FinalFeedbackFixComposer(
                config=FinalFeedbackFixComposerConfig(
                    db2_date_external_format="DD.MM.YYYY",
                    require_order_by_columns_in_select=False,
                )
            ),
            "fixed_format": FixedFormatComposer(),
            "manual_layout": ManualLayoutComposer(),
            "sqlcode_cleanup": SqlcodeWrapperCleanupComposer(),
            "style_preserver": ManualStylePreserver(),
            "update_program_feedback": UpdateProgramFeedbackComposer(
                mapping_repository=repositories["mapping"],
                dclgen_repository=repositories["dclgen"],
                table_name_resolver=resolvers["table_name"],
                host_variable_resolver=resolvers["host_variable"],
            ),
            "update_restart_skip": UpdateRestartSkipComposer(),
        }

    def _component_messages(
        self,
        component: object,
    ) -> list[str]:
        """
        Safely return messages from components that optionally expose messages.

        Some transformers/composers expose a messages attribute, while others
        do not. This helper keeps orchestration generic and avoids forcing all
        components to implement the same diagnostics interface.
        """

        messages = getattr(component, "messages", [])

        if callable(messages):
            messages = messages()

        if not messages:
            return []

        return [
            str(message)
            for message in messages
            if str(message or "").strip()
        ]

    def _unique_messages(
        self,
        messages: list[str],
    ) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()

        for message in messages:
            clean_message = str(message or "").strip()

            if not clean_message:
                continue

            if clean_message in seen:
                continue

            seen.add(clean_message)
            output.append(clean_message)

        return output