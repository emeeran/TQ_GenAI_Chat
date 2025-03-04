#!/usr/bin/env python3
"""
Debug tool to diagnose and fix document listing issues
"""
import os
import json
from pathlib import Path

def debug_file_manager():
    """Debug the file manager system"""
    print("Debugging file manager...")

    # Find the storage directory
    root_dir = Path(__file__).parent
    storage_dir = root_dir / 'storage'

    print(f"Storage directory: {storage_dir}")
    print(f"Storage exists: {storage_dir.exists()}")
    print(f"Storage is dir: {storage_dir.is_dir() if storage_dir.exists() else False}")

    # Check for document index
    index_path = storage_dir / 'document_index.json'
    print(f"Index file: {index_path}")
    print(f"Index exists: {index_path.exists()}")

    # Read index if it exists
    if index_path.exists():
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)

            doc_count = len(index_data.get('documents', {}))
            total_docs = index_data.get('total_documents', 0)

            print(f"Documents in index: {doc_count}")
            print(f"Total documents reported: {total_docs}")

            # Check if document files exist
            for filename, doc_data in index_data.get('documents', {}).items():
                file_hash = doc_data.get('hash', filename)
                file_path = storage_dir / file_hash

                print(f"Document: {filename}")
                print(f"  Hash: {file_hash}")
                print(f"  Size: {doc_data.get('size', 0)} bytes")
                print(f"  File exists: {file_path.exists()}")
        except Exception as e:
            print(f"Error reading index: {str(e)}")

    # List all files in the storage directory
    if storage_dir.exists() and storage_dir.is_dir():
        print("\nFiles in storage directory:")

        for item in os.listdir(storage_dir):
            if item == 'document_index.json':
                continue

            item_path = storage_dir / item
            if item_path.is_file():
                print(f"  {item} ({item_path.stat().st_size} bytes)")

    # Attempt to fix issues
    if not storage_dir.exists():
        storage_dir.mkdir(parents=True)
        print("Created storage directory")

    if not index_path.exists() or not os.path.getsize(index_path):
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump({
                'total_documents': 0,
                'total_size': 0,
                'documents': {}
            }, f, indent=2)

        print("Created empty document index")

if __name__ == "__main__":
    debug_file_manager()

    # Optional: Import and test file_manager module if available
    try:
        import sys
        sys.path.append(os.path.dirname(__file__))

        from services.file_manager import FileManager

        fm = FileManager()
        print("\nUsing FileManager module:")
        print(f"Storage dir: {fm.storage_dir}")
        print(f"Document count: {fm.total_documents}")

        docs = fm.list_documents()
        print(f"Documents found: {len(docs)}")

        for i, doc in enumerate(docs):
            print(f"  {i+1}. {doc['filename']} ({doc['size']} bytes)")

    except ImportError:
        print("Could not import FileManager module")
    except Exception as e:
        print(f"Error using FileManager: {str(e)}")
