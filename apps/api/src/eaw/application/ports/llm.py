"""LLM chat completion port."""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ChatMessage:
    role: str  # system | user | assistant
    content: str


@dataclass
class LLMResult:
    content: str
    model: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    raw: dict[str, Any] = field(default_factory=dict)


class LLMPort(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str:
        ...

    @abstractmethod
    def complete(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResult:
        ...

    @abstractmethod
    def stream(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> Iterator[str]:
        """Yield text deltas."""
