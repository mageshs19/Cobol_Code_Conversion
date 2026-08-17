from idms_db2_phase2.domain.models import ConversionInput
from patterns.validation_rules import INPUT_VALIDATION_MESSAGES


class ValidationService:
    """
    Validates the minimum required conversion inputs.

    This service performs input-level validation only.
    Production validation of converted COBOL output should remain in a
    separate production validator.
    """

    def validate(
        self,
        conversion_input: ConversionInput,
    ) -> list[str]:
        messages: list[str] = []

        if not conversion_input.sheet_mapping_rows:
            messages.append(INPUT_VALIDATION_MESSAGES["missing_sheet_mapping"])

        if not conversion_input.dclgen_columns:
            messages.append(INPUT_VALIDATION_MESSAGES["missing_dolgen"])

        if not conversion_input.idms_cobol_text.strip():
            messages.append(INPUT_VALIDATION_MESSAGES["missing_idms_cobol"])

        return messages