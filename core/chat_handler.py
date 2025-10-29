"""
Chat Handler Module

Centralized async chat processing and response management.
Handles context injection, verification, and response formatting.
"""

import logging
import re

from core.providers import generate_llm_response_async
from persona import PERSONAS
from services.file_manager import FileManager

logger = logging.getLogger(__name__)


class ChatHandler:
    """Handles chat request processing with context and verification"""

    def __init__(self, file_manager: FileManager):
        self.file_manager = file_manager
        self.markdown_instruction = (
            "Format your response using proper Markdown. Use headers (###) for sections, "
            "code blocks for examples or quotes (```), and proper linking when referencing "
            "sources. Use bullet points and numbered lists where appropriate."
        )

    def _validate_parameters(self, data: dict) -> dict:
        """Validate and normalize chat parameters"""
        provider = data.get("provider")
        model = data.get("model")
        message = data.get("message")
        persona = data.get("persona", "")

        if not provider:
            raise ValueError("Provider is required")
        if not model:
            raise ValueError("Model is required")
        if not message:
            raise ValueError("Message is required")

        # Convert and validate numeric parameters
        try:
            temperature = float(data.get("temperature", 0.7))
            max_tokens = int(data.get("max_tokens", 4000))
        except (ValueError, TypeError):
            temperature = 0.7
            max_tokens = 4000

        # Validate parameter ranges
        temperature = max(0.0, min(1.0, temperature))
        max_tokens = max(100, min(12000, max_tokens))

        return {
            "provider": provider,
            "model": model,
            "message": message,
            "persona": persona,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

    def _inject_context(self, message: str) -> str:
        """Inject relevant document context into the message"""
        try:
            context_results = self.file_manager.search_documents(message, top_n=3)
            if not context_results:
                return message

            context_texts = []
            for result in context_results:
                excerpt = (
                    result["content"][:800] + "..."
                    if len(result["content"]) > 800
                    else result["content"]
                )
                context_texts.append(
                    f"""### From {result['filename']} (Relevance: {result['similarity']:.2%})
```
{excerpt}
```"""
                )

            enhanced_message = f"""I have access to {self.file_manager.total_documents} documents. Here's relevant information I found:

{'\n\n'.join(context_texts)}

User question: {message}

Please synthesize a clear, well-organized answer using this context where relevant. Format your response in Markdown, and cite the source documents when using their information."""

            return enhanced_message

        except Exception as e:
            logger.warning(f"Error injecting context: {str(e)}")
            return message

    def _prepare_persona(self, persona_key: str) -> str:
        """Prepare persona content with markdown instructions"""
        persona_content = PERSONAS.get(persona_key, "")
        return f"{persona_content}\n{self.markdown_instruction}"

    async def _generate_initial_response(self, params: dict) -> dict:
        """Generate the initial AI response"""
        persona = self._prepare_persona(params["persona"])
        enhanced_message = self._inject_context(params["message"])
        messages = []
        if persona:
            messages.append({"role": "system", "content": persona})
        messages.append({"role": "user", "content": enhanced_message})
        model_str = f"{params['provider']}/{params['model']}"
        response = await generate_llm_response_async(
            model=model_str,
            messages=messages,
            temperature=params["temperature"],
            max_tokens=params["max_tokens"],
        )
        if not response.get("success"):
            return {"error": response.get("error", "Unknown error")}

        # Get metadata from the response
        metadata = response.get("metadata", {})

        # If metadata is not available, create basic metadata from response
        if not metadata:
            # Extract provider and model from the model string
            if "/" in model_str:
                provider, model_name = model_str.split("/", 1)
            else:
                provider = "unknown"
                model_name = model_str

            metadata = {
                "provider": provider,
                "model": model_name,
                "response_time": "0.0s",
                "usage": response.get("usage", {})
            }

        # Translate response if output_language is not English
        output_lang = params.get("output_language", "en")
        response_text = response["content"]
        if output_lang and output_lang != "en":
            try:
                from deep_translator import GoogleTranslator
                response_text = GoogleTranslator(source='auto', target=output_lang).translate(response_text)
            except Exception as e:
                # If translation fails, fallback to original
                metadata["translation_error"] = str(e)

        return {"response": {"text": response_text, "metadata": metadata}}

    async def _verify_response(self, response_text: str, original_params: dict) -> dict | None:
        """Verify response authenticity using a different model"""
        if original_params["persona"] == "authenticity_verifier":
            return None  # Avoid infinite recursion

        # Preferred verification providers (prioritizing free/open-source)
        preferred_verifiers = [
            ("groq", "llama-3.3-70b-versatile"),
            ("groq", "deepseek-r1-distill-llama-70b"),
            ("groq", "mixtral-8x7b-32768"),
        ]

        # Find a different verifier than the original
        verifier_found = False
        verifier_provider = None
        verifier_model = None
        for provider_name, model_name in preferred_verifiers:
            if (
                provider_name != original_params["provider"]
                or model_name != original_params["model"]
            ):
                verifier_found = True
                verifier_provider = provider_name
                verifier_model = model_name
                break
        if not verifier_found:
            return None

        try:
            verification_prompt = f"""Please review the following AI response for accuracy, completeness, and authenticity.\nIf you find any errors or improvements needed, provide a corrected version after 'Corrected Response:'.\nIf you have additional verification notes, add them after 'Verification Notes:'.\nIf the response is accurate as-is, just add verification notes.\n\nOriginal Response:\n{response_text}"""
            verification_persona = self._prepare_persona("authenticity_verifier")
            verification_messages = []
            if verification_persona:
                verification_messages.append({"role": "system", "content": verification_persona})
            verification_messages.append({"role": "user", "content": verification_prompt})
            model_str = f"{verifier_provider}/{verifier_model}"
            verification_response = await generate_llm_response_async(
                model=model_str,
                messages=verification_messages,
                temperature=0.3,
                max_tokens=1024
            )
            if verification_response.get("success"):
                return {"verification": verification_response["content"]}
            else:
                return {"error": verification_response.get("error", "Unknown error")}
        except Exception as e:
            return {"error": str(e)}

    def _integrate_verification(
        self, initial_response: dict, verification_response: dict | None
    ) -> dict:
        """Integrate verification results with the initial response"""
        if not verification_response:
            return initial_response

        # Defensive: handle error case in verification_response
        if "error" in verification_response:
            return {
                "response": initial_response.get("response", {}),
                "verification": {
                    "text": verification_response["error"],
                    "metadata": {},
                },
            }
        verification_text = None
        if "response" in verification_response and "text" in verification_response["response"]:
            verification_text = verification_response["response"]["text"]
        else:
            # fallback to error or raw content
            verification_text = verification_response.get("error", str(verification_response))

        # Try to extract corrected response and notes
        match = re.search(
            r"(?s)Corrected Response:?\s*(.+?)(?:\n+|$)Verification Notes:?\s*(.+)",
            verification_text,
        )

        if match:
            corrected_text = match.group(1).strip()
            verification_notes = match.group(2).strip()
            response_to_display = dict(initial_response.get("response", {}))
            response_to_display["text"] = corrected_text
        else:
            response_to_display = initial_response.get("response", {})
            verification_notes = verification_text

        metadata = {}
        if "response" in verification_response and isinstance(verification_response["response"], dict):
            raw_metadata = verification_response["response"].get("metadata", {})
            if raw_metadata and not isinstance(raw_metadata, dict):
                try:
                    metadata = dict(raw_metadata)
                except Exception:
                    metadata = str(raw_metadata)
            else:
                metadata = raw_metadata
        return {
            "response": response_to_display,
            "verification": {
                "text": verification_notes,
                "metadata": metadata,
            },
        }

    async def process_chat_request(self, data: dict) -> dict:
        """Process a complete chat request with validation, context, and verification"""
        try:
            # Validate and normalize parameters
            params = self._validate_parameters(data)

            # Generate initial response
            initial_response = await self._generate_initial_response(params)
            # If error in initial response, return immediately
            if "error" in initial_response:
                return initial_response

            # Verify response (optional)
            verification_text = initial_response.get("response", {}).get("text")
            verification_response = None
            if verification_text:
                verification_response = await self._verify_response(
                    verification_text, params
                )

            # Integrate verification results
            final_response = self._integrate_verification(initial_response, verification_response)
            return final_response

        except ValueError as e:
            raise e
        except Exception as e:
            logger.error(f"Chat processing error: {str(e)}")
            raise ValueError(f"Internal processing error: {str(e)}") from e


def create_chat_handler(file_manager: FileManager) -> ChatHandler:
    """Factory function to create a chat handler"""
    return ChatHandler(file_manager)
