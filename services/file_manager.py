import os
import json
import time
from pathlib import Path
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
from collections import OrderedDict
import hashlib
from sklearn.metrics.pairwise import cosine_similarity
import concurrent.futures
from flask import current_app
from utils.caching import LRUCache
from functools import lru_cache

class FileManagerError(Exception):
    """Exception raised for FileManager errors."""
    pass

class FileManager:
    """Manages the storage and retrieval of uploaded files and their contents."""

    def __init__(self, storage_dir: str = None, max_files: int = 100):
        """Initialize FileManager.

        Args:
            storage_dir: Directory to store processed files
            max_files: Maximum number of files to keep in memory
        """
        self.logger = logging.getLogger(__name__)
        self.storage_dir = storage_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), 'storage')
        os.makedirs(self.storage_dir, exist_ok=True)

        self.index_path = os.path.join(self.storage_dir, 'document_index.json')
        self.documents = OrderedDict()  # {filename: {content, timestamp, metadata}}
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.document_vectors = {}
        self.max_files = max_files
        self.total_documents = 0
        self.total_size = 0

        # Load existing index if available
        self._load_index()

    def _load_index(self):
        """Load document index from disk."""
        try:
            if os.path.exists(self.index_path):
                with open(self.index_path, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                    self.total_documents = index_data.get('total_documents', 0)
                    self.total_size = index_data.get('total_size', 0)

                    # Load documents metadata but not content
                    for filename, metadata in index_data.get('documents', {}).items():
                        file_path = os.path.join(self.storage_dir, metadata.get('hash', filename))
                        if os.path.exists(file_path):
                            self.documents[filename] = {
                                'timestamp': metadata.get('timestamp', datetime.now().isoformat()),
                                'metadata': metadata.get('metadata', {}),
                                'size': metadata.get('size', 0),
                                'hash': metadata.get('hash', ''),
                                'content': None  # Content loaded on demand
                            }

                self.logger.info(f"Loaded index with {len(self.documents)} documents")
                if self.documents:
                    # Initialize vectorizer with document content
                    self._build_vectors()
        except Exception as e:
            self.logger.error(f"Error loading document index: {str(e)}")
            # Continue with empty documents if index is corrupted

    def _save_index(self):
        """Save document index to disk."""
        try:
            index_data = {
                'total_documents': self.total_documents,
                'total_size': self.total_size,
                'documents': {
                    filename: {
                        'timestamp': doc.get('timestamp'),
                        'metadata': doc.get('metadata', {}),
                        'size': doc.get('size', 0),
                        'hash': doc.get('hash', '')
                    } for filename, doc in self.documents.items()
                }
            }

            # Create a temp file first to prevent corruption
            temp_path = self.index_path + ".tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)

            # Replace the original file
            os.replace(temp_path, self.index_path)
            self.logger.info(f"Saved document index with {len(self.documents)} documents")
        except Exception as e:
            self.logger.error(f"Error saving document index: {str(e)}")

    def _get_file_hash(self, content: str) -> str:
        """Generate a hash for the file content."""
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def add_document(self, filename: str, content: str, metadata: Dict = None) -> bool:
        """Add a document to the manager.

        Args:
            filename: Name of the file
            content: Text content of the file
            metadata: Additional metadata about the file

        Returns:
            bool: True if successful
        """
        try:
            # Generate a hash for deduplication and efficient storage
            file_hash = self._get_file_hash(content)

            # Check if this exact content already exists
            for doc_name, doc_data in self.documents.items():
                if doc_data.get('hash') == file_hash:
                    self.logger.info(f"Document with same content already exists as {doc_name}")
                    # Update the filename if it's different but content is the same
                    if filename != doc_name:
                        self.documents[filename] = self.documents[doc_name].copy()
                        return True

            # Store document content to disk
            file_path = os.path.join(self.storage_dir, file_hash)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # Add to document collection
            self.documents[filename] = {
                'timestamp': datetime.now().isoformat(),
                'metadata': metadata or {},
                'content': content,
                'size': len(content),
                'hash': file_hash
            }

            # Update stats
            self.total_documents = len(self.documents)
            self.total_size += len(content)

            # Rebuild the search vectors
            self._build_vectors()

            # Save the index
            self._save_index()

            # If we exceed the max files, remove the oldest ones
            if len(self.documents) > self.max_files:
                oldest_file = next(iter(self.documents))
                self._remove_document(oldest_file)

            return True

        except Exception as e:
            self.logger.error(f"Error adding document {filename}: {str(e)}")
            raise FileManagerError(f"Failed to add document: {str(e)}")

    def _remove_document(self, filename: str) -> bool:
        """Remove a document from the manager."""
        try:
            if filename in self.documents:
                file_hash = self.documents[filename].get('hash')
                file_path = os.path.join(self.storage_dir, file_hash)

                # Check if other documents reference the same content
                other_refs = False
                for doc_name, doc_data in self.documents.items():
                    if doc_name != filename and doc_data.get('hash') == file_hash:
                        other_refs = True
                        break

                # If no other documents reference this content, delete the file
                if not other_refs and os.path.exists(file_path):
                    os.remove(file_path)

                # Update stats
                self.total_size -= self.documents[filename].get('size', 0)

                # Remove from documents collection
                del self.documents[filename]
                self.total_documents = len(self.documents)

                # Rebuild the search vectors
                self._build_vectors()

                # Save the index
                self._save_index()

                return True
            return False
        except Exception as e:
            self.logger.error(f"Error removing document {filename}: {str(e)}")
            return False

    def get_document(self, filename: str) -> Dict:
        """Get a document by filename.

        Args:
            filename: Name of the file

        Returns:
            dict: Document data including content

        Raises:
            KeyError: If document is not found
        """
        if filename not in self.documents:
            raise KeyError(f"Document '{filename}' not found")

        doc = self.documents[filename]

        # Load content on demand if not already loaded
        if doc.get('content') is None:
            try:
                file_path = os.path.join(self.storage_dir, doc.get('hash', filename))
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        doc['content'] = f.read()
                else:
                    raise FileManagerError(f"Document content file not found: {file_path}")
            except Exception as e:
                self.logger.error(f"Error loading document content for {filename}: {str(e)}")
                raise FileManagerError(f"Failed to load document content: {str(e)}")

        return doc

    def get_document_preview(self, filename: str, max_length: int = 1000) -> Dict:
        """Get a preview of a document (with truncated content).

        Args:
            filename: Name of the file
            max_length: Maximum length of content preview

        Returns:
            dict: Document preview data
        """
        doc = self.get_document(filename)
        content = doc.get('content', '')

        # Create a preview of the content
        if len(content) > max_length:
            preview = content[:max_length] + "..."
        else:
            preview = content

        return {
            'filename': filename,
            'preview': preview,
            'timestamp': doc.get('timestamp'),
            'size': doc.get('size', len(content)),
            'metadata': doc.get('metadata', {})
        }

    def _build_vectors(self):
        """Build TF-IDF vectors for all documents."""
        try:
            if not self.documents:
                return

            # Get all document content
            doc_contents = []
            doc_names = []

            for filename, doc_data in self.documents.items():
                # Load content if needed
                if doc_data.get('content') is None:
                    try:
                        file_path = os.path.join(self.storage_dir, doc_data.get('hash', filename))
                        if os.path.exists(file_path):
                            with open(file_path, 'r', encoding='utf-8') as f:
                                doc_data['content'] = f.read()
                    except Exception as e:
                        self.logger.warning(f"Could not load content for {filename}: {str(e)}")
                        continue

                if doc_data.get('content'):
                    doc_contents.append(doc_data['content'])
                    doc_names.append(filename)

            if not doc_contents:
                return

            # Fit TF-IDF vectorizer on document contents
            self.vectorizer.fit(doc_contents)

            # Transform documents to vector space
            tfidf_matrix = self.vectorizer.transform(doc_contents)

            # Store document vectors by filename
            self.document_vectors = {
                doc_names[i]: tfidf_matrix[i] for i in range(len(doc_names))
            }

        except Exception as e:
            self.logger.error(f"Error building document vectors: {str(e)}")

    def search_documents(self, query: str, top_n: int = 3) -> List[Dict]:
        """Search for documents relevant to a query.

        Args:
            query: Search query
            top_n: Number of top results to return

        Returns:
            list: List of document results with similarity scores
        """
        try:
            if not self.documents or not query or not self.document_vectors:
                return []

            # Transform query to TF-IDF vector
            query_vector = self.vectorizer.transform([query])

            # Calculate cosine similarity between query and documents
            results = []
            for filename, doc_vector in self.document_vectors.items():
                similarity = (query_vector * doc_vector.T).toarray()[0][0]
                if similarity > 0:
                    doc = self.get_document(filename)
                    results.append({
                        'filename': filename,
                        'content': doc.get('content', ''),
                        'similarity': similarity
                    })

            # Sort by similarity score (descending)
            results.sort(key=lambda x: x['similarity'], reverse=True)

            # Return top N results
            return results[:top_n]

        except Exception as e:
            self.logger.error(f"Error searching documents: {str(e)}")
            return []

    def list_documents(self) -> List[Dict]:
        """List all documents with metadata but without content.

        Returns:
            list: List of document metadata
        """
        return [
            {
                'filename': filename,
                'timestamp': doc.get('timestamp'),
                'size': doc.get('size', 0),
                'metadata': doc.get('metadata', {})
            }
            for filename, doc in self.documents.items()
        ]

    def get_stats(self) -> Dict:
        """Get statistics about the document collection.

        Returns:
            dict: Statistics about documents
        """
        return {
            'total_documents': self.total_documents,
            'total_size': self.total_size,
            'storage_path': self.storage_dir
        }

    def clear_documents(self) -> bool:
        """Clear all documents.

        Returns:
            bool: True if successful
        """
        try:
            for filename in list(self.documents.keys()):
                self._remove_document(filename)
            return True
        except Exception as e:
            self.logger.error(f"Error clearing documents: {str(e)}")
            return False
