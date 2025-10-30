"""
Five-Stage Piping Workflow for TQ GenAI Chat
Advanced pipeline architecture for optimized AI request processing

Stage 1: Request Preprocessing & Validation
Stage 2: Context & Memory Management
Stage 3: Provider Selection & Load Balancing
Stage 4: Parallel Response Generation
Stage 5: Response Processing & Delivery
"""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional, Callable, Dict, List
from enum import Enum
import uuid

from core.providers.factory import ProviderFactory
from core.document_store import DocumentStore
from core.optimized.optimized_document_store import OptimizedDocumentStore
from core.load_balancing.load_balancer import LoadBalancer, get_load_balancer

logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """Pipeline processing stages"""
    PREPROCESSING = "preprocessing"
    CONTEXT_GATHERING = "context_gathering"
    PROVIDER_SELECTION = "provider_selection"
    RESPONSE_GENERATION = "response_generation"
    RESPONSE_PROCESSING = "response_processing"


@dataclass
class PipelineContext:
    """Context object that flows through the pipeline"""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    original_request: dict = field(default_factory=dict)
    user_id: Optional[str] = None
    session_id: Optional[str] = None

    # Stage 1: Preprocessing
    validated_request: Optional[dict] = None
    preprocessing_metadata: dict = field(default_factory=dict)

    # Stage 2: Context
    enhanced_context: dict = field(default_factory=dict)
    relevant_documents: List[dict] = field(default_factory=list)
    conversation_history: List[dict] = field(default_factory=list)

    # Stage 3: Provider Selection
    selected_providers: List[str] = field(default_factory=list)
    provider_metadata: dict = field(default_factory=dict)
    load_balancing_context: dict = field(default_factory=dict)

    # Stage 4: Response Generation
    raw_responses: List[dict] = field(default_factory=list)
    generation_metadata: dict = field(default_factory=dict)

    # Stage 5: Response Processing
    final_response: Optional[dict] = None
    processing_metadata: dict = field(default_factory=dict)

    # Pipeline metrics
    stage_timings: Dict[PipelineStage, float] = field(default_factory=dict)
    pipeline_start_time: float = field(default_factory=time.time)

    def record_stage_timing(self, stage: PipelineStage, duration: float):
        """Record timing for a pipeline stage"""
        self.stage_timings[stage] = duration

    def get_total_pipeline_time(self) -> float:
        """Get total pipeline processing time"""
        return time.time() - self.pipeline_start_time


class PipelineStageError(Exception):
    """Custom exception for pipeline stage errors"""
    def __init__(self, stage: PipelineStage, message: str, context: PipelineContext = None):
        self.stage = stage
        self.context = context
        super().__init__(f"[{stage.value}] {message}")


