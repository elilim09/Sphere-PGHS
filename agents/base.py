from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """Abstract base class for all agents.

    Agents expose asynchronous ``handle`` methods that execute the actual
    business logic. For now the method simply returns placeholder data.
    """

    name: str

    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    async def handle(self, *args: Any, **kwargs: Any) -> Any:
        """Process a request and return a result."""

