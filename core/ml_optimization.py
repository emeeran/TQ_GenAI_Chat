"""
ML-Powered features for TQ GenAI Chat application.
Provides intelligent caching, content recommendations, and usage prediction.
"""

import asyncio
import hashlib
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import numpy as np

try:
    import joblib
    from sklearn.cluster import KMeans
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class UserInteraction:
    """User interaction data point."""
    user_id: str
    message: str
    provider: str
    model: str
    response_time: float
    timestamp: datetime
    satisfaction_score: float | None = None
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentRecommendation:
    """Content recommendation with confidence score."""
    content: str
    confidence: float
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)


class SemanticCache:
    """Intelligent caching based on semantic similarity."""

    def __init__(self, similarity_threshold: float = 0.85, max_cache_size: int = 10000):
        self.similarity_threshold = similarity_threshold
        self.max_cache_size = max_cache_size
        self.cache: dict[str, dict] = {}
        self.embeddings: dict[str, np.ndarray] = {}
        self.vectorizer = None
        self.message_vectors = []
        self.message_keys = []

        if SKLEARN_AVAILABLE:
            self.vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words='english',
                ngram_range=(1, 2)
            )

    async def initialize(self):
        """Initialize the semantic cache."""
        if not SKLEARN_AVAILABLE:
            logger.warning("scikit-learn not available - semantic features disabled")
            return

        logger.info("Semantic cache initialized")

    def _compute_text_similarity(self, text1: str, text2: str) -> float:
        """Compute semantic similarity between two texts."""
        if not self.vectorizer:
            # Fallback to simple string similarity
            return self._simple_similarity(text1, text2)

        try:
            # Vectorize the texts
            vectors = self.vectorizer.fit_transform([text1, text2])
            similarity = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
            return float(similarity)
        except Exception:
            return self._simple_similarity(text1, text2)

    def _simple_similarity(self, text1: str, text2: str) -> float:
        """Simple similarity fallback."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return intersection / union if union > 0 else 0.0

    async def get_similar_response(self, message: str, provider: str = None,
                                 model: str = None) -> dict | None:
        """Find cached response for similar message."""
        best_match = None
        best_similarity = 0.0

        for _cache_key, cached_data in self.cache.items():
            # Check provider/model constraints
            if provider and cached_data.get('provider') != provider:
                continue
            if model and cached_data.get('model') != model:
                continue

            # Compute similarity
            cached_message = cached_data['message']
            similarity = self._compute_text_similarity(message, cached_message)

            if similarity > best_similarity and similarity >= self.similarity_threshold:
                best_similarity = similarity
                best_match = cached_data

        if best_match:
            logger.info(f"Cache hit with {best_similarity:.3f} similarity")
            # Update access time and hit count
            best_match['last_accessed'] = time.time()
            best_match['hit_count'] = best_match.get('hit_count', 0) + 1

        return best_match

    async def cache_response(self, message: str, response: str, provider: str,
                           model: str, response_time: float, user_id: str = None):
        """Cache a response with metadata."""
        cache_key = hashlib.sha256(
            f"{message}:{provider}:{model}".encode()
        ).hexdigest()

        cache_data = {
            'message': message,
            'response': response,
            'provider': provider,
            'model': model,
            'response_time': response_time,
            'user_id': user_id,
            'cached_at': time.time(),
            'last_accessed': time.time(),
            'hit_count': 0
        }

        self.cache[cache_key] = cache_data

        # Maintain cache size
        if len(self.cache) > self.max_cache_size:
            await self._evict_least_useful()

        logger.debug(f"Cached response for message: {message[:50]}...")

    async def _evict_least_useful(self):
        """Evict least useful cache entries."""
        # Score based on recency, frequency, and response time
        scored_entries = []

        current_time = time.time()
        for key, data in self.cache.items():
            recency_score = 1.0 / (current_time - data['last_accessed'] + 1)
            frequency_score = data['hit_count']
            speed_score = 1.0 / (data['response_time'] + 0.1)

            total_score = recency_score + frequency_score + speed_score
            scored_entries.append((total_score, key))

        # Remove lowest scoring entries
        scored_entries.sort()
        to_remove = len(scored_entries) - int(self.max_cache_size * 0.8)

        for _, key in scored_entries[:to_remove]:
            del self.cache[key]

        logger.info(f"Evicted {to_remove} cache entries")


class SmartRecommendationEngine:
    """ML-powered content and provider recommendation system."""

    def __init__(self):
        self.user_interactions: Dict[str, List[UserInteraction]] = defaultdict(list)
        self.provider_performance: Dict[str, Dict] = defaultdict(dict)
        self.content_clusters = None
        self.provider_predictor = None
        self.satisfaction_predictor = None

        # Recommendation models
        self.models_initialized = False

    async def initialize(self):
        """Initialize ML models."""
        if not SKLEARN_AVAILABLE:
            logger.warning("scikit-learn not available - ML recommendations disabled")
            return

        try:
            # Initialize models
            self.provider_predictor = LogisticRegression(random_state=42)
            self.satisfaction_predictor = RandomForestRegressor(random_state=42)

            # Load pre-trained models if available
            await self._load_models()

            self.models_initialized = True
            logger.info("Recommendation engine initialized")

        except Exception as e:
            logger.error(f"Failed to initialize recommendation engine: {e}")

    async def record_interaction(self, interaction: UserInteraction):
        """Record user interaction for learning."""
        self.user_interactions[interaction.user_id].append(interaction)

        # Update provider performance metrics
        provider_key = f"{interaction.provider}:{interaction.model}"
        if provider_key not in self.provider_performance:
            self.provider_performance[provider_key] = {
                'total_requests': 0,
                'total_response_time': 0.0,
                'satisfaction_scores': []
            }

        perf = self.provider_performance[provider_key]
        perf['total_requests'] += 1
        perf['total_response_time'] += interaction.response_time

        if interaction.satisfaction_score is not None:
            perf['satisfaction_scores'].append(interaction.satisfaction_score)

        # Trigger model retraining if we have enough data
        if len(self.user_interactions[interaction.user_id]) % 100 == 0:
            await self._retrain_models()

    async def recommend_provider(self, user_id: str, message: str,
                               available_providers: List[str]) -> str:
        """Recommend best provider for user and message."""
        if not self.models_initialized or not available_providers:
            # Fallback to performance-based recommendation
            return self._recommend_by_performance(available_providers)

        try:
            # Extract features for prediction
            features = self._extract_message_features(message, user_id)

            if hasattr(self.provider_predictor, 'predict_proba'):
                # Get probabilities for each provider
                provider_probs = self.provider_predictor.predict_proba([features])[0]
                classes = self.provider_predictor.classes_

                # Filter to available providers and select best
                best_provider = None
                best_prob = 0.0

                for provider, prob in zip(classes, provider_probs, strict=False):
                    if provider in available_providers and prob > best_prob:
                        best_provider = provider
                        best_prob = prob

                if best_provider:
                    logger.info(f"ML recommended provider: {best_provider} (confidence: {best_prob:.3f})")
                    return best_provider

        except Exception as e:
            logger.error(f"Provider recommendation failed: {e}")

        # Fallback
        return self._recommend_by_performance(available_providers)

    def _recommend_by_performance(self, available_providers: List[str]) -> str:
        """Fallback provider recommendation based on performance."""
        best_provider = available_providers[0]
        best_score = 0.0

        for provider in available_providers:
            # Calculate composite score based on speed and satisfaction
            provider_key = f"{provider}:default"
            perf = self.provider_performance.get(provider_key, {})

            if perf.get('total_requests', 0) > 0:
                avg_response_time = perf['total_response_time'] / perf['total_requests']
                avg_satisfaction = np.mean(perf['satisfaction_scores']) if perf['satisfaction_scores'] else 0.5

                # Score: high satisfaction, low response time
                speed_score = 1.0 / (avg_response_time + 0.1)
                satisfaction_score = avg_satisfaction
                composite_score = (speed_score * 0.3 + satisfaction_score * 0.7)

                if composite_score > best_score:
                    best_score = composite_score
                    best_provider = provider

        return best_provider

    async def recommend_content(self, user_id: str, context: str = "") -> List[ContentRecommendation]:
        """Recommend content based on user history and context."""
        recommendations = []

        user_history = self.user_interactions.get(user_id, [])
        if not user_history:
            return self._get_default_recommendations()

        # Analyze user patterns
        recent_interactions = user_history[-20:]  # Last 20 interactions

        # Content clustering recommendations
        if self.content_clusters is not None:
            cluster_recommendations = await self._recommend_from_clusters(
                recent_interactions, context
            )
            recommendations.extend(cluster_recommendations)

        # Collaborative filtering recommendations
        collaborative_recommendations = await self._recommend_collaborative(
            user_id, recent_interactions
        )
        recommendations.extend(collaborative_recommendations)

        # Trend-based recommendations
        trend_recommendations = await self._recommend_trending()
        recommendations.extend(trend_recommendations)

        # Sort by confidence and return top recommendations
        recommendations.sort(key=lambda x: x.confidence, reverse=True)
        return recommendations[:5]

    async def _recommend_from_clusters(self, user_interactions: List[UserInteraction],
                                     context: str) -> List[ContentRecommendation]:
        """Recommend content based on content clustering."""
        recommendations = []

        if not SKLEARN_AVAILABLE or not user_interactions:
            return recommendations

        try:
            # Extract topics from user's recent messages
            user_messages = [interaction.message for interaction in user_interactions]

            # Simple topic extraction (in production, use more sophisticated NLP)
            common_words = self._extract_common_words(user_messages + [context])

            # Generate recommendations based on common themes
            for word in common_words[:3]:
                recommendations.append(ContentRecommendation(
                    content=f"Tell me more about {word}",
                    confidence=0.7,
                    reason=f"Based on your interest in {word}",
                    metadata={"topic": word, "source": "clustering"}
                ))

        except Exception as e:
            logger.error(f"Cluster recommendation failed: {e}")

        return recommendations

    async def _recommend_collaborative(self, user_id: str,
                                     user_interactions: List[UserInteraction]) -> List[ContentRecommendation]:
        """Collaborative filtering recommendations."""
        recommendations = []

        try:
            # Find similar users based on interaction patterns
            similar_users = self._find_similar_users(user_id, user_interactions)

            # Recommend content that similar users found satisfying
            for similar_user_id, similarity_score in similar_users[:3]:
                similar_user_interactions = self.user_interactions.get(similar_user_id, [])

                # Find highly rated interactions
                high_satisfaction = [
                    interaction for interaction in similar_user_interactions
                    if interaction.satisfaction_score and interaction.satisfaction_score > 0.8
                ]

                if high_satisfaction:
                    interaction = high_satisfaction[-1]  # Most recent high satisfaction
                    recommendations.append(ContentRecommendation(
                        content=f"Similar to: {interaction.message[:50]}...",
                        confidence=similarity_score * 0.8,
                        reason="Users with similar interests enjoyed this",
                        metadata={
                            "similar_user": similar_user_id,
                            "original_message": interaction.message,
                            "source": "collaborative"
                        }
                    ))

        except Exception as e:
            logger.error(f"Collaborative recommendation failed: {e}")

        return recommendations

    async def _recommend_trending(self) -> List[ContentRecommendation]:
        """Recommend trending content."""
        recommendations = []

        try:
            # Analyze recent interactions across all users
            recent_cutoff = datetime.now() - timedelta(hours=24)
            recent_interactions = []

            for user_interactions in self.user_interactions.values():
                recent_interactions.extend([
                    interaction for interaction in user_interactions
                    if interaction.timestamp > recent_cutoff
                ])

            # Find trending topics/patterns
            if recent_interactions:
                messages = [interaction.message for interaction in recent_interactions]
                trending_words = self._extract_common_words(messages)

                for word in trending_words[:2]:
                    recommendations.append(ContentRecommendation(
                        content=f"What's trending: {word}",
                        confidence=0.6,
                        reason="This topic is trending today",
                        metadata={"trending_topic": word, "source": "trending"}
                    ))

        except Exception as e:
            logger.error(f"Trending recommendation failed: {e}")

        return recommendations

    def _get_default_recommendations(self) -> List[ContentRecommendation]:
        """Default recommendations for new users."""
        return [
            ContentRecommendation(
                content="How can I help you today?",
                confidence=0.9,
                reason="Getting started",
                metadata={"source": "default"}
            ),
            ContentRecommendation(
                content="What would you like to know about?",
                confidence=0.8,
                reason="Open-ended exploration",
                metadata={"source": "default"}
            ),
            ContentRecommendation(
                content="I can help with analysis, writing, and problem-solving",
                confidence=0.7,
                reason="Capability overview",
                metadata={"source": "default"}
            )
        ]

    def _extract_message_features(self, message: str, user_id: str) -> List[float]:
        """Extract features for ML prediction."""
        features = []

        # Message length features
        features.append(len(message))
        features.append(len(message.split()))

        # User history features
        user_history = self.user_interactions.get(user_id, [])
        features.append(len(user_history))

        if user_history:
            avg_response_time = np.mean([i.response_time for i in user_history])
            features.append(avg_response_time)

            # Recent satisfaction
            recent_satisfaction = [
                i.satisfaction_score for i in user_history[-10:]
                if i.satisfaction_score is not None
            ]
            features.append(np.mean(recent_satisfaction) if recent_satisfaction else 0.5)
        else:
            features.extend([0.0, 0.5])

        # Time-based features
        hour = datetime.now().hour
        features.append(hour / 24.0)  # Normalize hour

        return features

    def _extract_common_words(self, messages: List[str], top_k: int = 10) -> List[str]:
        """Extract most common meaningful words."""
        word_counts = defaultdict(int)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}

        for message in messages:
            words = message.lower().split()
            for word in words:
                word = word.strip('.,!?";')
                if len(word) > 3 and word not in stop_words:
                    word_counts[word] += 1

        return sorted(word_counts.keys(), key=word_counts.get, reverse=True)[:top_k]

    def _find_similar_users(self, user_id: str, user_interactions: List[UserInteraction],
                          top_k: int = 5) -> List[Tuple[str, float]]:
        """Find users with similar interaction patterns."""
        user_vector = self._create_user_vector(user_interactions)
        similarities = []

        for other_user_id, other_interactions in self.user_interactions.items():
            if other_user_id == user_id or len(other_interactions) < 5:
                continue

            other_vector = self._create_user_vector(other_interactions)
            similarity = self._cosine_similarity(user_vector, other_vector)
            similarities.append((other_user_id, similarity))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    def _create_user_vector(self, interactions: List[UserInteraction]) -> np.ndarray:
        """Create feature vector for user based on interactions."""
        if not interactions:
            return np.zeros(10)

        features = []

        # Average response time
        features.append(np.mean([i.response_time for i in interactions]))

        # Provider preferences
        providers = [i.provider for i in interactions]
        provider_counts = defaultdict(int)
        for provider in providers:
            provider_counts[provider] += 1

        total_interactions = len(interactions)
        features.extend([
            provider_counts.get('openai', 0) / total_interactions,
            provider_counts.get('anthropic', 0) / total_interactions,
            provider_counts.get('groq', 0) / total_interactions,
        ])

        # Message characteristics
        message_lengths = [len(i.message) for i in interactions]
        features.extend([
            np.mean(message_lengths),
            np.std(message_lengths),
        ])

        # Satisfaction patterns
        satisfaction_scores = [
            i.satisfaction_score for i in interactions
            if i.satisfaction_score is not None
        ]
        if satisfaction_scores:
            features.extend([
                np.mean(satisfaction_scores),
                np.std(satisfaction_scores)
            ])
        else:
            features.extend([0.5, 0.0])

        # Time patterns
        hours = [i.timestamp.hour for i in interactions]
        features.append(np.mean(hours) / 24.0)

        return np.array(features)

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    async def _retrain_models(self):
        """Retrain ML models with new data."""
        if not SKLEARN_AVAILABLE or not self.models_initialized:
            return

        try:
            # Prepare training data
            X, y_provider, y_satisfaction = self._prepare_training_data()

            if len(X) < 50:  # Need minimum data
                return

            # Train provider prediction model
            if len(set(y_provider)) > 1:
                self.provider_predictor.fit(X, y_provider)

            # Train satisfaction prediction model
            satisfaction_mask = [score is not None for score in y_satisfaction]
            if sum(satisfaction_mask) > 10:
                X_sat = [x for x, mask in zip(X, satisfaction_mask, strict=False) if mask]
                y_sat = [score for score in y_satisfaction if score is not None]
                self.satisfaction_predictor.fit(X_sat, y_sat)

            # Save models
            await self._save_models()

            logger.info("ML models retrained successfully")

        except Exception as e:
            logger.error(f"Model retraining failed: {e}")

    def _prepare_training_data(self) -> Tuple[List[List[float]], List[str], List[Optional[float]]]:
        """Prepare training data from user interactions."""
        X = []
        y_provider = []
        y_satisfaction = []

        for user_id, interactions in self.user_interactions.items():
            for interaction in interactions:
                features = self._extract_message_features(interaction.message, user_id)
                X.append(features)
                y_provider.append(interaction.provider)
                y_satisfaction.append(interaction.satisfaction_score)

        return X, y_provider, y_satisfaction

    async def _save_models(self):
        """Save trained models to disk."""
        if not SKLEARN_AVAILABLE:
            return

        try:
            if hasattr(self.provider_predictor, 'coef_'):
                joblib.dump(self.provider_predictor, 'models/provider_predictor.pkl')

            if hasattr(self.satisfaction_predictor, 'feature_importances_'):
                joblib.dump(self.satisfaction_predictor, 'models/satisfaction_predictor.pkl')

            logger.info("Models saved successfully")

        except Exception as e:
            logger.error(f"Model saving failed: {e}")

    async def _load_models(self):
        """Load pre-trained models from disk."""
        if not SKLEARN_AVAILABLE:
            return

        try:
            import os

            if os.path.exists('models/provider_predictor.pkl'):
                self.provider_predictor = joblib.load('models/provider_predictor.pkl')
                logger.info("Provider predictor model loaded")

            if os.path.exists('models/satisfaction_predictor.pkl'):
                self.satisfaction_predictor = joblib.load('models/satisfaction_predictor.pkl')
                logger.info("Satisfaction predictor model loaded")

        except Exception as e:
            logger.error(f"Model loading failed: {e}")


class UsagePredictionEngine:
    """Predict usage patterns for proactive scaling and optimization."""

    def __init__(self):
        self.usage_history: deque = deque(maxlen=10000)
        self.prediction_model = None
        self.seasonal_patterns = {}

    async def initialize(self):
        """Initialize the prediction engine."""
        if SKLEARN_AVAILABLE:
            self.prediction_model = RandomForestRegressor(
                n_estimators=100,
                random_state=42
            )

        logger.info("Usage prediction engine initialized")

    def record_usage(self, timestamp: datetime, concurrent_users: int,
                    request_rate: float, provider: str):
        """Record usage data point."""
        self.usage_history.append({
            'timestamp': timestamp,
            'concurrent_users': concurrent_users,
            'request_rate': request_rate,
            'provider': provider,
            'hour': timestamp.hour,
            'day_of_week': timestamp.weekday(),
            'day_of_month': timestamp.day
        })

    async def predict_usage(self, hours_ahead: int = 24) -> Dict[str, float]:
        """Predict usage metrics for the next N hours."""
        if not self.prediction_model or len(self.usage_history) < 100:
            return await self._simple_prediction(hours_ahead)

        try:
            # Prepare features and targets
            X, y = self._prepare_prediction_data()

            if len(X) < 50:
                return await self._simple_prediction(hours_ahead)

            # Train model
            self.prediction_model.fit(X, y)

            # Make predictions
            predictions = {}
            current_time = datetime.now()

            for hour in range(1, hours_ahead + 1):
                future_time = current_time + timedelta(hours=hour)
                features = self._extract_time_features(future_time)

                predicted_users = max(0, self.prediction_model.predict([features])[0])

                predictions[f"hour_{hour}"] = {
                    'predicted_users': predicted_users,
                    'timestamp': future_time.isoformat()
                }

            return predictions

        except Exception as e:
            logger.error(f"Usage prediction failed: {e}")
            return await self._simple_prediction(hours_ahead)

    async def _simple_prediction(self, hours_ahead: int) -> Dict[str, float]:
        """Simple pattern-based prediction fallback."""
        predictions = {}

        if not self.usage_history:
            # Default prediction
            for hour in range(1, hours_ahead + 1):
                predictions[f"hour_{hour}"] = {
                    'predicted_users': 10.0,
                    'timestamp': (datetime.now() + timedelta(hours=hour)).isoformat()
                }
            return predictions

        # Use recent average with time-of-day adjustment
        recent_data = list(self.usage_history)[-100:]
        avg_users = np.mean([d['concurrent_users'] for d in recent_data])

        current_time = datetime.now()
        for hour in range(1, hours_ahead + 1):
            future_time = current_time + timedelta(hours=hour)

            # Simple time-of-day multiplier
            hour_multiplier = self._get_hour_multiplier(future_time.hour)
            predicted_users = avg_users * hour_multiplier

            predictions[f"hour_{hour}"] = {
                'predicted_users': max(1.0, predicted_users),
                'timestamp': future_time.isoformat()
            }

        return predictions

    def _prepare_prediction_data(self) -> Tuple[List[List[float]], List[float]]:
        """Prepare data for ML prediction."""
        X = []
        y = []

        for data_point in self.usage_history:
            features = [
                data_point['hour'] / 24.0,
                data_point['day_of_week'] / 7.0,
                data_point['day_of_month'] / 31.0,
                data_point['request_rate']
            ]

            X.append(features)
            y.append(data_point['concurrent_users'])

        return X, y

    def _extract_time_features(self, timestamp: datetime) -> List[float]:
        """Extract time-based features for prediction."""
        return [
            timestamp.hour / 24.0,
            timestamp.weekday() / 7.0,
            timestamp.day / 31.0,
            self._get_recent_request_rate()
        ]

    def _get_recent_request_rate(self) -> float:
        """Get recent average request rate."""
        if not self.usage_history:
            return 1.0

        recent_data = list(self.usage_history)[-10:]
        return np.mean([d['request_rate'] for d in recent_data])

    def _get_hour_multiplier(self, hour: int) -> float:
        """Get multiplier based on typical usage patterns."""
        # Business hours have higher usage
        if 9 <= hour <= 17:
            return 1.2
        elif 18 <= hour <= 22:
            return 1.0
        elif 23 <= hour or hour <= 6:
            return 0.3
        else:
            return 0.8


class MLPoweredOptimizer:
    """Main ML optimization coordinator."""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

        self.semantic_cache = SemanticCache(
            similarity_threshold=self.config.get('similarity_threshold', 0.85),
            max_cache_size=self.config.get('max_cache_size', 10000)
        )

        self.recommendation_engine = SmartRecommendationEngine()
        self.usage_predictor = UsagePredictionEngine()

        # Performance tracking
        self.cache_hit_rate = 0.0
        self.recommendation_accuracy = 0.0
        self.prediction_accuracy = 0.0

    async def start(self):
        """Initialize all ML components."""
        await self.semantic_cache.initialize()
        await self.recommendation_engine.initialize()
        await self.usage_predictor.initialize()

        logger.info("ML-powered optimizer started")

    async def process_chat_request(self, user_id: str, message: str,
                                 available_providers: List[str]) -> Dict[str, Any]:
        """Process chat request with ML optimizations."""
        start_time = time.time()

        # 1. Try semantic cache first
        cached_response = await self.semantic_cache.get_similar_response(message)
        if cached_response:
            return {
                'response': cached_response['response'],
                'provider': cached_response['provider'],
                'model': cached_response['model'],
                'cached': True,
                'cache_similarity': cached_response.get('similarity', 1.0)
            }

        # 2. Get provider recommendation
        recommended_provider = await self.recommendation_engine.recommend_provider(
            user_id, message, available_providers
        )

        # 3. Get content recommendations
        recommendations = await self.recommendation_engine.recommend_content(
            user_id, message
        )

        return {
            'recommended_provider': recommended_provider,
            'content_recommendations': [
                {
                    'content': rec.content,
                    'confidence': rec.confidence,
                    'reason': rec.reason
                } for rec in recommendations
            ],
            'processing_time': time.time() - start_time,
            'cached': False
        }

    async def record_interaction_result(self, user_id: str, message: str,
                                      response: str, provider: str, model: str,
                                      response_time: float, satisfaction_score: float = None):
        """Record interaction result for learning."""
        # Record for recommendation engine
        interaction = UserInteraction(
            user_id=user_id,
            message=message,
            provider=provider,
            model=model,
            response_time=response_time,
            timestamp=datetime.now(),
            satisfaction_score=satisfaction_score
        )

        await self.recommendation_engine.record_interaction(interaction)

        # Cache the response
        await self.semantic_cache.cache_response(
            message, response, provider, model, response_time, user_id
        )

        logger.debug(f"Recorded interaction for user {user_id}")

    async def get_usage_predictions(self, hours_ahead: int = 24) -> Dict[str, Any]:
        """Get usage predictions for capacity planning."""
        return await self.usage_predictor.predict_usage(hours_ahead)

    async def get_optimization_metrics(self) -> Dict[str, Any]:
        """Get ML optimization performance metrics."""
        return {
            'semantic_cache': {
                'size': len(self.semantic_cache.cache),
                'hit_rate': self.cache_hit_rate,
                'similarity_threshold': self.semantic_cache.similarity_threshold
            },
            'recommendations': {
                'users_tracked': len(self.recommendation_engine.user_interactions),
                'providers_tracked': len(self.recommendation_engine.provider_performance),
                'models_trained': self.recommendation_engine.models_initialized
            },
            'usage_prediction': {
                'history_size': len(self.usage_predictor.usage_history),
                'model_available': self.usage_predictor.prediction_model is not None
            }
        }


# Global ML optimizer instance
_ml_optimizer = None

def get_ml_optimizer(config: Dict[str, Any] = None) -> MLPoweredOptimizer:
    """Get or create the global ML optimizer instance."""
    global _ml_optimizer
    if _ml_optimizer is None:
        _ml_optimizer = MLPoweredOptimizer(config)
    return _ml_optimizer


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        # Create ML optimizer
        config = {
            'similarity_threshold': 0.85,
            'max_cache_size': 5000
        }

        optimizer = get_ml_optimizer(config)
        await optimizer.start()

        # Simulate some interactions
        user_id = "test_user"
        available_providers = ["openai", "anthropic", "groq"]

        # Process a chat request
        await optimizer.process_chat_request(
            user_id,
            "What is machine learning?",
            available_providers
        )


        # Record interaction result
        await optimizer.record_interaction_result(
            user_id=user_id,
            message="What is machine learning?",
            response="Machine learning is a subset of AI...",
            provider="openai",
            model="gpt-4",
            response_time=1.5,
            satisfaction_score=0.9
        )

        # Get usage predictions
        await optimizer.get_usage_predictions(24)

        # Get metrics
        await optimizer.get_optimization_metrics()


    asyncio.run(main())
