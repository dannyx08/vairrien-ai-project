import asyncio
import os
import subprocess
from typing import Any

from dotenv import load_dotenv


load_dotenv()


class ReaderProvider:
    """
    Abstract-style interface for webpage readers.

    Vairrien uses this layer instead of depending directly
    on a specific webpage-reading service.
    """

    async def read(
        self,
        url: str,
    ) -> dict[str, Any]:
        raise NotImplementedError


class JinaReaderProvider(ReaderProvider):
    """
    Jina-powered webpage reader for Vairrien AI.

    Uses Jina Reader to convert webpages into clean,
    model-readable content.
    """

    READER_URL = "https://r.jina.ai/"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("JINA_API_KEY")

        if not self.api_key:
            raise ValueError(
                "JINA_API_KEY is not configured."
            )

    async def read(
        self,
        url: str,
    ) -> dict[str, Any]:

        if not url.strip():
            raise ValueError(
                "URL cannot be empty."
            )

        if not (
            url.startswith("http://")
            or url.startswith("https://")
        ):
            raise ValueError(
                "Only HTTP and HTTPS URLs are supported."
            )

        return await asyncio.to_thread(
            self._read_with_curl,
            url,
        )

    def _read_with_curl(
        self,
        url: str,
    ) -> dict[str, Any]:

        reader_url = (
            f"{self.READER_URL}{url}"
        )

        result = subprocess.run(
            [
                "curl.exe",
                "-L",
                "--max-time",
                "60",
                "-sS",
                "-H",
                f"Authorization: Bearer {self.api_key}",
                reader_url,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        if result.returncode != 0:
            raise RuntimeError(
                "Jina Reader failed: "
                f"{result.stderr.strip()}"
            )

        content = result.stdout.strip()

        if not content:
            raise RuntimeError(
                "Jina Reader returned empty content."
            )

        return {
            "status": "success",
            "url": url,
            "content": content,
        }