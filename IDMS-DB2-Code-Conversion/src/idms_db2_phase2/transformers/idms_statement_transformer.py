from idms_db2_phase2.generators.sql_error_generator import SqlErrorGenerator
from idms_db2_phase2.generators.sql_generator import SqlGenerator
from idms_db2_phase2.resolvers.cursor_name_resolver import CursorNameResolver
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from patterns.idms_patterns import (
    BIND_STATEMENT_PATTERN,
    COMMIT_PATTERN,
    CONNECT_STATEMENT_PATTERN,
    DB_END_OF_SET_TOKEN_PATTERN,
    DB_REC_NOT_FOUND_TOKEN_PATTERN,
    DISCONNECT_STATEMENT_PATTERN,
    ERASE_PATTERN,
    FIND_CURRENT_PATTERN,
    FIND_FIRST_PATTERN,
    FINISH_PATTERN,
    IDMS_ABORT_PERFORM_PATTERN,
    IDMS_DECLARATIVE_OR_CONTROL_PATTERNS,
    IDMS_STATUS_PERFORM_PATTERN,
    MODIFY_PATTERN,
    OBTAIN_CALC_PATTERN,
    OBTAIN_CALC_REVERSED_PATTERN,
    OBTAIN_FIRST_NEXT_PATTERN,
    ON_DB_REC_NOT_FOUND_PATTERN,
    READY_PATTERN,
    STORE_PATTERN,
    USAGE_MODE_PATTERN,
)


