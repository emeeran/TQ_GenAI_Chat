#!/usr/bin/env python3
"""
Phase 3: Performance Optimization & Async Implementation
- Async/await conversion for all I/O operations
- Response caching with Redis integration
- Connection pooling for database operations
- Background task processing
- Frontend performance optimizations
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List


class RefactorPhase3:
    def __init__(self, root_path: str = "."):
        self.root = Path(root_path)
        self.backup_dir = self.root / "refactor_backup/phase3"
        
    def run(self):
        """Execute Phase 3 refactoring"""
        print("🚀 Starting Phase 3: Performance Optimization & Async Implementation")
        
        self.create_backup()
        self.implement_async_providers()
        self.create_caching_layer()
        self.implement_connection_pooling()
        self.create_background_tasks()
        self.optimize_frontend()
        self.create_performance_monitoring()
        
        print("✅ Phase 3 completed successfully!")
        print("\nPerformance improvements:")
        print("- Async AI provider calls")
        print("- Redis response caching")
        print("- Database connection pooling")
        print("- Background file processing")
        print("- Optimized frontend utilities")
        
    def create_backup(self):
        """Create backup of current state"""
        print("📦 Creating Phase 3 backup...")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Backup key files that will be modified
        backup_items = [
            "core/providers",
            "core/services", 
            "static/script.js",
            "app/__init__.py"
        ]
        
        for item in backup_items:
            src = self.root / item
            if src.exists():
                dst = self.backup_dir / item
                dst.parent.mkdir(parents=True, exist_ok=True)
                if src.is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
    
    def implement_async_providers(self):
        """Convert providers to async/await pattern"""
        print("⚡ Implementing Async AI Providers...")
        
        # Async base provider interface
        async_base_provider = '''"""Async base provider interface for high-performance operations"""
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass
import aiohttp
import time


@dataclass
class ChatMessage:
    """Standardized chat message format"""
    role: str
    content: str
    

@dataclass 
class ChatRequest:
    """Standardized chat request format"""
    messages: List[ChatMessage]
    model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    

@dataclass
class ChatResponse:
    """Standardized chat response format"""
    content: str
    model: str
    usage: Dict[str, Any]
    provider: str
    response_time: float = 0.0
    cached: bool = False


class AsyncAIProviderInterface(ABC):
    """Async base class for AI providers with performance optimizations"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self._request_count = 0
        self._total_response_time = 0.0
    
    async def __aenter__(self):
        """Async context manager entry"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=60)
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector
            )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    @abstractmethod
    async def get_models(self) -> List[str]:
        """Get available models for this provider"""
        pass
    
    @abstractmethod
    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """Process chat completion request asynchronously"""
        pass
    
    @abstractmethod
    async def chat_completion_stream(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """Stream chat completion response"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name"""
        pass
    
    @property 
    def average_response_time(self) -> float:
        """Get average response time for this provider"""
        if self._request_count == 0:
            return 0.0
        return self._total_response_time / self._request_count
    
    def _record_response_time(self, response_time: float):
        """Record response time for performance monitoring"""
        self._request_count += 1
        self._total_response_time += response_time
'''
        
        async_base_file = self.root / "core/providers/async_base.py"
        async_base_file.write_text(async_base_provider)
        
        # Async OpenAI provider
        async_openai_provider = '''"""High-performance async OpenAI provider"""
import os
import time
import json
from typing import List, Dict, Any, AsyncGenerator
import aiohttp
from .async_base import AsyncAIProviderInterface, ChatRequest, ChatResponse, ChatMessage


