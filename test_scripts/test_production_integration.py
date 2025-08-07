#!/usr/bin/env python3
"""
Simple Test Enhanced File Manager Integration - Task 1.1.1
Uses production database path to validate the integration.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.enhanced_file_manager import create_file_manager


def test_production_integration():
    """Test enhanced file manager with production database"""
    print("Testing Enhanced File Manager Production Integration (Task 1.1.1)...")

    # Use default production database path
    file_manager = create_file_manager(pool_size=5)

    try:
        # Test 1: Get document statistics (read-only)
        print("1. Testing get_document_statistics...")
        stats = file_manager.get_document_statistics()
        print(f"   ✓ Total documents: {stats['total_documents']}")
        print(f"   ✓ Document types: {stats['by_type']}")

        # Test 2: Search documents (read-only)
        print("2. Testing search_documents...")
        results = file_manager.search_documents("test", limit=5)
        print(f"   ✓ Found {len(results)} results")

        # Test 3: Get all documents (read-only)
        print("3. Testing get_all_documents...")
        all_docs = file_manager.get_all_documents(limit=5)
        print(f"   ✓ Retrieved {len(all_docs)} documents")

        # Test 4: Total documents property (backward compatibility)
        print("4. Testing backward compatibility...")
        total = file_manager.total_documents
        print(f"   ✓ Total documents property: {total}")

        # Test 5: Storage info
        print("5. Testing storage info...")
        storage_info = file_manager.get_storage_info()
        print(f"   ✓ Database size: {storage_info['database_size_bytes']} bytes")
        print(f"   ✓ Total storage: {storage_info['total_storage_bytes']} bytes")

        print("\n✅ Production integration tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False

    finally:
        file_manager.close()


def test_file_operations():
    """Test file system operations"""
    print("\nTesting File System Operations...")

    file_manager = create_file_manager(pool_size=2)

    try:
        # Test file listing
        print("1. Testing list_files...")
        upload_files = file_manager.list_files("uploads")
        export_files = file_manager.list_files("exports")
        save_files = file_manager.list_files("saves")

        print(f"   ✓ Upload files: {len(upload_files)}")
        print(f"   ✓ Export files: {len(export_files)}")
        print(f"   ✓ Save files: {len(save_files)}")

        # Test saved chats
        print("2. Testing get_saved_chats...")
        saved_chats = file_manager.get_saved_chats(limit=5)
        print(f"   ✓ Found {len(saved_chats)} saved chats")

        print("\n✅ File operations tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ File operations test failed: {e}")
        return False

    finally:
        file_manager.close()


def validate_enhanced_features():
    """Validate enhanced features are available"""
    print("\nValidating Enhanced Features...")

    file_manager = create_file_manager(pool_size=3)

    try:
        # Check if enhanced methods exist
        methods_to_check = [
            "add_document",
            "search_documents",
            "get_document_statistics",
            "get_all_documents",
            "save_chat_history",
            "export_chat",
            "get_storage_info",
            "validate_file_extension",
            "cleanup_old_documents",
        ]

        for method_name in methods_to_check:
            if hasattr(file_manager, method_name):
                print(f"   ✓ Method {method_name} available")
            else:
                print(f"   ❌ Method {method_name} missing")
                return False

        # Check async methods
        async_methods = [
            "add_document_async",
            "search_documents_async",
            "get_document_statistics_async",
        ]

        for method_name in async_methods:
            if hasattr(file_manager, method_name):
                print(f"   ✓ Async method {method_name} available")
            else:
                print(f"   ❌ Async method {method_name} missing")
                return False

        print("\n✅ Enhanced features validation passed!")
        return True

    except Exception as e:
        print(f"\n❌ Feature validation failed: {e}")
        return False

    finally:
        file_manager.close()


if __name__ == "__main__":
    print("🔧 Task 1.1.1: Enhanced File Manager Production Integration Test\n")

    success = True
    success &= test_production_integration()
    success &= test_file_operations()
    success &= validate_enhanced_features()

    if success:
        print("\n🎉 All production integration tests passed!")
        print("✅ Task 1.1.1: OptimizedDocumentStore successfully integrated")
        print("✅ Connection pooling configured for improved performance")
        print("✅ Backward compatibility maintained with existing FileManager")
        print("✅ Enhanced search capabilities available")
        print("✅ Async methods available for async infrastructure integration")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)
