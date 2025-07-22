"""
Service for interacting with XAI (Grok) API.
"""
import requests

from utils.api_config import APIConfig


class XAIService:
    """Service for making requests to XAI API"""

    def __init__(self):
        self.api_key = APIConfig.get_api_key('xai')
        if not self.api_key:
            raise ValueError("XAI API key not configured. Please set XAI_API_KEY in .env file.")

        # Use the correct base URL for XAI/Grok API
        self.base_url = "https://api.x.ai/v1"

    def generate_response(self, prompt, model="grok-2-latest", **kwargs):
        """
        Generate a response using XAI

        Args:
            prompt (str): The prompt to send to XAI
            model (str): The model to use
            **kwargs: Additional parameters to send to the API

        Returns:
            dict: The response from XAI API
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        system_prompt = kwargs.pop('system_prompt', "You are a helpful AI assistant.")
        max_tokens = kwargs.pop('max_tokens', 4000)

        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            **kwargs
        }

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=data
        )

        if response.status_code != 200:
            error_msg = f"XAI API request failed with status code {response.status_code}: {response.text}"
            raise Exception(error_msg)

        response_data = response.json()

        # Extract the content from the response
        if 'choices' in response_data and len(response_data['choices']) > 0:
            text = response_data['choices'][0]['message']['content']
            return {'text': text, 'raw_response': response_data}

        return response_data

    @staticmethod
    def is_configured():
        """Check if XAI API is configured correctly"""
        return APIConfig.check_api_configured('xai')
