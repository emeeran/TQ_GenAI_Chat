"""
Configuration utilities for API services including XAI.
"""
import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class APIConfig:
    """Handles API configuration and key management"""

    @staticmethod
    def get_api_key(service_name):
        """
        Get API key for the specified service from environment variables

        Args:
            service_name (str): Name of the service (e.g., 'xai', 'openai', 'anthropic')

        Returns:
            str: API key if found, None otherwise
        """
        env_var_name = f"{service_name.upper()}_API_KEY"
        api_key = os.environ.get(env_var_name)

        if not api_key:
            # Check alternative naming conventions
            alt_env_var_name = f"{service_name}_API_KEY"
            api_key = os.environ.get(alt_env_var_name)

        return api_key

    @staticmethod
    def check_api_configured(service_name):
        """
        Check if API is properly configured

        Args:
            service_name (str): Name of the service to check

        Returns:
            bool: True if configured, False otherwise
        """
        return bool(APIConfig.get_api_key(service_name))
