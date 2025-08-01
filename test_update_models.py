#!/usr/bin/env python3
"""
Test script for the update models functionality
"""
import requests
import json

def test_update_models():
    base_url = "http://localhost:5000"
    
    print("Testing update models functionality...")
    print("=" * 50)
    
    # Test various providers
    providers_to_test = ['openai', 'anthropic', 'groq', 'xai', 'invalid_provider']
    
    for provider in providers_to_test:
        print(f"\nTesting update models for: {provider}")
        print("-" * 30)
        
        try:
            url = f"{base_url}/update_models/{provider}"
            response = requests.post(url, timeout=30)
            
            print(f"Status Code: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type', 'unknown')}")
            
            # Check if response is JSON
            if 'application/json' in response.headers.get('content-type', ''):
                try:
                    data = response.json()
                    print(f"Response: {json.dumps(data, indent=2)}")
                    
                    if response.status_code == 200:
                        if data.get('success'):
                            models = data.get('models', [])
                            print(f"✅ Success! Found {len(models)} models")
                        else:
                            print(f"❌ Failed: {data.get('error', 'Unknown error')}")
                    else:
                        print(f"❌ HTTP Error: {data.get('error', 'Unknown error')}")
                        
                except json.JSONDecodeError as e:
                    print(f"❌ JSON Decode Error: {e}")
                    print(f"Raw response: {response.text[:200]}...")
            else:
                print(f"❌ Non-JSON response: {response.text[:200]}...")
                
        except requests.exceptions.Timeout:
            print("❌ Request timeout")
        except requests.exceptions.ConnectionError:
            print("❌ Connection error - is the server running?")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("Update models test completed!")

if __name__ == '__main__':
    test_update_models()
