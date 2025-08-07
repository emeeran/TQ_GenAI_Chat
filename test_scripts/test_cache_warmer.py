"""
Test Suite for Cache Warming Strategies (Task 1.3.2)

Tests cache pre-population strategies for models, personas, and trending patterns.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from core.cache_warmer import CacheWarmer, WarmingConfig, WarmingStats, initialize_cache_warmer


class TestWarmingStats:
    """Test warming statistics tracking."""

    def test_stats_initialization(self):
        """Test stats object initialization."""
        stats = WarmingStats(warming_type="models")

        assert stats.warming_type == "models"
        assert stats.total_items == 0
        assert stats.successful_items == 0
        assert stats.failed_items == 0
        assert stats.total_duration == 0.0
        assert stats.started_at is not None
        assert stats.completed_at is None
        assert stats.errors == []
        assert stats.success_rate == 0.0
        assert stats.is_complete is False

    def test_stats_completion(self):
        """Test marking stats as complete."""
        stats = WarmingStats(warming_type="personas")
        stats.total_items = 10
        stats.successful_items = 8
        stats.failed_items = 2

        # Mark as complete
        stats.completed_at = datetime.now()

        assert stats.is_complete is True
        assert stats.success_rate == 80.0

    def test_stats_to_dict(self):
        """Test converting stats to dictionary."""
        stats = WarmingStats(warming_type="trending")
        stats.total_items = 5
        stats.successful_items = 5
        stats.completed_at = datetime.now()

        result = stats.to_dict()

        assert result["warming_type"] == "trending"
        assert result["total_items"] == 5
        assert result["successful_items"] == 5
        assert result["success_rate"] == 100.0
        assert result["is_complete"] is True
        assert "started_at" in result
        assert "completed_at" in result


class TestWarmingConfig:
    """Test warming configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = WarmingConfig()

        # Model warming settings
        assert config.warm_models_on_startup is True
        assert config.warm_all_providers is True
        assert config.warm_only_active_providers == []
        assert config.model_warming_timeout == 30

        # Persona warming settings
        assert config.warm_personas_on_startup is True
        assert config.persona_warming_timeout == 10

        # Background warming settings
        assert config.enable_background_warming is True
        assert config.background_warming_interval == 3600
        assert config.warm_trending_queries is True
        assert config.max_trending_cache_size == 100

        # Performance settings
        assert config.max_concurrent_warmers == 5
        assert config.warming_retry_attempts == 3
        assert config.warming_retry_delay == 1.0

        # Monitoring settings
        assert config.enable_warming_metrics is True
        assert config.metrics_retention_days == 7

    def test_custom_config(self):
        """Test custom configuration values."""
        config = WarmingConfig(
            warm_models_on_startup=False,
            warm_personas_on_startup=False,
            enable_background_warming=False,
            max_concurrent_warmers=10,
            model_warming_timeout=60,
        )

        assert config.warm_models_on_startup is False
        assert config.warm_personas_on_startup is False
        assert config.enable_background_warming is False
        assert config.max_concurrent_warmers == 10
        assert config.model_warming_timeout == 60


