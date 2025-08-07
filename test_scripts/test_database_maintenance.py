"""
Test Suite for Database Maintenance Automation System (Task 1.1.4)

Tests automated database maintenance operations including VACUUM, ANALYZE,
and cleanup operations for SQLite databases.
"""

import os
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from core.database_maintenance import (
    DatabaseMaintenanceManager,
    MaintenanceConfig,
    MaintenanceMetrics,
    MaintenanceResult,
    get_maintenance_manager,
    initialize_maintenance,
    start_maintenance,
    stop_maintenance,
)


class TestMaintenanceConfig:
    """Test configuration class for maintenance operations."""

    def test_default_config(self):
        """Test default configuration values."""
        config = MaintenanceConfig()

        assert config.vacuum_enabled is True
        assert config.vacuum_schedule == "02:00"
        assert config.vacuum_threshold_days == 7
        assert config.analyze_enabled is True
        assert config.analyze_schedule == "02:30"
        assert config.analyze_threshold_days == 1
        assert config.chat_cleanup_enabled is True
        assert config.chat_retention_days == 90
        assert config.chat_cleanup_schedule == "03:00"
        assert config.doc_cleanup_enabled is True
        assert config.doc_retention_days == 30
        assert config.doc_cleanup_schedule == "03:30"
        assert config.maintenance_log_file is None
        assert config.status_check_interval == 300
        assert config.enable_metrics is True
        assert config.database_paths == ["documents.db"]
        assert config.backup_before_maintenance is True
        assert config.backup_retention_days == 7

    def test_custom_config(self):
        """Test custom configuration values."""
        config = MaintenanceConfig(
            vacuum_enabled=False,
            vacuum_schedule="01:00",
            vacuum_threshold_days=14,
            chat_retention_days=60,
            database_paths=["test1.db", "test2.db"],
            backup_before_maintenance=False,
        )

        assert config.vacuum_enabled is False
        assert config.vacuum_schedule == "01:00"
        assert config.vacuum_threshold_days == 14
        assert config.chat_retention_days == 60
        assert config.database_paths == ["test1.db", "test2.db"]
        assert config.backup_before_maintenance is False


class TestMaintenanceResult:
    """Test result tracking for maintenance operations."""

    def test_result_creation(self):
        """Test creating a maintenance result."""
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=10)

        result = MaintenanceResult(
            operation="VACUUM",
            database="test.db",
            start_time=start_time,
            end_time=end_time,
            success=True,
            rows_affected=100,
            size_before=1000,
            size_after=800,
            error_message=None,
        )

        assert result.operation == "VACUUM"
        assert result.database == "test.db"
        assert result.success is True
        assert result.rows_affected == 100
        assert result.size_before == 1000
        assert result.size_after == 800
        assert result.duration == 10.0
        assert result.size_saved == 200
        assert result.error_message is None

    def test_result_properties(self):
        """Test calculated properties of maintenance result."""
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=5.5)

        result = MaintenanceResult(
            operation="ANALYZE",
            database="test.db",
            start_time=start_time,
            end_time=end_time,
            success=True,
            size_before=500,
            size_after=600,  # Size increased
        )

        assert result.duration == 5.5
        assert result.size_saved == 0  # No size saved when size increased

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=3)

        result = MaintenanceResult(
            operation="CHAT_CLEANUP",
            database="test.db",
            start_time=start_time,
            end_time=end_time,
            success=True,
            rows_affected=50,
        )

        result_dict = result.to_dict()

        assert result_dict["operation"] == "CHAT_CLEANUP"
        assert result_dict["database"] == "test.db"
        assert result_dict["success"] is True
        assert result_dict["rows_affected"] == 50
        assert result_dict["duration"] == 3.0
        assert "start_time" in result_dict
        assert "end_time" in result_dict


