from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ModelProvider(ABC):
    """
    Hardware-independent interface between Vairrien AI
    and the model runtime.
    """

    @abstractmethod
    async def generate(
        self,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Generate a structured response from the model.

        The response may contain:
        - text content
        - tool calls
        - usage information
        - provider metadata
        """
        raise NotImplementedError

    async def health(self) -> bool:
        """
        Return whether the model provider is reachable.
        """
        return True