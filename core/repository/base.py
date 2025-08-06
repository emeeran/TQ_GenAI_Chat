"""Base repository interface"""

from abc import ABC, abstractmethod
from typing import Any


class BaseRepository(ABC):
    """Abstract base repository"""

    @abstractmethod
    def save(self, data: dict[str, Any]) -> str:
        """Save data and return ID"""
        pass

    @abstractmethod
    def find_by_id(self, id: str) -> dict[str, Any] | None:
        """Find by ID"""
        pass

    @abstractmethod
    def find_all(self) -> list[dict[str, Any]]:
        """Find all records"""
        pass

    @abstractmethod
    def delete(self, id: str) -> bool:
        """Delete by ID"""
        pass
