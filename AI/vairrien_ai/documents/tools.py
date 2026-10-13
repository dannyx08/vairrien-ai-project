from __future__ import annotations

from pathlib import Path
from typing import Any

from vairrien_ai.documents.extractor import DocumentExtractor


class DocumentTool:
    """
    Vairrien document tool.

    Provides the AI tool layer with access to the
    DocumentExtractor without coupling extraction
    logic to the orchestrator.
    """

    def __init__(
        self,
        extractor: DocumentExtractor | None = None,
    ):
        self.extractor = extractor or DocumentExtractor()

    async def extract(
        self,
        file_path: str,
    ) -> dict[str, Any]:
        """
        Extract a supported document.

        The file path is resolved and validated before
        being passed to the extraction layer.
        """

        if not file_path or not file_path.strip():
            return {
                "status": "error",
                "error": "No file path was provided.",
            }

        path = Path(file_path).expanduser()

        if not path.exists():
            return {
                "status": "error",
                "error": "File does not exist.",
                "file_path": str(path),
            }

        if not path.is_file():
            return {
                "status": "error",
                "error": "The provided path is not a file.",
                "file_path": str(path),
            }

        result = await self.extractor.extract(path)

        return result