class IdmsStatementTransformer:
    """
    Converts executable IDMS statements to DB2-compatible COBOL.

    This transformer contains conversion logic only. Regex patterns live in
    patterns/idms_patterns.py.
    """

    def __init__(
        self,
        sql_generator: SqlGenerator,
        sql_error_generator: SqlErrorGenerator,
        table_name_resolver: TableNameResolver,
        cursor_name_resolver: CursorNameResolver,
    ) -> None:
        self.sql_generator = sql_generator
        self.sql_error_generator = sql_error_generator
        self.table_name_resolver = table_name_resolver
        self.cursor_name_resolver = cursor_name_resolver
        self.messages: list[str] = []

    def transform_line(
        self,
        line: str,
        current_division: str,
        sql_error_paragraph: str,
    ) -> tuple[list[str], str]:
        stripped_line = str(line or "").strip()
        upper = stripped_line.upper()

        if not stripped_line:
            return [line], ""

        if self._is_idms_declarative_or_control_statement(upper):
            return [
                f"* DB2: Removed residual IDMS control statement: {stripped_line}",
            ], ""

        if IDMS_STATUS_PERFORM_PATTERN.search(upper) or IDMS_ABORT_PERFORM_PATTERN.search(upper):
            return self._removed_idms_executable_lines(
                message=f"* DB2: Removed IDMS status/abort paragraph call: {stripped_line}",
                current_division=current_division,
            ), ""

        if BIND_STATEMENT_PATTERN.search(upper):
            return self._removed_idms_executable_lines(
                message=f"* DB2: Removed IDMS BIND statement: {stripped_line}",
                current_division=current_division,
            ), ""

        if USAGE_MODE_PATTERN.search(upper) or READY_PATTERN.search(upper):
            return self._removed_idms_executable_lines(
                message=f"* DB2: Removed IDMS usage/READY statement: {stripped_line}",
                current_division=current_division,
            ), ""

        if FIND_CURRENT_PATTERN.search(upper):
            return self._removed_idms_executable_lines(
                message=f"* DB2: Removed IDMS FIND CURRENT statement: {stripped_line}",
                current_division=current_division,
            ), ""

        if CONNECT_STATEMENT_PATTERN.search(upper) or DISCONNECT_STATEMENT_PATTERN.search(upper):
            return self._removed_idms_executable_lines(
                message=f"* DB2: Removed IDMS relationship statement. Relationship is handled by DB2 keys: {stripped_line}",
                current_division=current_division,
            ), ""

        finish_result = self._convert_finish_or_commit(
            upper=upper,
            stripped_line=stripped_line,
            current_division=current_division,
        )

        if finish_result is not None:
            return finish_result, ""

        on_not_found_result = self._convert_on_db_rec_not_found(stripped_line)

        if on_not_found_result is not None:
            return on_not_found_result, ""

        obtain_calc_result = self._convert_obtain_calc(
            upper=upper,
            stripped_line=stripped_line,
            current_division=current_division,
            sql_error_paragraph=sql_error_paragraph,
        )

        if obtain_calc_result is not None:
            return obtain_calc_result, ""

        obtain_set_result, opened_set = self._convert_obtain_set(
            upper=upper,
            stripped_line=stripped_line,
            current_division=current_division,
        )

        if obtain_set_result is not None:
            return obtain_set_result, opened_set

        find_first_result, opened_set = self._convert_find_first(
            upper=upper,
            stripped_line=stripped_line,
            current_division=current_division,
        )

        if find_first_result is not None:
            return find_first_result, opened_set

        store_result = self._convert_store_modify_erase(
            upper=upper,
            stripped_line=stripped_line,
            current_division=current_division,
            sql_error_paragraph=sql_error_paragraph,
        )

        if store_result is not None:
            return store_result, ""

        return self._replace_idms_condition_tokens(line), ""

    def _convert_finish_or_commit(
        self,
        upper: str,
        stripped_line: str,
        current_division: str,
    ) -> list[str] | None:
        if FINISH_PATTERN.search(upper):
            if current_division != "PROCEDURE":
                return [f"* DB2: FINISH ignored outside PROCEDURE DIVISION: {stripped_line}"]

            return [
                "* DB2: IDMS FINISH converted to COMMIT.",
                *self.sql_generator.commit(),
            ]

        if COMMIT_PATTERN.search(upper) and "EXEC SQL" not in upper:
            if current_division != "PROCEDURE":
                return [f"* DB2: COMMIT ignored outside PROCEDURE DIVISION: {stripped_line}"]

            return self.sql_generator.commit()

        return None

    def _convert_on_db_rec_not_found(
        self,
        stripped_line: str,
    ) -> list[str] | None:
        match = ON_DB_REC_NOT_FOUND_PATTERN.match(stripped_line)

        if not match:
            return None

        statement = str(match.group("statement") or "").strip()

        if not statement:
            return [
                "IF SQLCODE = 100",
                "    CONTINUE",
                "END-IF.",
            ]

        return [
            "IF SQLCODE = 100",
            f"    {statement}",
            "END-IF.",
        ]

    def _convert_obtain_calc(
        self,
        upper: str,
        stripped_line: str,
        current_division: str,
        sql_error_paragraph: str,
    ) -> list[str] | None:
        match = OBTAIN_CALC_PATTERN.search(upper)

        if not match:
            match = OBTAIN_CALC_REVERSED_PATTERN.search(upper)

        if not match:
            return None

        record = match.group("record").upper()

        if current_division != "PROCEDURE":
            return [
                f"* DB2: OBTAIN CALC ignored outside PROCEDURE DIVISION: {stripped_line}",
            ]

        return [
            f"* DB2: Converted OBTAIN CALC for {record}.",
            *self.sql_generator.select_by_key(record),
            "IF SQLCODE NOT = 0 AND SQLCODE NOT = 100",
            f"    PERFORM {sql_error_paragraph}.",
            "END-IF.",
        ]

    def _convert_obtain_set(
        self,
        upper: str,
        stripped_line: str,
        current_division: str,
    ) -> tuple[list[str] | None, str]:
        match = OBTAIN_FIRST_NEXT_PATTERN.search(upper)

        if not match:
            return None, ""

        mode = match.group("mode").upper()
        record = match.group("record").upper()
        set_name = match.group("set").upper()

        if current_division != "PROCEDURE":
            return [
                f"* DB2: OBTAIN {mode} ignored outside PROCEDURE DIVISION: {stripped_line}",
            ], ""

        table = self.table_name_resolver.table_for_record(record)
        cursor_name = self.cursor_name_resolver.cursor_name_from_table(table)

        return [
            f"* DB2: Converted OBTAIN {mode} {record} WITHIN {set_name}.",
            f"PERFORM OPEN-{cursor_name}.",
            f"PERFORM FETCH-{cursor_name}.",
        ], set_name

    def _convert_find_first(
        self,
        upper: str,
        stripped_line: str,
        current_division: str,
    ) -> tuple[list[str] | None, str]:
        match = FIND_FIRST_PATTERN.search(upper)

        if not match:
            return None, ""

        record = (match.group("record") or "").upper()
        set_name = match.group("set").upper()

        if current_division != "PROCEDURE":
            return [
                f"* DB2: FIND FIRST ignored outside PROCEDURE DIVISION: {stripped_line}",
            ], ""

        if not record:
            self.messages.append(
                f"FIND FIRST WITHIN {set_name} needs record inference from source code or mapping."
            )
            return [
                f"* DB2: FIND FIRST WITHIN {set_name} could not be converted because record name was not found.",
                "CONTINUE.",
            ], ""

        table = self.table_name_resolver.table_for_record(record)
        cursor_name = self.cursor_name_resolver.cursor_name_from_table(table)

        return [
            f"* DB2: Converted FIND FIRST {record} WITHIN {set_name}.",
            f"PERFORM OPEN-{cursor_name}.",
            f"PERFORM FETCH-{cursor_name}.",
        ], set_name

    def _convert_store_modify_erase(
        self,
        upper: str,
        stripped_line: str,
        current_division: str,
        sql_error_paragraph: str,
    ) -> list[str] | None:
        for pattern, operation_name, generator_method in [
            (STORE_PATTERN, "STORE", self.sql_generator.insert),
            (MODIFY_PATTERN, "MODIFY", self.sql_generator.update),
            (ERASE_PATTERN, "ERASE", self.sql_generator.delete),
        ]:
            match = pattern.search(upper)

            if not match:
                continue

            record = match.group("record").upper()

            if current_division != "PROCEDURE":
                return [
                    f"* DB2: {operation_name} ignored outside PROCEDURE DIVISION: {stripped_line}",
                ]

            return [
                f"* DB2: Converted {operation_name} for {record}.",
                *generator_method(record),
                "IF SQLCODE NOT = 0",
                f"    PERFORM {sql_error_paragraph}.",
                "END-IF.",
            ]

        return None

    def _replace_idms_condition_tokens(
        self,
        line: str,
    ) -> list[str]:
        updated = DB_REC_NOT_FOUND_TOKEN_PATTERN.sub("SQLCODE = 100", line)
        updated = DB_END_OF_SET_TOKEN_PATTERN.sub("SQLCODE = 100", updated)

        return [updated]

    def _is_idms_declarative_or_control_statement(
        self,
        upper: str,
    ) -> bool:
        return any(pattern.search(upper) for pattern in IDMS_DECLARATIVE_OR_CONTROL_PATTERNS)

    def _removed_idms_executable_lines(
        self,
        message: str,
        current_division: str,
    ) -> list[str]:
        if current_division == "PROCEDURE":
            return [
                message,
                "CONTINUE.",
            ]

        return [message]