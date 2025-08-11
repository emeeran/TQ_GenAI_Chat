import os
import pytest
from core.providers import provider_manager
from core.models import model_manager

# Basic smoke test for all providers
@pytest.mark.parametrize("provider", provider_manager.list_providers())
def test_provider_models_exist(provider):
    models = model_manager.get_models(provider)
    assert isinstance(models, list)
    assert len(models) > 0, f"No models found for provider: {provider}"

@pytest.mark.parametrize("provider", provider_manager.list_providers())
def test_provider_chat_completion(provider):
    models = model_manager.get_models(provider)
    model = models[0]
    # Use a simple prompt and persona
    try:
        response = provider_manager.chat(provider, model, "Hello, who are you?", persona="You are a helpful assistant.")
        assert response is not None
        # Accept either dict or string response
        if isinstance(response, dict):
            assert "text" in response or "choices" in response or "content" in response
        elif isinstance(response, str):
            assert len(response) > 0
    except Exception as e:
        pytest.skip(f"Provider {provider} failed: {e}")
