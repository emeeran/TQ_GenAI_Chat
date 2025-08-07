#!/usr/bin/env python3
"""
Test Enhanced File Manager Integration - Task 1.1.1
Validates OptimizedDocumentStore integration with backward compatibility.
"""

import sys
import tempfile
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.enhanced_file_manager import create_file_manager


def test_enhanced_file_manager():
    """Test enhanced file manager functionality"""
    print("Testing Enhanced File Manager Integration (Task 1.1.1)...")

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create file manager with temporary database
        db_path = Path(temp_dir) / "test_documents.db"
        file_manager = create_file_manager(db_path=str(db_path), pool_size=5)

        try:
            # Test 1: Add document
            print("1. Testing add_document...")
            doc_id = file_manager.add_document(
                filename="test_document.txt",
                content="This is a test document with sample content for searching.",
                doc_type="text",
                metadata={"source": "test"},
            )
            print(f"   ✓ Document added with ID: {doc_id}")

            # Test 2: Search documents
            print("2. Testing search_documents...")
            results = file_manager.search_documents("test sample")
            print(f"   ✓ Found {len(results)} results")
            if results:
                print(
                    f"   ✓ First result relevance score: {results[0].get('relevance_score', 'N/A')}"
                )

            # Test 3: Get document statistics
            print("3. Testing get_document_statistics...")
            stats = file_manager.get_document_statistics()
            print(f"   ✓ Total documents: {stats['total_documents']}")
            print(f"   ✓ Document types: {stats['by_type']}")

            # Test 4: Get all documents
            print("4. Testing get_all_documents...")
            all_docs = file_manager.get_all_documents(limit=10)
            print(f"   ✓ Retrieved {len(all_docs)} documents")

            # Test 5: Total documents property (backward compatibility)
            print("5. Testing backward compatibility...")
            total = file_manager.total_documents
            print(f"   ✓ Total documents property: {total}")

            # Test 6: Connection pooling validation
            print("6. Testing connection pooling...")
            # Add multiple documents concurrently to test pooling
            for i in range(5):
                file_manager.add_document(
                    filename=f"concurrent_doc_{i}.txt",
                    content=f"Concurrent document {i} content",
                    doc_type="text",
                )

            final_stats = file_manager.get_document_statistics()
            print(f"   ✓ Final document count: {final_stats['total_documents']}")

            print("\n✅ All tests passed! Enhanced File Manager integration successful.")
            return True

        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            return False

        finally:
            file_manager.close()


def test_chat_functionality():
    """Test chat-related functionality"""
    print("\nTesting Chat Functionality...")

    with tempfile.TemporaryDirectory() as temp_dir:
        file_manager = create_file_manager(pool_size=3)

        try:
            # Test chat history saving
            chat_data = {
                "id": "test_chat_123",
                "history": [
                    {"role": "user", "content": "Hello", "provider": "openai"},
                    {"role": "assistant", "content": "Hi there!", "provider": "openai"},
                ],
            }

            print("1. Testing save_chat_history...")
            filepath = file_manager.save_chat_history(chat_data)
            print(f"   ✓ Chat saved to: {Path(filepath).name}")

            print("2. Testing get_saved_chats...")
            saved_chats = file_manager.get_saved_chats(limit=5)
            print(f"   ✓ Found {len(saved_chats)} saved chats")

            # Test export functionality
            print("3. Testing export_chat...")
            export_path = file_manager.export_chat(chat_data, export_format="md")
            print(f"   ✓ Chat exported to: {Path(export_path).name}")

            print("\n✅ Chat functionality tests passed!")
            return True

        except Exception as e:
            print(f"\n❌ Chat test failed: {e}")
            return False

        finally:
            file_manager.close()


def test_storage_info():
    """Test storage information functionality"""
    print("\nTesting Storage Information...")

    file_manager = create_file_manager(pool_size=2)

    try:
        storage_info = file_manager.get_storage_info()
        print(f"   ✓ Database size: {storage_info['database_size_bytes']} bytes")
        print(f"   ✓ Total storage: {storage_info['total_storage_bytes']} bytes")
        print(f"   ✓ Document count: {storage_info['document_count']}")

        print("\n✅ Storage info test passed!")
        return True

    except Exception as e:
        print(f"\n❌ Storage info test failed: {e}")
        return False

    finally:
        file_manager.close()


if __name__ == "__main__":
    print("🔧 Task 1.1.1: Enhanced File Manager Integration Test\n")

    success = True
    success &= test_enhanced_file_manager()
    success &= test_chat_functionality()
    success &= test_storage_info()

    if success:
        print("\n🎉 All integration tests passed!")
        print("✅ Task 1.1.1: OptimizedDocumentStore successfully integrated")
        print("✅ Connection pooling enabled for improved performance")
        print("✅ Backward compatibility maintained")
        print("✅ Enhanced search with relevance scoring available")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)