class AsyncOpenAIProvider(AsyncAIProviderInterface):
    """High-performance async OpenAI API provider"""
    
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.base_url = "https://api.openai.com/v1"
        self._models = [
            "gpt-4o",
            "gpt-4o-mini", 
            "gpt-4-turbo",
            "gpt-3.5-turbo"
        ]
    
    @property
    def name(self) -> str:
        return "openai"
    
    async def get_models(self) -> List[str]:
        return self._models
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """Process chat completion using async OpenAI API"""
        start_time = time.time()
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            messages = [
                {"role": msg.role, "content": msg.content} 
                for msg in request.messages
            ]
            
            payload = {
                "model": request.model,
                "messages": messages,
                "temperature": request.temperature,
                "stream": False
            }
            
            if request.max_tokens:
                payload["max_tokens"] = request.max_tokens
            
            async with self.session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"OpenAI API error: {response.status} - {error_text}")
                
                data = await response.json()
                
                response_time = time.time() - start_time
                self._record_response_time(response_time)
                
                return ChatResponse(
                    content=data["choices"][0]["message"]["content"],
                    model=data["model"],
                    usage={
                        "prompt_tokens": data["usage"]["prompt_tokens"],
                        "completion_tokens": data["usage"]["completion_tokens"],
                        "total_tokens": data["usage"]["total_tokens"]
                    },
                    provider=self.name,
                    response_time=response_time
                )
                
        except Exception as e:
            response_time = time.time() - start_time
            self._record_response_time(response_time)
            raise Exception(f"Async OpenAI API error: {str(e)}")
    
    async def chat_completion_stream(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """Stream chat completion response"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = [
            {"role": msg.role, "content": msg.content} 
            for msg in request.messages
        ]
        
        payload = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "stream": True
        }
        
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        
        try:
            async with self.session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        data_str = line[6:]
                        if data_str == '[DONE]':
                            break
                        try:
                            data = json.loads(data_str)
                            if 'choices' in data and len(data['choices']) > 0:
                                delta = data['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    yield delta['content']
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            raise Exception(f"OpenAI streaming error: {str(e)}")
'''
        
        async_openai_file = self.root / "core/providers/async_openai_provider.py"
        async_openai_file.write_text(async_openai_provider)
        
        # Async provider factory
        async_factory = '''"""Async provider factory with connection pooling"""
import asyncio
from typing import Dict, List, Optional, Union
from .async_base import AsyncAIProviderInterface
from .async_openai_provider import AsyncOpenAIProvider
from core.cache import CacheManager


class AsyncProviderFactory:
    """Factory for creating and managing async AI providers"""
    
    def __init__(self):
        self._providers: Dict[str, AsyncAIProviderInterface] = {}
        self._provider_pool: Dict[str, List[AsyncAIProviderInterface]] = {}
        self.cache_manager = CacheManager()
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize all available providers"""
        available_providers = [
            AsyncOpenAIProvider(),
        ]
        
        for provider in available_providers:
            if provider.is_available():
                self._providers[provider.name] = provider
                # Create provider pool for connection reuse
                self._provider_pool[provider.name] = [provider]
    
    async def get_provider(self, name: str) -> Optional[AsyncAIProviderInterface]:
        """Get provider by name with connection pooling"""
        if name not in self._providers:
            return None
        
        # Return provider from pool if available
        if name in self._provider_pool and self._provider_pool[name]:
            provider = self._provider_pool[name][0]
            async with provider:
                return provider
        
        return self._providers[name]
    
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names"""
        return list(self._providers.keys())
    
    async def get_models_for_provider(self, provider_name: str) -> List[str]:
        """Get models for specific provider"""
        provider = await self.get_provider(provider_name)
        if provider:
            return await provider.get_models()
        return []
    
    async def get_all_models(self) -> Dict[str, List[str]]:
        """Get all models grouped by provider"""
        result = {}
        for name in self._providers.keys():
            models = await self.get_models_for_provider(name)
            if models:
                result[name] = models
        return result
    
    def get_provider_stats(self) -> Dict[str, Dict[str, float]]:
        """Get performance statistics for all providers"""
        stats = {}
        for name, provider in self._providers.items():
            stats[name] = {
                "average_response_time": provider.average_response_time,
                "request_count": provider._request_count
            }
        return stats
'''
        
        async_factory_file = self.root / "core/providers/async_factory.py"
        async_factory_file.write_text(async_factory)
    
    def create_caching_layer(self):
        """Implement Redis-based response caching"""
        print("💾 Creating Caching Layer...")
        
        cache_manager = '''"""Redis-based caching with fallback to memory"""
import json
import hashlib
import time
from typing import Optional, Any, Dict
from dataclasses import asdict
import asyncio

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class CacheManager:
    """High-performance caching with Redis and memory fallback"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 300  # 5 minutes default TTL
        self._initialize_redis()
    
    def _initialize_redis(self):
        """Initialize Redis connection if available"""
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            except Exception as e:
                print(f"Redis connection failed, using memory cache: {e}")
                self.redis_client = None
    
    def _generate_cache_key(self, prefix: str, data: Dict[str, Any]) -> str:
        """Generate consistent cache key from request data"""
        # Create deterministic hash from request data
        data_str = json.dumps(data, sort_keys=True)
        hash_obj = hashlib.md5(data_str.encode())
        return f"{prefix}:{hash_obj.hexdigest()}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        try:
            if self.redis_client:
                # Try Redis first
                cached = await self.redis_client.get(key)
                if cached:
                    return json.loads(cached)
            
            # Fallback to memory cache
            if key in self.memory_cache:
                cache_entry = self.memory_cache[key]
                if time.time() < cache_entry["expires_at"]:
                    return cache_entry["data"]
                else:
                    # Clean expired entry
                    del self.memory_cache[key]
            
            return None
            
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set cached value"""
        ttl = ttl or self.cache_ttl
        
        try:
            if self.redis_client:
                # Store in Redis
                await self.redis_client.setex(key, ttl, json.dumps(value))
            
            # Always store in memory cache as backup
            self.memory_cache[key] = {
                "data": value,
                "expires_at": time.time() + ttl
            }
            
            return True
            
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete cached value"""
        try:
            if self.redis_client:
                await self.redis_client.delete(key)
            
            if key in self.memory_cache:
                del self.memory_cache[key]
            
            return True
            
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    async def clear_all(self) -> bool:
        """Clear all cached values"""
        try:
            if self.redis_client:
                await self.redis_client.flushdb()
            
            self.memory_cache.clear()
            return True
            
        except Exception as e:
            print(f"Cache clear error: {e}")
            return False
    
    def get_cache_key_for_chat_request(self, request_data: Dict[str, Any]) -> str:
        """Generate cache key for chat requests"""
        # Remove timestamp and other non-deterministic fields
        cache_data = {k: v for k, v in request_data.items() 
                     if k not in ['timestamp', 'request_id']}
        return self._generate_cache_key("chat", cache_data)
    
    async def cleanup_expired(self):
        """Clean up expired memory cache entries"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.memory_cache.items()
            if current_time >= entry["expires_at"]
        ]
        
        for key in expired_keys:
            del self.memory_cache[key]
        
        return len(expired_keys)
'''
        
        cache_file = self.root / "core/cache.py"
        cache_file.write_text(cache_manager)
    
    def implement_connection_pooling(self):
        """Implement database connection pooling"""
        print("🔗 Implementing Connection Pooling...")
        
        # Async database manager
        async_db_manager = '''"""Async database operations with connection pooling"""
import asyncio
import sqlite3
import aiosqlite
from typing import List, Dict, Any, Optional, AsyncContextManager
from contextlib import asynccontextmanager
from pathlib import Path


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
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """)
            
            # Chat messages table
            await conn.execute("""
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
            """)
            
            # Document store table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT,
                    content TEXT,
                    file_type TEXT,
                    file_size INTEGER,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Performance metrics table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT,
                    model TEXT,
                    response_time REAL,
                    token_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
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
    
    async def execute_query(self, query: str, params: tuple = ()) -> Optional[List[Dict[str, Any]]]:
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
'''
        
        async_db_file = self.root / "core/async_database.py"
        async_db_file.write_text(async_db_manager)
    
    def create_background_tasks(self):
        """Implement background task processing"""
        print("⚙️ Creating Background Task System...")
        
        background_tasks = '''"""Background task processing system"""
