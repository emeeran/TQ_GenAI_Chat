"""
Async LiteLLM provider integration for multi-provider AI support.
"""

import asyncio
import logging
from typing import Any

import litellm

logger = logging.getLogger(__name__)


async def generate_llm_response(
    model: str,
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 4000,
    **kwargs: Any
) -> dict[str, Any]:
    """Unified async LLM response using LiteLLM"""
    try:
        # Use acompletion for async calls
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
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
        logger.error(f"LiteLLM error for model {model}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "provider": "litellm",
        }


def generate_llm_response_sync(
    model: str,
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 4000,
    **kwargs: Any
) -> dict[str, Any]:
    """Synchronous wrapper for backward compatibility"""
    try:
        # Get current event loop if it exists
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're in an async context, create a new task
            return asyncio.create_task(
                generate_llm_response(model, messages, temperature, max_tokens, **kwargs)
            )
        else:
            # No event loop running, run in new loop
            return asyncio.run(
                generate_llm_response(model, messages, temperature, max_tokens, **kwargs)
            )
    except Exception as e:
        logger.error(f"Sync wrapper error for model {model}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "provider": "litellm",
        }