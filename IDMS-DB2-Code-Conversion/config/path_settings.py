"""
Path settings for local command-line runs.

Update these values for your local machine.

This file is intentionally separate from parser, transformer, generator,
and orchestration logic so file paths are not hardcoded inside business logic.
"""

from pathlib import Path


# ---------------------------------------------------------------------------
# Project folders
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SRC_DIR = PROJECT_ROOT / "src"

LOGS_DIR = PROJECT_ROOT / "logs"


# ---------------------------------------------------------------------------
# Default local input/output folders
# ---------------------------------------------------------------------------
# Change this folder if your input files are stored somewhere else.
#
# Expected default layout:
#
# C:\S\S-Input
# ├── Excel_Sheet_mapping.csv
# ├── Retrieval.txt
# ├── Update.txt
# ├── DCLGENS_BEFF.txt
# ├── DCLGENS_BFAR.txt
# ├── DCLGENS_EVEF.txt
# └── Output
#
# ---------------------------------------------------------------------------

DEFAULT_INPUT_DIR = Path(r"C:\S\S-Input")

DEFAULT_OUTPUT_DIR = DEFAULT_INPUT_DIR / "Output"


# ---------------------------------------------------------------------------
# Required input files
# ---------------------------------------------------------------------------

DEFAULT_SHEET_MAPPING_PATH = DEFAULT_INPUT_DIR / "Excel_Sheet_mapping.csv"

DEFAULT_RETRIEVAL_SOURCE_PATH = DEFAULT_INPUT_DIR / "Retrieval.txt"

DEFAULT_UPDATE_SOURCE_PATH = DEFAULT_INPUT_DIR / "Update.txt"


# ---------------------------------------------------------------------------
# DCLGEN candidate files
# ---------------------------------------------------------------------------
# The runner will load only files that actually exist.
# Add more DCLGEN files here if needed.
# ---------------------------------------------------------------------------

DEFAULT_DCLGEN_CANDIDATE_PATHS = [
    DEFAULT_INPUT_DIR / "DCLGENS_BEFF.txt",
    DEFAULT_INPUT_DIR / "DCLGENS_BFAR.txt",
    DEFAULT_INPUT_DIR / "DCLGENS_EVEF.txt",
]


# ---------------------------------------------------------------------------
# Optional copybook candidate files
# ---------------------------------------------------------------------------
# The runner will load only files that actually exist.
# Copybook is optional.
# ---------------------------------------------------------------------------

DEFAULT_COPYBOOK_CANDIDATE_PATHS = [
    DEFAULT_INPUT_DIR / "Copybook.txt",
]


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def existing_files(
    paths: list[Path],
) -> list[Path]:
    """
    Return only paths that exist and are files.
    """

    return [
        path
        for path in paths
        if path.exists() and path.is_file()
    ]


def ensure_output_dir() -> None:
    """
    Ensure the default output directory exists.
    """

    DEFAULT_OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )