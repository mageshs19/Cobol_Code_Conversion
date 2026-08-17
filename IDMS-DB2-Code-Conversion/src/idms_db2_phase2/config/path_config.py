"""
Path settings for local command-line runs.

These paths are intentionally centralized here instead of being embedded in
runner, parser, or conversion logic.

Update these values for your local environment.
"""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


SRC_DIR = PROJECT_ROOT / "src"


LOGS_DIR = PROJECT_ROOT / "logs"


DEFAULT_INPUT_DIR = Path(r"C:\S\S-Input")


DEFAULT_OUTPUT_DIR = DEFAULT_INPUT_DIR / "Output"


DEFAULT_SHEET_MAPPING_PATH = DEFAULT_INPUT_DIR / "Excel_Sheet_mapping.csv"


DEFAULT_RETRIEVAL_SOURCE_PATH = DEFAULT_INPUT_DIR / "Retrieval.txt"


DEFAULT_UPDATE_SOURCE_PATH = DEFAULT_INPUT_DIR / "Update.txt"


DEFAULT_DCLGEN_CANDIDATE_PATHS = [
    DEFAULT_INPUT_DIR / "DCLGENS_BEFF.txt",
    DEFAULT_INPUT_DIR / "DCLGENS_BFAR.txt",
    DEFAULT_INPUT_DIR / "DCLGENS_EVEF.txt",
]


DEFAULT_COPYBOOK_CANDIDATE_PATHS = [
    DEFAULT_INPUT_DIR / "Copybook.txt",
]