# AI Models Configuration
# This file contains model configurations for various AI providers

# OpenAI Models
OPENAI_MODELS = {
    'gpt-4o': {
        'name': 'GPT-4o',
        'context_window': 128000,
        'max_output_tokens': 4096,
        'supports_vision': True,
        'supports_function_calling': True
    },
    'gpt-4o-mini': {
        'name': 'GPT-4o Mini',
        'context_window': 128000,
        'max_output_tokens': 16384,
        'supports_vision': True,
        'supports_function_calling': True
    },
    'chatgpt-4o-latest': {
        'name': 'ChatGPT-4o Latest',
        'context_window': 128000,
        'max_output_tokens': 4096,
        'supports_vision': True,
        'supports_function_calling': True
    },
    'o1': {
        'name': 'o1',
        'context_window': 200000,
        'max_output_tokens': 100000,
        'supports_reasoning': True
    },
    'o1-mini': {
        'name': 'o1-mini',
        'context_window': 128000,
        'max_output_tokens': 65536,
        'supports_reasoning': True
    },
    'o3-mini': {
        'name': 'o3-mini',
        'context_window': 128000,
        'max_output_tokens': 65536,
        'supports_reasoning': True
    },
    'o1-preview': {
        'name': 'o1-preview',
        'context_window': 128000,
        'max_output_tokens': 32768,
        'supports_reasoning': True
    }
}

# Anthropic Models
ANTHROPIC_MODELS = {
    'claude-3-5-sonnet-20241022': {
        'name': 'Claude 3.5 Sonnet',
        'context_window': 200000,
        'max_output_tokens': 8192,
        'supports_vision': True,
        'supports_function_calling': True
    },
    'claude-3-5-sonnet-latest': {
        'name': 'Claude 3.5 Sonnet (Latest)',
        'context_window': 200000,
        'max_output_tokens': 8192,
        'supports_vision': True,
        'supports_function_calling': True
    },
    'claude-3-5-haiku-20241022': {
        'name': 'Claude 3.5 Haiku',
        'context_window': 200000,
        'max_output_tokens': 8192,
        'supports_vision': True,
        'supports_function_calling': True
    },
    'claude-3-5-haiku-latest': {
        'name': 'Claude 3.5 Haiku (Latest)',
        'context_window': 200000,
        'max_output_tokens': 8192,
        'supports_vision': True,
        'supports_function_calling': True
    },
    'claude-3-opus-20240229': {
        'name': 'Claude 3 Opus',
        'context_window': 200000,
        'max_output_tokens': 4096,
        'supports_vision': True,
        'supports_function_calling': True
    },
    'claude-3-sonnet-20240229': {
        'name': 'Claude 3 Sonnet',
        'context_window': 200000,
        'max_output_tokens': 4096,
        'supports_vision': True,
        'supports_function_calling': True
    },
    'claude-3-haiku-20240307': {
        'name': 'Claude 3 Haiku',
        'context_window': 200000,
        'max_output_tokens': 4096,
        'supports_vision': True,
        'supports_function_calling': True
    }
}

# Groq Models
GROQ_MODELS = {
    'llama-3.3-70b-versatile': {
        'name': 'Llama 3.3 70B Versatile',
        'context_window': 128000,
        'max_output_tokens': 32768,
        'developer': 'Meta'
    },
    'llama-3.1-8b-instant': {
        'name': 'Llama 3.1 8B Instant',
        'context_window': 128000,
        'max_output_tokens': 8192,
        'developer': 'Meta'
    },
    'llama3-70b-8192': {
        'name': 'Llama 3 70B',
        'context_window': 8192,
        'max_output_tokens': 8192,
        'developer': 'Meta'
    },
    'llama3-8b-8192': {
        'name': 'Llama 3 8B',
        'context_window': 8192,
        'max_output_tokens': 8192,
        'developer': 'Meta'
    },
    'mixtral-8x7b-32768': {
        'name': 'Mixtral 8x7B',
        'context_window': 32768,
        'max_output_tokens': 32768,
        'developer': 'Mistral'
    },
    'gemma2-9b-it': {
        'name': 'Gemma 2 9B IT',
        'context_window': 8192,
        'max_output_tokens': 8192,
        'developer': 'Google'
    },
    'deepseek-r1-distill-llama-70b': {
        'name': 'DeepSeek R1 Distill Llama 70B',
        'context_window': 128000,
        'max_output_tokens': 16384,
        'developer': 'DeepSeek'
    },
    'deepseek-r1-distill-qwen-32b': {
        'name': 'DeepSeek R1 Distill Qwen 32B',
        'context_window': 128000,
        'max_output_tokens': 16384,
        'developer': 'DeepSeek'
    },
    'qwen-2.5-coder-32b': {
        'name': 'Qwen 2.5 Coder 32B',
        'context_window': 128000,
        'max_output_tokens': 32768,
        'developer': 'Alibaba Cloud'
    },
    'qwen-2.5-32b': {
        'name': 'Qwen 2.5 32B',
        'context_window': 128000,
        'max_output_tokens': 32768,
        'developer': 'Alibaba Cloud'
    }
}

