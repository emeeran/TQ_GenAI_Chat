"""
Cache Warming Strategies Implementation

This module provides intelligent cache pre-population strategies to improve
application performance by loading frequently accessed data before user requests.

Key Features:
- Model metadata pre-caching from all active providers
- Persona pre-loading for instant access
- Background cache warming based on usage patterns
- Configurable warming strategies and schedules
- Comprehensive warming metrics and monitoring

Author: TQ GenAI Chat
Created: 2025-08-07
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from core.cache_integration import ChatCacheManager

# Internal imports


@dataclass
class WarmingStats:
    """Track cache warming statistics"""

    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    total_items: int = 0
    successful_items: int = 0
    failed_items: int = 0
    total_duration: float = 0.0
    warming_type: str = "unknown"
    errors: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_items == 0:
            return 0.0
        return (self.successful_items / self.total_items) * 100

    @property
    def is_complete(self) -> bool:
        """Check if warming is complete"""
        return self.completed_at is not None

    def to_dict(self) -> dict:
        """Convert stats to dictionary for serialization"""
        return {
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_items": self.total_items,
            "successful_items": self.successful_items,
            "failed_items": self.failed_items,
            "total_duration": self.total_duration,
            "warming_type": self.warming_type,
            "success_rate": self.success_rate,
            "is_complete": self.is_complete,
            "errors": self.errors,
        }


@dataclass
class WarmingConfig:
    """Configuration for cache warming strategies"""

    # Model warming settings
    warm_models_on_startup: bool = True
    warm_all_providers: bool = True
    warm_only_active_providers: list[str] = field(default_factory=list)
    model_warming_timeout: int = 30

    # Persona warming settings
    warm_personas_on_startup: bool = True
    persona_warming_timeout: int = 10

    # Background warming settings
    enable_background_warming: bool = True
    background_warming_interval: int = 3600  # 1 hour
    warm_trending_queries: bool = True
    max_trending_cache_size: int = 100

    # Performance settings
    max_concurrent_warmers: int = 5
    warming_retry_attempts: int = 3
    warming_retry_delay: float = 1.0

    # Monitoring settings
    enable_warming_metrics: bool = True
    metrics_retention_days: int = 7


class CacheWarmer:
    """
    Advanced cache warming system with multiple strategies

    Provides intelligent cache pre-population for:
    - Model metadata from AI providers
    - Persona definitions
    - Frequently accessed chat patterns
    - Document search results
    """

    def __init__(
        self,
        cache_manager: ChatCacheManager,
        config: Optional[WarmingConfig] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.cache_manager = cache_manager
        self.config = config or WarmingConfig()
        self.logger = logger or logging.getLogger(__name__)

        # Warming state
        self.warming_stats: dict[str, WarmingStats] = {}
        self.is_warming: bool = False
        self.background_task: Optional[asyncio.Task] = None
        self.warming_executor = ThreadPoolExecutor(
            max_workers=self.config.max_concurrent_warmers, thread_name_prefix="cache_warmer"
        )

        # Trending patterns tracking
        self.query_patterns: dict[str, int] = {}
        self.last_pattern_analysis = datetime.now()

        self.logger.info("CacheWarmer initialized with config: %s", self.config.__dict__)

    async def start_warming(
        self, strategies: Optional[list[str]] = None
    ) -> dict[str, WarmingStats]:
        """
        Start cache warming with specified strategies

        Args:
            strategies: List of warming strategies to execute.
                       Options: ['models', 'personas', 'trending', 'all']
                       Defaults to ['models', 'personas'] if not specified

        Returns:
            Dictionary of warming statistics by strategy
        """
        if self.is_warming:
            self.logger.warning("Cache warming already in progress")
            return self.warming_stats

        # Default strategies
        if strategies is None:
            strategies = []
            if self.config.warm_models_on_startup:
                strategies.append("models")
            if self.config.warm_personas_on_startup:
                strategies.append("personas")

        # Handle 'all' strategy
        if "all" in strategies:
            strategies = ["models", "personas", "trending"]

        self.is_warming = True
        self.warming_stats.clear()

        try:
            # Create warming tasks
            warming_tasks = []

            if "models" in strategies:
                warming_tasks.append(self._warm_models())

            if "personas" in strategies:
                warming_tasks.append(self._warm_personas())

            if "trending" in strategies:
                warming_tasks.append(self._warm_trending_patterns())

            # Execute warming strategies concurrently
            if warming_tasks:
                self.logger.info("Starting cache warming with strategies: %s", strategies)
                await asyncio.gather(*warming_tasks, return_exceptions=True)

            self.logger.info(
                "Cache warming completed. Stats: %s",
                {k: v.success_rate for k, v in self.warming_stats.items()},
            )

        except Exception as e:
            self.logger.error("Cache warming failed: %s", str(e))
        finally:
            self.is_warming = False

        return self.warming_stats

    async def _warm_models(self) -> WarmingStats:
        """Warm cache with model metadata from all providers"""
        stats = WarmingStats(warming_type="models")
        self.warming_stats["models"] = stats

        try:
            # Get available providers
            providers = await self._get_active_providers()
            stats.total_items = len(providers)

            self.logger.info("Warming models for %d providers: %s", len(providers), providers)

            # Warm each provider's models
            for provider in providers:
                try:
                    # Use cache manager to load models (this will cache them)
                    models = await self.cache_manager.get_models(provider)

                    if models and len(models) > 0:
                        stats.successful_items += 1
                        self.logger.debug(
                            "Warmed models for provider %s: %d models", provider, len(models)
                        )
                    else:
                        stats.failed_items += 1
                        stats.errors.append(f"No models found for provider: {provider}")

                except Exception as e:
                    stats.failed_items += 1
                    error_msg = f"Failed to warm models for {provider}: {str(e)}"
                    stats.errors.append(error_msg)
                    self.logger.warning(error_msg)

        except Exception as e:
            stats.errors.append(f"Model warming failed: {str(e)}")
            self.logger.error("Model warming failed: %s", str(e))

        finally:
            stats.completed_at = datetime.now()
            stats.total_duration = (stats.completed_at - stats.started_at).total_seconds()

        return stats

    async def _warm_personas(self) -> WarmingStats:
        """Warm cache with all available personas"""
        stats = WarmingStats(warming_type="personas")
        self.warming_stats["personas"] = stats

        try:
            # Get available personas
            personas = await self._get_available_personas()
            stats.total_items = len(personas)

            self.logger.info("Warming %d personas: %s", len(personas), personas)

            # Warm each persona
            for persona_name in personas:
                try:
                    # Import personas directly and cache them
                    import os
                    import sys

                    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

                    from persona import PERSONAS

                    if persona_name in PERSONAS:
                        persona_content = PERSONAS[persona_name]
                        # Cache the persona using cache manager
                        success = await self.cache_manager.set_persona(
                            persona_content, persona_name
                        )

                        if success:
                            stats.successful_items += 1
                            self.logger.debug("Warmed persona: %s", persona_name)
                        else:
                            stats.failed_items += 1
                            stats.errors.append(f"Failed to cache persona: {persona_name}")
                    else:
                        stats.failed_items += 1
                        stats.errors.append(f"Persona not found: {persona_name}")

                except Exception as e:
                    stats.failed_items += 1
                    error_msg = f"Failed to warm persona {persona_name}: {str(e)}"
                    stats.errors.append(error_msg)
                    self.logger.warning(error_msg)

        except Exception as e:
            stats.errors.append(f"Persona warming failed: {str(e)}")
            self.logger.error("Persona warming failed: %s", str(e))

        finally:
            stats.completed_at = datetime.now()
            stats.total_duration = (stats.completed_at - stats.started_at).total_seconds()

        return stats

    async def _warm_trending_patterns(self) -> WarmingStats:
        """Warm cache with trending query patterns"""
        stats = WarmingStats(warming_type="trending")
        self.warming_stats["trending"] = stats

        try:
            # Get trending patterns
            trending_patterns = await self._analyze_trending_patterns()
            stats.total_items = len(trending_patterns)

            if not trending_patterns:
                self.logger.info("No trending patterns found for cache warming")
                stats.completed_at = datetime.now()
                stats.total_duration = (stats.completed_at - stats.started_at).total_seconds()
                return stats

            self.logger.info("Warming %d trending patterns", len(trending_patterns))

            # Pre-warm trending patterns
            for pattern in trending_patterns:
                try:
                    # Simulate cache warming for trending queries
                    await self._warm_pattern(pattern)
                    stats.successful_items += 1

                except Exception as e:
                    stats.failed_items += 1
                    error_msg = f"Failed to warm pattern {pattern}: {str(e)}"
                    stats.errors.append(error_msg)
                    self.logger.warning(error_msg)

        except Exception as e:
            stats.errors.append(f"Trending pattern warming failed: {str(e)}")
            self.logger.error("Trending pattern warming failed: %s", str(e))

        finally:
            stats.completed_at = datetime.now()
            stats.total_duration = (stats.completed_at - stats.started_at).total_seconds()

        return stats

    async def start_background_warming(self) -> bool:
        """Start background cache warming task"""
        if not self.config.enable_background_warming:
            self.logger.info("Background cache warming is disabled")
            return False

        if self.background_task and not self.background_task.done():
            self.logger.warning("Background warming task already running")
            return False

        self.background_task = asyncio.create_task(self._background_warming_loop())
        self.logger.info(
            "Started background cache warming with %ds interval",
            self.config.background_warming_interval,
        )
        return True

    async def stop_background_warming(self) -> bool:
        """Stop background cache warming task"""
        if self.background_task and not self.background_task.done():
            self.background_task.cancel()
            try:
                await self.background_task
            except asyncio.CancelledError:
                pass
            self.logger.info("Stopped background cache warming")
            return True
        return False

    async def _background_warming_loop(self):
        """Background task for periodic cache warming"""
        try:
            while True:
                await asyncio.sleep(self.config.background_warming_interval)

                if self.is_warming:
                    self.logger.debug("Skipping background warming - manual warming in progress")
                    continue

                self.logger.debug("Starting background cache warming")
                await self.start_warming(["trending"])

        except asyncio.CancelledError:
            self.logger.info("Background warming loop cancelled")
            raise
        except Exception as e:
            self.logger.error("Background warming loop error: %s", str(e))

    async def get_warming_stats(self) -> dict[str, dict]:
        """Get comprehensive warming statistics"""
        return {
            "warming_active": self.is_warming,
            "background_warming_enabled": self.config.enable_background_warming,
            "background_task_running": (
                self.background_task is not None and not self.background_task.done()
            ),
            "current_stats": {name: stats.to_dict() for name, stats in self.warming_stats.items()},
            "config": {
                "warm_models_on_startup": self.config.warm_models_on_startup,
                "warm_personas_on_startup": self.config.warm_personas_on_startup,
                "enable_background_warming": self.config.enable_background_warming,
                "background_warming_interval": self.config.background_warming_interval,
                "max_concurrent_warmers": self.config.max_concurrent_warmers,
            },
            "trending_patterns": len(self.query_patterns),
        }

    async def record_query_pattern(self, query_hash: str, provider: str, model: str):
        """Record a query pattern for trending analysis"""
        if not self.config.warm_trending_queries:
            return

        pattern_key = f"{provider}_{model}_{query_hash[:16]}"
        self.query_patterns[pattern_key] = self.query_patterns.get(pattern_key, 0) + 1

        # Limit pattern storage
        if len(self.query_patterns) > self.config.max_trending_cache_size:
            # Keep only top patterns
            sorted_patterns = sorted(self.query_patterns.items(), key=lambda x: x[1], reverse=True)
            self.query_patterns = dict(sorted_patterns[: self.config.max_trending_cache_size])

    # Helper methods

    async def _get_active_providers(self) -> list[str]:
        """Get list of active providers for warming"""
        # Default providers that typically have API keys configured
        default_providers = [
            "openai",
            "anthropic",
            "groq",
            "xai",
            "mistral",
            "openrouter",
            "together",
            "perplexity",
            "cohere",
            "gemini",
        ]

        if self.config.warm_only_active_providers:
            return self.config.warm_only_active_providers

        return default_providers

    async def _get_available_personas(self) -> list[str]:
        """Get list of available personas for warming"""
        # Get actual personas from persona.py
        try:
            import os
            import sys

            sys.path.append(os.path.dirname(os.path.dirname(__file__)))

            from persona import PERSONAS

            return list(PERSONAS.keys())
        except ImportError:
            # Fallback personas if import fails
            return [
                "helpful_assistant",
                "code_expert",
                "medical_doctor",
                "pharmacist",
                "teacher",
                "therapist",
                "student",
                "researcher",
            ]

    async def _analyze_trending_patterns(self) -> list[str]:
        """Analyze trending query patterns"""
        if not self.query_patterns:
            return []

        # Get top trending patterns
        trending_threshold = 2  # Pattern must appear at least 2 times
        trending_patterns = [
            pattern for pattern, count in self.query_patterns.items() if count >= trending_threshold
        ]

        # Sort by usage count
        trending_patterns.sort(key=lambda p: self.query_patterns.get(p, 0), reverse=True)

        return trending_patterns[:20]  # Top 20 trending patterns

    async def _warm_pattern(self, pattern: str):
        """Warm a specific query pattern"""
        # This is a placeholder for pattern-specific warming
        # In a real implementation, this would reconstruct and cache
        # common query types based on the pattern
        await asyncio.sleep(0.1)  # Simulate warming work

    def __del__(self):
        """Cleanup resources"""
        try:
            if hasattr(self, "warming_executor"):
                self.warming_executor.shutdown(wait=False)
        except Exception:
            pass


async def initialize_cache_warmer(
    cache_manager: ChatCacheManager,
    config: Optional[WarmingConfig] = None,
    start_background: bool = True,
) -> CacheWarmer:
    """
    Initialize and start cache warmer

    Args:
        cache_manager: Cache manager instance
        config: Warming configuration (optional)
        start_background: Whether to start background warming

    Returns:
        Initialized and started CacheWarmer instance
    """
    warmer = CacheWarmer(cache_manager, config)

    # Start initial warming
    await warmer.start_warming()

    # Start background warming if requested
    if start_background:
        await warmer.start_background_warming()

    return warmer


# Export main components
__all__ = ["CacheWarmer", "WarmingConfig", "WarmingStats", "initialize_cache_warmer"]
