"""
Centralized Provider Service
Eliminates duplicate provider/model management logic across multiple files.
"""

import logging
from typing import Dict, List, Optional

from core.providers.async_factory import AsyncProviderFactory
from core.model_utils import DEFAULT_MODELS

logger = logging.getLogger(__name__)


class ProviderService:
    """
    Centralized service for provider and model management.
    
    Replaces duplicate logic in:
    - app/api/models.py (multiple routes)
    - app/web/views.py
    - blueprints/chat.py
    """

    def __init__(self):
        self._factory = None
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes

    @property
    async def factory(self) -> AsyncProviderFactory:
        """Lazy-load provider factory"""
        if self._factory is None:
            self._factory = AsyncProviderFactory()
        return self._factory

    async def get_available_providers(self) -> List[str]:
        """
        Get list of available providers.

        Returns:
            List of provider names that have valid API keys or cached models
        """
        # Get providers from AsyncProviderFactory
        factory = await self.factory
        factory_providers = set(factory.get_available_providers())

        # Get all providers that have models in model_manager
        from core.models import model_manager
        all_providers = set(model_manager.get_all_models().keys())

        # Combine both sets to ensure comprehensive coverage
        all_available_providers = sorted(list(factory_providers.union(all_providers)))

        logger.info(f"Available providers: {len(all_available_providers)} total "
                   f"({len(factory_providers)} from factory, {len(all_providers - factory_providers)} from cache)")

        return all_available_providers

    async def get_models_for_provider(
        self, provider: str, force_refresh: bool = False
    ) -> Dict:
        """
        Get available models for a specific provider.

        Args:
            provider: Provider name (e.g., 'openai', 'anthropic')
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            Dictionary with provider, models list, default model, and metadata
        """
        cache_key = f"models_{provider}"

        # Check cache unless force refresh
        if not force_refresh and cache_key in self._cache:
            logger.info(f"Returning cached models for {provider}")
            return self._cache[cache_key]

        try:
            # Try to get models from AsyncProviderFactory first
            factory = await self.factory
            models = await factory.get_models_for_provider(provider)

            if not models:
                # Fallback to cached model_manager data when provider fetching fails
                logger.info(f"Provider {provider} not available in AsyncProviderFactory, falling back to cached data")
                from core.models import model_manager

                models = model_manager.get_models(provider)

                if not models:
                    logger.warning(f"No models available for {provider}")
                    return {
                        "provider": provider,
                        "models": [],
                        "default": None,
                        "count": 0,
                        "error": f"No models available for {provider}",
                        "is_dynamic": False,
                    }

            # Get default model for provider
            from core.models import model_manager
            default_model = model_manager.get_default_model(provider)
            if not default_model:
                default_model = DEFAULT_MODELS.get(provider.lower())

            # Categorize models
            preview_models = [m for m in models if "preview" in m.lower()]
            stable_models = [m for m in models if "preview" not in m.lower()]

            result = {
                "provider": provider,
                "models": models,
                "default": default_model,
                "count": len(models),
                "preview_models": preview_models,
                "stable_models": stable_models,
                "preview_count": len(preview_models),
                "stable_count": len(stable_models),
                "has_preview_models": len(preview_models) > 0,
                "is_dynamic": True,
            }

            # Cache result
            self._cache[cache_key] = result
            logger.info(
                f"Retrieved {len(models)} models for {provider} "
                f"({len(stable_models)} stable, {len(preview_models)} preview)"
            )

            return result

        except Exception as e:
            logger.error(f"Error getting models for {provider}: {e}", exc_info=True)

            # Final fallback to model_manager cached data
            try:
                from core.models import model_manager
                models = model_manager.get_models(provider)
                default_model = model_manager.get_default_model(provider)

                if models:
                    logger.info(f"Successfully fell back to cached data for {provider}: {len(models)} models")

                    preview_models = [m for m in models if "preview" in m.lower()]
                    stable_models = [m for m in models if "preview" not in m.lower()]

                    result = {
                        "provider": provider,
                        "models": models,
                        "default": default_model,
                        "count": len(models),
                        "preview_models": preview_models,
                        "stable_models": stable_models,
                        "preview_count": len(preview_models),
                        "stable_count": len(stable_models),
                        "has_preview_models": len(preview_models) > 0,
                        "is_dynamic": False,  # Using cached data
                        "fallback_used": True,
                    }

                    # Cache the fallback result
                    self._cache[cache_key] = result
                    return result

            except Exception as fallback_error:
                logger.error(f"Fallback to cached data also failed for {provider}: {fallback_error}")

            return {
                "provider": provider,
                "models": [],
                "default": None,
                "count": 0,
                "error": f"Failed to get models for {provider}: {str(e)}",
                "is_dynamic": False,
            }

    async def update_models_from_api(self, provider: str) -> Dict:
        """
        Refresh models for a provider by fetching from their API.
        
        Args:
            provider: Provider name
            
        Returns:
            Dictionary with updated models and metadata
        """
        try:
            # Import here to avoid circular dependencies
            from scripts.update_models_from_providers import fetch_provider_models

            logger.info(f"Fetching latest models from {provider} API...")
            new_models = fetch_provider_models(provider)

            if not new_models:
                raise ValueError(f"Failed to fetch models from {provider} API")

            # Update cache
            cache_key = f"models_{provider}"
            if cache_key in self._cache:
                del self._cache[cache_key]

            # Get fresh data with new models
            result = await self.get_models_for_provider(provider, force_refresh=True)
            result["message"] = (
                f"Successfully updated {len(new_models)} models for {provider}"
            )
            result["success"] = True

            logger.info(f"Successfully updated {len(new_models)} models for {provider}")
            return result

        except Exception as e:
            logger.error(f"Error updating models for {provider}: {e}", exc_info=True)
            return {
                "success": False,
                "provider": provider,
                "error": f"Failed to update models: {str(e)}",
                "models": [],
            }

    async def get_all_models(self) -> Dict[str, List[str]]:
        """
        Get all models grouped by provider.
        
        Returns:
            Dictionary mapping provider names to their model lists
        """
        try:
            factory = await self.factory
            providers = factory.get_available_providers()

            all_models = {}
            for provider in providers:
                result = await self.get_models_for_provider(provider)
                all_models[provider] = result.get("models", [])

            return all_models

        except Exception as e:
            logger.error(f"Error getting all models: {e}", exc_info=True)
            return {}

    async def update_all_models(self) -> Dict:
        """
        Update models for all providers.
        
        Returns:
            Dictionary with update results for each provider
        """
        try:
            providers = await self.get_available_providers()
            results = {}

            for provider in providers:
                result = await self.update_models_from_api(provider)
                results[provider] = result

            # Calculate summary
            total_models = sum(
                r.get("count", 0) for r in results.values() if "count" in r
            )
            providers_with_errors = [
                p for p, r in results.items() if "error" in r or not r.get("success")
            ]

            return {
                "success": True,
                "message": f"Updated models for {len(providers)} providers",
                "providers": results,
                "summary": {
                    "total_providers": len(providers),
                    "total_models": total_models,
                    "providers_with_errors": providers_with_errors,
                    "error_count": len(providers_with_errors),
                },
            }

        except Exception as e:
            logger.error(f"Error updating all models: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "providers": {},
            }

    def clear_cache(self, provider: Optional[str] = None):
        """
        Clear cached model data.
        
        Args:
            provider: If specified, clear cache for this provider only.
                     If None, clear all cache.
        """
        if provider:
            cache_key = f"models_{provider}"
            if cache_key in self._cache:
                del self._cache[cache_key]
                logger.info(f"Cleared cache for {provider}")
        else:
            self._cache.clear()
            logger.info("Cleared all provider cache")


# Singleton instance
_provider_service = None


def get_provider_service() -> ProviderService:
    """Get or create the singleton ProviderService instance"""
    global _provider_service
    if _provider_service is None:
        _provider_service = ProviderService()
    return _provider_service
