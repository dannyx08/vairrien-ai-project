from typing import Any
from urllib.parse import urlparse

import httpx
import trafilatura

from vairrien_ai.providers.search import SearchProvider
from vairrien_ai.providers.reader import ReaderProvider


class WebTool:
    """
    Native web capability for Vairrien AI.

    Provides:

    - web.search()
        Search the internet through a provider.

    - web.fetch()
        Retrieve raw webpage content directly.

    - web.read()
        Convert a webpage into model-readable content
        through the configured reader provider.

    - web.read_direct()
        Local webpage extraction fallback.

    - web.research()
        Search, select sources, read those sources, and
        return structured research context.

    The WebTool does not depend on a specific vendor.
    Search and reading providers are injected through
    provider interfaces.
    """

    def __init__(
        self,
        search_provider: SearchProvider | None = None,
        reader_provider: ReaderProvider | None = None,
    ):
        self.search_provider = search_provider
        self.reader_provider = reader_provider

    # ========================================================
    # URL VALIDATION
    # ========================================================

    @staticmethod
    def _validate_url(url: str) -> None:
        """
        Validate that a URL uses HTTP or HTTPS and
        contains a valid network location.
        """

        if not isinstance(url, str):
            raise ValueError("URL must be a string.")

        url = url.strip()

        if not url:
            raise ValueError("URL cannot be empty.")

        parsed = urlparse(url)

        if parsed.scheme not in {"http", "https"}:
            raise ValueError(
                "Only HTTP and HTTPS URLs are allowed."
            )

        if not parsed.netloc:
            raise ValueError("Invalid URL.")

    # ========================================================
    # HTTP HEADERS
    # ========================================================

    @staticmethod
    def _headers() -> dict[str, str]:
        """
        Headers used for direct webpage retrieval.
        """

        return {
            "User-Agent": (
                "Vairrien-AI/1.0 "
                "(native web capability)"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/json;q=0.9,*/*;q=0.8"
            ),
        }

    # ========================================================
    # WEB FETCH
    # ========================================================

    async def fetch(
        self,
        url: str,
        *,
        timeout: float = 20.0,
    ) -> dict[str, Any]:
        """
        Retrieve a webpage directly.

        This returns the raw HTTP response content.

        Use web.read() when model-readable content is
        preferred.
        """

        self._validate_url(url)

        if timeout <= 0:
            raise ValueError(
                "Timeout must be greater than zero."
            )

        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers=self._headers(),
        ) as client:
            response = await client.get(url)

        response.raise_for_status()

        return {
            "status": "success",
            "url": str(response.url),
            "status_code": response.status_code,
            "content_type": response.headers.get(
                "content-type",
                "",
            ),
            "content": response.text,
        }

    # ========================================================
    # PROVIDER-BASED WEBPAGE READING
    # ========================================================

    async def read(
        self,
        url: str,
    ) -> dict[str, Any]:
        """
        Read a webpage through the configured
        ReaderProvider.

        This is the preferred method for obtaining
        clean, model-readable webpage content.
        """

        self._validate_url(url)

        if self.reader_provider is None:
            return {
                "status": "unconfigured",
                "url": url,
                "content": "",
                "message": (
                    "No webpage reader provider "
                    "is configured."
                ),
            }

        result = await self.reader_provider.read(url)

        if not isinstance(result, dict):
            raise RuntimeError(
                "Reader provider returned an invalid result."
            )

        return result

    # ========================================================
    # LOCAL READ FALLBACK
    # ========================================================

    async def read_direct(
        self,
        url: str,
        *,
        timeout: float = 20.0,
    ) -> dict[str, Any]:
        """
        Retrieve a webpage directly and extract
        readable content locally.

        This provides a fallback when a reader provider
        is unavailable or fails.
        """

        fetched = await self.fetch(
            url,
            timeout=timeout,
        )

        raw_content = fetched["content"]

        extracted = trafilatura.extract(
            raw_content,
            include_comments=False,
            include_tables=True,
            include_links=True,
            favor_precision=True,
        )

        if not extracted:
            return {
                "status": "no_content",
                "url": fetched["url"],
                "status_code": fetched["status_code"],
                "content_type": fetched["content_type"],
                "content": "",
                "message": (
                    "The webpage was retrieved, "
                    "but readable content could not "
                    "be extracted."
                ),
            }

        return {
            "status": "success",
            "url": fetched["url"],
            "status_code": fetched["status_code"],
            "content_type": fetched["content_type"],
            "content": extracted,
        }

    # ========================================================
    # WEB SEARCH
    # ========================================================

    async def search(
        self,
        query: str,
        *,
        limit: int = 5,
    ) -> dict[str, Any]:
        """
        Search the internet through the configured
        SearchProvider.

        The WebTool does not know or care whether the
        provider is Jina, Tavily, Brave, Serper, or
        another implementation.
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

        if self.search_provider is None:
            return {
                "status": "unconfigured",
                "query": query,
                "results": [],
                "message": (
                    "No web search provider "
                    "is configured."
                ),
            }

        result = await self.search_provider.search(
            query,
            limit=limit,
        )

        if not isinstance(result, dict):
            raise RuntimeError(
                "Search provider returned an invalid result."
            )

        return result

    # ========================================================
    # RESULT NORMALIZATION
    # ========================================================

    @staticmethod
    def _normalize_search_results(
        results: Any,
    ) -> list[dict[str, Any]]:
        """
        Normalize provider search results into a common
        internal structure.

        Providers can return different metadata, but
        research should work with a stable format.
        """

        if not isinstance(results, list):
            return []

        normalized: list[dict[str, Any]] = []

        for result in results:
            if not isinstance(result, dict):
                continue

            url = result.get("url")

            if not isinstance(url, str):
                continue

            url = url.strip()

            if not (
                url.startswith("http://")
                or url.startswith("https://")
            ):
                continue

            title = result.get("title", "")
            snippet = result.get("snippet", "")

            content = result.get("content", "")

            if not isinstance(title, str):
                title = str(title)

            if not isinstance(snippet, str):
                snippet = str(snippet)

            if not isinstance(content, str):
                content = str(content)

            if not snippet and content:
                snippet = content[:1000]

            normalized.append(
                {
                    "title": title.strip(),
                    "url": url,
                    "snippet": snippet.strip(),
                }
            )

        return normalized

    # ========================================================
    # SOURCE READING
    # ========================================================

    async def _read_research_source(
        self,
        source: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Read one research source.

        If the configured reader provider fails, attempt
        the local direct extraction fallback.
        """

        url = source["url"]

        try:
            result = await self.read(url)

            if result.get("status") == "success":
                return {
                    "title": source.get(
                        "title",
                        "",
                    ),
                    "url": url,
                    "snippet": source.get(
                        "snippet",
                        "",
                    ),
                    "read_status": "success",
                    "content": result.get(
                        "content",
                        "",
                    ),
                }

            provider_error = result.get(
                "message",
                "Reader provider did not return content.",
            )

        except Exception as exc:
            provider_error = str(exc)

        # ----------------------------------------------------
        # LOCAL FALLBACK
        # ----------------------------------------------------

        try:
            fallback = await self.read_direct(url)

            if fallback.get("status") == "success":
                return {
                    "title": source.get(
                        "title",
                        "",
                    ),
                    "url": url,
                    "snippet": source.get(
                        "snippet",
                        "",
                    ),
                    "read_status": "success",
                    "reader": "direct_fallback",
                    "content": fallback.get(
                        "content",
                        "",
                    ),
                }

            return {
                "title": source.get(
                    "title",
                    "",
                ),
                "url": url,
                "snippet": source.get(
                    "snippet",
                    "",
                ),
                "read_status": "failed",
                "content": "",
                "error": (
                    fallback.get(
                        "message",
                        "Unable to read source.",
                    )
                ),
                "provider_error": provider_error,
            }

        except Exception as exc:
            return {
                "title": source.get(
                    "title",
                    "",
                ),
                "url": url,
                "snippet": source.get(
                    "snippet",
                    "",
                ),
                "read_status": "failed",
                "content": "",
                "error": str(exc),
                "provider_error": provider_error,
            }

    # ========================================================
    # WEB RESEARCH
    # ========================================================

    async def research(
        self,
        query: str,
        *,
        search_limit: int = 8,
        source_limit: int = 4,
    ) -> dict[str, Any]:
        """
        Perform multi-source web research.

        Workflow:

            search
                ↓
            normalize results
                ↓
            select sources
                ↓
            read sources
                ↓
            return structured evidence

        This method gathers evidence.

        It does NOT attempt to answer the user's question.
        The model/orchestrator remains responsible for
        reasoning over the collected evidence.
        """

        if not isinstance(query, str):
            raise ValueError(
                "Research query must be a string."
            )

        query = query.strip()

        if not query:
            raise ValueError(
                "Research query cannot be empty."
            )

        if search_limit < 1:
            raise ValueError(
                "Search limit must be at least 1."
            )

        if source_limit < 1:
            raise ValueError(
                "Source limit must be at least 1."
            )

        if source_limit > search_limit:
            source_limit = search_limit

        # ----------------------------------------------------
        # STEP 1: SEARCH
        # ----------------------------------------------------

        search_result = await self.search(
            query,
            limit=search_limit,
        )

        if search_result.get("status") != "success":
            return {
                "status": search_result.get(
                    "status",
                    "error",
                ),
                "query": query,
                "search": search_result,
                "source_count": 0,
                "successful_source_count": 0,
                "sources": [],
            }

        # ----------------------------------------------------
        # STEP 2: NORMALIZE SEARCH RESULTS
        # ----------------------------------------------------

        sources = self._normalize_search_results(
            search_result.get(
                "results",
                [],
            )
        )

        if not sources:
            return {
                "status": "no_sources",
                "query": query,
                "search": {
                    "status": "success",
                    "result_count": 0,
                },
                "source_count": 0,
                "successful_source_count": 0,
                "sources": [],
                "message": (
                    "Search completed, but no usable "
                    "web sources were found."
                ),
            }

        # ----------------------------------------------------
        # STEP 3: SELECT SOURCES
        # ----------------------------------------------------

        selected_sources = sources[:source_limit]

        # ----------------------------------------------------
        # STEP 4: READ SOURCES
        # ----------------------------------------------------

        researched_sources: list[dict[str, Any]] = []

        for source in selected_sources:
            researched_source = (
                await self._read_research_source(
                    source
                )
            )

            researched_sources.append(
                researched_source
            )

        successful_sources = [
            source
            for source in researched_sources
            if source.get("read_status")
            == "success"
        ]

        # ----------------------------------------------------
        # STEP 5: RETURN RESEARCH CONTEXT
        # ----------------------------------------------------

        return {
            "status": "success",
            "query": query,
            "search_result_count": len(sources),
            "source_count": len(
                researched_sources
            ),
            "successful_source_count": len(
                successful_sources
            ),
            "sources": researched_sources,
        }
