from __future__ import annotations

from idms_db2_phase2.composers.update_program_sql_feedback_composer import (
    UpdateProgramSqlFeedbackComposer,
)
from idms_db2_phase2.composers.update_program_structure_feedback_composer import (
    UpdateProgramStructureFeedbackComposer,
)
from idms_db2_phase2.repositories.dclgen_repository import DclgenRepository
from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.host_variable_resolver import HostVariableResolver
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver


class UpdateProgramFeedbackComposer:
    """
    Public update-program feedback composer.

    Keeps a stable import point while delegating to focused smaller files.
    """

    def __init__(
        self,
        mapping_repository: MappingRepository,
        dclgen_repository: DclgenRepository,
        table_name_resolver: TableNameResolver,
        host_variable_resolver: HostVariableResolver,
    ) -> None:
        self.sql_feedback = UpdateProgramSqlFeedbackComposer(
            mapping_repository=mapping_repository,
            dclgen_repository=dclgen_repository,
            table_name_resolver=table_name_resolver,
            host_variable_resolver=host_variable_resolver,
        )
        self.structure_feedback = UpdateProgramStructureFeedbackComposer(
            mapping_repository=mapping_repository,
            dclgen_repository=dclgen_repository,
            table_name_resolver=table_name_resolver,
            host_variable_resolver=host_variable_resolver,
        )
        self.messages: list[str] = []

    def compose(
        self,
        text: str,
    ) -> str:
        self.messages = []
        output = str(text or "")

        if not output.strip():
            return output

        output = self.sql_feedback.compose(output)
        self.messages.extend(self.sql_feedback.messages)

        output = self.structure_feedback.compose(output)
        self.messages.extend(self.structure_feedback.messages)

        return output.rstrip() + "\n"