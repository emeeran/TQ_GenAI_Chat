"""
Service for interacting with XAI (Grok) API.
"""

import logging
import os
from typing import Any

import requests

# Create module-level logger
logger = logging.getLogger(__name__)


class XAIService:
    @classmethod
    def is_configured(cls) -> bool:
        """Check if XAI API key is configured"""
        return bool(os.environ.get("XAI_API_KEY", ""))

    """Service for making requests to XAI API"""

    def __init__(self):
        """Initialize XAI service with API key validation"""
        self.api_key = os.environ.get("XAI_API_KEY", "")
        if not self.api_key:
            raise ValueError("XAI API key not configured. Please set XAI_API_KEY in .env file.")

        # Use the correct base URL for XAI/Grok API
        self.base_url = "https://api.x.ai/v1"

        # Configure timeout and retry settings
        self.timeout = (10, 60)  # (connect_timeout, read_timeout)

    def _create_headers(self) -> dict[str, str]:
        """Create request headers with API key"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def generate_response(
        self,
        prompt: str,
        model: str = "grok-2-latest",
        system_prompt: str = "You are a helpful AI assistant.",
        max_tokens: int = 4000,
        temperature: float = 0.7,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Generate a response using XAI

        Args:
            prompt (str): The prompt to send to XAI
            model (str): The model to use
            system_prompt (str): The system prompt to use
            max_tokens (int): Maximum tokens to generate
            temperature (float): Temperature parameter
            **kwargs: Additional parameters to send to the API

        Returns:
            dict: The response from XAI API
        """
        headers = self._create_headers()

        # Prepare request data
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs,
        }

        try:
            logger.debug(f"Calling XAI API with model: {model}")
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=self.timeout,
            )

            response.raise_for_status()
            result = response.json()

            # Extract and return the response content
            if "choices" in result and result["choices"]:
                return {
                    "content": result["choices"][0]["message"]["content"],
                    "model": model,
                    "provider": "xai",
                    "raw_response": result,
                }
            else:
                raise ValueError("Unexpected response format from XAI API")

        except requests.exceptions.RequestException as e:
            logger.error(f"XAI API request failed: {str(e)}")
            if hasattr(e, "response") and e.response:
                logger.error(f"Status code: {e.response.status_code}")
                logger.error(f"Response: {e.response.text}")
            raise ValueError(f"XAI API request failed: {str(e)}") from e

    def list_models(self) -> list[dict[str, Any]]:
        """
        Get list of available models from XAI API

        Returns:
            List[Dict[str, Any]]: List of model information
        """
        headers = self._create_headers()

        try:
            response = requests.get(
                f"{self.base_url}/models", headers=headers, timeout=self.timeout
            )

            response.raise_for_status()
            result = response.json()

            if "data" in result:
                return result["data"]
            else:
                return []

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get XAI models: {str(e)}")
            return []
