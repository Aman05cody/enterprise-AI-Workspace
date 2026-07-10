"""Email port."""

from abc import ABC, abstractmethod


class EmailPort(ABC):
    @abstractmethod
    def send(self, *, to: str, subject: str, body: str) -> None:
        raise NotImplementedError
