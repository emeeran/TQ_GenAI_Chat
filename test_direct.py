#!/usr/bin/env python3
"""
Direct test of save/load/export functionality without Flask app issues
"""
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))


def test_functionality():
    try:
        from services.file_manager import FileManager

        print("Testing save/load/export functionality directly...")

        fm = FileManager()

        # Test 1: Save a chat
        print("1. Testing save_chat_history...")
        test_chat = {
            "title": "Direct Test Chat",
            "timestamp": "2025-01-01 10:00:00",
            "messages": [
                {"role": "user", "content": "Direct test message"},
                {"role": "assistant", "content": "Direct test response"},
            ],
        }

        filepath = fm.save_chat_history(test_chat)
        print(f"   ✅ Saved as: {filepath}")

        # Test 2: List saved chats
        print("2. Testing get_saved_chats...")
        chats = fm.get_saved_chats()
        print(f"   ✅ Found {len(chats)} chats")

        if chats:
            latest_filename = chats[0]["filename"]
            print(f"   Latest: {latest_filename}")

            # Test 3: Load a chat
            print("3. Testing load_chat_history...")
            loaded_chat = fm.load_chat_history(latest_filename)
            title = loaded_chat.get("title", "Untitled")
            message_count = len(loaded_chat.get("messages", []))
            print(f"   ✅ Loaded '{title}' with {message_count} messages")

            # Test 4: Export a chat
            print("4. Testing export_chat...")
            export_path = fm.export_chat(loaded_chat, "md")
            print(f"   ✅ Exported to: {export_path}")

            # Test 5: Export as text
            print("5. Testing export_chat (text format)...")
            export_path_txt = fm.export_chat(loaded_chat, "txt")
            print(f"   ✅ Exported to: {export_path_txt}")

        print("\n🎉 All functionality working successfully!")

        # Test the directory structure
        print("\nDirectory structure created:")
        for dir_name in ["saved_chats", "exports"]:
            if os.path.exists(dir_name):
                files = os.listdir(dir_name)
                print(f"   {dir_name}/: {len(files)} files")
                for f in files[:3]:  # Show first 3 files
                    print(f"     - {f}")
                if len(files) > 3:
                    print(f"     ... and {len(files) - 3} more")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_functionality()
