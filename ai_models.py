# AI Models Configuration
# This file contains model configurations for various AI providers
# AI Models Configuration
# This file contains model configurations for various AI providers

# OpenAI Models (latest as of July 2025)
OPENAI_MODELS = {
    'gpt-4o': {
        'name': 'GPT-4o',
        'context_window': 128000,
        'max_output_tokens': 4096,
        'supports_vision': True,
        'supports_function_calling': True
    },
    'gpt-4-turbo': {
        'name': 'GPT-4 Turbo',
        'context_window': 128000,
        'max_output_tokens': 4096,
        'supports_vision': True,
        'supports_function_calling': True
    },
    'gpt-4.1': {
        'name': 'GPT-4.1',
        'context_window': 128000,
        'max_output_tokens': 4096,
        'supports_vision': True,
        'supports_function_calling': True
    },
    'gpt-3.5-turbo': {
        'name': 'GPT-3.5 Turbo',
        'context_window': 16000,
        'max_output_tokens': 4096,
        'supports_vision': False,
        'supports_function_calling': True
    }
}

# Anthropic Models (latest as of July 2025)
ANTHROPIC_MODELS = {
    'claude-3-opus': {
        'name': 'Claude 3 Opus',
        'context_window': 200000,
        'max_output_tokens': 4096,
        'supports_vision': True,
        'supports_function_calling': True
    },
    'claude-3-sonnet': {
        'name': 'Claude 3 Sonnet',
        'context_window': 200000,
        'max_output_tokens': 4096,
        'supports_vision': True,
        'supports_function_calling': True
    },
    'claude-3-haiku': {
        'name': 'Claude 3 Haiku',
        'context_window': 200000,
        'max_output_tokens': 4096,
        'supports_vision': True,
        'supports_function_calling': True
    },
    'claude-3-5-sonnet': {
        'name': 'Claude 3.5 Sonnet',
        'context_window': 200000,
        'max_output_tokens': 8192,
        'supports_vision': True,
        'supports_function_calling': True
    },
    'claude-3-5-haiku': {
        'name': 'Claude 3.5 Haiku',
        'context_window': 200000,
        'max_output_tokens': 8192,
        'supports_vision': True,
        'supports_function_calling': True
    }
}

# Groq Models (latest as of July 2025)
GROQ_MODELS = {
    'llama-3-70b': {
        'name': 'Llama 3 70B',
        'context_window': 128000,
        'max_output_tokens': 32768,
        'developer': 'Meta'
    },
    'mixtral-8x22b': {
        'name': 'Mixtral 8x22B',
        'context_window': 32768,
        'max_output_tokens': 32768,
        'developer': 'Mistral'
    }
}

# Mistral Models (latest as of July 2025)
MISTRAL_MODELS = {
    'codestral': {
        'name': 'Codestral',
        'context_window': 256000,
        'max_output_tokens': 8192,
        'specialization': 'coding'
    },
    'mistral-large': {
        'name': 'Mistral Large',
        'context_window': 131000,
        'max_output_tokens': 8192,
        'tier': 'flagship'
    }
}

# X.AI (Grok) Models (latest as of July 2025)
XAI_MODELS = {
    'grok-4': {
        'name': 'Grok 4',
        'context_window': 256000,
        'max_output_tokens': 8192,
        'supports_vision': True,
        'supports_function_calling': True
    }
}

# DeepSeek Models (latest as of July 2025)
DEEPSEEK_MODELS = {
    'deepseek-chat': {
        'name': 'DeepSeek Chat',
        'context_window': 64000,
        'max_output_tokens': 8192,
        'supports_function_calling': True
    }
}

# Google Gemini Models (latest as of July 2025)
GEMINI_MODELS = {
    'gemini-2.5-pro': {
        'name': 'Gemini 2.5 Pro',
        'context_window': 2000000,
        'max_output_tokens': 8192,
        'supports_vision': True,
        'supports_function_calling': True,
        'supports_code_execution': True
    },
    'gemini-2.5-flash': {
        'name': 'Gemini 2.5 Flash',
        'context_window': 2000000,
        'max_output_tokens': 8192,
        'supports_vision': True,
        'supports_function_calling': True
    },
    'gemini-2.5-flash-lite-preview': {
        'name': 'Gemini 2.5 Flash-Lite Preview',
        'context_window': 2000000,
        'max_output_tokens': 8192,
        'supports_vision': True
    }
}

# Cohere Models (latest as of July 2025)
COHERE_MODELS = {
    'command-a-03-2025': {
        'name': 'Command A',
        'context_window': 256000,
        'max_output_tokens': 8192,
        'supports_function_calling': True
    },
    'command-r-plus': {
        'name': 'Command R+',
        'context_window': 128000,
        'max_output_tokens': 4096,
        'supports_function_calling': True
    },
    'command-r': {
        'name': 'Command R',
        'context_window': 128000,
        'max_output_tokens': 4096,
        'supports_function_calling': True
    },
    'command': {
        'name': 'Command',
        'context_window': 4096,
        'max_output_tokens': 4096,
        'supports_function_calling': True
    }
}

# Alibaba (Qwen) Models (latest as of July 2025)
ALIBABA_MODELS = {
    'qwen3-235b-a22b-instruct': {
        'name': 'Qwen3 235B A22B Instruct',
        'context_window': 131072,
        'max_output_tokens': 8192,
        'supports_function_calling': True
    }
}

# OpenRouter Models (latest as of July 2025)
OPENROUTER_MODELS = {
    'google/gemini-2.5-pro-preview': {
        'name': 'Gemini 2.5 Pro Preview',
        'context_window': 2000000,
        'max_output_tokens': 8192,
        'provider': 'Google'
    },
    'anthropic/claude-3.5-sonnet': {
        'name': 'Claude 3.5 Sonnet (OpenRouter)',
        'context_window': 200000,
        'max_output_tokens': 8192,
        'provider': 'Anthropic'
    },
    'moonshot/moonshot-v1-128k': {
        'name': 'Kimi (Moonshot v1 128K)',
        'context_window': 131072,
        'max_output_tokens': 32768,
        'provider': 'Moonshot'
    }
}

# Hugging Face Models (latest as of July 2025)
HUGGINGFACE_MODELS = {
    'Qwen/Qwen3-235B-A22B-Instruct-2507': {
        'name': 'Qwen3 235B A22B Instruct',
        'context_window': 131072,
        'max_output_tokens': 8192,
        'provider': 'Alibaba'
    },
    'moonshotai/Kimi-K2-Instruct': {
        'name': 'Kimi K2 Instruct',
        'context_window': 131072,
        'max_output_tokens': 32768,
        'provider': 'Moonshot'
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