# Mistral Models
MISTRAL_MODELS = {
    'codestral-latest': {
        'name': 'Codestral (Latest)',
        'context_window': 256000,
        'max_output_tokens': 8192,
        'specialization': 'coding'
    },
    'mistral-large-latest': {
        'name': 'Mistral Large (Latest)',
        'context_window': 131000,
        'max_output_tokens': 8192,
        'tier': 'flagship'
    },
    'pixtral-large-latest': {
        'name': 'Pixtral Large (Latest)',
        'context_window': 131000,
        'max_output_tokens': 8192,
        'supports_vision': True,
        'tier': 'flagship'
    },
    'mistral-small-latest': {
        'name': 'Mistral Small (Latest)',
        'context_window': 32000,
        'max_output_tokens': 8192,
        'tier': 'efficient'
    },
    'mistral-saba-latest': {
        'name': 'Mistral Saba (Latest)',
        'context_window': 32000,
        'max_output_tokens': 8192,
        'specialization': 'multilingual'
    },
    'ministral-3b-latest': {
        'name': 'Ministral 3B (Latest)',
        'context_window': 131000,
        'max_output_tokens': 8192,
        'tier': 'edge'
    },
    'ministral-8b-latest': {
        'name': 'Ministral 8B (Latest)',
        'context_window': 131000,
        'max_output_tokens': 8192,
        'tier': 'edge'
    },
    'pixtral-12b-2409': {
        'name': 'Pixtral 12B',
        'context_window': 131000,
        'max_output_tokens': 8192,
        'supports_vision': True
    },
    'open-mistral-nemo': {
        'name': 'Mistral Nemo',
        'context_window': 131000,
        'max_output_tokens': 8192,
        'license': 'Apache 2.0'
    },
    'open-codestral-mamba': {
        'name': 'Codestral Mamba',
        'context_window': 256000,
        'max_output_tokens': 8192,
        'specialization': 'coding',
        'license': 'Apache 2.0'
    }
}

# X.AI (Grok) Models
XAI_MODELS = {
    'grok-2-latest': {
        'name': 'Grok 2 (Latest)',
        'context_window': 131072,
        'max_output_tokens': 8192,
        'supports_function_calling': True
    },
    'grok-2': {
        'name': 'Grok 2',
        'context_window': 131072,
        'max_output_tokens': 8192,
        'supports_function_calling': True
    },
    'grok-2-1212': {
        'name': 'Grok 2 (Dec 2024)',
        'context_window': 131072,
        'max_output_tokens': 8192,
        'supports_function_calling': True
    },
    'grok-2-vision-latest': {
        'name': 'Grok 2 Vision (Latest)',
        'context_window': 32768,
        'max_output_tokens': 8192,
        'supports_vision': True,
        'supports_function_calling': True
    },
    'grok-2-vision': {
        'name': 'Grok 2 Vision',
        'context_window': 32768,
        'max_output_tokens': 8192,
        'supports_vision': True,
        'supports_function_calling': True
    },
    'grok-2-vision-1212': {
        'name': 'Grok 2 Vision (Dec 2024)',
        'context_window': 32768,
        'max_output_tokens': 8192,
        'supports_vision': True,
        'supports_function_calling': True
    },
    'grok-beta': {
        'name': 'Grok Beta',
        'context_window': 131072,
        'max_output_tokens': 8192,
        'status': 'beta'
    },
    'grok-vision-beta': {
        'name': 'Grok Vision Beta',
        'context_window': 8192,
        'max_output_tokens': 8192,
        'supports_vision': True,
        'status': 'beta'
    }
}

# DeepSeek Models
DEEPSEEK_MODELS = {
    'deepseek-chat': {
        'name': 'DeepSeek Chat',
        'context_window': 64000,
        'max_output_tokens': 8192,
        'supports_function_calling': True
    },
    'deepseek-reasoner': {
        'name': 'DeepSeek Reasoner',
        'context_window': 64000,
        'max_output_tokens': 8192,
        'max_cot_tokens': 32000,
        'supports_reasoning': True
    }
}