import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class BackgroundTask:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    func: Optional[Callable] = None
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0


class BackgroundTaskManager:
    """High-performance background task processing"""
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.tasks: Dict[str, BackgroundTask] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.workers: List[asyncio.Task] = []
        self.running = False
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Start background task processing"""
        if self.running:
            return
        
        self.running = True
        self.workers = [
            asyncio.create_task(self._worker(f"worker-{i}"))
            for i in range(self.max_workers)
        ]
        self.logger.info(f"Started {self.max_workers} background workers")
    
    async def stop(self):
        """Stop background task processing"""
        self.running = False
        
        # Cancel all workers
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
        self.logger.info("Stopped all background workers")
    
    async def submit_task(self, name: str, func: Callable, *args, **kwargs) -> str:
        """Submit a task for background processing"""
        task = BackgroundTask(
            name=name,
            func=func,
            args=args,
            kwargs=kwargs
        )
        
        self.tasks[task.id] = task
        await self.task_queue.put(task)
        
        self.logger.info(f"Submitted task: {name} ({task.id})")
        return task.id
    
    def get_task_status(self, task_id: str) -> Optional[BackgroundTask]:
        """Get task status by ID"""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[BackgroundTask]:
        """Get all tasks"""
        return list(self.tasks.values())
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[BackgroundTask]:
        """Get tasks by status"""
        return [task for task in self.tasks.values() if task.status == status]
    
    async def _worker(self, worker_name: str):
        """Background worker process"""
        self.logger.info(f"Worker {worker_name} started")
        
        while self.running:
            try:
                # Get task from queue with timeout
                task = await asyncio.wait_for(
                    self.task_queue.get(), 
                    timeout=1.0
                )
                
                await self._execute_task(task, worker_name)
                
            except asyncio.TimeoutError:
                # No tasks available, continue
                continue
            except Exception as e:
                self.logger.error(f"Worker {worker_name} error: {e}")
        
        self.logger.info(f"Worker {worker_name} stopped")
    
    async def _execute_task(self, task: BackgroundTask, worker_name: str):
        """Execute a single task"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        
        self.logger.info(f"Worker {worker_name} executing task: {task.name} ({task.id})")
        
        try:
            if asyncio.iscoroutinefunction(task.func):
                # Async function
                task.result = await task.func(*task.args, **task.kwargs)
            else:
                # Sync function - run in thread pool
                loop = asyncio.get_event_loop()
                task.result = await loop.run_in_executor(
                    None, lambda: task.func(*task.args, **task.kwargs)
                )
            
            task.status = TaskStatus.COMPLETED
            task.progress = 100.0
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            self.logger.error(f"Task {task.name} ({task.id}) failed: {e}")
        
        task.completed_at = datetime.now()
        
        # Clean up old completed tasks (keep last 100)
        await self._cleanup_old_tasks()
    
    async def _cleanup_old_tasks(self):
        """Clean up old completed tasks"""
        completed_tasks = self.get_tasks_by_status(TaskStatus.COMPLETED)
        failed_tasks = self.get_tasks_by_status(TaskStatus.FAILED)
        
        all_finished = completed_tasks + failed_tasks
        all_finished.sort(key=lambda t: t.completed_at or datetime.now(), reverse=True)
        
        # Keep only last 100 finished tasks
        if len(all_finished) > 100:
            tasks_to_remove = all_finished[100:]
            for task in tasks_to_remove:
                if task.id in self.tasks:
                    del self.tasks[task.id]


