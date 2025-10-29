"""Async database operations with connection pooling"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncContextManager

import aiosqlite


class AsyncDatabaseManager:
    """Async database manager with connection pooling"""

    def __init__(self, db_path: str = "app_data.db", pool_size: int = 10):
        self.db_path = db_path
        self.pool_size = pool_size
        self._connection_pool: asyncio.Queue = None
        self._initialized = False

    async def initialize(self):
        """Initialize connection pool"""
        if self._initialized:
            return

        self._connection_pool = asyncio.Queue(maxsize=self.pool_size)

        # Create database tables
        await self._create_tables()

        # Pre-populate connection pool
        for _ in range(self.pool_size):
            conn = await aiosqlite.connect(self.db_path)
            await self._connection_pool.put(conn)

        self._initialized = True

    async def _create_tables(self):
        """Create necessary database tables"""
        async with aiosqlite.connect(self.db_path) as conn:
            # Chat sessions table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """
            )

            # Chat messages table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    model TEXT,
                    provider TEXT,
                    response_time REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions (id)
                )
            """
            )

            # Document store table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT,
                    content TEXT,
                    file_type TEXT,
                    file_size INTEGER,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Performance metrics table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT,
                    model TEXT,
                    response_time REAL,
                    token_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            await conn.commit()

    @asynccontextmanager
    async def get_connection(self) -> AsyncContextManager[aiosqlite.Connection]:
        """Get database connection from pool"""
        if not self._initialized:
            await self.initialize()

        # Get connection from pool
        conn = await self._connection_pool.get()
        try:
            yield conn
        finally:
            # Return connection to pool
            await self._connection_pool.put(conn)

    async def execute_query(self, query: str, params: tuple = ()) -> list[dict[str, Any]] | None:
        """Execute SELECT query and return results"""
        async with self.get_connection() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows] if rows else None

    async def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT/UPDATE/DELETE query and return affected rows"""
        async with self.get_connection() as conn:
            cursor = await conn.execute(query, params)
            await conn.commit()
            return cursor.rowcount

    async def close_all_connections(self):
        """Close all connections in the pool"""
        if not self._connection_pool:
            return

        while not self._connection_pool.empty():
            try:
                conn = self._connection_pool.get_nowait()
                await conn.close()
            except asyncio.QueueEmpty:
                break
