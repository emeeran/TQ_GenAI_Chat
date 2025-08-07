"""
Database Maintenance Automation System (Task 1.1.4)

This module implements automated database maintenance operations including
VACUUM, ANALYZE, and cleanup operations for SQLite databases.
"""

import logging
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import schedule

logger = logging.getLogger(__name__)


@dataclass
class MaintenanceConfig:
    """Configuration for database maintenance operations."""

    # VACUUM operations
    vacuum_enabled: bool = True
    vacuum_schedule: str = "02:00"  # Daily at 2 AM
    vacuum_threshold_days: int = 7  # VACUUM if not done in X days

    # ANALYZE operations
    analyze_enabled: bool = True
    analyze_schedule: str = "02:30"  # Daily at 2:30 AM
    analyze_threshold_days: int = 1  # ANALYZE if not done in X days

    # Chat history cleanup
    chat_cleanup_enabled: bool = True
    chat_retention_days: int = 90  # Keep chat history for X days
    chat_cleanup_schedule: str = "03:00"  # Daily at 3 AM

    # Document cleanup
    doc_cleanup_enabled: bool = True
    doc_retention_days: int = 30  # Remove unused documents after X days
    doc_cleanup_schedule: str = "03:30"  # Daily at 3:30 AM

    # Monitoring and logging
    maintenance_log_file: str | None = None
    status_check_interval: int = 300  # Check status every 5 minutes
    enable_metrics: bool = True

    # Database settings
    database_paths: list[str] = field(default_factory=lambda: ["documents.db"])
    backup_before_maintenance: bool = True
    backup_retention_days: int = 7


@dataclass
class MaintenanceResult:
    """Result of a maintenance operation."""

    operation: str
    database: str
    start_time: datetime
    end_time: datetime
    success: bool
    rows_affected: int = 0
    size_before: int = 0
    size_after: int = 0
    error_message: str | None = None

    @property
    def duration(self) -> float:
        """Duration of operation in seconds."""
        return (self.end_time - self.start_time).total_seconds()

    @property
    def size_saved(self) -> int:
        """Bytes saved by the operation."""
        return max(0, self.size_before - self.size_after)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "operation": self.operation,
            "database": self.database,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration": self.duration,
            "success": self.success,
            "rows_affected": self.rows_affected,
            "size_before": self.size_before,
            "size_after": self.size_after,
            "size_saved": self.size_saved,
            "error_message": self.error_message,
        }


class MaintenanceMetrics:
    """Metrics collection for maintenance operations."""

    def __init__(self):
        self.operations_count: dict[str, int] = {}
        self.total_duration: dict[str, float] = {}
        self.total_size_saved: dict[str, int] = {}
        self.last_operation: dict[str, datetime] = {}
        self.success_count: dict[str, int] = {}
        self.error_count: dict[str, int] = {}
        self.recent_results: list[MaintenanceResult] = []
        self.max_recent_results = 100

    def record_operation(self, result: MaintenanceResult):
        """Record a maintenance operation result."""
        op = result.operation

        # Update counters
        self.operations_count[op] = self.operations_count.get(op, 0) + 1
        self.total_duration[op] = self.total_duration.get(op, 0) + result.duration
        self.total_size_saved[op] = self.total_size_saved.get(op, 0) + result.size_saved
        self.last_operation[op] = result.end_time

        if result.success:
            self.success_count[op] = self.success_count.get(op, 0) + 1
        else:
            self.error_count[op] = self.error_count.get(op, 0) + 1

        # Store recent results
        self.recent_results.append(result)
        if len(self.recent_results) > self.max_recent_results:
            self.recent_results.pop(0)

        logger.info(f"Recorded maintenance operation: {op} on {result.database}")

    def get_summary(self) -> dict[str, Any]:
        """Get summary of maintenance metrics."""
        return {
            "operations_performed": sum(self.operations_count.values()),
            "operations_by_type": dict(self.operations_count),
            "total_duration_seconds": sum(self.total_duration.values()),
            "average_duration_by_type": {
                op: self.total_duration[op] / self.operations_count[op]
                for op in self.operations_count
                if self.operations_count[op] > 0
            },
            "total_size_saved_bytes": sum(self.total_size_saved.values()),
            "size_saved_by_type": dict(self.total_size_saved),
            "last_operation_times": {op: dt.isoformat() for op, dt in self.last_operation.items()},
            "success_rates": {
                op: (self.success_count.get(op, 0) / self.operations_count[op]) * 100
                for op in self.operations_count
                if self.operations_count[op] > 0
            },
            "error_counts": dict(self.error_count),
            "recent_operations": len(self.recent_results),
        }