# Google Gemini Models
GEMINI_MODELS = {
    'gemini-1.5-pro': {
        'name': 'Gemini 1.5 Pro',
        'context_window': 2000000,
        'max_output_tokens': 8192,
        'supports_vision': True,
        'supports_function_calling': True,
        'supports_code_execution': True
    },
    'gemini-1.5-pro-002': {
        'name': 'Gemini 1.5 Pro (002)',
        'context_window': 2000000,
        'max_output_tokens': 8192,
        'supports_vision': True,
        'supports_function_calling': True,
        'supports_code_execution': True
    },
    'gemini-1.5-flash': {
        'name': 'Gemini 1.5 Flash',
        'context_window': 1000000,
        'max_output_tokens': 8192,
        'supports_vision': True,
        'supports_function_calling': True,
        'tier': 'fast'
    },
    'gemini-1.5-flash-002': {
        'name': 'Gemini 1.5 Flash (002)',
        'context_window': 1000000,
        'max_output_tokens': 8192,
        'supports_vision': True,
        'supports_function_calling': True,
        'tier': 'fast'
    },
    'gemini-1.5-flash-8b': {
        'name': 'Gemini 1.5 Flash 8B',
        'context_window': 1000000,
        'max_output_tokens': 8192,
        'supports_vision': True,
        'supports_function_calling': True,
        'tier': 'efficient'
    },
    'gemini-2.0-flash-exp': {
        'name': 'Gemini 2.0 Flash (Experimental)',
        'context_window': 1000000,
        'max_output_tokens': 8192,
        'supports_vision': True,
        'supports_function_calling': True,
        'supports_multimodal_live': True,
        'status': 'experimental'
    }
}

# Cohere Models
COHERE_MODELS = {
    'command-r-plus': {
        'name': 'Command R+',
        'context_window': 128000,
        'max_output_tokens': 4096,
        'supports_function_calling': True,
        'supports_rag': True,
        'tier': 'flagship'
    },
    'command-r': {
        'name': 'Command R',
        'context_window': 128000,
        'max_output_tokens': 4096,
        'supports_function_calling': True,
        'supports_rag': True,
        'tier': 'balanced'
    },
    'command': {
        'name': 'Command',
        'context_window': 4096,
        'max_output_tokens': 4096,
        'supports_function_calling': True
    },
    'command-light': {
        'name': 'Command Light',
        'context_window': 4096,
        'max_output_tokens': 4096,
        'tier': 'efficient'
    }
}

# Alibaba (Qwen) Models via OpenRouter/Direct API
ALIBABA_MODELS = {
    'qwen-2.5-72b-instruct': {
        'name': 'Qwen 2.5 72B Instruct',
        'context_window': 131072,
        'max_output_tokens': 8192,
        'supports_function_calling': True
    },
    'qwen-2.5-32b-instruct': {
        'name': 'Qwen 2.5 32B Instruct',
        'context_window': 131072,
        'max_output_tokens': 8192,
        'supports_function_calling': True
    },
    'qwen-2.5-14b-instruct': {
        'name': 'Qwen 2.5 14B Instruct',
        'context_window': 131072,
        'max_output_tokens': 8192,
        'supports_function_calling': True
    },
    'qwen-2.5-7b-instruct': {
        'name': 'Qwen 2.5 7B Instruct',
        'context_window': 131072,
        'max_output_tokens': 8192,
        'supports_function_calling': True
    },
    'qwen-2.5-coder-32b-instruct': {
        'name': 'Qwen 2.5 Coder 32B Instruct',
        'context_window': 131072,
        'max_output_tokens': 8192,
        'specialization': 'coding',
        'supports_function_calling': True
    },
    'qwen-2.5-math-72b-instruct': {
        'name': 'Qwen 2.5 Math 72B Instruct',
        'context_window': 131072,
        'max_output_tokens': 8192,
        'specialization': 'mathematics',
        'supports_function_calling': True
    }
}

# OpenRouter Models (including Kimi)
OPENROUTER_MODELS = {
    # Kimi Models
    'moonshot/moonshot-v1-8k': {
        'name': 'Kimi (Moonshot v1 8K)',
        'context_window': 8192,
        'max_output_tokens': 8192,
        'provider': 'Moonshot'
    },
    'moonshot/moonshot-v1-32k': {
        'name': 'Kimi (Moonshot v1 32K)',
        'context_window': 32768,
        'max_output_tokens': 32768,
        'provider': 'Moonshot'
    },
    'moonshot/moonshot-v1-128k': {
        'name': 'Kimi (Moonshot v1 128K)',
        'context_window': 131072,
        'max_output_tokens': 32768,
        'provider': 'Moonshot'
    },
    # Popular OpenRouter Models
    'anthropic/claude-3.5-sonnet': {
        'name': 'Claude 3.5 Sonnet (OpenRouter)',
        'context_window': 200000,
        'max_output_tokens': 8192,
        'provider': 'Anthropic'
    },
    'openai/gpt-4o': {
        'name': 'GPT-4o (OpenRouter)',
        'context_window': 128000,
        'max_output_tokens': 4096,
        'provider': 'OpenAI'
    },
    'google/gemini-2.0-flash-exp': {
        'name': 'Gemini 2.0 Flash Exp (OpenRouter)',
        'context_window': 1000000,
        'max_output_tokens': 8192,
        'provider': 'Google'
    },
    'meta-llama/llama-3.1-405b-instruct': {
        'name': 'Llama 3.1 405B Instruct',
        'context_window': 131072,
        'max_output_tokens': 4096,
        'provider': 'Meta'
    },
    'qwen/qwen-2.5-72b-instruct': {
        'name': 'Qwen 2.5 72B Instruct (OpenRouter)',
        'context_window': 131072,
        'max_output_tokens': 8192,
        'provider': 'Alibaba'
    }
}

