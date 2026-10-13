from abc import ABC, abstractmethod
from typing import Any


class SearchProvider(ABC):
    """
    Abstract interface for Vairrien web search providers.

    Vairrien depends on this interface, not on a specific
    search service such as Tavily, Brave, or Serper.
    """

    @abstractmethod
    async def search(
        self,
        query: str,
        *,
        limit: int = 5,
    ) -> dict[str, Any]:
        """
        Search the web and return normalized results.
        """
        raise NotImplementedError