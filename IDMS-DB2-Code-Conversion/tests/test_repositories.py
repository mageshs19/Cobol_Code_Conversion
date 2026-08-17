from idms_db2_phase2.domain.models import CopybookField, DclgenColumn, SheetMappingRow
from idms_db2_phase2.repositories.copybook_repository import CopybookRepository
from idms_db2_phase2.repositories.dclgen_repository import DclgenRepository
from idms_db2_phase2.repositories.mapping_repository import MappingRepository


def test_mapping_repository_returns_records():
    repository = MappingRepository(
        [
            SheetMappingRow(
                cobol_record_idms="VMB-FAR",
                new_db2_record="DZBFARTB",
                new_db2_field_name="NR_ID",
            )
        ]
    )

    assert repository.records() == ["VMB_FAR"]


def test_mapping_repository_finds_rows_for_record():
    repository = MappingRepository(
        [
            SheetMappingRow(
                cobol_record_idms="VMB-FAR",
                new_db2_record="DZBFARTB",
                new_db2_field_name="NR_ID",
            )
        ]
    )

    rows = repository.rows_for_record("VMB-FAR")

    assert len(rows) == 1
    assert rows[0].new_db2_record == "DZBFARTB"


def test_mapping_repository_returns_table_for_record():
    repository = MappingRepository(
        [
            SheetMappingRow(
                cobol_record_idms="VMB-FAR",
                new_db2_record="DZBFARTB",
            )
        ]
    )

    assert repository.db2_table_for_record("VMB-FAR") == "DZBFARTB"


def test_dclgen_repository_has_table():
    repository = DclgenRepository(
        [
            DclgenColumn(
                table_name="DZBFARTV",
                column_name="NR_ID",
                cobol_host_name="NR-ID",
            )
        ]
    )

    assert repository.has_table("DZBFARTV")


def test_dclgen_repository_host_for_column():
    repository = DclgenRepository(
        [
            DclgenColumn(
                table_name="DZBFARTV",
                column_name="NR_ID",
                cobol_host_name="NR-ID",
            )
        ]
    )

    assert repository.host_for_column("DZBFARTV", "NR_ID") == "NR-ID"


def test_copybook_repository_finds_field():
    repository = CopybookRepository(
        [
            CopybookField(
                level="10",
                name="NR-ID",
                picture="9(8)",
            )
        ]
    )

    assert repository.has_field("NR-ID")
    assert repository.picture_for("NR-ID") == "9(8)"