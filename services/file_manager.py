from typing import Dict, List
from datetime import datetime
import traceback
from pathlib import Path
from flask import current_app
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class FileManagerError(Exception):
    """Custom exception for FileManager errors"""
    pass

class FileManager:
    """Handle file storage and retrieval with vector search"""

    def __init__(self):
        """Initialize with Flask app context"""
        self.document_store = {}
        self.vectorizer = TfidfVectorizer(
            strip_accents='unicode',
            max_features=10000,
            stop_words='english'
        )
        self.vector_store = None
        self.total_documents = 0
        self.total_size = 0

        # Register with Flask app
        current_app.file_manager = self
        current_app.logger.info("FileManager initialized and registered with app")

    def get_stats(self) -> Dict:
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

    def list_documents(self) -> List[Dict]:
        """Get list of available documents"""
        return [
            {
                'filename': filename,
                'size': len(doc['content']),
                'timestamp': doc['timestamp']
            }
            for filename, doc in self.document_store.items()
        ]

    def _update_vectors(self) -> None:
        """Update document vectors with error handling"""
        try:
            if not self.document_store:
                self.vector_store = None
                return

            texts = [doc['content'] for doc in self.document_store.values()]
            self.vector_store = self.vectorizer.fit_transform(texts)
            current_app.logger.debug(f"Updated vectors for {len(texts)} documents")

        except Exception as e:
            current_app.logger.error(f"Vector update error: {str(e)}")
            self.vector_store = None
            raise FileManagerError(f"Failed to update vectors: {str(e)}")

    def search_documents(self, query: str, top_n: int = 3) -> List[Dict]:
        """Search documents by similarity with proper array handling"""
        try:
            if not self.document_store or self.vector_store is None:
                return []

            # Transform query and get raw similarities
            query_vector = self.vectorizer.transform([query])
            similarity_matrix = cosine_similarity(query_vector, self.vector_store)
            similarities = similarity_matrix[0]  # Get the first row as a flat array

            # Get indices of documents above threshold
            threshold = 0.1
            valid_indices = [
                i for i, score in enumerate(similarities)
                if score > threshold
            ]

            # Sort by similarity score
            scored_indices = [
                (i, similarities[i]) for i in valid_indices
            ]
            scored_indices.sort(key=lambda x: x[1], reverse=True)

            # Get top N results
            documents = []
            filenames = list(self.document_store.keys())

            for idx, score in scored_indices[:top_n]:
                filename = filenames[idx]
                documents.append({
                    'filename': filename,
                    'content': self.document_store[filename]['content'],
                    'similarity': float(score)
                })

            return documents

        except Exception as e:
            current_app.logger.error(f"Search error: {str(e)}")
            return []

    def get_document(self, filename: str) -> Dict:
        """Get a document by filename"""
        if filename not in self.document_store:
            raise KeyError(f"Document not found: {filename}")
        return self.document_store[filename]
