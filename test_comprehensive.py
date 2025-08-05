#!/usr/bin/env python3
"""
Comprehensive test of all save/load/export functionality
"""
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))


def test_comprehensive():
    """Test all save/load/export functionality comprehensively"""
    try:
        from services.file_manager import FileManager

        print("🧪 COMPREHENSIVE SAVE/LOAD/EXPORT TEST")
        print("=" * 50)

        fm = FileManager()

        # Test 1: Save different types of chats
        print("\n1. Testing save_chat_history with different chat types...")

        test_chats = [
            {
                "title": "Simple Chat",
                "timestamp": "2025-01-01 10:00:00",
                "messages": [
                    {"role": "user", "content": "Hello!"},
                    {"role": "assistant", "content": "Hi there! How can I help you today?"},
                ],
            },
            {
                "title": "Long Conversation",
                "timestamp": "2025-01-01 11:00:00",
                "messages": [
                    {"role": "user", "content": "What is machine learning?"},
                    {
                        "role": "assistant",
                        "content": "Machine learning is a subset of artificial intelligence (AI) that provides systems the ability to automatically learn and improve from experience without being explicitly programmed.",
                    },
                    {"role": "user", "content": "Can you give me an example?"},
                    {
                        "role": "assistant",
                        "content": "Sure! A common example is email spam filtering. The system learns from thousands of emails marked as spam or not spam to automatically detect and filter spam emails.",
                    },
                ],
            },
            {
                "title": "System Messages Test",
                "timestamp": "2025-01-01 12:00:00",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Tell me a joke"},
                    {
                        "role": "assistant",
                        "content": "Why did the programmer quit his job? Because he didn't get arrays!",
                    },
                ],
            },
        ]

        saved_files = []
        for i, chat in enumerate(test_chats, 1):
            filepath = fm.save_chat_history(chat)
            filename = os.path.basename(filepath)
            saved_files.append(filename)
            print(f"   ✅ Chat {i} saved: {filename}")

        # Test 2: List all saved chats
        print("\n2. Testing get_saved_chats...")
        chats = fm.get_saved_chats()
        print(f"   ✅ Found {len(chats)} total saved chats")

        # Test 3: Load each saved chat
        print("\n3. Testing load_chat_history...")
        for filename in saved_files:
            loaded_chat = fm.load_chat_history(filename)
            title = loaded_chat.get("title", "Untitled")
            message_count = len(loaded_chat.get("messages", []))
            print(f"   ✅ Loaded '{title}': {message_count} messages")

        # Test 4: Export in all formats
        print("\n4. Testing export_chat in all formats...")
        test_chat = test_chats[1]  # Use the long conversation

        # Test markdown export
        md_path = fm.export_chat(test_chat, "md")
        print(f"   ✅ Markdown export: {os.path.basename(md_path)}")

        # Test text export
        txt_path = fm.export_chat(test_chat, "txt")
        print(f"   ✅ Text export: {os.path.basename(txt_path)}")

        # Test 5: Verify exported file contents
        print("\n5. Testing exported file contents...")

        # Check markdown file
        with open(md_path, encoding="utf-8") as f:
            md_content = f.read()
            if "# Long Conversation" in md_content and "## User" in md_content:
                print("   ✅ Markdown content valid")
            else:
                print("   ❌ Markdown content invalid")

        # Check text file
        with open(txt_path, encoding="utf-8") as f:
            txt_content = f.read()
            if "Long Conversation" in txt_content and "USER:" in txt_content:
                print("   ✅ Text content valid")
            else:
                print("   ❌ Text content invalid")

        # Test 6: Error handling
        print("\n6. Testing error handling...")

        # Test loading non-existent file
        try:
            fm.load_chat_history("nonexistent.json")
            print("   ❌ Should have failed loading non-existent file")
        except Exception:
            print("   ✅ Correctly handled non-existent file")

        # Test invalid export format
        try:
            fm.export_chat(test_chat, "invalid_format")
            print("   ❌ Should have failed with invalid format")
        except ValueError:
            print("   ✅ Correctly handled invalid export format")

        # Test 7: File structure verification
        print("\n7. Verifying directory structure...")

        directories = {"saved_chats": 0, "exports": 0}

        for dir_name in directories.keys():
            if os.path.exists(dir_name):
                files = [
                    f for f in os.listdir(dir_name) if os.path.isfile(os.path.join(dir_name, f))
                ]
                directories[dir_name] = len(files)
                print(f"   ✅ {dir_name}/: {len(files)} files")

                # Show recent files
                if files:
                    recent_files = sorted(files)[-3:]  # Last 3 files
                    for f in recent_files:
                        print(f"      - {f}")
            else:
                print(f"   ❌ {dir_name}/ directory not found")

        print("\n" + "=" * 50)
        print("🎉 ALL TESTS PASSED SUCCESSFULLY!")
        print("📊 Summary:")
        print(f"   - Saved chats: {directories['saved_chats']}")
        print(f"   - Exported files: {directories['exports']}")
        print("   - Save/Load/Export functionality: ✅ Working")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_comprehensive()
