import concurrent.futures
from datetime import datetime
from functools import lru_cache

import numpy as np
from flask import current_app
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from utils.caching import LRUCache


class FileManagerError(Exception):
    """Custom exception for FileManager errors"""
    pass

class FileManager:
    """Optimized file storage and vector search"""

    def __init__(self):
        self.document_store = {}
        self.vector_store = None
        self.total_documents = 0
        self.total_size = 0

        # Optimized vectorizer
        self.vectorizer = TfidfVectorizer(
            strip_accents='unicode',
            max_features=10000,
            stop_words='english',
            dtype=np.float32  # Use float32 for better memory usage
        )

        # Replace lru_cache_extended with our custom LRUCache
        self.search_cache = LRUCache(maxsize=1000, ttl=300)

        # Initialize thread pool
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)

        current_app.file_manager = self
        current_app.logger.info("FileManager initialized and registered with app")

    def get_stats(self) -> dict:
        """Get current document store statistics"""
        return {
            'total_documents': self.total_documents,
            'total_size': self.total_size,
            'documents': [
                {
                    'filename': filename,
                    'size': len(doc['content']),
                    'timestamp': doc['timestamp']
                }
                for filename, doc in self.document_store.items()
            ]
        }

    def add_document(self, filename: str, content: str) -> None:
        """Add or update a document with improved tracking"""
        try:
            if not content:
                raise FileManagerError("Empty content")

            # Update stats
            if filename not in self.document_store:
                self.total_documents += 1
            else:
                self.total_size -= len(self.document_store[filename]['content'])

            self.document_store[filename] = {
                'content': content,
                'timestamp': datetime.now().isoformat()
            }
            self.total_size += len(content)

            self._update_vectors()
            current_app.logger.info(f"Added document: {filename} (size: {len(content)} bytes)")

        except Exception as e:
            current_app.logger.error(f"Error adding document {filename}: {str(e)}")
            raise FileManagerError(f"Failed to add document: {str(e)}")

    def list_documents(self) -> list[dict]:
        """Get list of available documents with previews"""
        return [
            {
                'filename': filename,
                'size': len(doc['content']),
                'timestamp': doc['timestamp'],
                'preview': doc['content'][:200] + '...' if len(doc['content']) > 200 else doc['content']
            }
            for filename, doc in self.document_store.items()
        ]

    def _update_vectors(self) -> None:
        """Update document vectors with error handling"""
        try:
            self.vector_store = None
            return

            texts = [doc['content'] for doc in self.document_store.values()]
            self.vector_store = self.vectorizer.fit_transform(texts)
            current_app.logger.debug(f"Updated vectors for {len(texts)} documents")

        except Exception as e:
            current_app.logger.error(f"Vector update error: {str(e)}")
            self.vector_store = None
            raise FileManagerError(f"Failed to update vectors: {str(e)}")

    @lru_cache(maxsize=100)
    def _compute_similarity(self, query_vector, doc_vector) -> float:
        """Cached similarity computation"""
        return float(cosine_similarity(query_vector, doc_vector)[0, 0])

    def search_documents(self, query: str, top_n: int = 3) -> list[dict]:
        """Optimized vector search with caching"""
        cache_key = f"{query}:{top_n}"

        # Use our custom cache
        if cache_key in self.search_cache:
            return self.search_cache.get(cache_key)

        if not self.document_store or self.vector_store is None:
            return []

        try:
            # Transform query
            query_vector = self.vectorizer.transform([query])

            # Compute similarities in parallel
            futures = []
            for i in range(self.vector_store.shape[0]):
                doc_vector = self.vector_store[i:i+1]
                futures.append(
                    self.pool.submit(self._compute_similarity, query_vector, doc_vector)
                )

            # Collect results
            similarities = [f.result() for f in futures]

            # Get top results
            threshold = 0.1
            scored_indices = [
                (i, score) for i, score in enumerate(similarities)
                if score > threshold
            ]
            scored_indices.sort(key=lambda x: x[1], reverse=True)

            filenames = list(self.document_store.keys())
            results = []

            for idx, score in scored_indices[:top_n]:
                filename = filenames[idx]
                results.append({
                    'filename': filename,
                    'content': self.document_store[filename]['content'],
                    'similarity': score
                })

            # Cache results with our custom cache
            self.search_cache.set(cache_key, results)
            return results

        except Exception as e:
            current_app.logger.error(f"Search error: {str(e)}")
            return []

    def get_document(self, filename: str) -> dict:
        """Get a document by filename"""
        if filename not in self.document_store:
            raise KeyError(f"Document not found: {filename}")
        return self.document_store[filename]