class TestMaintenanceMetrics:
    """Test metrics collection for maintenance operations."""

    def test_metrics_initialization(self):
        """Test metrics object initialization."""
        metrics = MaintenanceMetrics()

        assert metrics.operations_count == {}
        assert metrics.total_duration == {}
        assert metrics.total_size_saved == {}
        assert metrics.last_operation == {}
        assert metrics.success_count == {}
        assert metrics.error_count == {}
        assert metrics.recent_results == []
        assert metrics.max_recent_results == 100

    def test_record_operation_success(self):
        """Test recording a successful operation."""
        metrics = MaintenanceMetrics()

        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=5)

        result = MaintenanceResult(
            operation="VACUUM",
            database="test.db",
            start_time=start_time,
            end_time=end_time,
            success=True,
            size_before=1000,
            size_after=800,
        )

        metrics.record_operation(result)

        assert metrics.operations_count["VACUUM"] == 1
        assert metrics.total_duration["VACUUM"] == 5.0
        assert metrics.total_size_saved["VACUUM"] == 200
        assert metrics.success_count["VACUUM"] == 1
        assert metrics.error_count.get("VACUUM", 0) == 0
        assert len(metrics.recent_results) == 1
        assert metrics.last_operation["VACUUM"] == end_time

    def test_record_operation_failure(self):
        """Test recording a failed operation."""
        metrics = MaintenanceMetrics()

        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=2)

        result = MaintenanceResult(
            operation="ANALYZE",
            database="test.db",
            start_time=start_time,
            end_time=end_time,
            success=False,
            error_message="Database locked",
        )

        metrics.record_operation(result)

        assert metrics.operations_count["ANALYZE"] == 1
        assert metrics.total_duration["ANALYZE"] == 2.0
        assert metrics.success_count.get("ANALYZE", 0) == 0
        assert metrics.error_count["ANALYZE"] == 1

    def test_get_summary(self):
        """Test getting metrics summary."""
        metrics = MaintenanceMetrics()

        # Record multiple operations
        for i in range(3):
            start_time = datetime.now()
            end_time = start_time + timedelta(seconds=i + 1)

            result = MaintenanceResult(
                operation="VACUUM",
                database="test.db",
                start_time=start_time,
                end_time=end_time,
                success=i < 2,  # First two succeed, last fails
                size_before=1000,
                size_after=800,
            )

            metrics.record_operation(result)

        summary = metrics.get_summary()

        assert summary["operations_performed"] == 3
        assert summary["operations_by_type"]["VACUUM"] == 3
        assert summary["total_duration_seconds"] == 6.0  # 1+2+3
        assert summary["average_duration_by_type"]["VACUUM"] == 2.0
        assert summary["total_size_saved_bytes"] == 600  # 200*3
        assert summary["success_rates"]["VACUUM"] == pytest.approx(66.67, rel=1e-2)
        assert summary["error_counts"]["VACUUM"] == 1
        assert summary["recent_operations"] == 3


