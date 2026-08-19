from idms_db2_phase2.repositories.dclgen_repository import DclgenRepository
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from patterns.sequence_patterns import strip_sequence_numbers
from patterns.sql_patterns import HOST_REFERENCE_PATTERN
from patterns.validation_patterns import (
    ERROR_DB2_PATTERN,
    FORBIDDEN_EXECUTABLE_IDMS_PATTERNS,
    FORBIDDEN_IDMS_DECLARATIVE_PATTERNS,
    NO_FETCH_HOST_VARIABLES_PATTERN,
    TODO_DB2_PATTERN,
    TODO_HOST_VARIABLE_PATTERN,
    UNABLE_TO_DECLARE_CURSOR_PATTERN,
)
from rules.db2_validation_rules import REQUIRED_DB2_TOKENS
from rules.validation_rules import PRODUCTION_VALIDATION_MESSAGES


class ProductionValidator:
    """
    Performs production-focused validation for generated DB2 COBOL.

    It detects:
    - Missing required DB2 constructs.
    - TODO host variables.
    - Generated DB2 error markers.
    - Residual executable IDMS statements.
    - Residual IDMS declarative/control statements.
    - Generated DCLGEN host variables not found in uploaded DCLGEN metadata.

    This validator must ignore commented fixed-format lines.
    """

    def __init__(
        self,
        dclgen_repository: DclgenRepository,
    ) -> None:
        self.dclgen_repository = dclgen_repository

    def validate(
        self,
        converted_cobol_text: str,
    ) -> list[str]:
        messages: list[str] = []
        text = str(converted_cobol_text or "")

        if not text.strip():
            return ["Production validation: converted COBOL text is empty."]

        self._validate_required_db2_tokens(text, messages)
        self._validate_no_todo_or_generated_error(text, messages)
        self._validate_forbidden_idms_patterns(text, messages)
        self._validate_forbidden_idms_declaratives(text, messages)
        self._validate_generated_dclgen_host_variables(text, messages)

        return messages

    def _validate_required_db2_tokens(
        self,
        text: str,
        messages: list[str],
    ) -> None:
        upper_text = text.upper()

        for token in REQUIRED_DB2_TOKENS:
            if token.upper() in upper_text:
                continue

            key = f"missing_{NameNormalizer.normalize(token).lower()}"

            if key in PRODUCTION_VALIDATION_MESSAGES:
                messages.append(PRODUCTION_VALIDATION_MESSAGES[key])
                continue

            messages.append(
                f"Production validation: required DB2 token missing: {token}"
            )

    def _validate_no_todo_or_generated_error(
        self,
        text: str,
        messages: list[str],
    ) -> None:
        if TODO_HOST_VARIABLE_PATTERN.search(text):
            messages.append(
                PRODUCTION_VALIDATION_MESSAGES["todo_host_variable"]
            )

        if TODO_DB2_PATTERN.search(text):
            messages.append(
                PRODUCTION_VALIDATION_MESSAGES["todo_db2"]
            )

        if ERROR_DB2_PATTERN.search(text):
            messages.append(
                PRODUCTION_VALIDATION_MESSAGES["error_db2"]
            )

        if UNABLE_TO_DECLARE_CURSOR_PATTERN.search(text):
            messages.append(
                PRODUCTION_VALIDATION_MESSAGES["unable_to_declare_cursor"]
            )

        if NO_FETCH_HOST_VARIABLES_PATTERN.search(text):
            messages.append(
                PRODUCTION_VALIDATION_MESSAGES["no_fetch_host_variables"]
            )

    def _validate_forbidden_idms_patterns(
        self,
        text: str,
        messages: list[str],
    ) -> None:
        for line_number, line in enumerate(text.splitlines(), start=1):
            logical = self._logical_line(line)

            if self._is_comment_or_blank(logical):
                continue

            for pattern in FORBIDDEN_EXECUTABLE_IDMS_PATTERNS:
                if pattern.search(logical):
                    messages.append(
                        "Production validation: residual executable IDMS statement "
                        f"remains near line {line_number}: {logical}"
                    )
                    break

    def _validate_forbidden_idms_declaratives(
        self,
        text: str,
        messages: list[str],
    ) -> None:
        for line_number, line in enumerate(text.splitlines(), start=1):
            logical = self._logical_line(line)

            if self._is_comment_or_blank(logical):
                continue

            for pattern in FORBIDDEN_IDMS_DECLARATIVE_PATTERNS:
                if pattern.search(logical):
                    messages.append(
                        "Production validation: residual IDMS declarative/control "
                        f"statement remains near line {line_number}: {logical}"
                    )
                    break

    def _validate_generated_dclgen_host_variables(
        self,
        converted_cobol_text: str,
        messages: list[str],
    ) -> None:
        generated_hosts = self._generated_dclgen_host_references(
            converted_cobol_text
        )

        if not generated_hosts:
            return

        valid_hosts = self._valid_dclgen_host_reference_keys()

        if not valid_hosts:
            messages.append(
                PRODUCTION_VALIDATION_MESSAGES["no_dclgen_hosts"]
            )
            return

        missing_hosts = sorted(
            host for host in generated_hosts if host not in valid_hosts
        )

        for host in missing_hosts:
            messages.append(
                f"Production validation: generated host variable {host} "
                "was not found in uploaded DCLGEN columns."
            )

    def _generated_dclgen_host_references(
        self,
        converted_cobol_text: str,
    ) -> set[str]:
        output: set[str] = set()

        for match in HOST_REFERENCE_PATTERN.finditer(converted_cobol_text):
            group = NameNormalizer.to_cobol(match.group("group"))
            field = NameNormalizer.to_cobol(match.group("field"))

            key = self._host_key(group=group, field=field)

            if key:
                output.add(key)

        return output

    def _valid_dclgen_host_reference_keys(
        self,
    ) -> set[str]:
        output: set[str] = set()

        for column in self.dclgen_repository.all():
            table = NameNormalizer.normalize(column.table_name)
            field = NameNormalizer.to_cobol(
                column.cobol_host_name or column.column_name
            )

            if not table or not field:
                continue

            group = self.dclgen_repository.group_for_table(table)
            key = self._host_key(group=group, field=field)

            if key:
                output.add(key)

        return output

    def _host_key(
        self,
        group: str,
        field: str,
    ) -> str:
        clean_group = NameNormalizer.to_cobol(group)
        clean_field = NameNormalizer.to_cobol(field)

        if not clean_group or not clean_field:
            return ""

        return f"{clean_group}.{clean_field}"

    def _logical_line(
        self,
        line: str,
    ) -> str:
        text = str(line or "").rstrip()

        if self._is_fixed_format_comment(text):
            return "*"

        return strip_sequence_numbers(text).strip()

    def _is_fixed_format_comment(
        self,
        line: str,
    ) -> bool:
        text = str(line or "")

        if len(text) >= 7 and text[:6].isdigit() and text[6:7] in ("*", "/"):
            return True

        stripped = text.strip()

        if stripped.startswith("*") or stripped.startswith("/"):
            return True

        return False

    def _is_comment_or_blank(
        self,
        line: str,
    ) -> bool:
        stripped = str(line or "").strip()

        if not stripped:
            return True

        if stripped.startswith("*") or stripped.startswith("/"):
            return True

        return False