class BasePipelineStage:
    """Base class for pipeline stages"""

    def __init__(self, name: str, config: dict = None):
        self.name = name
        self.config = config or {}
        self.logger = logging.getLogger(f"pipeline.{name}")

    async def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute the pipeline stage"""
        start_time = time.time()
        try:
            self.logger.info(f"Starting stage: {self.name}")
            context = await self.process(context)

            duration = time.time() - start_time
            context.record_stage_timing(PipelineStage(self.name), duration)
            self.logger.info(f"Completed stage: {self.name} in {duration:.3f}s")

            return context

        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Failed stage: {self.name} after {duration:.3f}s - {e}")
            raise PipelineStageError(PipelineStage(self.name), str(e), context)

    async def process(self, context: PipelineContext) -> PipelineContext:
        """Override this method in subclasses"""
        raise NotImplementedError


class Stage1Preprocessing(BasePipelineStage):
    """Stage 1: Request Preprocessing & Validation"""

    def __init__(self, config: dict = None):
        super().__init__("preprocessing", config)
        self.max_message_length = self.config.get("max_message_length", 10000)
        self.rate_limiter_enabled = self.config.get("rate_limiter_enabled", True)

    async def process(self, context: PipelineContext) -> PipelineContext:
        """Validate and preprocess the request"""
        request = context.original_request

        # Extract basic information
        message = request.get("message", "")
        model = request.get("model", "gpt-3.5-turbo")
        context.user_id = request.get("user_id")
        context.session_id = request.get("session_id")

        # Validate message
        if not message or not message.strip():
            raise ValueError("Message cannot be empty")

        if len(message) > self.max_message_length:
            raise ValueError(f"Message too long (max {self.max_message_length} characters)")

        # Rate limiting check (if enabled)
        if self.rate_limiter_enabled:
            await self._check_rate_limits(context.user_id)

        # Sanitize and normalize request
        validated_request = {
            "message": message.strip(),
            "model": model,
            "temperature": min(max(float(request.get("temperature", 0.7)), 0.0), 2.0),
            "max_tokens": min(int(request.get("max_tokens", 1000)), 4000),
            "user_id": context.user_id,
            "session_id": context.session_id,
            "timestamp": time.time()
        }

        # Add preprocessing metadata
        context.preprocessing_metadata = {
            "original_length": len(message),
            "sanitized_length": len(validated_request["message"]),
            "model_requested": model,
            "processing_time": time.time()
        }

        context.validated_request = validated_request
        return context

    async def _check_rate_limits(self, user_id: str):
        """Check rate limits for user"""
        # Implement rate limiting logic here
        # This could integrate with Redis for distributed rate limiting
        pass


class Stage2ContextGathering(BasePipelineStage):
    """Stage 2: Context & Memory Management"""

    def __init__(self, document_store=None, config: dict = None):
        super().__init__("context_gathering", config)
        self.document_store = document_store or OptimizedDocumentStore(enable_async=True)
        self.max_context_documents = self.config.get("max_context_documents", 5)
        self.context_ttl = self.config.get("context_ttl", 3600)  # 1 hour

    async def process(self, context: PipelineContext) -> PipelineContext:
        """Gather relevant context and documents"""
        if not context.validated_request:
            raise ValueError("No validated request available")

        message = context.validated_request["message"]

        # Gather relevant documents in parallel
        tasks = [
            self._search_relevant_documents(message),
            self._get_conversation_history(context.user_id, context.session_id),
            self._get_user_preferences(context.user_id)
        ]

        search_results, history, preferences = await asyncio.gather(*tasks, return_exceptions=True)

        # Process document search results
        if not isinstance(search_results, Exception):
            context.relevant_documents = search_results

        # Process conversation history
        if not isinstance(history, Exception):
            context.conversation_history = history

        # Build enhanced context
        context.enhanced_context = {
            "user_preferences": preferences if not isinstance(preferences, Exception) else {},
            "document_count": len(context.relevant_documents),
            "history_length": len(context.conversation_history),
            "context_timestamp": time.time()
        }

        return context

    async def _search_relevant_documents(self, query: str) -> List[dict]:
        """Search for relevant documents"""
        try:
            results = await self.document_store.search_documents_async(
                query=query,
                limit=self.max_context_documents,
                user_id=None  # Search across all users for now
            )

            return [
                {
                    "id": doc.id,
                    "title": doc.title,
                    "content": doc.content[:500],  # Truncate for context
                    "relevance_score": doc.relevance_score,
                    "type": doc.type
                }
                for doc in results
            ]
        except Exception as e:
            self.logger.error(f"Document search failed: {e}")
            return []

    async def _get_conversation_history(self, user_id: str, session_id: str) -> List[dict]:
        """Get conversation history"""
        # This would integrate with your conversation storage
        # For now, return empty history
        return []

    async def _get_user_preferences(self, user_id: str) -> dict:
        """Get user preferences and settings"""
        # This would integrate with your user management system
        return {}


class Stage3ProviderSelection(BasePipelineStage):
    """Stage 3: Provider Selection & Load Balancing"""

    def __init__(self, config: dict = None):
        super().__init__("provider_selection", config)
        self.provider_factory = ProviderFactory()
        self.load_balancer = get_load_balancer("response_time")
        self.fallback_enabled = self.config.get("fallback_enabled", True)
        self.max_providers = self.config.get("max_providers", 3)

    async def process(self, context: PipelineContext) -> PipelineContext:
        """Select optimal providers for the request"""
        if not context.validated_request:
            raise ValueError("No validated request available")

        requested_model = context.validated_request["model"]

        # Get available providers for the requested model
        available_providers = await self._get_available_providers(requested_model)

        if not available_providers:
            raise ValueError(f"No providers available for model: {requested_model}")

        # Select providers using load balancer
        selected_providers = await self._select_providers(
            available_providers,
            context,
            max_selections=min(self.max_providers, len(available_providers))
        )

        context.selected_providers = selected_providers
        context.provider_metadata = {
            "requested_model": requested_model,
            "available_count": len(available_providers),
            "selected_count": len(selected_providers),
            "selection_strategy": "load_balanced"
        }

        return context

    async def _get_available_providers(self, model: str) -> List[str]:
        """Get list of available providers for model"""
        # This would check provider health and availability
        # For now, return common providers
        return ["openai", "anthropic", "groq", "mistral"]

    async def _select_providers(self, providers: List[str], context: PipelineContext, max_selections: int) -> List[str]:
        """Select providers using load balancing strategy"""
        # Simulate load balancer selection
        # In real implementation, this would use the LoadBalancer from trash2move
        return providers[:max_selections]


class Stage4ResponseGeneration(BasePipelineStage):
    """Stage 4: Parallel Response Generation"""

    def __init__(self, config: dict = None):
        super().__init__("response_generation", config)
        self.timeout = self.config.get("timeout", 30.0)
        self.parallel_execution = self.config.get("parallel_execution", True)

    async def process(self, context: PipelineContext) -> PipelineContext:
        """Generate responses using selected providers in parallel"""
        if not context.selected_providers:
            raise ValueError("No providers selected")

        if not context.validated_request:
            raise ValueError("No validated request available")

        # Prepare generation tasks
        tasks = []
        for provider in context.selected_providers:
            task = self._generate_response(provider, context)
            tasks.append(task)

        # Execute providers in parallel or sequentially
        if self.parallel_execution:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            results = []
            for task in tasks:
                try:
                    result = await task
                    results.append(result)
                except Exception as e:
                    results.append(e)

        # Process results
        successful_responses = []
        failed_providers = []

        for i, result in enumerate(results):
            provider = context.selected_providers[i]

            if isinstance(result, Exception):
                failed_providers.append({"provider": provider, "error": str(result)})
                self.logger.error(f"Provider {provider} failed: {result}")
            else:
                successful_responses.append({
                    "provider": provider,
                    "response": result,
                    "timestamp": time.time()
                })

        context.raw_responses = successful_responses
        context.generation_metadata = {
            "total_providers": len(context.selected_providers),
            "successful_responses": len(successful_responses),
            "failed_providers": len(failed_providers),
            "parallel_execution": self.parallel_execution,
            "failed_details": failed_providers
        }

        if not successful_responses:
            raise ValueError("All providers failed to generate responses")

        return context

    async def _generate_response(self, provider: str, context: PipelineContext) -> dict:
        """Generate response from a specific provider"""
        try:
            # Simulate API call with timeout
            await asyncio.sleep(0.5)  # Simulate network latency

            # Mock response for demo
            return {
                "content": f"Response from {provider} for: {context.validated_request['message'][:50]}...",
                "model": context.validated_request["model"],
                "tokens_used": 150,
                "response_time": 0.5
            }

        except asyncio.TimeoutError:
            raise Exception(f"Provider {provider} timed out after {self.timeout}s")
        except Exception as e:
            raise Exception(f"Provider {provider} failed: {e}")


class Stage5ResponseProcessing(BasePipelineStage):
    """Stage 5: Response Processing & Delivery"""

    def __init__(self, config: dict = None):
        super().__init__("response_processing", config)
        self.response_validation_enabled = self.config.get("response_validation_enabled", True)
        self.caching_enabled = self.config.get("caching_enabled", True)

    async def process(self, context: PipelineContext) -> PipelineContext:
        """Process and validate the final response"""
        if not context.raw_responses:
            raise ValueError("No raw responses available")

        # Select best response
        best_response = await self._select_best_response(context.raw_responses)

        # Validate response if enabled
        if self.response_validation_enabled:
            validation_result = await self._validate_response(best_response, context)
            best_response["validation"] = validation_result

        # Format final response
        final_response = {
            "request_id": context.request_id,
            "content": best_response["content"],
            "model": best_response["model"],
            "provider": best_response["provider"],
            "metadata": {
                "total_providers": len(context.selected_providers),
                "successful_providers": len(context.raw_responses),
                "response_time": context.get_total_pipeline_time(),
                "stage_timings": {k.value: v for k, v in context.stage_timings.items()},
                "documents_used": len(context.relevant_documents),
                "tokens_used": best_response.get("tokens_used", 0),
                "validation_score": best_response.get("validation", {}).get("score", 1.0)
            }
        }

        context.final_response = final_response
        context.processing_metadata = {
            "selected_provider": best_response["provider"],
            "response_quality": best_response.get("validation", {}).get("quality", "good"),
            "cached": False,  # Would be set by caching logic
            "processing_complete": True
        }

        # Cache response if enabled
        if self.caching_enabled:
            await self._cache_response(context)

        return context

    async def _select_best_response(self, responses: List[dict]) -> dict:
        """Select the best response from multiple providers"""
        if not responses:
            raise ValueError("No responses to select from")

        if len(responses) == 1:
            return responses[0]

        # Score responses based on multiple factors
        scored_responses = []
        for response in responses:
            score = 0.0

            # Factor 1: Response time (lower is better)
            response_time = response.get("response_time", 1.0)
            time_score = 1.0 / (1.0 + response_time)
            score += time_score * 0.3

            # Factor 2: Content length (balanced score)
            content_length = len(response.get("content", ""))
            length_score = min(1.0, content_length / 500.0)  # Ideal around 500 chars
            score += length_score * 0.2

            # Factor 3: Provider preference
            provider_preferences = {
                "anthropic": 1.0,
                "openai": 0.9,
                "groq": 0.8,
                "mistral": 0.7
            }
            provider_score = provider_preferences.get(response["provider"], 0.5)
            score += provider_score * 0.3

            # Factor 4: Token efficiency
            tokens_used = response.get("tokens_used", 100)
            efficiency_score = max(0.1, 1.0 - (tokens_used / 1000.0))
            score += efficiency_score * 0.2

            scored_responses.append((score, response))

        # Return highest scoring response
        scored_responses.sort(key=lambda x: x[0], reverse=True)
        return scored_responses[0][1]

    async def _validate_response(self, response: dict, context: PipelineContext) -> dict:
        """Validate response quality and authenticity"""
        # Simulate response validation
        validation_score = 0.85  # Mock validation score

        return {
            "score": validation_score,
            "quality": "good" if validation_score > 0.7 else "fair",
            "authenticity_check": True,
            "content_filter": "passed",
            "validation_time": 0.1
        }

    async def _cache_response(self, context: PipelineContext):
        """Cache the processed response"""
        # This would integrate with Redis or other caching system
        pass


class PipelineOrchestrator:
    """Main pipeline orchestrator that manages the five-stage workflow"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.logger = logging.getLogger("pipeline.orchestrator")

        # Initialize pipeline stages
        self.stages = {
            PipelineStage.PREPROCESSING: Stage1Preprocessing(
                self.config.get("preprocessing", {})
            ),
            PipelineStage.CONTEXT_GATHERING: Stage2ContextGathering(
                document_store=self.config.get("document_store"),
                config=self.config.get("context_gathering", {})
            ),
            PipelineStage.PROVIDER_SELECTION: Stage3ProviderSelection(
                self.config.get("provider_selection", {})
            ),
            PipelineStage.RESPONSE_GENERATION: Stage4ResponseGeneration(
                self.config.get("response_generation", {})
            ),
            PipelineStage.RESPONSE_PROCESSING: Stage5ResponseProcessing(
                self.config.get("response_processing", {})
            )
        }

        # Metrics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.stage_errors = {}

    async def process_request(self, request: dict) -> dict:
        """Process a request through the complete pipeline"""
        self.total_requests += 1
        start_time = time.time()

        # Initialize pipeline context
        context = PipelineContext(original_request=request)

        try:
            self.logger.info(f"Processing request {context.request_id} through pipeline")

            # Execute pipeline stages
            for stage_enum in PipelineStage:
                stage = self.stages[stage_enum]
                context = await stage.execute(context)

            # Pipeline completed successfully
            self.successful_requests += 1
            total_time = time.time() - start_time

            self.logger.info(
                f"Pipeline completed for {context.request_id} in {total_time:.3f}s"
            )

            return context.final_response

        except PipelineStageError as e:
            self.failed_requests += 1
            self.stage_errors[e.stage] = self.stage_errors.get(e.stage, 0) + 1

            self.logger.error(f"Pipeline failed for {context.request_id} at stage {e.stage}: {e}")

            return {
                "error": str(e),
                "stage": e.stage.value,
                "request_id": context.request_id,
                "partial_context": self._extract_safe_context(e.context) if e.context else None
            }

        except Exception as e:
            self.failed_requests += 1
            self.logger.error(f"Unexpected pipeline error for {context.request_id}: {e}")

            return {
                "error": f"Pipeline error: {str(e)}",
                "request_id": context.request_id,
                "unexpected_error": True
            }

    def _extract_safe_context(self, context: PipelineContext) -> dict:
        """Extract safe context information for error responses"""
        if not context:
            return {}

        return {
            "request_id": context.request_id,
            "stage_timings": {k.value: v for k, v in context.stage_timings.items()},
            "completed_stages": list(context.stage_timings.keys())
        }

    def get_pipeline_metrics(self) -> dict:
        """Get pipeline performance metrics"""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.successful_requests / max(1, self.total_requests),
            "stage_errors": self.stage_errors,
            "stages_configured": list(self.stages.keys())
        }


# Global pipeline instance
_pipeline_orchestrator = None


def get_pipeline_orchestrator(config: dict = None) -> PipelineOrchestrator:
    """Get or create the global pipeline orchestrator"""
    global _pipeline_orchestrator
    if _pipeline_orchestrator is None:
        _pipeline_orchestrator = PipelineOrchestrator(config)
    return _pipeline_orchestrator


# Convenience function for direct pipeline usage
async def process_chat_request(request: dict, pipeline_config: dict = None) -> dict:
    """Process a chat request through the five-stage pipeline"""
    orchestrator = get_pipeline_orchestrator(pipeline_config)
    return await orchestrator.process_request(request)