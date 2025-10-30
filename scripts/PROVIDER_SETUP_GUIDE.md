# TQ GenAI Chat - Provider API Setup Guide

This guide provides step-by-step instructions for setting up API keys for all supported AI providers in the TQ GenAI Chat application.

## 📊 Current Provider Status (as of 2025-10-31 00:37:09)

- ✅ **Working**: 1 provider (7.7%)
- ❌ **Failed**: 12 providers (92.3%)
- ⚠️  **Need Setup**: 12 providers

## 🔧 Provider Setup Instructions

### ✅ Working Providers

#### 1. Cohere API
- **Status**: ✅ Working
- **Sample Response**: "Hello! I'm Command, a Cohere-built AI model designed to assist with a wide range of tasks and provid..."
- **API Key**: Valid and configured
- **Setup URL**: https://dashboard.cohere.com/api-keys
- **Environment Variable**: `COHERE_API_KEY`

---

### ❌ Providers Needing Setup

#### 2. OpenAI API
- **Status**: ❌ Project access issue
- **Error**: `Project 'proj_MuCjS15hmYUbapNZea3ybUo6' does not have access to model 'gpt-3.5-turbo'`
- **Setup Steps**:
  1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
  2. Create a new API key or use existing one
  3. Ensure your project has access to GPT models
  4. Check billing status and usage limits
  5. Set environment variable: `export OPENAI_API_KEY="your-api-key-here"`
- **Environment Variable**: `OPENAI_API_KEY`

