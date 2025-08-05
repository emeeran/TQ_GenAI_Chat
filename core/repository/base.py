"""Base repository interface"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseRepository(ABC):
    """Abstract base repository"""
    
    @abstractmethod
    def save(self, data: Dict[str, Any]) -> str:
        """Save data and return ID"""
        pass
    
    @abstractmethod
    def find_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """Find by ID"""
        pass
    
    @abstractmethod
    def find_all(self) -> List[Dict[str, Any]]:
        """Find all records"""
        pass
    
    @abstractmethod
    def delete(self, id: str) -> bool:
        """Delete by ID"""
        pass
