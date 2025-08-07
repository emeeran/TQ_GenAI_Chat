"""
Database Migration Script for TQ GenAI Chat
Implements Task 1.1.2: Database Schema Optimization
Updated for Task 1.1.1: OptimizedDocumentStore Integration

This script migrates existing databases to include optimized indexes and schema enhancements
for the new OptimizedDocumentStore with connection pooling.
"""

import logging
import sqlite3
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


class DatabaseMigrator:
    """Handles database migrations for schema optimization"""

    def __init__(self, database_path: str = "documents.db"):
        self.database_path = database_path
        self.migration_log: list[str] = []

    def log_migration(self, message: str):
        """Log migration step"""
        logger.info(message)
        self.migration_log.append(message)
        print(f"[MIGRATION] {message}")

    def check_database_exists(self) -> bool:
        """Check if database file exists"""
        return Path(self.database_path).exists()

    def backup_database(self) -> str:
        """Create a backup of the existing database"""
        if not self.check_database_exists():
            self.log_migration("No existing database found, skipping backup")
            return ""

        backup_path = f"{self.database_path}.backup"
        import shutil

        shutil.copy2(self.database_path, backup_path)
        self.log_migration(f"Database backed up to {backup_path}")
        return backup_path

    def get_database_version(self) -> str:
        """Get current database version from user_version pragma"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA user_version")
                version = cursor.fetchone()[0]
                return str(version)
        except Exception as e:
            self.log_migration(f"Could not determine database version: {e}")
            return "0"

    def set_database_version(self, version: str):
        """Set database version in user_version pragma"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA user_version = {version}")
                conn.commit()
                self.log_migration(f"Database version set to {version}")
        except Exception as e:
            self.log_migration(f"Could not set database version: {e}")

    def get_existing_indexes(self) -> dict[str, list[str]]:
        """Get list of existing indexes for each table"""
        indexes = {}
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()

                # Get all tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]

                for table in tables:
                    cursor.execute(
                        f"SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='{table}'"
                    )
                    table_indexes = [row[0] for row in cursor.fetchall()]
                    indexes[table] = table_indexes

        except Exception as e:
            self.log_migration(f"Error getting existing indexes: {e}")

        return indexes

    def get_table_columns(self, table_name: str) -> list[str]:
        """Get column names for a table"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [row[1] for row in cursor.fetchall()]
                return columns
        except Exception as e:
            self.log_migration(f"Error getting columns for {table_name}: {e}")
            return []

    def migrate_to_optimized_schema(self) -> bool:
        """Migrate database to optimized schema"""
        self.log_migration("Starting migration to optimized schema")

        try:
            # Check current version
            current_version = self.get_database_version()
            self.log_migration(f"Current database version: {current_version}")

            if current_version >= "2":
                self.log_migration("Database already at target version")
                return True

            # Get existing state
            existing_indexes = self.get_existing_indexes()
            self.log_migration(f"Found existing indexes: {existing_indexes}")

            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()

                # Enable WAL mode if not already enabled
                cursor.execute("PRAGMA journal_mode")
                current_mode = cursor.fetchone()[0]
                if current_mode.upper() != "WAL":
                    cursor.execute("PRAGMA journal_mode=WAL")
                    self.log_migration("Enabled WAL mode for better performance")

                # Optimize SQLite settings
                cursor.execute("PRAGMA cache_size = -64000")  # 64MB cache
                cursor.execute("PRAGMA temp_store = memory")
                cursor.execute("PRAGMA mmap_size = 268435456")  # 256MB memory map
                cursor.execute("PRAGMA optimize")
                self.log_migration("Applied SQLite performance optimizations")

                # Add missing columns to documents table if needed
                documents_columns = self.get_table_columns("documents")

                if "title" not in documents_columns:
                    cursor.execute("ALTER TABLE documents ADD COLUMN title TEXT")
                    # Populate title from filename if filename exists
                    if "filename" in documents_columns:
                        cursor.execute("UPDATE documents SET title = filename WHERE title IS NULL")
                    self.log_migration("Added title column to documents table")

                if "file_type" not in documents_columns and "type" not in documents_columns:
                    cursor.execute("ALTER TABLE documents ADD COLUMN file_type TEXT")
                    # Try to infer file type from filename extension
                    cursor.execute(
                        """
                        UPDATE documents
                        SET file_type = CASE
                            WHEN filename LIKE '%.pdf' THEN 'pdf'
                            WHEN filename LIKE '%.txt' THEN 'text'
                            WHEN filename LIKE '%.docx' THEN 'docx'
                            WHEN filename LIKE '%.doc' THEN 'doc'
                            WHEN filename LIKE '%.csv' THEN 'csv'
                            WHEN filename LIKE '%.xlsx' THEN 'xlsx'
                            WHEN filename LIKE '%.md' THEN 'markdown'
                            ELSE 'unknown'
                        END
                        WHERE file_type IS NULL AND filename IS NOT NULL
                    """
                    )
                    self.log_migration("Added file_type column to documents table")

                # Add OptimizedDocumentStore columns (Task 1.1.1)
                if "size_bytes" not in documents_columns:
                    cursor.execute("ALTER TABLE documents ADD COLUMN size_bytes INTEGER DEFAULT 0")
                    cursor.execute(
                        """
                        UPDATE documents
                        SET size_bytes = LENGTH(content)
                        WHERE size_bytes = 0 OR size_bytes IS NULL
                    """
                    )
                    self.log_migration("Added size_bytes column to documents table")

                if "content_hash" not in documents_columns:
                    cursor.execute("ALTER TABLE documents ADD COLUMN content_hash TEXT DEFAULT ''")
                    cursor.execute(
                        """
                        UPDATE documents
                        SET content_hash = SUBSTR(CAST(ABS(RANDOM()) AS TEXT), 1, 16)
                        WHERE content_hash = '' OR content_hash IS NULL
                    """
                    )
                    self.log_migration("Added content_hash column to documents table")

                if "last_accessed" not in documents_columns:
                    cursor.execute(
                        "ALTER TABLE documents ADD COLUMN last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                    )
                    cursor.execute(
                        """
                        UPDATE documents
                        SET last_accessed = COALESCE(timestamp, CURRENT_TIMESTAMP)
                        WHERE last_accessed IS NULL
                    """
                    )
                    self.log_migration("Added last_accessed column to documents table")

                if "access_count" not in documents_columns:
                    cursor.execute(
                        "ALTER TABLE documents ADD COLUMN access_count INTEGER DEFAULT 0"
                    )
                    self.log_migration("Added access_count column to documents table")

                # Create missing indexes for documents table
                new_indexes = [
                    (
                        "idx_documents_title",
                        "CREATE INDEX IF NOT EXISTS idx_documents_title ON documents(title)",
                    ),
                    (
                        "idx_documents_type_enhanced",
                        "CREATE INDEX IF NOT EXISTS idx_documents_type_enhanced ON documents(type)",
                    ),
                    (
                        "idx_documents_type_date",
                        "CREATE INDEX IF NOT EXISTS idx_documents_type_date ON documents(type, timestamp)",
                    ),
                    (
                        "idx_documents_title_type_enhanced",
                        "CREATE INDEX IF NOT EXISTS idx_documents_title_type_enhanced ON documents(title, type)",
                    ),
                    (
                        "idx_documents_accessed_type",
                        "CREATE INDEX IF NOT EXISTS idx_documents_accessed_type ON documents(last_accessed, type)",
                    ),
                    (
                        "idx_documents_size",
                        "CREATE INDEX IF NOT EXISTS idx_documents_size ON documents(size_bytes)",
                    ),
                    (
                        "idx_documents_content_hash",
                        "CREATE INDEX IF NOT EXISTS idx_documents_content_hash ON documents(content_hash)",
                    ),
                ]

                for index_name, index_sql in new_indexes:
                    if index_name not in existing_indexes.get("documents", []):
                        cursor.execute(index_sql)
                        self.log_migration(f"Created index: {index_name}")

                # Create missing composite indexes for chat_history table (if table exists)
                if "chat_history" in existing_indexes:
                    chat_indexes = [
                        (
                            "idx_chat_timestamp_provider",
                            "CREATE INDEX IF NOT EXISTS idx_chat_timestamp_provider ON chat_history(timestamp, provider)",
                        ),
                        (
                            "idx_chat_timestamp_session",
                            "CREATE INDEX IF NOT EXISTS idx_chat_timestamp_session ON chat_history(timestamp, session_id)",
                        ),
                        (
                            "idx_chat_provider_session",
                            "CREATE INDEX IF NOT EXISTS idx_chat_provider_session ON chat_history(provider, session_id)",
                        ),
                        (
                            "idx_chat_timestamp_provider_session",
                            "CREATE INDEX IF NOT EXISTS idx_chat_timestamp_provider_session ON chat_history(timestamp, provider, session_id)",
                        ),
                    ]

                    for index_name, index_sql in chat_indexes:
                        if index_name not in existing_indexes.get("chat_history", []):
                            cursor.execute(index_sql)
                            self.log_migration(f"Created composite index: {index_name}")
                else:
                    self.log_migration("Skipping chat_history indexes - table does not exist")

                # Run ANALYZE to update statistics
                cursor.execute("ANALYZE")
                self.log_migration("Updated database statistics with ANALYZE")

                conn.commit()

            # Set new database version
            self.set_database_version("2")
            self.log_migration("Migration completed successfully")
            return True

        except Exception as e:
            self.log_migration(f"Migration failed: {e}")
            return False

    def verify_migration(self) -> bool:
        """Verify that migration was successful"""
        self.log_migration("Verifying migration...")

        try:
            # Check database version
            version = self.get_database_version()
            if version != "2":
                self.log_migration(
                    f"Migration verification failed: version is {version}, expected 2"
                )
                return False

            # Check that required indexes exist
            indexes = self.get_existing_indexes()

            required_document_indexes = [
                "idx_documents_title",
                "idx_documents_type_enhanced",
                "idx_documents_type_date",
                "idx_documents_title_type_enhanced",
                "idx_documents_accessed_type",
                "idx_documents_size",
                "idx_documents_content_hash",
            ]

            missing_indexes = []

            for index in required_document_indexes:
                if index not in indexes.get("documents", []):
                    missing_indexes.append(index)

            # Only check chat indexes if chat_history table exists
            if "chat_history" in indexes:
                required_chat_indexes = [
                    "idx_chat_timestamp_provider",
                    "idx_chat_timestamp_session",
                    "idx_chat_provider_session",
                    "idx_chat_timestamp_provider_session",
                ]

                for index in required_chat_indexes:
                    if index not in indexes.get("chat_history", []):
                        missing_indexes.append(index)

            if missing_indexes:
                self.log_migration(
                    f"Migration verification failed: missing indexes {missing_indexes}"
                )
                return False

            self.log_migration("Migration verification successful")
            return True

        except Exception as e:
            self.log_migration(f"Migration verification error: {e}")
            return False

    def get_migration_report(self) -> dict:
        """Generate migration report"""
        return {
            "database_path": self.database_path,
            "migration_log": self.migration_log,
            "final_version": self.get_database_version(),
            "indexes": self.get_existing_indexes(),
        }


def main():
    """Main migration function"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate TQ GenAI Chat database to optimized schema"
    )
    parser.add_argument("--database", "-d", default="documents.db", help="Database path")
    parser.add_argument(
        "--backup", "-b", action="store_true", help="Create backup before migration"
    )
    parser.add_argument(
        "--verify-only", "-v", action="store_true", help="Only verify existing migration"
    )
    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    migrator = DatabaseMigrator(args.database)

    print("TQ GenAI Chat Database Migration Tool")
    print(f"Database: {args.database}")
    print("=" * 50)

    if args.verify_only:
        success = migrator.verify_migration()
        print(f"\nVerification {'PASSED' if success else 'FAILED'}")
        return 0 if success else 1

    # Create backup if requested
    if args.backup:
        backup_path = migrator.backup_database()
        if backup_path:
            print(f"Backup created: {backup_path}")

    # Run migration
    success = migrator.migrate_to_optimized_schema()

    if success:
        # Verify migration
        verified = migrator.verify_migration()
        if verified:
            print("\n" + "=" * 50)
            print("✅ MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 50)

            # Print report
            report = migrator.get_migration_report()
            print(f"\nDatabase Version: {report['final_version']}")
            print(f"Total Migration Steps: {len(report['migration_log'])}")

            return 0
        else:
            print("\n" + "=" * 50)
            print("❌ MIGRATION VERIFICATION FAILED")
            print("=" * 50)
            return 1
    else:
        print("\n" + "=" * 50)
        print("❌ MIGRATION FAILED")
        print("=" * 50)
        return 1


if __name__ == "__main__":
    exit(main())