# Hugging Face Models
HUGGINGFACE_MODELS = {
    'microsoft/DialoGPT-large': {
        'name': 'DialoGPT Large',
        'context_window': 1024,
        'max_output_tokens': 1024,
        'provider': 'Microsoft'
    },
    'meta-llama/Llama-2-70b-chat-hf': {
        'name': 'Llama 2 70B Chat',
        'context_window': 4096,
        'max_output_tokens': 4096,
        'provider': 'Meta'
    },
    'mistralai/Mixtral-8x7B-Instruct-v0.1': {
        'name': 'Mixtral 8x7B Instruct',
        'context_window': 32768,
        'max_output_tokens': 8192,
        'provider': 'Mistral'
    },
    'microsoft/phi-2': {
        'name': 'Phi-2',
        'context_window': 2048,
        'max_output_tokens': 2048,
        'provider': 'Microsoft'
    }
}

# Model list exports for easy access
ALL_MODELS = {
    'openai': list(OPENAI_MODELS.keys()),
    'anthropic': list(ANTHROPIC_MODELS.keys()),
    'groq': list(GROQ_MODELS.keys()),
    'mistral': list(MISTRAL_MODELS.keys()),
    'xai': list(XAI_MODELS.keys()),
    'deepseek': list(DEEPSEEK_MODELS.keys()),
    'gemini': list(GEMINI_MODELS.keys()),
    'cohere': list(COHERE_MODELS.keys()),
    'alibaba': list(ALIBABA_MODELS.keys()),
    'openrouter': list(OPENROUTER_MODELS.keys()),
    'huggingface': list(HUGGINGFACE_MODELS.keys())
}

# Default models for each provider
DEFAULT_MODELS = {
    'groq': 'deepseek-r1-distill-llama-70b',
    'openai': 'gpt-4o-mini',
    'xai': 'grok-2-latest',
    'mistral': 'codestral-latest',
    'anthropic': 'claude-3-5-sonnet-latest',
    'deepseek': 'deepseek-chat',
    'gemini': 'gemini-1.5-flash',
    'cohere': 'command-r',
    'alibaba': 'qwen-2.5-72b-instruct',
    'openrouter': 'moonshot/moonshot-v1-32k',
    'huggingface': 'meta-llama/Llama-2-70b-chat-hf'
}

# API Endpoints
API_ENDPOINTS = {
    'openai': 'https://api.openai.com/v1/chat/completions',
    'anthropic': 'https://api.anthropic.com/v1/messages',
    'groq': 'https://api.groq.com/openai/v1/chat/completions',
    'mistral': 'https://api.mistral.ai/v1/chat/completions',
    'xai': 'https://api.x.ai/v1/chat/completions',
    'deepseek': 'https://api.deepseek.com/v1/chat/completions',
    'gemini': 'https://generativelanguage.googleapis.com/v1/models/',
    'cohere': 'https://api.cohere.com/v1/chat',
    'alibaba': 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation',
    'openrouter': 'https://openrouter.ai/api/v1/chat/completions',
    'huggingface': 'https://api-inference.huggingface.co/models/'
}

# Function to get model info
def get_model_info(provider: str, model: str) -> dict:
    """Get detailed information about a specific model"""
    model_dict_map = {
        'openai': OPENAI_MODELS,
        'anthropic': ANTHROPIC_MODELS,
        'groq': GROQ_MODELS,
        'mistral': MISTRAL_MODELS,
        'xai': XAI_MODELS,
        'deepseek': DEEPSEEK_MODELS,
        'gemini': GEMINI_MODELS,
        'cohere': COHERE_MODELS,
        'alibaba': ALIBABA_MODELS,
        'openrouter': OPENROUTER_MODELS,
        'huggingface': HUGGINGFACE_MODELS
    }

    return model_dict_map.get(provider, {}).get(model, {})

def get_provider_models(provider: str) -> list:
    """Get all models for a specific provider"""
    return ALL_MODELS.get(provider, [])

def get_default_model(provider: str) -> str:
    """Get the default model for a provider"""
    return DEFAULT_MODELS.get(provider, '')

def get_api_endpoint(provider: str) -> str:
    """Get the API endpoint for a provider"""
    return API_ENDPOINTS.get(provider, '')
