from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RuntimeContext:
    """
    Runtime context for local executions.

    Keep runtime paths outside parser and service logic.
    Parser and service classes should receive data, not know where the files
    came from.
    """

    project_root: Path
    input_dir: Path
    output_dir: Path
    sheet_mapping_path: Path | None = None
    dclgen_paths: list[Path] = field(default_factory=list)
    copybook_paths: list[Path] = field(default_factory=list)
    idms_cobol_source_path: Path | None = None
    target_program_id: str = ""
    auto_fix_pic_length_mismatches: bool = False

    def ensure_output_dir(
        self,
    ) -> None:
        self.output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    def validate_required_files(
        self,
    ) -> None:
        if self.sheet_mapping_path is None:
            raise ValueError("Sheet Mapping path is required.")

        if self.idms_cobol_source_path is None:
            raise ValueError("IDMS COBOL source path is required.")

        self._validate_file_exists(
            self.sheet_mapping_path,
            "Sheet Mapping",
        )

        self._validate_file_exists(
            self.idms_cobol_source_path,
            "IDMS COBOL Source",
        )

        if not self.dclgen_paths:
            raise ValueError("At least one DCLGEN file path is required.")

        for index, dclgen_path in enumerate(self.dclgen_paths, start=1):
            self._validate_file_exists(
                dclgen_path,
                f"DCLGEN {index}",
            )

        for index, copybook_path in enumerate(self.copybook_paths, start=1):
            self._validate_file_exists(
                copybook_path,
                f"Copybook {index}",
            )

        self.ensure_output_dir()

    def _validate_file_exists(
        self,
        file_path: Path,
        label: str,
    ) -> None:
        if not file_path.exists():
            raise FileNotFoundError(f"{label} file not found: {file_path}")

        if not file_path.is_file():
            raise FileNotFoundError(f"{label} path is not a file: {file_path}")