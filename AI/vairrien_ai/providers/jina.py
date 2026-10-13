import asyncio
import os
import re
import subprocess
from typing import Any
from urllib.parse import quote

from dotenv import load_dotenv

from vairrien_ai.providers.search import SearchProvider


load_dotenv()


class JinaSearchProvider(SearchProvider):
    """
    Jina-powered web search provider for Vairrien.

    Converts Jina's search response into normalized
    source records that Vairrien's WebTool can consume.
    """

    SEARCH_URL = "https://s.jina.ai/"

    def __init__(
        self,
        api_key: str | None = None,
    ):
        self.api_key = (
            api_key
            or os.getenv("JINA_API_KEY")
        )

        if not self.api_key:
            raise ValueError(
                "JINA_API_KEY is not configured."
            )

    async def search(
        self,
        query: str,
        *,
        limit: int = 5,
    ) -> dict[str, Any]:
        """
        Search the web through Jina.
        """

        if not isinstance(query, str):
            raise ValueError(
                "Search query must be a string."
            )

        query = query.strip()

        if not query:
            raise ValueError(
                "Search query cannot be empty."
            )

        if limit < 1:
            raise ValueError(
                "Search limit must be at least 1."
            )

        return await asyncio.to_thread(
            self._search_with_curl,
            query,
            limit,
        )

    # =========================================================
    # JINA REQUEST
    # =========================================================

    def _search_with_curl(
        self,
        query: str,
        limit: int,
    ) -> dict[str, Any]:

        encoded_query = quote(
            query,
            safe="",
        )

        url = (
            f"{self.SEARCH_URL}"
            f"{encoded_query}"
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
                url,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        if result.returncode != 0:
            raise RuntimeError(
                "Jina search failed: "
                f"{result.stderr.strip()}"
            )

        content = result.stdout.strip()

        if not content:
            raise RuntimeError(
                "Jina search returned an empty response."
            )

        results = self._parse_results(
            content,
            limit,
        )

        return {
            "status": "success",
            "query": query,
            "results": results,
            "raw_content": content,
        }

    # =========================================================
    # RESULT PARSING
    # =========================================================

    @staticmethod
    def _parse_results(
        content: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """
        Parse Jina's plain-text/Markdown search response.

        Typical Jina output:

            [1] Title: Python (programming language)
            [1] URL Source: https://example.com
            [1] Description: ...
            [1] Published Time: ...

            [2] Title: ...
            [2] URL Source: https://example.org
            [2] Description: ...

        The parser intentionally focuses on the stable URL Source
        markers and treats title/description as optional metadata.
        """

        results: list[dict[str, Any]] = []

        # -----------------------------------------------------
        # Split the response into source blocks.
        # -----------------------------------------------------

        blocks = re.split(
            r"(?m)(?=^\[\d+\]\s*Title:)",
            content,
        )

        for block in blocks:

            if len(results) >= limit:
                break

            block = block.strip()

            if not block:
                continue

            # -------------------------------------------------
            # Extract title.
            # -------------------------------------------------

            title_match = re.search(
                r"(?m)^\[\d+\]\s*Title:\s*(.+?)\s*$",
                block,
            )

            title = (
                title_match.group(1).strip()
                if title_match
                else ""
            )

            # -------------------------------------------------
            # Extract URL.
            # -------------------------------------------------

            url_match = re.search(
                r"(?m)^\[\d+\]\s*URL Source:\s*(https?://\S+)",
                block,
            )

            if not url_match:
                continue

            url = url_match.group(1).strip()

            # Remove punctuation accidentally attached
            # to the URL.
            url = url.rstrip(
                ".,);]"
            )

            if not url.startswith(
                (
                    "http://",
                    "https://",
                )
            ):
                continue

            # -------------------------------------------------
            # Extract description.
            # -------------------------------------------------

            description_match = re.search(
                r"(?ms)^\[\d+\]\s*Description:\s*(.*?)(?=^\[\d+\]\s*(?:Published Time|Title|URL Source):|\Z)",
                block,
            )

            description = (
                description_match.group(1).strip()
                if description_match
                else ""
            )

            results.append(
                {
                    "title": title,
                    "url": url,
                    "snippet": description,
                }
            )

        # -----------------------------------------------------
        # Fallback: extract every URL Source directly.
        # -----------------------------------------------------

        if not results:

            url_matches = re.findall(
                r"(?m)^\[\d+\]\s*URL Source:\s*(https?://\S+)",
                content,
            )

            for source_url in url_matches:

                if len(results) >= limit:
                    break

                source_url = source_url.strip().rstrip(
                    ".,);]"
                )

                if not source_url.startswith(
                    (
                        "http://",
                        "https://",
                    )
                ):
                    continue

                results.append(
                    {
                        "title": "",
                        "url": source_url,
                        "snippet": "",
                    }
                )

        return results