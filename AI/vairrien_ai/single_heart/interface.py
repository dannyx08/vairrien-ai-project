from abc import ABC, abstractmethod
from typing import Any


class SingleHeartInterface(ABC):
    """
    Interface between Vairrien AI and the Single Heart subsystem.

    The internal implementation remains independent from
    the AI orchestration layer.
    """

    @abstractmethod
    async def process(
        self,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> Any:
        """
        Process information through Single Heart.
        """
        raise NotImplementedError

    async def health(self) -> bool:
        """
        Report whether Single Heart is available.
        """
        return True