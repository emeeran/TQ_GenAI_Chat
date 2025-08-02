"""
Chat Handler Module

Centralized chat processing and response management.
Handles context injection, verification, and response formatting.
"""

import re

from flask import current_app

from core.providers import provider_manager
from persona import PERSONAS
from services.file_manager import FileManager


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
        provider = data.get('provider')
        model = data.get('model')
        message = data.get('message')
        persona = data.get('persona', '')
        
        if not provider:
            raise ValueError("Provider is required")
        if not model:
            raise ValueError("Model is required")
        if not message:
            raise ValueError("Message is required")
        
        # Convert and validate numeric parameters
        try:
            temperature = float(data.get('temperature', 0.7))
            max_tokens = int(data.get('max_tokens', 4000))
        except (ValueError, TypeError):
            temperature = 0.7
            max_tokens = 4000
        
        # Validate parameter ranges
        temperature = max(0.0, min(1.0, temperature))
        max_tokens = max(100, min(12000, max_tokens))
        
        return {
            'provider': provider,
            'model': model,
            'message': message,
            'persona': persona,
            'temperature': temperature,
            'max_tokens': max_tokens
        }
    
    def _inject_context(self, message: str) -> str:
        """Inject relevant document context into the message"""
        try:
            context_results = self.file_manager.search_documents(message, top_n=3)
            if not context_results:
                return message
            
            context_texts = []
            for result in context_results:
                excerpt = result['content'][:800] + '...' if len(result['content']) > 800 else result['content']
                context_texts.append(f"""### From {result['filename']} (Relevance: {result['similarity']:.2%})
```
{excerpt}
```""")
            
            enhanced_message = f"""I have access to {self.file_manager.total_documents} documents. Here's relevant information I found:

{'\n\n'.join(context_texts)}

User question: {message}

Please synthesize a clear, well-organized answer using this context where relevant. Format your response in Markdown, and cite the source documents when using their information."""
            
            return enhanced_message
            
        except Exception as e:
            current_app.logger.warning(f"Error injecting context: {str(e)}")
            return message
    
    def _prepare_persona(self, persona_key: str) -> str:
        """Prepare persona content with markdown instructions"""
        persona_content = PERSONAS.get(persona_key, '')
        return f"{persona_content}\n{self.markdown_instruction}"
    
    def _generate_initial_response(self, params: dict) -> dict:
        """Generate the initial AI response"""
        provider = provider_manager.get_provider(params['provider'])
        if not provider:
            raise ValueError(f"Provider '{params['provider']}' not available or not configured")
        
        persona = self._prepare_persona(params['persona'])
        enhanced_message = self._inject_context(params['message'])
        
        response = provider.generate_response(
            model=params['model'],
            message=enhanced_message,
            persona=persona,
            temperature=params['temperature'],
            max_tokens=params['max_tokens']
        )
        
        if not response.success:
            raise ValueError(response.error or "Failed to generate response")
        
        return {
            'response': {
                'text': response.text,
                'metadata': response.metadata
            }
        }
    
    def _verify_response(self, response_text: str, original_params: dict) -> dict | None:
        """Verify response authenticity using a different model"""
        if original_params['persona'] == 'authenticity_verifier':
            return None  # Avoid infinite recursion
        
        # Preferred verification providers (prioritizing free/open-source)
        preferred_verifiers = [
            ('groq', 'llama-3.3-70b-versatile'),
            ('groq', 'deepseek-r1-distill-llama-70b'),
            ('groq', 'mixtral-8x7b-32768'),
        ]
        
        # Find a different verifier than the original
        verifier_provider = None
        for provider_name, model_name in preferred_verifiers:
            if (provider_name != original_params['provider'] or 
                model_name != original_params['model']):
                if provider_manager.is_provider_available(provider_name):
                    verifier_provider = provider_manager.get_provider(provider_name)
                    if verifier_provider:
                        break
        
        if not verifier_provider:
            return None
        
        try:
            verification_prompt = f"""Please review the following AI response for accuracy, completeness, and authenticity. 
If you find any errors or improvements needed, provide a corrected version after "Corrected Response:".
If you have additional verification notes, add them after "Verification Notes:".
If the response is accurate as-is, just add verification notes.

Original Response:
{response_text}"""
            
            verification_response = verifier_provider.generate_response(
                model=model_name if 'model_name' in locals() else verifier_provider.config.default_model,
                message=verification_prompt,
                persona="You are a thorough fact-checker and response verifier."
            )
            
            if verification_response.success:
                return {
                    'response': {
                        'text': verification_response.text,
                        'metadata': verification_response.metadata
                    }
                }
        except Exception as e:
            current_app.logger.warning(f"Verification failed: {str(e)}")
        
        return None
    
    def _integrate_verification(self, initial_response: dict, verification_response: dict | None) -> dict:
        """Integrate verification results with the initial response"""
        if not verification_response:
            return initial_response
        
        verification_text = verification_response['response']['text']
        
        # Try to extract corrected response and notes
        match = re.search(r"(?s)Corrected Response:?\s*(.+?)(?:\n+|$)Verification Notes:?\s*(.+)", verification_text)
        
        if match:
            corrected_text = match.group(1).strip()
            verification_notes = match.group(2).strip()
            
            # Use corrected response if available
            response_to_display = dict(initial_response['response'])
            response_to_display['text'] = corrected_text
        else:
            response_to_display = initial_response['response']
            verification_notes = verification_text
        
        return {
            'response': response_to_display,
            'verification': {
                'text': verification_notes,
                'metadata': verification_response['response'].get('metadata', {})
            }
        }
    
    def process_chat_request(self, data: dict) -> dict:
        """Process a complete chat request with validation, context, and verification"""
        try:
            # Validate and normalize parameters
            params = self._validate_parameters(data)
            
            # Generate initial response
            initial_response = self._generate_initial_response(params)
            
            # Verify response (optional)
            verification_response = self._verify_response(
                initial_response['response']['text'], 
                params
            )
            
            # Integrate verification results
            final_response = self._integrate_verification(initial_response, verification_response)
            
            return final_response
            
        except ValueError as e:
            raise e
        except Exception as e:
            current_app.logger.error(f"Chat processing error: {str(e)}")
            raise ValueError(f"Internal processing error: {str(e)}") from e


def create_chat_handler(file_manager: FileManager) -> ChatHandler:
    """Factory function to create a chat handler"""
    return ChatHandler(file_manager)