class DatabaseMaintenanceManager:
    """Manages automated database maintenance operations."""

    def __init__(self, config: MaintenanceConfig):
        self.config = config
        self.metrics = MaintenanceMetrics()
        self.is_running = False
        self.scheduler_thread: threading.Thread | None = None
        self.status_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        # Setup logging
        if config.maintenance_log_file:
            self._setup_maintenance_logging()

        logger.info("Database Maintenance Manager initialized")

    def _setup_maintenance_logging(self):
        """Setup dedicated logging for maintenance operations."""
        maintenance_logger = logging.getLogger("maintenance")
        handler = logging.FileHandler(self.config.maintenance_log_file)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        maintenance_logger.addHandler(handler)
        maintenance_logger.setLevel(logging.INFO)

    @contextmanager
    def get_database_connection(self, db_path: str):
        """Get database connection with proper configuration."""
        conn = None
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("PRAGMA busy_timeout = 30000")  # 30 second timeout
            yield conn
        except Exception as e:
            logger.error(f"Database connection error for {db_path}: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def get_database_size(self, db_path: str) -> int:
        """Get database file size in bytes."""
        try:
            return os.path.getsize(db_path)
        except OSError:
            return 0

    def create_backup(self, db_path: str) -> str | None:
        """Create backup of database before maintenance."""
        if not self.config.backup_before_maintenance:
            return None

        try:
            backup_dir = Path(db_path).parent / "backups"
            backup_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{Path(db_path).stem}_backup_{timestamp}.db"
            backup_path = backup_dir / backup_name

            # Create backup using SQLite backup API
            with self.get_database_connection(db_path) as source_conn:
                backup_conn = sqlite3.connect(str(backup_path))
                source_conn.backup(backup_conn)
                backup_conn.close()

            logger.info(f"Created backup: {backup_path}")
            return str(backup_path)

        except Exception as e:
            logger.error(f"Failed to create backup for {db_path}: {e}")
            return None

    def cleanup_old_backups(self):
        """Remove old backup files."""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.config.backup_retention_days)

            for db_path in self.config.database_paths:
                backup_dir = Path(db_path).parent / "backups"
                if not backup_dir.exists():
                    continue

                for backup_file in backup_dir.glob("*_backup_*.db"):
                    if backup_file.stat().st_mtime < cutoff_date.timestamp():
                        backup_file.unlink()
                        logger.info(f"Removed old backup: {backup_file}")

        except Exception as e:
            logger.error(f"Error cleaning up old backups: {e}")

    def perform_vacuum(self, db_path: str) -> MaintenanceResult:
        """Perform VACUUM operation on database."""
        start_time = datetime.now()
        size_before = self.get_database_size(db_path)

        result = MaintenanceResult(
            operation="VACUUM",
            database=db_path,
            start_time=start_time,
            end_time=start_time,  # Will be updated
            success=False,
            size_before=size_before,
        )

        try:
            # Create backup if configured
            backup_path = self.create_backup(db_path)

            with self.get_database_connection(db_path) as conn:
                # Check if VACUUM is needed
                cursor = conn.execute("PRAGMA freelist_count")
                free_pages = cursor.fetchone()[0]

                if free_pages > 0:
                    logger.info(f"Starting VACUUM on {db_path} ({free_pages} free pages)")
                    conn.execute("VACUUM")
                    conn.commit()

                    result.success = True
                    logger.info(f"VACUUM completed on {db_path}")
                else:
                    logger.info(f"VACUUM skipped for {db_path} (no free pages)")
                    result.success = True

        except Exception as e:
            result.error_message = str(e)
            logger.error(f"VACUUM failed on {db_path}: {e}")

        finally:
            result.end_time = datetime.now()
            result.size_after = self.get_database_size(db_path)
            self.metrics.record_operation(result)

        return result

    def perform_analyze(self, db_path: str) -> MaintenanceResult:
        """Perform ANALYZE operation on database."""
        start_time = datetime.now()

        result = MaintenanceResult(
            operation="ANALYZE",
            database=db_path,
            start_time=start_time,
            end_time=start_time,
            success=False,
        )

        try:
            with self.get_database_connection(db_path) as conn:
                logger.info(f"Starting ANALYZE on {db_path}")
                conn.execute("ANALYZE")
                conn.commit()

                result.success = True
                logger.info(f"ANALYZE completed on {db_path}")

        except Exception as e:
            result.error_message = str(e)
            logger.error(f"ANALYZE failed on {db_path}: {e}")

        finally:
            result.end_time = datetime.now()
            self.metrics.record_operation(result)

        return result

    def cleanup_old_chat_history(self, db_path: str) -> MaintenanceResult:
        """Remove old chat history records."""
        start_time = datetime.now()
        cutoff_date = datetime.now() - timedelta(days=self.config.chat_retention_days)

        result = MaintenanceResult(
            operation="CHAT_CLEANUP",
            database=db_path,
            start_time=start_time,
            end_time=start_time,
            success=False,
        )

        try:
            with self.get_database_connection(db_path) as conn:
                # Delete old chat history
                cursor = conn.execute(
                    "DELETE FROM chat_history WHERE timestamp < ?", (cutoff_date.isoformat(),)
                )
                rows_deleted = cursor.rowcount
                conn.commit()

                result.success = True
                result.rows_affected = rows_deleted
                logger.info(f"Cleaned up {rows_deleted} old chat records from {db_path}")

        except Exception as e:
            result.error_message = str(e)
            logger.error(f"Chat cleanup failed on {db_path}: {e}")

        finally:
            result.end_time = datetime.now()
            self.metrics.record_operation(result)

        return result

    def cleanup_unused_documents(self, db_path: str) -> MaintenanceResult:
        """Remove unused document records."""
        start_time = datetime.now()
        cutoff_date = datetime.now() - timedelta(days=self.config.doc_retention_days)

        result = MaintenanceResult(
            operation="DOC_CLEANUP",
            database=db_path,
            start_time=start_time,
            end_time=start_time,
            success=False,
        )

        try:
            with self.get_database_connection(db_path) as conn:
                # Find documents not accessed recently
                cursor = conn.execute(
                    """
                    DELETE FROM documents
                    WHERE last_accessed < ?
                    AND last_accessed IS NOT NULL
                """,
                    (cutoff_date.isoformat(),),
                )

                rows_deleted = cursor.rowcount
                conn.commit()

                result.success = True
                result.rows_affected = rows_deleted
                logger.info(f"Cleaned up {rows_deleted} unused documents from {db_path}")

        except Exception as e:
            result.error_message = str(e)
            logger.error(f"Document cleanup failed on {db_path}: {e}")

        finally:
            result.end_time = datetime.now()
            self.metrics.record_operation(result)

        return result

    def should_run_operation(self, operation: str, db_path: str) -> bool:
        """Check if operation should run based on last execution time."""
        last_run = self.metrics.last_operation.get(f"{operation}_{db_path}")
        if not last_run:
            return True

        if operation == "VACUUM":
            threshold = timedelta(days=self.config.vacuum_threshold_days)
        elif operation == "ANALYZE":
            threshold = timedelta(days=self.config.analyze_threshold_days)
        else:
            return True  # Always run cleanup operations when scheduled

        return datetime.now() - last_run > threshold

    def run_scheduled_maintenance(self):
        """Run scheduled maintenance operations."""
        logger.info("Starting scheduled maintenance operations")

        for db_path in self.config.database_paths:
            if not os.path.exists(db_path):
                logger.warning(f"Database not found: {db_path}")
                continue

            try:
                # VACUUM operation
                if self.config.vacuum_enabled and self.should_run_operation("VACUUM", db_path):
                    self.perform_vacuum(db_path)

                # ANALYZE operation
                if self.config.analyze_enabled and self.should_run_operation("ANALYZE", db_path):
                    self.perform_analyze(db_path)

                # Chat history cleanup
                if self.config.chat_cleanup_enabled:
                    self.cleanup_old_chat_history(db_path)

                # Document cleanup
                if self.config.doc_cleanup_enabled:
                    self.cleanup_unused_documents(db_path)

            except Exception as e:
                logger.error(f"Maintenance failed for {db_path}: {e}")

        # Cleanup old backups
        self.cleanup_old_backups()

        logger.info("Scheduled maintenance operations completed")

    def setup_scheduler(self):
        """Setup maintenance operation scheduler."""
        # Clear any existing jobs
        schedule.clear()

        # Schedule VACUUM operations
        if self.config.vacuum_enabled:
            schedule.every().day.at(self.config.vacuum_schedule).do(self.run_scheduled_maintenance)

        # Schedule ANALYZE operations
        if self.config.analyze_enabled:
            schedule.every().day.at(self.config.analyze_schedule).do(self.run_scheduled_maintenance)

        # Schedule chat cleanup
        if self.config.chat_cleanup_enabled:
            schedule.every().day.at(self.config.chat_cleanup_schedule).do(
                self.run_scheduled_maintenance
            )

        # Schedule document cleanup
        if self.config.doc_cleanup_enabled:
            schedule.every().day.at(self.config.doc_cleanup_schedule).do(
                self.run_scheduled_maintenance
            )

        logger.info("Maintenance scheduler configured")

    def scheduler_worker(self):
        """Background thread worker for scheduler."""
        logger.info("Maintenance scheduler thread started")

        while not self._stop_event.is_set():
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)

    def status_monitor_worker(self):
        """Background thread worker for status monitoring."""
        logger.info("Maintenance status monitor started")

        while not self._stop_event.is_set():
            try:
                if self.config.enable_metrics:
                    summary = self.metrics.get_summary()
                    logger.debug(f"Maintenance status: {summary}")

                time.sleep(self.config.status_check_interval)
            except Exception as e:
                logger.error(f"Status monitor error: {e}")
                time.sleep(self.config.status_check_interval)

    def start(self):
        """Start the maintenance manager."""
        if self.is_running:
            logger.warning("Maintenance manager is already running")
            return

        logger.info("Starting database maintenance manager")

        # Setup scheduler
        self.setup_scheduler()

        # Start scheduler thread
        self.scheduler_thread = threading.Thread(
            target=self.scheduler_worker, name="MaintenanceScheduler", daemon=True
        )
        self.scheduler_thread.start()

        # Start status monitor thread
        if self.config.enable_metrics:
            self.status_thread = threading.Thread(
                target=self.status_monitor_worker, name="MaintenanceStatusMonitor", daemon=True
            )
            self.status_thread.start()

        self.is_running = True
        logger.info("Database maintenance manager started successfully")

    def stop(self):
        """Stop the maintenance manager."""
        if not self.is_running:
            return

        logger.info("Stopping database maintenance manager")

        # Signal threads to stop
        self._stop_event.set()

        # Wait for threads to finish
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)

        if self.status_thread and self.status_thread.is_alive():
            self.status_thread.join(timeout=5)

        self.is_running = False
        logger.info("Database maintenance manager stopped")

    def run_manual_maintenance(self, operations: list[str] = None) -> list[MaintenanceResult]:
        """Run maintenance operations manually."""
        if operations is None:
            operations = ["VACUUM", "ANALYZE", "CHAT_CLEANUP", "DOC_CLEANUP"]

        results = []
        logger.info(f"Running manual maintenance: {operations}")

        for db_path in self.config.database_paths:
            if not os.path.exists(db_path):
                logger.warning(f"Database not found: {db_path}")
                continue

            for operation in operations:
                try:
                    if operation == "VACUUM":
                        result = self.perform_vacuum(db_path)
                    elif operation == "ANALYZE":
                        result = self.perform_analyze(db_path)
                    elif operation == "CHAT_CLEANUP":
                        result = self.cleanup_old_chat_history(db_path)
                    elif operation == "DOC_CLEANUP":
                        result = self.cleanup_unused_documents(db_path)
                    else:
                        logger.warning(f"Unknown operation: {operation}")
                        continue

                    results.append(result)

                except Exception as e:
                    logger.error(f"Manual {operation} failed on {db_path}: {e}")

        return results

    def get_status(self) -> dict[str, Any]:
        """Get current maintenance manager status."""
        return {
            "is_running": self.is_running,
            "config": {
                "vacuum_enabled": self.config.vacuum_enabled,
                "vacuum_schedule": self.config.vacuum_schedule,
                "analyze_enabled": self.config.analyze_enabled,
                "analyze_schedule": self.config.analyze_schedule,
                "chat_cleanup_enabled": self.config.chat_cleanup_enabled,
                "chat_retention_days": self.config.chat_retention_days,
                "doc_cleanup_enabled": self.config.doc_cleanup_enabled,
                "doc_retention_days": self.config.doc_retention_days,
                "database_paths": self.config.database_paths,
            },
            "metrics": self.metrics.get_summary(),
            "next_scheduled_runs": {
                job.tags[0] if job.tags else "unknown": job.next_run.isoformat()
                if job.next_run
                else None
                for job in schedule.jobs
            },
            "database_info": {
                db_path: {
                    "exists": os.path.exists(db_path),
                    "size_bytes": self.get_database_size(db_path),
                    "last_modified": datetime.fromtimestamp(os.path.getmtime(db_path)).isoformat()
                    if os.path.exists(db_path)
                    else None,
                }
                for db_path in self.config.database_paths
            },
        }


# Global maintenance manager instance
maintenance_manager: DatabaseMaintenanceManager | None = None


def get_maintenance_manager() -> DatabaseMaintenanceManager | None:
    """Get the global maintenance manager instance."""
    return maintenance_manager


def initialize_maintenance(config: MaintenanceConfig = None) -> DatabaseMaintenanceManager:
    """Initialize the database maintenance manager."""
    global maintenance_manager

    if config is None:
        config = MaintenanceConfig()

    maintenance_manager = DatabaseMaintenanceManager(config)
    return maintenance_manager


def start_maintenance() -> bool:
    """Start the maintenance manager if initialized."""
    if maintenance_manager:
        maintenance_manager.start()
        return True
    return False


def stop_maintenance() -> bool:
    """Stop the maintenance manager if running."""
    if maintenance_manager:
        maintenance_manager.stop()
        return True
    return False


# Task 1.1.4 completion marker
logger.info(
    "[Database Maintenance] Task 1.1.4 Database Maintenance Automation - Implementation Complete"
)
