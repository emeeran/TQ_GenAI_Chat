"""Service container for dependency injection"""

from typing import Any, TypeVar

from core.context import ContextManager
from core.providers import ProviderFactory

from .chat_service import ChatService

T = TypeVar("T")


class ServiceContainer:
    """Simple dependency injection container"""

    def __init__(self):
        self._services: dict[str, Any] = {}
        self._singletons: dict[str, Any] = {}
        self._initialize_core_services()

    def _initialize_core_services(self):
        """Initialize core services"""
        # Register factory functions
        self.register("provider_factory", lambda: ProviderFactory())
        self.register("context_manager", lambda: ContextManager())
        self.register("cache_manager", lambda: self._create_cache_manager())
        self.register(
            "chat_service",
            lambda: ChatService(self.get("provider_factory"), self.get("context_manager")),
        )

    def _create_cache_manager(self):
        """Create cache manager instance"""
        from core.cache import CacheManager

        return CacheManager()

    def register(self, name: str, factory_func):
        """Register a service factory function"""
        self._services[name] = factory_func

    def get(self, name: str) -> Any:
        """Get service instance (singleton pattern)"""
        if name not in self._singletons:
            if name not in self._services:
                raise ValueError(f"Service {name} not registered")
            self._singletons[name] = self._services[name]()
        return self._singletons[name]

    def clear(self):
        """Clear all singleton instances"""
        self._singletons.clear()


# Global service container instance
container = ServiceContainer()


def get_service(name: str) -> Any:
    """Get service from global container"""
    return container.get(name)