class TestCacheWarmer:
    """Test cache warmer functionality."""

    @pytest.fixture
    def mock_cache_manager(self):
        """Mock cache manager for testing."""
        cache_manager = Mock()
        cache_manager.set = AsyncMock()
        cache_manager.get = AsyncMock(return_value=None)
        cache_manager.exists = AsyncMock(return_value=False)
        return cache_manager

    @pytest.fixture
    def config(self):
        """Test configuration."""
        return WarmingConfig(
            warm_models_on_startup=True,
            warm_personas_on_startup=True,
            enable_background_warming=False,  # Disable for testing
            max_concurrent_warmers=2,
            model_warming_timeout=5,
            persona_warming_timeout=5,
        )

    def test_warmer_initialization(self, mock_cache_manager, config):
        """Test cache warmer initialization."""
        warmer = CacheWarmer(mock_cache_manager, config)

        assert warmer.cache_manager == mock_cache_manager
        assert warmer.config == config
        assert warmer.executor is not None
        assert warmer.is_warming is False
        assert warmer.is_background_running is False
        assert len(warmer.warming_history) == 0

    @pytest.mark.asyncio
    async def test_startup_warming(self, mock_cache_manager, config):
        """Test startup warming process."""
        warmer = CacheWarmer(mock_cache_manager, config)

        # Mock the warming methods
        with patch.object(
            warmer, "_warm_models", new_callable=AsyncMock
        ) as mock_warm_models, patch.object(
            warmer, "_warm_personas", new_callable=AsyncMock
        ) as mock_warm_personas:
            # Set up return values
            mock_warm_models.return_value = WarmingStats(warming_type="models")
            mock_warm_personas.return_value = WarmingStats(warming_type="personas")

            await warmer.start_warming()

            # Verify methods were called
            mock_warm_models.assert_called_once()
            mock_warm_personas.assert_called_once()

    @pytest.mark.asyncio
    async def test_selective_warming(self, mock_cache_manager, config):
        """Test selective warming strategies."""
        warmer = CacheWarmer(mock_cache_manager, config)

        with patch.object(
            warmer, "_warm_models", new_callable=AsyncMock
        ) as mock_warm_models, patch.object(
            warmer, "_warm_personas", new_callable=AsyncMock
        ) as mock_warm_personas, patch.object(
            warmer, "_warm_trending_patterns", new_callable=AsyncMock
        ) as mock_warm_trending:
            # Set up return values
            mock_warm_models.return_value = WarmingStats(warming_type="models")
            mock_warm_personas.return_value = WarmingStats(warming_type="personas")
            mock_warm_trending.return_value = WarmingStats(warming_type="trending")

            # Test warming only models
            await warmer.warm_cache(["models"])
            mock_warm_models.assert_called_once()
            mock_warm_personas.assert_not_called()
            mock_warm_trending.assert_not_called()

            # Reset mocks
            mock_warm_models.reset_mock()
            mock_warm_personas.reset_mock()
            mock_warm_trending.reset_mock()

            # Test warming all strategies
            await warmer.warm_cache(["models", "personas", "trending"])
            mock_warm_models.assert_called_once()
            mock_warm_personas.assert_called_once()
            mock_warm_trending.assert_called_once()

    @pytest.mark.asyncio
    async def test_model_warming(self, mock_cache_manager, config):
        """Test model metadata warming."""
        warmer = CacheWarmer(mock_cache_manager, config)

        # Mock model data
        mock_models = {
            "openai": ["gpt-4", "gpt-3.5-turbo"],
            "anthropic": ["claude-3-opus", "claude-3-sonnet"],
        }

        with patch.object(
            warmer, "_get_available_models", new_callable=AsyncMock
        ) as mock_get_models:
            mock_get_models.return_value = mock_models

            stats = await warmer._warm_models()

            assert stats.warming_type == "models"
            assert stats.total_items > 0
            assert stats.is_complete is True

    @pytest.mark.asyncio
    async def test_persona_warming(self, mock_cache_manager, config):
        """Test persona pre-loading."""
        warmer = CacheWarmer(mock_cache_manager, config)

        # Mock persona data
        mock_personas = [
            {"name": "Assistant", "prompt": "You are a helpful assistant"},
            {"name": "Coder", "prompt": "You are a coding expert"},
        ]

        with patch.object(
            warmer, "_get_available_personas", new_callable=AsyncMock
        ) as mock_get_personas:
            mock_get_personas.return_value = mock_personas

            stats = await warmer._warm_personas()

            assert stats.warming_type == "personas"
            assert stats.total_items == len(mock_personas)
            assert stats.is_complete is True

    @pytest.mark.asyncio
    async def test_trending_patterns_warming(self, mock_cache_manager, config):
        """Test trending patterns warming."""
        warmer = CacheWarmer(mock_cache_manager, config)

        # Mock trending patterns
        mock_patterns = [
            "What is machine learning?",
            "How to write Python code?",
            "Explain neural networks",
        ]

        with patch.object(
            warmer, "_get_trending_patterns", new_callable=AsyncMock
        ) as mock_get_trending:
            mock_get_trending.return_value = mock_patterns

            stats = await warmer._warm_trending_patterns()

            assert stats.warming_type == "trending"
            assert stats.total_items == len(mock_patterns)
            assert stats.is_complete is True

    @pytest.mark.asyncio
    async def test_background_warming(self, mock_cache_manager, config):
        """Test background warming process."""
        # Enable background warming for this test
        config.enable_background_warming = True
        config.background_warming_interval = 1  # 1 second for testing

        warmer = CacheWarmer(mock_cache_manager, config)

        with patch.object(warmer, "warm_cache", new_callable=AsyncMock) as mock_warm_cache:
            # Start background warming
            await warmer.start_background_warming()

            # Wait a bit for background process to run
            await asyncio.sleep(1.5)

            # Stop background warming
            await warmer.stop_background_warming()

            # Verify warm_cache was called at least once
            assert mock_warm_cache.call_count >= 1

    def test_get_warming_stats(self, mock_cache_manager, config):
        """Test getting warming statistics."""
        warmer = CacheWarmer(mock_cache_manager, config)

        # Add some mock history
        stats1 = WarmingStats(warming_type="models")
        stats1.completed_at = datetime.now()
        stats2 = WarmingStats(warming_type="personas")
        stats2.completed_at = datetime.now()

        warmer.warming_history = [stats1, stats2]

        all_stats = warmer.get_warming_stats()
        assert len(all_stats) == 2

        model_stats = warmer.get_warming_stats(warming_type="models")
        assert len(model_stats) == 1
        assert model_stats[0].warming_type == "models"

    def test_get_warming_summary(self, mock_cache_manager, config):
        """Test getting warming summary."""
        warmer = CacheWarmer(mock_cache_manager, config)

        # Add mock history
        stats = WarmingStats(warming_type="models")
        stats.total_items = 10
        stats.successful_items = 8
        stats.completed_at = datetime.now()
        warmer.warming_history = [stats]

        summary = warmer.get_warming_summary()

        assert "total_warmings" in summary
        assert "success_rate" in summary
        assert "warming_types" in summary
        assert summary["total_warmings"] == 1

    @pytest.mark.asyncio
    async def test_warming_error_handling(self, mock_cache_manager, config):
        """Test error handling during warming."""
        warmer = CacheWarmer(mock_cache_manager, config)

        # Mock a method that raises an exception
        with patch.object(warmer, "_warm_models", new_callable=AsyncMock) as mock_warm_models:
            mock_warm_models.side_effect = Exception("Test error")

            # Should not raise exception, but handle gracefully
            await warmer.warm_cache(["models"])

            # Check that error was recorded in history
            assert len(warmer.warming_history) > 0
            # Note: Specific error handling depends on implementation

    @pytest.mark.asyncio
    async def test_concurrent_warming_limit(self, mock_cache_manager, config):
        """Test concurrent warming limits."""
        config.max_concurrent_warmers = 2
        warmer = CacheWarmer(mock_cache_manager, config)

        # This test verifies that the executor is configured correctly
        # The actual concurrency limiting is handled by ThreadPoolExecutor
        assert warmer.executor._max_workers == 2


