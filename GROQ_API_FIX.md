# Groq API Key Issue - Fix Documentation

## Problem

When trying to update Groq models, you get the error:
```
❌ Error updating models: Failed to update models
```

## Root Cause

The Groq API key in the `.env` file is invalid or expired. The API returns:
- **Status Code**: 401 Unauthorized
- **Error**: `{"error":{"message":"Invalid API Key","type":"invalid_request_error","code":"invalid_api_key"}}`

## Solution

### Option 1: Update with a Valid Groq API Key (Recommended)

1. **Get a new API key**:
   - Visit https://console.groq.com/
   - Sign in or create an account
   - Navigate to API Keys section
   - Generate a new API key

2. **Update the environment file**:
   ```bash
   # Edit the .env file
   nano .env
   ```

3. **Replace the Groq API key**:
   ```env
   GROQ_API_KEY="your_new_valid_groq_api_key_here"
   ```

4. **Restart the application**:
   ```bash
   # Stop the current running instance (Ctrl+C)
   # Then restart
   source fastapi_env/bin/activate && python main.py
   ```

### Option 2: Use Current Cached Models (Temporary)

The application has cached Groq models that will continue to work:
- `llama-3.3-70b-versatile`
- `llama-3.1-8b-instant`
- `gemma2-9b-it`
- `deepseek-r1-distill-llama-70b`
- `mixtral-8x7b-32768`
- `mistral-saba-24b`
- `qwen/qwen3-32b`
- `moonshotai/kimi-k2-instruct`

**Note**: These cached models may become outdated over time.

## How to Verify the Fix

1. **Test the API key directly**:
   ```bash
   source fastapi_env/bin/activate
   python3 -c "
   import os, requests
   from dotenv import load_dotenv
   load_dotenv()

   api_key = os.getenv('GROQ_API_KEY')
   headers = {'Authorization': f'Bearer {api_key}'}
   response = requests.get('https://api.groq.com/openai/v1/models', headers=headers)
   print(f'Status: {response.status_code}')
   if response.status_code == 200:
       print('✅ API key is valid')
   else:
       print('❌ API key is invalid')
   "
   ```

2. **Test model update via API**:
   ```bash
   curl -u emeeran:3u0qL1lizU19WE -X POST http://127.0.0.1:5005/update_models/groq
   ```

## Error Message Details

**Before Fix**:
```json
{
  "detail": "Failed to update models: [Error details]"
}
```

**After Fix** (with improved error handling):
```json
{
  "detail": {
    "error": "Failed to fetch Groq models due to invalid API key",
    "solution": "Please update your GROQ_API_KEY in the .env file with a valid key from https://console.groq.com/",
    "provider": "groq",
    "current_models": ["llama-3.3-70b-versatile", "..."]
  }
}
```

## Console Output

When the error occurs, you'll see this helpful console message:
```
❌ Groq API key is invalid or expired
💡 To fix this:
   1. Get a new API key from https://console.groq.com/
   2. Update GROQ_API_KEY in your .env file
   3. Restart the application
```

## Impact

- **Application Status**: ✅ Still fully functional
- **Groq Models**: ⚠️ Using cached models (may be outdated)
- **Other Providers**: ✅ Working normally (Cerebras, OpenAI, etc.)
- **Five-Stage Pipeline**: ✅ Fully operational

## Preventive Measures

1. **Regular API Key Validation**: Check API keys periodically
2. **Backup API Keys**: Keep backup keys from different providers
3. **Monitoring**: Set up alerts for API failures
4. **Documentation**: Keep API key access and renewal information documented

---

**Status**: Issue identified and documented with clear fix instructions
**Priority**: Medium - Application remains functional with cached models
**Impact**: Limited to Groq model updates only