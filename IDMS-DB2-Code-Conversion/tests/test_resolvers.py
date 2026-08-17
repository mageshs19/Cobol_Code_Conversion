from idms_db2_phase2.domain.models import DclgenColumn, SheetMappingRow
from idms_db2_phase2.repositories.dclgen_repository import DclgenRepository
from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.column_name_resolver import ColumnNameResolver
from idms_db2_phase2.resolvers.cursor_name_resolver import CursorNameResolver
from idms_db2_phase2.resolvers.host_variable_resolver import HostVariableResolver
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver


def build_repositories():
    mapping_repository = MappingRepository(
        [
            SheetMappingRow(
                cobol_record_idms="VMB-FAR",
                idms_key="CALC",
                db2_key="PRIMARY KEY",
                new_db2_record="DZBFARTB",
                new_db2_field_name="NR_ID",
            )
        ]
    )

    dclgen_repository = DclgenRepository(
        [
            DclgenColumn(
                table_name="DZBFARTV",
                column_name="NR_ID",
                cobol_host_name="NR-ID",
            )
        ]
    )

    return mapping_repository, dclgen_repository


def test_table_name_resolver_resolves_tb_to_tv():
    mapping_repository, dclgen_repository = build_repositories()

    resolver = TableNameResolver(
        mapping_repository=mapping_repository,
        dclgen_repository=dclgen_repository,
    )

    assert resolver.resolve_table("DZBFARTB") == "DZBFARTV"


def test_table_name_resolver_table_for_record():
    mapping_repository, dclgen_repository = build_repositories()

    resolver = TableNameResolver(
        mapping_repository=mapping_repository,
        dclgen_repository=dclgen_repository,
    )

    assert resolver.table_for_record("VMB-FAR") == "DZBFARTV"


def test_column_name_resolver_columns_for_record():
    mapping_repository, dclgen_repository = build_repositories()

    table_resolver = TableNameResolver(
        mapping_repository=mapping_repository,
        dclgen_repository=dclgen_repository,
    )

    column_resolver = ColumnNameResolver(
        mapping_repository=mapping_repository,
        dclgen_repository=dclgen_repository,
        table_name_resolver=table_resolver,
    )

    assert column_resolver.columns_for_record("VMB-FAR") == ["NR_ID"]


def test_host_variable_resolver_host_reference_for_column():
    mapping_repository, dclgen_repository = build_repositories()

    table_resolver = TableNameResolver(
        mapping_repository=mapping_repository,
        dclgen_repository=dclgen_repository,
    )

    host_resolver = HostVariableResolver(
        dclgen_repository=dclgen_repository,
        table_name_resolver=table_resolver,
    )

    assert host_resolver.host_reference_for_column("DZBFARTB", "NR_ID") == ":NR-ID OF DCLDZBFARTV"


def test_cursor_name_resolver_from_table():
    resolver = CursorNameResolver()

    assert resolver.cursor_name_from_table("DZBFARTV") == "DZBFARC1"