class TestInitializeFunction:
    """Test the initialize_cache_warmer function."""

    @pytest.mark.asyncio
    async def test_initialize_cache_warmer(self):
        """Test cache warmer initialization function."""
        mock_cache_manager = Mock()
        mock_cache_manager.set = AsyncMock()
        mock_cache_manager.get = AsyncMock(return_value=None)

        config = WarmingConfig(
            warm_models_on_startup=False,  # Disable for testing
            warm_personas_on_startup=False,
            enable_background_warming=False,
        )

        with patch("core.cache_warmer.CacheWarmer") as MockCacheWarmer:
            mock_warmer = Mock()
            mock_warmer.start_warming = AsyncMock()
            mock_warmer.start_background_warming = AsyncMock()
            MockCacheWarmer.return_value = mock_warmer

            result = await initialize_cache_warmer(
                cache_manager=mock_cache_manager, config=config, start_background=False
            )

            MockCacheWarmer.assert_called_once_with(mock_cache_manager, config)
            mock_warmer.start_warming.assert_called_once()
            mock_warmer.start_background_warming.assert_not_called()
            assert result == mock_warmer


class TestIntegration:
    """Integration tests for cache warming functionality."""

    @pytest.mark.asyncio
    async def test_full_warming_cycle(self):
        """Test complete warming cycle."""
        from core.hybrid_cache import HybridCache

        # Use real cache manager for integration test
        cache_manager = HybridCache()

        config = WarmingConfig(
            warm_models_on_startup=True,
            warm_personas_on_startup=True,
            enable_background_warming=False,
            max_concurrent_warmers=2,
        )

        warmer = CacheWarmer(cache_manager, config)

        # Mock external data sources
        with patch.object(
            warmer, "_get_available_models", new_callable=AsyncMock
        ) as mock_models, patch.object(
            warmer, "_get_available_personas", new_callable=AsyncMock
        ) as mock_personas:
            mock_models.return_value = {
                "openai": ["gpt-4", "gpt-3.5-turbo"],
                "anthropic": ["claude-3-opus"],
            }

            mock_personas.return_value = [
                {"name": "Assistant", "prompt": "You are helpful"},
                {"name": "Expert", "prompt": "You are an expert"},
            ]

            # Run startup warming
            await warmer.start_warming()

            # Verify warming history
            assert len(warmer.warming_history) >= 2

            # Check that models and personas strategies were executed
            warming_types = [stats.warming_type for stats in warmer.warming_history]
            assert "models" in warming_types
            assert "personas" in warming_types

            # Verify all warmings completed successfully
            for stats in warmer.warming_history:
                assert stats.is_complete is True

    @pytest.mark.asyncio
    async def test_metrics_collection(self):
        """Test warming metrics collection."""
        from core.hybrid_cache import HybridCache

        cache_manager = HybridCache()
        config = WarmingConfig(enable_warming_metrics=True)
        warmer = CacheWarmer(cache_manager, config)

        # Create some warming stats
        stats = WarmingStats(warming_type="test")
        stats.total_items = 5
        stats.successful_items = 4
        stats.failed_items = 1
        stats.completed_at = datetime.now()

        warmer.warming_history.append(stats)

        # Get summary
        summary = warmer.get_warming_summary()

        assert summary["total_warmings"] == 1
        assert summary["total_items_warmed"] == 5
        assert summary["total_successful_items"] == 4
        assert summary["total_failed_items"] == 1
        assert summary["average_success_rate"] == 80.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
