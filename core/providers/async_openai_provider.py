"""High-performance async OpenAI provider"""

import json
import os
import time
from collections.abc import AsyncGenerator

from .async_base import AsyncAIProviderInterface, ChatRequest, ChatResponse


class AsyncOpenAIProvider(AsyncAIProviderInterface):
    """High-performance async OpenAI API provider"""

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.base_url = "https://api.openai.com/v1"
        self._models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]

    @property
    def name(self) -> str:
        return "openai"

    async def get_models(self) -> list[str]:
        return self._models

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """Process chat completion using async OpenAI API"""
        start_time = time.time()

        try:
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
                    raise Exception(f"OpenAI API error: {response.status} - {error_text}")

                data = await response.json()

                response_time = time.time() - start_time
                self._record_response_time(response_time)

                return ChatResponse(
                    content=data["choices"][0]["message"]["content"],
                    model=data["model"],
                    usage={
                        "prompt_tokens": data["usage"]["prompt_tokens"],
                        "completion_tokens": data["usage"]["completion_tokens"],
                        "total_tokens": data["usage"]["total_tokens"],
                    },
                    provider=self.name,
                    response_time=response_time,
                )

        except Exception as e:
            response_time = time.time() - start_time
            self._record_response_time(response_time)
            raise Exception(f"Async OpenAI API error: {str(e)}")

    async def chat_completion_stream(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """Stream chat completion response"""
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        payload = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "stream": True,
        }

        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens

        try:
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
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            raise Exception(f"OpenAI streaming error: {str(e)}")