# Global task manager instance
task_manager = BackgroundTaskManager()


async def submit_background_task(name: str, func: Callable, *args, **kwargs) -> str:
    """Submit a background task"""
    return await task_manager.submit_task(name, func, *args, **kwargs)


def get_task_status(task_id: str) -> Optional[BackgroundTask]:
    """Get task status"""
    return task_manager.get_task_status(task_id)
'''
        
        bg_tasks_file = self.root / "core/background_tasks.py"
        bg_tasks_file.write_text(background_tasks)
    
    def optimize_frontend(self):
        """Optimize frontend JavaScript performance"""
        print("🎨 Optimizing Frontend Performance...")
        
        # Read current script.js to get a sense of the structure
        script_file = self.root / "static/script.js"
        if not script_file.exists():
            return
        
        # Create optimized utilities
        optimized_js = '''/**
 * High-Performance Frontend Utilities
 * Optimized for modern browsers with async/await and performance monitoring
 */

class APIService {
    constructor() {
        this.baseURL = '/api/v1';
        this.requestQueue = new Map();
        this.cache = new Map();
        this.cacheTTL = 5 * 60 * 1000; // 5 minutes
    }

    /**
     * Debounced API request with caching
     */
    async request(endpoint, options = {}, cacheKey = null) {
        const url = `${this.baseURL}${endpoint}`;
        const method = options.method || 'GET';
        
        // Check cache first for GET requests
        if (method === 'GET' && cacheKey && this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < this.cacheTTL) {
                return cached.data;
            }
        }
        
        // Prevent duplicate requests
        const requestKey = `${method}:${url}`;
        if (this.requestQueue.has(requestKey)) {
            return this.requestQueue.get(requestKey);
        }
        
        const requestPromise = this._executeRequest(url, options);
        this.requestQueue.set(requestKey, requestPromise);
        