#### 3. Anthropic Claude API
- **Status**: ❌ Token expired or incorrect
- **Error**: `token expired or incorrect`
- **Setup Steps**:
  1. Go to [Anthropic Console](https://console.anthropic.com/)
  2. Generate a new API key
  3. Set environment variable: `export ANTHROPIC_API_KEY="your-api-key-here"`
- **Environment Variable**: `ANTHROPIC_API_KEY`

#### 4. Groq API
- **Status**: ❌ Invalid API Key
- **Error**: `Invalid API Key`
- **Setup Steps**:
  1. Go to [Groq Console](https://console.groq.com/keys)
  2. Create a new API key
  3. Set environment variable: `export GROQ_API_KEY="your-api-key-here"`
- **Environment Variable**: `GROQ_API_KEY`

#### 5. Mistral AI API
- **Status**: ❌ Unauthorized
- **Error**: `Unauthorized`
- **Setup Steps**:
  1. Go to [Mistral Console](https://console.mistral.ai/api-keys/)
  2. Create a new API key
  3. Set environment variable: `export MISTRAL_API_KEY="your-api-key-here"`
- **Environment Variable**: `MISTRAL_API_KEY`

#### 6. Google Gemini API
- **Status**: ❌ API Key not found
- **Error**: `API Key not found. Please pass a valid API key.`
- **Setup Steps**:
  1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
  2. Create a new API key
  3. Enable Gemini API in Google Cloud Console
  4. Set environment variable: `export GEMINI_API_KEY="your-api-key-here"`
- **Environment Variable**: `GEMINI_API_KEY`

#### 7. xAI (Grok) API
- **Status**: ❌ Credits exhausted
- **Error**: `Your team has either used all available credits or reached its monthly spending limit`
- **Setup Steps**:
  1. Go to [xAI Console](https://console.x.ai/)
  2. Purchase more credits or raise spending limit
  3. Set environment variable: `export XAI_API_KEY="your-api-key-here"`
- **Environment Variable**: `XAI_API_KEY`

#### 8. DeepSeek API
- **Status**: ❌ Insufficient Balance
- **Error**: `Insufficient Balance`
- **Setup Steps**:
  1. Go to [DeepSeek Platform](https://platform.deepseek.com/)
  2. Add credits to your account
  3. Set environment variable: `export DEEPSEEK_API_KEY="your-api-key-here"`
- **Environment Variable**: `DEEPSEEK_API_KEY`

#### 9. Alibaba (Qwen) API
- **Status**: ❌ Model not found (requires Ollama setup)
- **Error**: `model 'qwen-turbo' not found`
- **Setup Steps**:
  1. Install Ollama: `curl -fsSL https://ollama.ai/install.sh | sh`
  2. Pull Qwen model: `ollama pull qwen-turbo`
  3. Start Ollama server: `ollama serve`
  4. Set environment variable: `export ALIBABA_API_KEY="not-required-for-ollama"`
- **Alternative**: Use [DashScope API](https://dashscope.aliyun.com/api)
- **Environment Variable**: `ALIBABA_API_KEY` (optional for Ollama)

#### 10. OpenRouter API
- **Status**: ❌ Model not found
- **Error**: `No endpoints found for meta-llama/llama-3.1-8b-instruct:free`
- **Setup Steps**:
  1. Go to [OpenRouter Keys](https://openrouter.ai/keys)
  2. Create a new API key
  3. Check available models at [OpenRouter Models](https://openrouter.ai/models)
  4. Set environment variable: `export OPENROUTER_API_KEY="your-api-key-here"`
  5. Update model configuration if needed
- **Environment Variable**: `OPENROUTER_API_KEY`

#### 11. Hugging Face API
- **Status**: ❌ Model not supported
- **Error**: `The requested model 'microsoft/DialoGPT-medium' is not supported by any provider you have enabled`
- **Setup Steps**:
  1. Go to [Hugging Face Tokens](https://huggingface.co/settings/tokens)
  2. Create a new access token
  3. Enable Inference API in your account settings
  4. Set environment variable: `export HF_PHRM_ACCESS_TOKEN="your-token-here"`
  5. Use a supported model (check Hugging Face documentation)
- **Environment Variable**: `HF_PHRM_ACCESS_TOKEN`

#### 12. Moonshot AI API
- **Status**: ❌ Incorrect API Key
- **Error**: `Incorrect API key provided`
- **Setup Steps**:
  1. Go to [Moonshot Console](https://platform.moonshot.cn/console/api-keys)
  2. Create a new API key
  3. Set environment variable: `export MOONSHOT_API_KEY="your-api-key-here"`
- **Environment Variable**: `MOONSHOT_API_KEY`

#### 13. Perplexity API
- **Status**: ❌ Invalid model
- **Error**: `Invalid model 'llama-3.1-sonar-small-128k-online'`
- **Setup Steps**:
  1. Go to [Perplexity Settings](https://www.perplexity.ai/settings/api)
  2. Create a new API key
  3. Check [Perplexity Models](https://docs.perplexity.ai/getting-started/models) for available models
  4. Set environment variable: `export PERPLEXITY_API_KEY="your-api-key-here"`
  5. Update model configuration if needed
- **Environment Variable**: `PERPLEXITY_API_KEY`

---

## 🚀 Quick Setup Commands

### 1. Set Environment Variables
```bash
# OpenAI
export OPENAI_API_KEY="sk-proj-your-key-here"

# Anthropic
export ANTHROPIC_API_KEY="your-anthropic-key-here"

# Groq
export GROQ_API_KEY="gsk_your-groq-key-here"

# Mistral
export MISTRAL_API_KEY="your-mistral-key-here"

# Gemini
export GEMINI_API_KEY="AIzaSy-your-gemini-key-here"

# Cohere (already working)
export COHERE_API_KEY="WzrDp8HJYQnrqdWmsyfSXctwqe0vqfGBNHhit2Ie"

# xAI
export XAI_API_KEY="xai-your-xai-key-here"

# DeepSeek
export DEEPSEEK_API_KEY="sk-your-deepseek-key-here"

# OpenRouter
export OPENROUTER_API_KEY="sk-or-your-openrouter-key-here"

# Hugging Face
export HF_PHRM_ACCESS_TOKEN="hf_your-hf-token-here"

# Moonshot
export MOONSHOT_API_KEY="sk-your-moonshot-key-here"

# Perplexity
export PERPLEXITY_API_KEY="pplx-your-perplexity-key-here"

# Alibaba (for DashScope)
export ALIBABA_API_KEY="sk-your-alibaba-key-here"
```

### 2. Make Environment Variables Permanent
Add the above exports to your shell profile:
```bash
# For bash
echo 'export OPENAI_API_KEY="your-key"' >> ~/.bashrc

# For zsh
echo 'export OPENAI_API_KEY="your-key"' >> ~/.zshrc

# Reload
source ~/.bashrc  # or ~/.zshrc
```

### 3. Add to .env file
```bash
# Edit your .env file
nano .env

# Add or update the API keys
OPENAI_API_KEY="your-key-here"
ANTHROPIC_API_KEY="your-key-here"
# ... etc
```

---

## 🛠️ Validation and Testing

### Run Provider Validation
```bash
# Test all providers
python scripts/validate_providers.py --verbose

# Test specific provider
python scripts/validate_providers.py --provider openai --verbose

# Save results to file
python scripts/validate_providers.py --save --template

# Generate .env template
python scripts/validate_providers.py --template
```

### Check Provider Status in Application
```bash
# Start the application
source .venv/bin/activate
export BASIC_AUTH_USERNAME=emeeran
export BASIC_AUTH_PASSWORD=3u0qL1lizU19WE
python -m uvicorn backend.main:app --host 127.0.0.1 --port 5005

# Check available providers
curl http://127.0.0.1:5005/providers
```

---

## 💡 Tips and Troubleshooting

### Common Issues
1. **API Key Format**: Ensure API keys are copied correctly without extra spaces
2. **Billing**: Check account billing and usage limits
3. **Model Access**: Some models require special permissions or higher tier plans
4. **Network**: Ensure firewall allows API access
5. **Environment Variables**: Verify variables are set correctly

### Best Practices
1. **Security**: Never commit API keys to version control
2. **Rotation**: Regularly rotate API keys
3. **Monitoring**: Monitor usage and costs
4. **Testing**: Test API keys after setup using the validation script
5. **Backup**: Keep backup of API keys in secure location

### Testing Individual Providers
```bash
# Test only working providers
python scripts/validate_providers.py --provider cohere

# Test specific problematic provider
python scripts/validate_providers.py --provider openai --verbose
```

---

## 📞 Support Links

- **OpenAI**: https://platform.openai.com/
- **Anthropic**: https://console.anthropic.com/
- **Groq**: https://console.groq.com/
- **Mistral**: https://console.mistral.ai/
- **Gemini**: https://makersuite.google.com/
- **Cohere**: https://dashboard.cohere.com/
- **xAI**: https://console.x.ai/
- **DeepSeek**: https://platform.deepseek.com/
- **OpenRouter**: https://openrouter.ai/
- **Hugging Face**: https://huggingface.co/
- **Moonshot**: https://platform.moonshot.cn/
- **Perplexity**: https://www.perplexity.ai/
- **Alibaba**: https://dashscope.aliyun.com/

---

## 🔄 Automated Setup Script

You can run the validation script with template generation to create a new .env file:

```bash
python scripts/validate_providers.py --template
```

This will create `scripts/.env.template` with all providers marked as working or needing setup.

---

*Last updated: 2025-10-31*
*Generated by TQ GenAI Chat Provider Validation Script*