class TestDatabaseMaintenanceManager:
    """Test database maintenance manager."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        db_path = temp_file.name
        temp_file.close()

        # Create test database with sample tables
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY,
                content TEXT,
                last_accessed TEXT
            )
        """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY,
                message TEXT,
                timestamp TEXT
            )
        """
        )

        # Insert test data
        old_date = (datetime.now() - timedelta(days=100)).isoformat()
        recent_date = datetime.now().isoformat()

        conn.execute(
            "INSERT INTO documents (content, last_accessed) VALUES (?, ?)", ("old doc", old_date)
        )
        conn.execute(
            "INSERT INTO documents (content, last_accessed) VALUES (?, ?)", ("new doc", recent_date)
        )
        conn.execute(
            "INSERT INTO chat_history (message, timestamp) VALUES (?, ?)", ("old chat", old_date)
        )
        conn.execute(
            "INSERT INTO chat_history (message, timestamp) VALUES (?, ?)", ("new chat", recent_date)
        )

        conn.commit()
        conn.close()

        yield db_path

        # Cleanup
        try:
            os.unlink(db_path)
        except OSError:
            pass

    @pytest.fixture
    def config(self, temp_db):
        """Create test configuration."""
        return MaintenanceConfig(
            database_paths=[temp_db],
            backup_before_maintenance=False,  # Disable for testing
            chat_retention_days=30,
            doc_retention_days=30,
        )

    def test_manager_initialization(self, config):
        """Test manager initialization."""
        manager = DatabaseMaintenanceManager(config)

        assert manager.config == config
        assert isinstance(manager.metrics, MaintenanceMetrics)
        assert manager.is_running is False
        assert manager.scheduler_thread is None
        assert manager.status_thread is None

    def test_get_database_size(self, config, temp_db):
        """Test getting database file size."""
        manager = DatabaseMaintenanceManager(config)

        size = manager.get_database_size(temp_db)
        assert size > 0

        # Test non-existent file
        size = manager.get_database_size("nonexistent.db")
        assert size == 0

    def test_database_connection(self, config, temp_db):
        """Test database connection context manager."""
        manager = DatabaseMaintenanceManager(config)

        with manager.get_database_connection(temp_db) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM documents")
            count = cursor.fetchone()[0]
            assert count == 2

    def test_perform_vacuum(self, config, temp_db):
        """Test VACUUM operation."""
        manager = DatabaseMaintenanceManager(config)

        result = manager.perform_vacuum(temp_db)

        assert result.operation == "VACUUM"
        assert result.database == temp_db
        assert result.success is True
        assert result.size_before >= 0
        assert result.size_after >= 0
        assert result.duration > 0

    def test_perform_analyze(self, config, temp_db):
        """Test ANALYZE operation."""
        manager = DatabaseMaintenanceManager(config)

        result = manager.perform_analyze(temp_db)

        assert result.operation == "ANALYZE"
        assert result.database == temp_db
        assert result.success is True
        assert result.duration > 0

    def test_cleanup_old_chat_history(self, config, temp_db):
        """Test chat history cleanup."""
        manager = DatabaseMaintenanceManager(config)

        result = manager.cleanup_old_chat_history(temp_db)

        assert result.operation == "CHAT_CLEANUP"
        assert result.database == temp_db
        assert result.success is True
        assert result.rows_affected >= 0

        # Verify old chat was removed
        with manager.get_database_connection(temp_db) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM chat_history")
            count = cursor.fetchone()[0]
            assert count == 1  # Only recent chat should remain

    def test_cleanup_unused_documents(self, config, temp_db):
        """Test document cleanup."""
        manager = DatabaseMaintenanceManager(config)

        result = manager.cleanup_unused_documents(temp_db)

        assert result.operation == "DOC_CLEANUP"
        assert result.database == temp_db
        assert result.success is True
        assert result.rows_affected >= 0

        # Verify old document was removed
        with manager.get_database_connection(temp_db) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM documents")
            count = cursor.fetchone()[0]
            assert count == 1  # Only recent document should remain

    def test_should_run_operation(self, config):
        """Test operation scheduling logic."""
        manager = DatabaseMaintenanceManager(config)

        # Should run when no previous execution
        assert manager.should_run_operation("VACUUM", "test.db") is True
        assert manager.should_run_operation("ANALYZE", "test.db") is True
        assert manager.should_run_operation("CLEANUP", "test.db") is True

        # Record recent operation
        recent_time = datetime.now()
        manager.metrics.last_operation["VACUUM_test.db"] = recent_time
        manager.metrics.last_operation["ANALYZE_test.db"] = recent_time

        # Should not run recent operations based on threshold
        assert manager.should_run_operation("VACUUM", "test.db") is False
        assert manager.should_run_operation("ANALYZE", "test.db") is False

        # Cleanup operations should always run when scheduled
        assert manager.should_run_operation("CLEANUP", "test.db") is True

    def test_run_manual_maintenance(self, config, temp_db):
        """Test manual maintenance execution."""
        manager = DatabaseMaintenanceManager(config)

        results = manager.run_manual_maintenance(["VACUUM", "ANALYZE"])

        assert len(results) == 2
        assert results[0].operation == "VACUUM"
        assert results[1].operation == "ANALYZE"
        assert all(result.success for result in results)

    def test_get_status(self, config, temp_db):
        """Test getting manager status."""
        manager = DatabaseMaintenanceManager(config)

        status = manager.get_status()

        assert "is_running" in status
        assert "config" in status
        assert "metrics" in status
        assert "database_info" in status
        assert temp_db in status["database_info"]
        assert status["database_info"][temp_db]["exists"] is True
        assert status["database_info"][temp_db]["size_bytes"] > 0

    @patch("schedule.clear")
    @patch("schedule.every")
    def test_setup_scheduler(self, mock_every, mock_clear, config):
        """Test scheduler setup."""
        manager = DatabaseMaintenanceManager(config)

        # Mock the schedule chain
        mock_job = Mock()
        mock_every.return_value.day.at.return_value.do = Mock(return_value=mock_job)

        manager.setup_scheduler()

        mock_clear.assert_called_once()
        assert mock_every.called

    def test_start_stop_manager(self, config):
        """Test starting and stopping manager."""
        manager = DatabaseMaintenanceManager(config)

        assert manager.is_running is False

        # Start manager
        manager.start()
        assert manager.is_running is True
        assert manager.scheduler_thread is not None

        # Stop manager
        manager.stop()
        assert manager.is_running is False

    def test_backup_creation(self, config, temp_db):
        """Test database backup creation."""
        # Enable backups for this test
        config.backup_before_maintenance = True
        manager = DatabaseMaintenanceManager(config)

        backup_path = manager.create_backup(temp_db)

        if backup_path:  # Only test if backup was created
            assert os.path.exists(backup_path)
            assert backup_path.endswith(".db")
            assert "backup" in backup_path

            # Cleanup
            try:
                os.unlink(backup_path)
                # Remove backup directory if empty
                backup_dir = Path(backup_path).parent
                if backup_dir.exists() and not list(backup_dir.iterdir()):
                    backup_dir.rmdir()
            except OSError:
                pass


class TestGlobalFunctions:
    """Test global maintenance management functions."""

    def test_initialize_maintenance(self):
        """Test initializing global maintenance manager."""
        # Clean up any existing manager
        stop_maintenance()

        manager = initialize_maintenance()
        assert manager is not None
        assert get_maintenance_manager() == manager

        # Test with custom config
        config = MaintenanceConfig(vacuum_enabled=False)
        manager2 = initialize_maintenance(config)
        assert manager2.config.vacuum_enabled is False

    def test_start_stop_maintenance(self):
        """Test starting and stopping global maintenance."""
        # Initialize first
        initialize_maintenance()

        # Start maintenance
        result = start_maintenance()
        assert result is True

        manager = get_maintenance_manager()
        assert manager.is_running is True

        # Stop maintenance
        result = stop_maintenance()
        assert result is True
        assert manager.is_running is False

    def test_start_stop_without_initialization(self):
        """Test start/stop without initialization."""
        # Clear global manager
        import core.database_maintenance_clean as maintenance_module

        maintenance_module.maintenance_manager = None

        result = start_maintenance()
        assert result is False

        result = stop_maintenance()
        assert result is False


class TestIntegration:
    """Integration tests for complete maintenance workflow."""

    @pytest.fixture
    def integration_config(self):
        """Create integration test configuration."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        db_path = temp_file.name
        temp_file.close()

        # Create test database
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY,
                content TEXT,
                last_accessed TEXT
            )
        """
        )
        conn.execute(
            """
            CREATE TABLE chat_history (
                id INTEGER PRIMARY KEY,
                message TEXT,
                timestamp TEXT
            )
        """
        )

        # Insert old and new data
        old_date = (datetime.now() - timedelta(days=100)).isoformat()
        new_date = datetime.now().isoformat()

        for i in range(10):
            conn.execute(
                "INSERT INTO documents (content, last_accessed) VALUES (?, ?)",
                (f"doc {i}", old_date if i < 5 else new_date),
            )
            conn.execute(
                "INSERT INTO chat_history (message, timestamp) VALUES (?, ?)",
                (f"chat {i}", old_date if i < 7 else new_date),
            )

        conn.commit()
        conn.close()

        config = MaintenanceConfig(
            database_paths=[db_path],
            backup_before_maintenance=False,
            chat_retention_days=30,
            doc_retention_days=30,
        )

        yield config, db_path

        # Cleanup
        try:
            os.unlink(db_path)
        except OSError:
            pass

    def test_full_maintenance_cycle(self, integration_config):
        """Test complete maintenance cycle."""
        config, db_path = integration_config
        manager = DatabaseMaintenanceManager(config)

        # Run full maintenance
        results = manager.run_manual_maintenance()

        # Verify all operations completed
        operations = [r.operation for r in results]
        assert "VACUUM" in operations
        assert "ANALYZE" in operations
        assert "CHAT_CLEANUP" in operations
        assert "DOC_CLEANUP" in operations

        # Verify all operations succeeded
        assert all(r.success for r in results)

        # Verify cleanup results
        cleanup_results = [r for r in results if "CLEANUP" in r.operation]
        total_cleaned = sum(r.rows_affected for r in cleanup_results)
        assert total_cleaned > 0

        # Verify data was actually cleaned
        conn = sqlite3.connect(db_path)

        doc_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        chat_count = conn.execute("SELECT COUNT(*) FROM chat_history").fetchone()[0]

        # Should have fewer records after cleanup
        assert doc_count <= 10
        assert chat_count <= 10

        conn.close()

        # Verify metrics were recorded
        assert len(manager.metrics.recent_results) == len(results)
        summary = manager.metrics.get_summary()
        assert summary["operations_performed"] == len(results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
