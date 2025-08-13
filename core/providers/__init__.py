import litellm

# Import classes for external use
from .base import ChatMessage
from .factory import ProviderFactory

# Export for external use
__all__ = ["ChatMessage", "ProviderFactory", "generate_llm_response", "generate_llm_response_async"]

def generate_llm_response(model: list, messages: list, temperature: float = 0.7, max_tokens: int = 4000):
    """Unified LLM response using LiteLLM"""
    try:
        response = litellm.completion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Convert usage to serializable dict
        usage = response.get("usage", {})
        if usage:
            # Convert any non-serializable objects to dict
            usage_dict = {}
            for key, value in usage.items():
                if hasattr(value, '__dict__'):
                    # Convert object to dict
                    usage_dict[key] = value.__dict__
                elif hasattr(value, 'model_dump'):
                    # For Pydantic models
                    usage_dict[key] = value.model_dump()
                else:
                    usage_dict[key] = value
        else:
            usage_dict = {}

        return {
            "success": True,
            "content": response["choices"][0]["message"]["content"],
            "model": model,
            "provider": "litellm",
            "usage": usage_dict,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "provider": "litellm",
        }


async def generate_llm_response_async(model: str, messages: list, temperature: float = 0.7, max_tokens: int = 4000):
    """Unified async LLM response using LiteLLM"""
    try:
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Convert usage to serializable dict
        usage = response.get("usage", {})
        if usage:
            # Convert any non-serializable objects to dict
            if hasattr(usage, 'model_dump'):
                # For Pydantic models
                usage_dict = usage.model_dump()
            elif hasattr(usage, '__dict__'):
                # Convert object to dict
                usage_dict = usage.__dict__
            elif hasattr(usage, 'items'):
                # Already a dict-like object
                usage_dict = dict(usage)
            else:
                # Fallback - convert to string
                usage_dict = {"usage": str(usage)}
        else:
            usage_dict = {}

        return {
            "success": True,
            "content": response["choices"][0]["message"]["content"],
            "model": model,
            "provider": "litellm",
            "usage": usage_dict,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "provider": "litellm",
        }