        try {
            const result = await requestPromise;
            
            // Cache GET requests
            if (method === 'GET' && cacheKey) {
                this.cache.set(cacheKey, {
                    data: result,
                    timestamp: Date.now()
                });
            }
            
            return result;
        } finally {
            this.requestQueue.delete(requestKey);
        }
    }

    async _executeRequest(url, options) {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return response.json();
    }

    // Specialized methods
    async sendChatMessage(data) {
        return this.request('/chat', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async getProviders() {
        return this.request('/providers', {}, 'providers');
    }

    async getModels(provider) {
        return this.request(`/models/${provider}`, {}, `models-${provider}`);
    }
}

class DOMUtils {
    /**
     * Efficient DOM manipulation utilities
     */
    static createElement(tag, attributes = {}, children = []) {
        const element = document.createElement(tag);
        
        // Set attributes
        Object.entries(attributes).forEach(([key, value]) => {
            if (key === 'className') {
                element.className = value;
            } else if (key === 'innerHTML') {
                element.innerHTML = value;
            } else {
                element.setAttribute(key, value);
            }
        });
        
        // Add children
        children.forEach(child => {
            if (typeof child === 'string') {
                element.appendChild(document.createTextNode(child));
            } else {
                element.appendChild(child);
            }
        });
        
        return element;
    }

    static debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    static throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        }
    }

    static animateValue(element, start, end, duration, callback) {
        const startTime = performance.now();
        const difference = end - start;

        function step(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            const value = start + (difference * progress);
            callback(value);
            
            if (progress < 1) {
                requestAnimationFrame(step);
            }
        }
        
        requestAnimationFrame(step);
    }
}

class PerformanceMonitor {
    constructor() {
        this.metrics = new Map();
        this.startTimes = new Map();
    }

    startTimer(name) {
        this.startTimes.set(name, performance.now());
    }

    endTimer(name) {
        const startTime = this.startTimes.get(name);
        if (startTime) {
            const duration = performance.now() - startTime;
            this.recordMetric(name, duration);
            this.startTimes.delete(name);
            return duration;
        }
        return 0;
    }

    recordMetric(name, value) {
        if (!this.metrics.has(name)) {
            this.metrics.set(name, []);
        }
        this.metrics.get(name).push({
            value,
            timestamp: Date.now()
        });
        
        // Keep only last 100 measurements
        if (this.metrics.get(name).length > 100) {
            this.metrics.get(name).shift();
        }
    }

    getAverageMetric(name) {
        const values = this.metrics.get(name);
        if (!values || values.length === 0) return 0;
        
        const sum = values.reduce((acc, item) => acc + item.value, 0);
        return sum / values.length;
    }

    getAllMetrics() {
        const result = {};
        this.metrics.forEach((values, name) => {
            result[name] = {
                average: this.getAverageMetric(name),
                count: values.length,
                latest: values[values.length - 1]?.value || 0
            };
        });
        return result;
    }
}

// Export utilities
window.APIService = APIService;
window.DOMUtils = DOMUtils;
window.PerformanceMonitor = PerformanceMonitor;

// Global instances
window.apiService = new APIService();
window.perfMonitor = new PerformanceMonitor();
'''
        
        optimized_file = self.root / "static/optimizations.js"
        optimized_file.write_text(optimized_js)
    
    def create_performance_monitoring(self):
        """Create performance monitoring system"""
        print("📊 Creating Performance Monitoring...")
        
        monitoring_code = '''"""Performance monitoring and metrics collection"""
import time
import psutil
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque


