from idms_db2_phase2.domain.models import ConversionInput
from rules.validation_rules import INPUT_VALIDATION_MESSAGES


class InputValidator:
    """
    Validates required conversion inputs.

    This validator checks only input availability. It does not validate
    generated COBOL production quality.
    """

    def validate(
        self,
        conversion_input: ConversionInput,
    ) -> list[str]:
        messages: list[str] = []

        if not conversion_input.sheet_mapping_rows:
            messages.append(
                INPUT_VALIDATION_MESSAGES["missing_sheet_mapping"]
            )

        if not conversion_input.dclgen_columns:
            messages.append(
                INPUT_VALIDATION_MESSAGES["missing_dclgen"]
            )

        if not conversion_input.idms_cobol_text.strip():
            messages.append(
                INPUT_VALIDATION_MESSAGES["missing_idms_cobol"]
            )

        return messages