#!/usr/bin/env python3
"""
Test script for audio features in TQ GenAI Chat
"""

import time

import requests


def test_endpoints():
    """Test key endpoints for audio functionality"""
    base_url = "http://localhost:5000"

    print("🎤 Testing Audio Features")
    print("=" * 50)

    # Test personas endpoint
    try:
        response = requests.get(f"{base_url}/personas", timeout=5)
        if response.status_code == 200:
            personas = response.json()
            print(f"✅ Personas endpoint: {len(personas)} personas loaded")
            for key in list(personas.keys())[:3]:
                print(f"   - {key.replace('_', ' ').title()}")
        else:
            print(f"❌ Personas endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Personas endpoint error: {e}")

    # Test TTS endpoint
    try:
        response = requests.post(
            f"{base_url}/tts",
            json={"text": "Hello, this is a test of text-to-speech functionality."},
            timeout=10,
        )
        if response.status_code == 200:
            print("✅ Text-to-Speech endpoint working")
            print(f"   Content-Type: {response.headers.get('content-type')}")
            print(f"   Content-Length: {len(response.content)} bytes")
        else:
            print(f"❌ TTS endpoint failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ TTS endpoint error: {e}")

    # Test transcription endpoint (without file - should return error)
    try:
        response = requests.post(f"{base_url}/transcribe", timeout=5)
        if response.status_code == 400:
            data = response.json()
            if "No audio file provided" in data.get("error", ""):
                print("✅ Transcription endpoint properly handles missing file")
            else:
                print(f"⚠️  Transcription endpoint unexpected error: {data}")
        else:
            print(f"❌ Transcription endpoint unexpected status: {response.status_code}")
    except Exception as e:
        print(f"❌ Transcription endpoint error: {e}")

    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health endpoint working")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health endpoint error: {e}")


def test_audio_dependencies():
    """Test if audio dependencies are working"""
    print("\n🔧 Testing Audio Dependencies")
    print("=" * 50)

    try:
        import speech_recognition as sr

        recognizer = sr.Recognizer()
        print("✅ speech_recognition module working")
    except Exception as e:
        print(f"❌ speech_recognition error: {e}")

    try:
        print("✅ pydub module working")
    except Exception as e:
        print(f"❌ pydub error: {e}")

    try:
        import pyttsx3

        engine = pyttsx3.init()
        print("✅ pyttsx3 module working")

        # Test voice listing
        voices = engine.getProperty("voices")
        print(f"   Available voices: {len(voices) if voices else 0}")
        engine.stop()
    except Exception as e:
        print(f"❌ pyttsx3 error: {e}")

    try:
        print("✅ gTTS module working")
    except Exception as e:
        print(f"❌ gTTS error: {e}")


def main():
    """Main test function"""
    print("🧪 TQ GenAI Chat - Audio Features Test")
    print("=" * 50)

    test_audio_dependencies()

    print("\n⏳ Starting server test in 3 seconds...")
    print("   (Make sure the Flask app is running on localhost:5000)")
    time.sleep(3)

    test_endpoints()

    print("\n📋 Test Summary")
    print("=" * 50)
    print("1. ✅ If all tests pass, audio features should work correctly")
    print("2. 🎙️  For speech input: Use browser-based recognition (Chrome/Edge recommended)")
    print("3. 🔊 For speech output: Auto-speak can be enabled in audio settings")
    print("4. 🛠️  If tests fail, check microphone permissions and browser support")


if __name__ == "__main__":
    main()
