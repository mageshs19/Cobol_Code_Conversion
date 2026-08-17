from pathlib import Path


class LocalUploadedFile:
    """
    Local file wrapper.

    Existing parser flow expects uploaded-file-like objects with:
    - .name
    - .getvalue()

    This wrapper allows local runner scripts to reuse the same parser logic
    used by the Streamlit file uploader flow.
    """

    def __init__(
        self,
        file_path: Path,
    ) -> None:
        self.file_path = Path(file_path)
        self.name = self.file_path.name

    def getvalue(
        self,
    ) -> bytes:
        return self.file_path.read_bytes()