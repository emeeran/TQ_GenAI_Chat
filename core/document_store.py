"""
Document Store Module
Handles document storage, retrieval, and management with SQLite backend.
Enhanced with connection pooling, prepared statements, and comprehensive indexing.
"""
import json
import sqlite3
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
from contextlib import contextmanager

from flask import current_app
from config.settings import BASE_DIR
from .database.connection_pool import get_db_connection
from .database.migrations import MigrationManager
from .document_chunking import IntelligentChunker, ChunkingStrategy, ChunkRetriever
from .cache import get_cache_manager, cache_get, cache_set, cache_delete, cache_invalidate_tag
from .search_engine import AdvancedSearchEngine
from utils.logging import get_logger

logger = get_logger(__name__)


class DocumentStore:
    """
    Optimized SQLite-based document storage system with:
    - Connection pooling for better performance
    - Comprehensive indexing for fast search
    - Prepared statements for security and performance
    - Full-text search capabilities
    - Document versioning and statistics
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the document store
        
        Args:
            db_path: Path to SQLite database file, defaults to BASE_DIR/documents.db
        """
        self.db_path = db_path or str(BASE_DIR / "documents.db")
        self._migration_manager = MigrationManager(self.db_path)
        self._initialize_database()
        self._prepared_statements = self._prepare_statements()
        
        # Initialize enhanced chunking system
        self._chunker = IntelligentChunker()
        self._chunk_retriever = ChunkRetriever(self)
        
        # Initialize cache manager
        self._cache = get_cache_manager()
        
        # Initialize advanced search engine
        self._search_engine = AdvancedSearchEngine(self)

    def _initialize_database(self) -> None:
        """Initialize database with migrations"""
        try:
            # Run migrations to ensure schema is up to date
            self._migration_manager.migrate()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def _prepare_statements(self) -> Dict[str, str]:
        """Prepare commonly used SQL statements for better performance"""
        return {
            'insert_document': '''
                INSERT INTO documents 
                (id, title, content, metadata, file_path, timestamp, type, user_id, 
                 content_hash, size, created_at, updated_at, version, is_latest)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            'insert_chunk': '''
                INSERT INTO chunks
                (id, document_id, content, chunk_index, metadata, content_hash, 
                 start_pos, end_pos, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            'insert_document_stats': '''
                INSERT OR REPLACE INTO document_stats
                (document_id, word_count, char_count, chunk_count, access_count, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?)
            ''',
            'get_document': 'SELECT * FROM documents WHERE id = ? AND is_latest = 1',
            'get_document_chunks': '''
                SELECT * FROM chunks WHERE document_id = ? ORDER BY chunk_index
            ''',
            'search_documents_fts': '''
                SELECT d.*, rank FROM documents d
                JOIN documents_fts fts ON d.rowid = fts.rowid
                WHERE documents_fts MATCH ? AND d.is_latest = 1
                ORDER BY rank LIMIT ?
            ''',
            'search_chunks_fts': '''
                SELECT c.*, d.title, d.type FROM chunks c
                JOIN chunks_fts fts ON c.rowid = fts.rowid
                JOIN documents d ON c.document_id = d.id
                WHERE chunks_fts MATCH ? AND d.is_latest = 1
                ORDER BY rank LIMIT ?
            ''',
            'update_access_stats': '''
                UPDATE document_stats 
                SET access_count = access_count + 1, last_accessed = ?
                WHERE document_id = ?
            ''',
            'delete_document': 'UPDATE documents SET is_latest = 0 WHERE id = ?',
            'get_recent_documents': '''
                SELECT * FROM documents 
                WHERE is_latest = 1 AND (? IS NULL OR type = ?)
                ORDER BY timestamp DESC LIMIT ?
            ''',
            'get_popular_documents': '''
                SELECT d.*, s.access_count FROM documents d
                JOIN document_stats s ON d.id = s.document_id
                WHERE d.is_latest = 1
                ORDER BY s.access_count DESC, d.timestamp DESC
                LIMIT ?
            '''
        }

    def add_document(self, 
                    content: str, 
                    title: Optional[str] = None,
                    file_path: Optional[str] = None, 
                    doc_type: str = "text",
                    metadata: Optional[Dict[str, Any]] = None,
                    user_id: Optional[str] = None) -> str:
        """
        Add a document to the store with enhanced metadata and versioning
        
        Args:
            content: Document content
            title: Document title
            file_path: Source file path
            doc_type: Document type (text, pdf, docx, etc.)
            metadata: Additional metadata
            user_id: User identifier
            
        Returns:
            Document ID
        """
        if not content:
            raise ValueError("Document content cannot be empty")
        
        # Generate document metadata
        timestamp = int(time.time())
        if not title:
            title = content[:50] + ("..." if len(content) > 50 else "")
            
        # Create content hash for deduplication
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        doc_id = f"doc_{hashlib.md5(f"{content_hash}{timestamp}".encode()).hexdigest()}"
        
        # Calculate document statistics
        word_count = len(content.split())
        char_count = len(content)
        size = len(content.encode('utf-8'))
        
        metadata_json = json.dumps(metadata or {})
        
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                # Insert document using prepared statement
                cursor.execute(
                    self._prepared_statements['insert_document'],
                    (doc_id, title, content, metadata_json, file_path, timestamp, 
                     doc_type, user_id, content_hash, size, timestamp, timestamp, 1, 1)
                )
                
                # Process document into chunks
                chunks = self._process_chunks(doc_id, content, metadata or {})
                
                # Insert document statistics
                cursor.execute(
                    self._prepared_statements['insert_document_stats'],
                    (doc_id, word_count, char_count, len(chunks), 0, None)
                )
                
                conn.commit()
                
                # Invalidate relevant caches
                cache_invalidate_tag(f"doc_type:{doc_type}")
                cache_invalidate_tag("recent_documents")
                cache_invalidate_tag("search_results")
                
                logger.info(f"Added document {doc_id} with {len(chunks)} chunks")
                return doc_id
                
            except sqlite3.Error as e:
                conn.rollback()
                logger.error(f"Database error adding document: {e}")
                raise
    
    def _process_chunks(self, doc_id: str, content: str, metadata: Dict[str, Any], 
                      strategy: ChunkingStrategy = ChunkingStrategy.SENTENCE_BOUNDARY) -> List[str]:
        """
        Process document into intelligent chunks using enhanced chunking system
        
        Args:
            doc_id: Document ID
            content: Document content
            metadata: Document metadata
            strategy: Chunking strategy to use
            
        Returns:
            List of chunk IDs created
        """
        try:
            # Use intelligent chunker to create optimized chunks
            document_chunks = self._chunker.chunk_document(
                document_id=doc_id,
                content=content,
                strategy=strategy,
                metadata=metadata
            )
            
            # Convert chunks to database format
            db_chunks = []
            for chunk in document_chunks:
                chunk_data = chunk.to_dict()
                db_chunks.append((
                    chunk_data['id'],
                    chunk_data['document_id'],
                    chunk_data['content'],
                    chunk_data['chunk_index'],
                    json.dumps({
                        **metadata,
                        'word_count': chunk_data['word_count'],
                        'sentence_count': chunk_data['sentence_count'],
                        'paragraph_count': chunk_data['paragraph_count'],
                        'keywords': chunk_data['keywords'],
                        'strategy': chunk_data['strategy'],
                        'overlap_prev': chunk_data['overlap_prev'],
                        'overlap_next': chunk_data['overlap_next']
                    }),
                    chunk_data['content_hash'],
                    chunk_data['start_pos'],
                    chunk_data['end_pos'],
                    chunk_data['created_at']
                ))
            
            # Bulk insert chunks using connection pool
            with get_db_connection(self.db_path) as conn:
                cursor = conn.cursor()
                
                try:
                    cursor.executemany(
                        self._prepared_statements['insert_chunk'],
                        db_chunks
                    )
                    conn.commit()
                    logger.debug(f"Created {len(db_chunks)} intelligent chunks for document {doc_id}")
                    return [chunk[0] for chunk in db_chunks]  # Return chunk IDs
                    
                except sqlite3.Error as e:
                    conn.rollback()
                    logger.error(f"Database error processing chunks: {e}")
                    raise
                    
        except Exception as e:
            logger.error(f"Error in intelligent chunking: {e}")
            # Fallback to simple chunking if intelligent chunking fails
            return self._fallback_chunking(doc_id, content, metadata)
    
    def _fallback_chunking(self, doc_id: str, content: str, metadata: Dict[str, Any]) -> List[str]:
        """Fallback to simple fixed-size chunking if intelligent chunking fails"""
        chunk_size = 1000
        overlap = 200
        chunks = []
        timestamp = int(time.time())
        
        if len(content) <= chunk_size:
            chunk_id = f"{doc_id}_chunk_0"
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            chunks.append((chunk_id, doc_id, content, 0, json.dumps(metadata), 
                          content_hash, 0, len(content), timestamp))
        else:
            for i in range(0, len(content), chunk_size - overlap):
                chunk_content = content[i:i + chunk_size]
                if chunk_content.strip():
                    chunk_index = len(chunks)
                    chunk_id = f"{doc_id}_chunk_{chunk_index}"
                    content_hash = hashlib.sha256(chunk_content.encode()).hexdigest()
                    chunks.append((chunk_id, doc_id, chunk_content, chunk_index, 
                                 json.dumps(metadata), content_hash, i, i + len(chunk_content), timestamp))
        
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.executemany(self._prepared_statements['insert_chunk'], chunks)
                conn.commit()
                return [chunk[0] for chunk in chunks]
            except sqlite3.Error as e:
                conn.rollback()
                logger.error(f"Database error in fallback chunking: {e}")
                raise
    
    def get_document(self, doc_id: str, include_chunks: bool = False) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document by ID with enhanced features and caching
        
        Args:
            doc_id: Document ID
            include_chunks: Whether to include document chunks
            
        Returns:
            Document data or None if not found
        """
        # Check cache first
        cache_key = f"document:{doc_id}:chunks:{include_chunks}"
        cached_doc = cache_get(cache_key)
        if cached_doc is not None:
            return cached_doc
        
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                # Get document using prepared statement
                cursor.execute(self._prepared_statements['get_document'], (doc_id,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                # Convert row to dictionary
                doc = dict(row)
                
                # Parse metadata JSON
                if doc.get('metadata'):
                    doc['metadata'] = json.loads(doc['metadata'])
                else:
                    doc['metadata'] = {}
                
                # Update access statistics
                cursor.execute(
                    self._prepared_statements['update_access_stats'],
                    (int(time.time()), doc_id)
                )
                
                # Include chunks if requested
                if include_chunks:
                    cursor.execute(self._prepared_statements['get_document_chunks'], (doc_id,))
                    chunks = []
                    for chunk_row in cursor.fetchall():
                        chunk = dict(chunk_row)
                        if chunk.get('metadata'):
                            chunk['metadata'] = json.loads(chunk['metadata'])
                        chunks.append(chunk)
                    doc['chunks'] = chunks
                
                conn.commit()  # Commit access stats update
                
                # Cache the document with tags for invalidation
                cache_set(
                    cache_key, 
                    doc, 
                    ttl=300,  # 5 minutes
                    tags=[f"document:{doc_id}", f"doc_type:{doc.get('type', 'unknown')}"]
                )
                
                return doc
                
            except sqlite3.Error as e:
                logger.error(f"Database error retrieving document: {e}")
                return None
    
    def search_documents(self, query: str, 
                       doc_type: Optional[str] = None, 
                       limit: int = 10,
                       use_fts: bool = True) -> List[Dict[str, Any]]:
        """
        Search documents using full-text search or simple keyword matching with caching
        
        Args:
            query: Search query
            doc_type: Filter by document type
            limit: Maximum number of results
            use_fts: Whether to use full-text search (faster and more accurate)
            
        Returns:
            List of matching documents with relevance ranking
        """
        # Create cache key based on search parameters
        cache_key = f"search:docs:{hashlib.md5(f'{query}:{doc_type}:{limit}:{use_fts}'.encode()).hexdigest()}"
        cached_results = cache_get(cache_key)
        if cached_results is not None:
            return cached_results
        
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                results = []
                
                if use_fts:
                    # Use full-text search for better performance and ranking
                    fts_query = query.replace("'", "''")  # Escape single quotes
                    
                    if doc_type:
                        cursor.execute(
                            '''
                            SELECT d.*, rank FROM documents d
                            JOIN documents_fts fts ON d.rowid = fts.rowid
                            WHERE documents_fts MATCH ? AND d.type = ? AND d.is_latest = 1
                            ORDER BY rank LIMIT ?
                            ''',
                            (fts_query, doc_type, limit)
                        )
                    else:
                        cursor.execute(
                            self._prepared_statements['search_documents_fts'],
                            (fts_query, limit)
                        )
                else:
                    # Fallback to LIKE search
                    search_term = f"%{query}%"
                    
                    if doc_type:
                        cursor.execute(
                            '''
                            SELECT * FROM documents 
                            WHERE (title LIKE ? OR content LIKE ?) AND type = ? AND is_latest = 1
                            ORDER BY timestamp DESC LIMIT ?
                            ''',
                            (search_term, search_term, doc_type, limit)
                        )
                    else:
                        cursor.execute(
                            '''
                            SELECT * FROM documents 
                            WHERE (title LIKE ? OR content LIKE ?) AND is_latest = 1
                            ORDER BY timestamp DESC LIMIT ?
                            ''',
                            (search_term, search_term, limit)
                        )
                
                for row in cursor.fetchall():
                    doc = dict(row)
                    
                    # Parse metadata JSON
                    if doc.get('metadata'):
                        doc['metadata'] = json.loads(doc['metadata'])
                    else:
                        doc['metadata'] = {}
                        
                    results.append(doc)
                
                # Cache search results with appropriate tags
                cache_tags = ["search_results"]
                if doc_type:
                    cache_tags.append(f"doc_type:{doc_type}")
                
                cache_set(
                    cache_key,
                    results,
                    ttl=180,  # 3 minutes for search results
                    tags=cache_tags
                )
                    
                return results
                
            except sqlite3.Error as e:
                logger.error(f"Database error searching documents: {e}")
                return []
    
    def delete_document(self, doc_id: str) -> bool:
        """
        Soft delete a document by marking it as not latest
        
        Args:
            doc_id: Document ID
            
        Returns:
            True if successful, False otherwise
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                # Get document info before deletion for cache invalidation
                cursor.execute(self._prepared_statements['get_document'], (doc_id,))
                doc_row = cursor.fetchone()
                
                # Soft delete by marking as not latest
                cursor.execute(self._prepared_statements['delete_document'], (doc_id,))
                
                conn.commit()
                success = cursor.rowcount > 0
                
                if success:
                    # Invalidate caches
                    cache_invalidate_tag(f"document:{doc_id}")
                    if doc_row:
                        doc_type = doc_row['type']
                        cache_invalidate_tag(f"doc_type:{doc_type}")
                    cache_invalidate_tag("recent_documents")
                    cache_invalidate_tag("search_results")
                    
                    logger.info(f"Soft deleted document {doc_id}")
                else:
                    logger.warning(f"Document {doc_id} not found for deletion")
                
                return success
                
            except sqlite3.Error as e:
                conn.rollback()
                logger.error(f"Database error deleting document: {e}")
                return False
    
    def get_recent_documents(self, limit: int = 10, 
                          doc_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get most recent documents using optimized query
        
        Args:
            limit: Maximum number of documents to retrieve
            doc_type: Optional document type filter
            
        Returns:
            List of documents
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                # Use prepared statement with type filter
                cursor.execute(
                    self._prepared_statements['get_recent_documents'],
                    (doc_type, doc_type, limit)
                )
                
                results = []
                for row in cursor.fetchall():
                    doc = dict(row)
                    
                    # Parse metadata JSON
                    if doc.get('metadata'):
                        doc['metadata'] = json.loads(doc['metadata'])
                    else:
                        doc['metadata'] = {}
                        
                    results.append(doc)
                    
                return results
                
            except sqlite3.Error as e:
                logger.error(f"Database error retrieving recent documents: {e}")
                return []

    def get_popular_documents(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most popular documents based on access count
        
        Args:
            limit: Maximum number of documents to retrieve
            
        Returns:
            List of documents ordered by popularity
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute(self._prepared_statements['get_popular_documents'], (limit,))
                
                results = []
                for row in cursor.fetchall():
                    doc = dict(row)
                    
                    # Parse metadata JSON
                    if doc.get('metadata'):
                        doc['metadata'] = json.loads(doc['metadata'])
                    else:
                        doc['metadata'] = {}
                        
                    results.append(doc)
                    
                return results
                
            except sqlite3.Error as e:
                logger.error(f"Database error retrieving popular documents: {e}")
                return []

    def search_chunks(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search document chunks using full-text search
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching chunks with document context
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                fts_query = query.replace("'", "''")  # Escape single quotes
                cursor.execute(self._prepared_statements['search_chunks_fts'], (fts_query, limit))
                
                results = []
                for row in cursor.fetchall():
                    chunk = dict(row)
                    
                    # Parse metadata JSON
                    if chunk.get('metadata'):
                        chunk['metadata'] = json.loads(chunk['metadata'])
                    else:
                        chunk['metadata'] = {}
                        
                    results.append(chunk)
                    
                return results
                
            except sqlite3.Error as e:
                logger.error(f"Database error searching chunks: {e}")
                return []

    def get_document_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics for monitoring and optimization
        
        Returns:
            Dictionary with database statistics
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                stats = {}
                
                # Document counts
                cursor.execute("SELECT COUNT(*) FROM documents WHERE is_latest = 1")
                stats['total_documents'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT type, COUNT(*) FROM documents WHERE is_latest = 1 GROUP BY type")
                stats['documents_by_type'] = dict(cursor.fetchall())
                
                # Chunk statistics
                cursor.execute("SELECT COUNT(*) FROM chunks")
                stats['total_chunks'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT AVG(chunk_count) FROM document_stats")
                avg_chunks = cursor.fetchone()[0]
                stats['avg_chunks_per_document'] = round(avg_chunks, 2) if avg_chunks else 0
                
                # Size statistics
                cursor.execute("SELECT SUM(size), AVG(size) FROM documents WHERE is_latest = 1")
                size_row = cursor.fetchone()
                stats['total_size_bytes'] = size_row[0] or 0
                stats['avg_document_size_bytes'] = round(size_row[1], 2) if size_row[1] else 0
                
                # Access statistics
                cursor.execute("SELECT SUM(access_count), AVG(access_count) FROM document_stats")
                access_row = cursor.fetchone()
                stats['total_accesses'] = access_row[0] or 0
                stats['avg_accesses_per_document'] = round(access_row[1], 2) if access_row[1] else 0
                
                return stats
                
            except sqlite3.Error as e:
                logger.error(f"Database error getting statistics: {e}")
                return {}

    def optimize_database(self) -> bool:
        """
        Optimize database performance by running maintenance operations
        
        Returns:
            True if successful, False otherwise
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                # Analyze tables for query optimization
                cursor.execute("ANALYZE")
                
                # Rebuild FTS indexes
                cursor.execute("INSERT INTO documents_fts(documents_fts) VALUES('rebuild')")
                cursor.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
                
                # Vacuum database to reclaim space
                cursor.execute("VACUUM")
                
                conn.commit()
                logger.info("Database optimization completed successfully")
                return True
                
            except sqlite3.Error as e:
                logger.error(f"Database optimization failed: {e}")
                return False

    def retrieve_relevant_chunks(self, query: str, document_id: Optional[str] = None,
                               max_chunks: int = 10, min_relevance: float = 0.1) -> List[Dict[str, Any]]:
        """
        Retrieve chunks relevant to a query with enhanced relevance scoring
        
        Args:
            query: Search query
            document_id: Optional document ID to limit search
            max_chunks: Maximum number of chunks to return
            min_relevance: Minimum relevance score threshold
            
        Returns:
            List of chunks with relevance scores
        """
        return self._chunk_retriever.retrieve_relevant_chunks(
            query=query,
            document_id=document_id,
            max_chunks=max_chunks,
            min_relevance=min_relevance
        )

    def get_chunk_context(self, chunk_id: str, context_size: int = 2) -> Dict[str, Any]:
        """
        Get chunk with surrounding context chunks
        
        Args:
            chunk_id: Chunk identifier
            context_size: Number of chunks before and after to include
            
        Returns:
            Dictionary with chunk and context
        """
        return self._chunk_retriever.get_chunk_context(chunk_id, context_size)

    def update_document(self, doc_id: str, content: str, title: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Update a document by creating a new version
        
        Args:
            doc_id: Original document ID
            content: New document content
            title: Updated title
            metadata: Updated metadata
            
        Returns:
            New document version ID
        """
        # Get original document
        original_doc = self.get_document(doc_id)
        if not original_doc:
            raise ValueError(f"Document {doc_id} not found")
        
        # Create new version
        timestamp = int(time.time())
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        new_version = original_doc.get('version', 1) + 1
        new_doc_id = f"{doc_id}_v{new_version}"
        
        # Use original metadata as base, update with new values
        combined_metadata = original_doc.get('metadata', {})
        if metadata:
            combined_metadata.update(metadata)
        
        # Calculate statistics
        word_count = len(content.split())
        char_count = len(content)
        size = len(content.encode('utf-8'))
        
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                # Mark old version as not latest
                cursor.execute(
                    "UPDATE documents SET is_latest = 0 WHERE id = ?",
                    (doc_id,)
                )
                
                # Insert new version
                cursor.execute(
                    self._prepared_statements['insert_document'],
                    (new_doc_id, title or original_doc['title'], content, 
                     json.dumps(combined_metadata), original_doc.get('file_path'),
                     timestamp, original_doc['type'], original_doc.get('user_id'),
                     content_hash, size, timestamp, timestamp, new_version, 1)
                )
                
                # Set parent relationship
                cursor.execute(
                    "UPDATE documents SET parent_id = ? WHERE id = ?",
                    (doc_id, new_doc_id)
                )
                
                # Process new chunks
                chunks = self._process_chunks(new_doc_id, content, combined_metadata)
                
                # Update statistics
                cursor.execute(
                    self._prepared_statements['insert_document_stats'],
                    (new_doc_id, word_count, char_count, len(chunks), 0, None)
                )
                
                conn.commit()
                logger.info(f"Updated document {doc_id} to version {new_version} as {new_doc_id}")
                return new_doc_id
                
            except sqlite3.Error as e:
                conn.rollback()
                logger.error(f"Database error updating document: {e}")
                raise

    def get_document_versions(self, doc_id: str) -> List[Dict[str, Any]]:
        """
        Get all versions of a document
        
        Args:
            doc_id: Document ID (any version)
            
        Returns:
            List of document versions ordered by version number
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                # Find the root document ID
                cursor.execute(
                    "SELECT id, parent_id FROM documents WHERE id = ? OR parent_id = ?",
                    (doc_id, doc_id)
                )
                
                root_id = doc_id
                for row in cursor.fetchall():
                    if row['parent_id'] is None:
                        root_id = row['id']
                        break
                
                # Get all versions
                cursor.execute(
                    '''
                    SELECT * FROM documents 
                    WHERE id = ? OR parent_id = ?
                    ORDER BY version ASC
                    ''',
                    (root_id, root_id)
                )
                
                versions = []
                for row in cursor.fetchall():
                    doc = dict(row)
                    if doc.get('metadata'):
                        doc['metadata'] = json.loads(doc['metadata'])
                    versions.append(doc)
                
                return versions
                
            except sqlite3.Error as e:
                logger.error(f"Database error getting document versions: {e}")
                return []

    def advanced_search(self, query: str, 
                       doc_type: Optional[str] = None,
                       limit: int = 10,
                       enable_fuzzy: bool = True,
                       enable_caching: bool = True) -> List[Dict[str, Any]]:
        """
        Perform advanced search with TF-IDF relevance scoring and fuzzy matching
        
        Args:
            query: Search query
            doc_type: Optional document type filter
            limit: Maximum number of results
            enable_fuzzy: Enable fuzzy matching
            enable_caching: Enable result caching
            
        Returns:
            List of search results with enhanced relevance scores
        """
        search_results = self._search_engine.search(
            query=query,
            doc_type=doc_type,
            limit=limit,
            enable_fuzzy=enable_fuzzy,
            enable_caching=enable_caching
        )
        
        # Convert SearchResult objects to dictionaries for consistency
        return [
            {
                'id': result.document_id,
                'title': result.title,
                'content': result.content,
                'type': result.doc_type,
                'relevance_score': result.relevance_score,
                'match_highlights': result.match_highlights,
                'matched_terms': result.matched_terms,
                'snippet': result.snippet,
                'metadata': result.metadata,
                'timestamp': result.timestamp
            }
            for result in search_results
        ]

    def get_search_suggestions(self, partial_query: str, limit: int = 5) -> List[str]:
        """
        Get search suggestions based on partial query
        
        Args:
            partial_query: Partial search query
            limit: Maximum number of suggestions
            
        Returns:
            List of search suggestions
        """
        return self._search_engine.get_search_suggestions(partial_query, limit)

    def search_with_filters(self, query: str, filters: Dict[str, Any], 
                          limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search documents with advanced filters
        
        Args:
            query: Search query
            filters: Dictionary of filters (type, date_range, user_id, etc.)
            limit: Maximum number of results
            
        Returns:
            List of filtered search results
        """
        # Build filter query
        filter_parts = []
        filter_values = []
        
        base_query = '''
            SELECT d.*, rank FROM documents d
            JOIN documents_fts fts ON d.rowid = fts.rowid
            WHERE documents_fts MATCH ? AND d.is_latest = 1
        '''
        
        # Add type filter
        if filters.get('type'):
            filter_parts.append("d.type = ?")
            filter_values.append(filters['type'])
        
        # Add user filter
        if filters.get('user_id'):
            filter_parts.append("d.user_id = ?")
            filter_values.append(filters['user_id'])
        
        # Add date range filter
        if filters.get('date_from'):
            filter_parts.append("d.timestamp >= ?")
            filter_values.append(int(filters['date_from']))
        
        if filters.get('date_to'):
            filter_parts.append("d.timestamp <= ?")
            filter_values.append(int(filters['date_to']))
        
        # Add size filter
        if filters.get('min_size'):
            filter_parts.append("d.size >= ?")
            filter_values.append(filters['min_size'])
        
        if filters.get('max_size'):
            filter_parts.append("d.size <= ?")
            filter_values.append(filters['max_size'])
        
        # Combine filters
        if filter_parts:
            base_query += " AND " + " AND ".join(filter_parts)
        
        base_query += " ORDER BY rank LIMIT ?"
        
        # Execute query
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                fts_query = query.replace("'", "''")
                query_params = [fts_query] + filter_values + [limit]
                
                cursor.execute(base_query, query_params)
                
                results = []
                for row in cursor.fetchall():
                    doc = dict(row)
                    
                    # Parse metadata JSON
                    if doc.get('metadata'):
                        doc['metadata'] = json.loads(doc['metadata'])
                    else:
                        doc['metadata'] = {}
                        
                    results.append(doc)
                
                return results
                
            except sqlite3.Error as e:
                logger.error(f"Database error in filtered search: {e}")
                return []

    def get_search_analytics(self) -> Dict[str, Any]:
        """
        Get search analytics and performance metrics
        
        Returns:
            Dictionary with search analytics
        """
        # Get cache statistics
        cache_stats = self._cache.get_stats()
        
        # Get database statistics
        db_stats = self.get_document_statistics()
        
        # Combine analytics
        analytics = {
            'cache_performance': {
                'hit_rate': cache_stats['global']['hit_rate'],
                'total_hits': cache_stats['global']['hits'],
                'total_misses': cache_stats['global']['misses']
            },
            'database_stats': db_stats,
            'search_index_stats': {
                'fts_enabled': True,
                'total_indexed_documents': db_stats.get('total_documents', 0),
                'total_indexed_chunks': db_stats.get('total_chunks', 0)
            }
        }
        
        return analytics

    def rebuild_search_index(self) -> bool:
        """
        Rebuild full-text search indexes for better performance
        
        Returns:
            True if successful, False otherwise
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                logger.info("Rebuilding search indexes...")
                
                # Rebuild document FTS index
                cursor.execute("INSERT INTO documents_fts(documents_fts) VALUES('rebuild')")
                
                # Rebuild chunks FTS index
                cursor.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
                
                # Optimize FTS indexes
                cursor.execute("INSERT INTO documents_fts(documents_fts) VALUES('optimize')")
                cursor.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('optimize')")
                
                conn.commit()
                
                # Invalidate search-related caches
                cache_invalidate_tag("search_results")
                cache_invalidate_tag("tfidf_stats")
                
                logger.info("Search indexes rebuilt successfully")
                return True
                
            except sqlite3.Error as e:
                logger.error(f"Failed to rebuild search indexes: {e}")
                return False
