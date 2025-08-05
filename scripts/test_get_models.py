#!/usr/bin/env python3
"""
Test script to verify the /get_models/<provider> endpoint is working correctly
and returns proper JSON responses for both valid and invalid providers.
"""


import requests


def test_get_models_endpoint():
    base_url = "http://127.0.0.1:5000"

    print("Testing /get_models/<provider> endpoint...")
    print("=" * 50)

    # Test valid providers
    valid_providers = ['openai', 'anthropic', 'groq', 'xai']

    for provider in valid_providers:
        try:
            url = f"{base_url}/get_models/{provider}"
            print(f"\nTesting: {url}")

            response = requests.get(url, timeout=10)
            print(f"Status Code: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type', 'Not set')}")

            if response.status_code == 200:
                data = response.json()
                print(f"Models found: {len(data.get('models', []))}")
                print(f"Default model: {data.get('default', 'None')}")
                print("✅ SUCCESS")
            else:
                print(f"❌ ERROR: Expected 200, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error message: {error_data.get('error', 'No error message')}")
                except:
                    print(f"Non-JSON response: {response.text[:100]}...")

        except Exception as e:
            print(f"❌ EXCEPTION: {str(e)}")

    # Test invalid provider
    print(f"\n{'='*20} Testing Invalid Provider {'='*20}")
    try:
        url = f"{base_url}/get_models/invalid_provider_123"
        print(f"Testing: {url}")

        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type', 'Not set')}")

        if response.headers.get('content-type', '').startswith('application/json'):
            data = response.json()
            print(f"Error message: {data.get('error', 'No error message')}")
            print("✅ SUCCESS: Returns JSON even for invalid provider")
        else:
            print(f"❌ ERROR: Non-JSON response: {response.text[:100]}...")

    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")

    print(f"\n{'='*50}")
    print("Test completed!")

if __name__ == "__main__":
    test_get_models_endpoint()
