"""High-performance async Moonshot provider"""

import os
import time
import json
import logging
from collections.abc import AsyncGenerator
from .async_base import AsyncAIProviderInterface, ChatRequest, ChatResponse

class AsyncMoonshotProvider(AsyncAIProviderInterface):
    """Async Moonshot API provider"""

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("MOONSHOT_API_KEY", "")
        self.base_url = "https://api.moonshot.ai/v1"
        self._models = [
            "moonshot-v1-32k",
            "moonshot-v1-128k",
            "moonshot-v1-8k",
            "moonshot-v1-auto",
            "kimi-k2-0711-preview",
            "kimi-latest",
            "kimi-thinking-preview",
        ]

    @property
    def name(self) -> str:
        return "moonshot"

    async def get_models(self) -> list[str]:
        return self._models

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """Process chat completion using async Moonshot API"""
        start_time = time.time()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        payload = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "stream": False,
        }
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        async with self.session.post(
            f"{self.base_url}/chat/completions", headers=headers, json=payload
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Moonshot API error: {response.status} - {error_text}")
            data = await response.json()
            content = data["choices"][0]["message"]["content"] if "choices" in data and data["choices"] else ""
            usage = data.get("usage", {})
            response_time = time.time() - start_time
            self._request_count += 1
            self._total_response_time += response_time
            return ChatResponse(
                content=content,
                model=data.get("model", request.model),
                usage=usage,
                provider=self.name,
                response_time=response_time,
            )

    async def chat_completion_stream(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """Stream chat completion response"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        payload = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "stream": True,
        }
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        async with self.session.post(
            f"{self.base_url}/chat/completions", headers=headers, json=payload
        ) as response:
            async for line in response.content:
                line = line.decode("utf-8").strip()
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        content = data["choices"][0]["delta"]["content"]
                        yield content
                    except Exception:
                        logging.exception("Moonshot stream parse error")