@dataclass
class PerformanceMetric:
    name: str
    value: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceMonitor:
    """Comprehensive performance monitoring system"""
    
    def __init__(self, retention_hours: int = 24):
        self.retention_hours = retention_hours
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.timers: Dict[str, float] = {}
        self.counters: Dict[str, int] = defaultdict(int)
        self.system_stats_task: Optional[asyncio.Task] = None
        self._monitoring = False
    
    def start_monitoring(self):
        """Start system monitoring"""
        if not self._monitoring:
            self._monitoring = True
            self.system_stats_task = asyncio.create_task(self._collect_system_stats())
    
    def stop_monitoring(self):
        """Stop system monitoring"""
        self._monitoring = False
        if self.system_stats_task and not self.system_stats_task.done():
            self.system_stats_task.cancel()
    
    def start_timer(self, name: str) -> str:
        """Start a performance timer"""
        timer_key = f"{name}_{time.time()}"
        self.timers[timer_key] = time.time()
        return timer_key
    
    def end_timer(self, timer_key: str) -> float:
        """End a performance timer and record the metric"""
        if timer_key in self.timers:
            duration = time.time() - self.timers[timer_key]
            del self.timers[timer_key]
            
            # Extract metric name from timer key
            metric_name = timer_key.rsplit('_', 1)[0]
            self.record_metric(f"{metric_name}_duration", duration)
            return duration
        return 0.0
    
    def record_metric(self, name: str, value: float, metadata: Dict[str, Any] = None):
        """Record a performance metric"""
        metric = PerformanceMetric(
            name=name,
            value=value,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        self.metrics[name].append(metric)
        self._cleanup_old_metrics()
    
    def increment_counter(self, name: str, value: int = 1):
        """Increment a counter metric"""
        self.counters[name] += value
        self.record_metric(f"{name}_count", self.counters[name])
    
    def get_metric_stats(self, name: str) -> Dict[str, float]:
        """Get statistics for a metric"""
        if name not in self.metrics:
            return {}
        
        values = [m.value for m in self.metrics[name]]
        if not values:
            return {}
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "latest": values[-1]
        }
    
    def get_all_metrics(self) -> Dict[str, Dict[str, float]]:
        """Get all metric statistics"""
        return {name: self.get_metric_stats(name) for name in self.metrics.keys()}
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get current system health metrics"""
        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "active_connections": len(psutil.net_connections()),
            "process_count": len(psutil.pids()),
            "timestamp": datetime.now().isoformat()
        }
    
    async def _collect_system_stats(self):
        """Collect system statistics periodically"""
        while self._monitoring:
            try:
                # CPU metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                self.record_metric("system_cpu_percent", cpu_percent)
                
                # Memory metrics
                memory = psutil.virtual_memory()
                self.record_metric("system_memory_percent", memory.percent)
                self.record_metric("system_memory_used_gb", memory.used / (1024**3))
                
                # Disk metrics
                disk = psutil.disk_usage('/')
                self.record_metric("system_disk_percent", disk.percent)
                
                # Network metrics
                net_io = psutil.net_io_counters()
                self.record_metric("system_bytes_sent", net_io.bytes_sent)
                self.record_metric("system_bytes_received", net_io.bytes_recv)
                
                await asyncio.sleep(30)  # Collect every 30 seconds
                
            except Exception as e:
                print(f"System stats collection error: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    def _cleanup_old_metrics(self):
        """Clean up metrics older than retention period"""
        cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)
        
        for name, metric_queue in self.metrics.items():
            # Remove old metrics (deque handles max size automatically)
            while metric_queue and metric_queue[0].timestamp < cutoff_time:
                metric_queue.popleft()
    
    def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics for external monitoring systems"""
        return {
            "metrics": self.get_all_metrics(),
            "counters": dict(self.counters),
            "system_health": self.get_system_health(),
            "export_timestamp": datetime.now().isoformat()
        }


# Global performance monitor instance
perf_monitor = PerformanceMonitor()


def monitor_performance(func_name: str = None):
    """Decorator for monitoring function performance"""
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            name = func_name or f"{func.__module__}.{func.__name__}"
            timer_key = perf_monitor.start_timer(name)
            
            try:
                result = await func(*args, **kwargs)
                perf_monitor.increment_counter(f"{name}_success")
                return result
            except Exception as e:
                perf_monitor.increment_counter(f"{name}_error")
                raise
            finally:
                perf_monitor.end_timer(timer_key)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            name = func_name or f"{func.__module__}.{func.__name__}"
            timer_key = perf_monitor.start_timer(name)
            
            try:
                result = func(*args, **kwargs)
                perf_monitor.increment_counter(f"{name}_success")
                return result
            except Exception as e:
                perf_monitor.increment_counter(f"{name}_error")
                raise
            finally:
                perf_monitor.end_timer(timer_key)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator
'''
        
        monitoring_file = self.root / "core/performance.py"
        monitoring_file.write_text(monitoring_code)


if __name__ == "__main__":
    refactor = RefactorPhase3()
    refactor.run()
