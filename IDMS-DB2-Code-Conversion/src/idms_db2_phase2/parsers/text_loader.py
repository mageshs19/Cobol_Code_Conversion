from idms_db2_phase2.infrastructure.file_loader import FileLoader


class TextLoader(FileLoader):
    """
    Backward-compatible alias for FileLoader.

    Existing UI and testing code may import TextLoader from parsers.
    Clean architecture keeps actual file loading in infrastructure.
    """

    pass