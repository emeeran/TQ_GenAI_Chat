#!/usr/bin/env python3
"""
Test script for save/load/export routes
"""
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))


def test_routes():
    try:
        # Import the original app directly
        import app as original_app

        with original_app.app.test_client() as client:
            print("Testing save/load/export routes...")

            # Test 1: Save a chat
            test_data = {
                "title": "Test Route Save",
                "history": [
                    {"content": "Hello from test", "isUser": True},
                    {"content": "Hi there from test!", "isUser": False},
                ],
            }

            print("1. Testing save_chat route...")
            response = client.post("/save_chat", json=test_data)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                result = response.get_json()
                filename = result.get("filename")
                print(f"   ✅ Saved as: {filename}")
            else:
                print(f"   ❌ Error: {response.get_json()}")
                return

            # Test 2: List saved chats
            print("2. Testing list_saved_chats route...")
            response = client.get("/list_saved_chats")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                result = response.get_json()
                chat_count = len(result.get("chats", []))
                print(f"   ✅ Found {chat_count} chats")
                if chat_count > 0:
                    latest_filename = result["chats"][0]["filename"]
                    print(f"   Latest: {latest_filename}")
                else:
                    print("   ❌ No chats found")
                    return
            else:
                print(f"   ❌ Error: {response.get_json()}")
                return

            # Test 3: Load a chat
            print("3. Testing load_chat route...")
            response = client.get(f"/load_chat/{latest_filename}")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                result = response.get_json()
                title = result.get("title", "Untitled")
                history_len = len(result.get("history", []))
                print(f"   ✅ Loaded '{title}' with {history_len} messages")
            else:
                print(f"   ❌ Error: {response.get_json()}")
                return

            # Test 4: Export a chat
            print("4. Testing export_chat route...")
            response = client.get(f"/export_chat?filename={latest_filename}&format=md")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                result = response.get_json()
                message = result.get("message", "")
                export_path = result.get("file_path", "")
                print(f"   ✅ {message}")
                print(f"   Export path: {export_path}")
            else:
                print(f"   ❌ Error: {response.get_json()}")
                return

            print("\n🎉 All routes working successfully!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_routes()
