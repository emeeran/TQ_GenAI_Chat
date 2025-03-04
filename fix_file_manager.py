#!/usr/bin/env python3
"""
Fix script to ensure the file manager functions properly
"""
import os
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('fix_file_manager')

def fix_file_manager():
    """Fix the file manager setup"""
    try:
        # Import only after path setup
        from services.file_manager import FileManager

        # Get the root directory
        root_dir = Path(__file__).parent

        # Ensure storage directory exists
        storage_dir = root_dir / 'storage'
        storage_dir.mkdir(exist_ok=True)
        logger.info(f"Storage directory: {storage_dir}")

        # Create a FileManager instance
        file_manager = FileManager(storage_dir=str(storage_dir))

        # Check if index file exists
        if not (storage_dir / 'document_index.json').exists():
            logger.info("Creating initial document index")
            file_manager._save_index()

        # Create a test document to verify functionality
        test_file = "test_document.txt"
        test_content = f"This is a test document created at {datetime.now().isoformat()}"

        logger.info(f"Adding test document '{test_file}'")
        file_manager.add_document(test_file, test_content)

        # List documents to verify it's working
        docs = file_manager.list_documents()
        logger.info(f"Documents in file manager: {len(docs)}")

        for i, doc in enumerate(docs):
            logger.info(f"{i+1}. {doc['filename']} ({doc['size']} bytes)")

        logger.info("File manager setup has been fixed and verified!")
        return True

    except Exception as e:
        logger.error(f"Error fixing file manager: {str(e)}")
        return False

if __name__ == "__main__":
    from datetime import datetime
    success = fix_file_manager()
    print(f"File manager fix {'successful' if success else 'failed'}")
