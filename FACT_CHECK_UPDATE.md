# Fact-Checking Default Provider Change Summary

## Changes Made

### ✅ **Primary Change: Moonshot Kimi-k2 is now the default fact-checker**

**Before:**
1. **Primary**: Groq (llama-3.3-70b-versatile) 
2. **Fallback**: Moonshot AI (kimi-k2-instruct)

**After:**
1. **Primary**: Moonshot AI (kimi-k2-instruct) 
2. **Fallback**: Groq (llama-3.3-70b-versatile)

### **Technical Implementation:**

#### **Function Updated:** `fact_check_response()` in `app.py`
- **Line ~186-250**: Swapped the order of provider attempts
- **Primary**: Moonshot AI Kimi-k2 now runs first for thorough fact-checking
- **Fallback**: Groq kept as backup for speed if Moonshot fails
- **Enhanced logging**: Added "(primary)" and "(fallback)" labels to logs

#### **Benefits of This Change:**
1. **Better Accuracy**: Kimi-k2 has access to more current information
2. **Enhanced Fact-Checking**: Moonshot AI specializes in thorough verification
3. **Maintained Speed**: Groq still available as fast fallback
4. **No Breaking Changes**: Same API structure and error handling

### **API Configuration Details:**

**Moonshot AI (Primary):**
- Model: `kimi-k2-instruct`
- Endpoint: `https://api.moonshot.ai/v1/chat/completions`
- Temperature: 0.1 (for consistent fact-checking)
- Max Tokens: 4000

**Groq (Fallback):**
- Model: `llama-3.3-70b-versatile`
- Endpoint: `https://api.groq.com/openai/v1/chat/completions`
- Temperature: 0.1 (for consistent fact-checking)
- Max Tokens: 4000

### **Environment Variables Required:**
- `MOONSHOT_API_KEY` - Now primary for fact-checking
- `GROQ_API_KEY` - Fallback if Moonshot unavailable

### **How It Works:**
1. User sends message → AI generates response
2. **Moonshot Kimi-k2** fact-checks the response first
3. If Moonshot succeeds → Returns fact-checked version
4. If Moonshot fails → **Groq** attempts fact-checking
5. If both fail → Original response returned with warning

### **Log Messages to Watch For:**
- ✅ `"Fact-checking completed with Moonshot AI Kimi-k2 (primary)"`
- ⚠️ `"Moonshot AI fact-checking failed: [error]"`
- 🔄 `"Fact-checking completed with Groq (fallback)"`
- ❌ `"Fact-checking unavailable - no API keys or services failed"`

The fact-checking system now prioritizes Moonshot Kimi-k2 for more thorough and current fact verification, while maintaining Groq as a reliable fallback option.
