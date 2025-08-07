"""
Serialization Optimization - Task 3.2.3
High-performance serialization/deserialization with MessagePack, lazy loading,
streaming, and benchmarking capabilities
"""

import gzip
import io
import json
import logging
import sqlite3
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

# Optional dependencies with fallbacks
try:
    import msgpack

    MSGPACK_AVAILABLE = True
except ImportError:
    MSGPACK_AVAILABLE = False
    msgpack = None

try:
    import orjson

    ORJSON_AVAILABLE = True
except ImportError:
    ORJSON_AVAILABLE = False
    orjson = None


class SerializationFormat(Enum):
    """Available serialization formats"""

    JSON = "json"
    MSGPACK = "msgpack"
    ORJSON = "orjson"
    GZIP_JSON = "gzip_json"
    GZIP_MSGPACK = "gzip_msgpack"


@dataclass
class SerializationMetrics:
    """Performance metrics for serialization operations"""

    ser_format: SerializationFormat
    total_serializations: int = 0
    total_deserializations: int = 0
    total_bytes_serialized: int = 0
    total_bytes_deserialized: int = 0
    avg_serialization_time: float = 0.0
    avg_deserialization_time: float = 0.0
    avg_serialized_size: float = 0.0
    compression_ratio: float = 1.0
    last_reset: datetime = field(default_factory=datetime.now)


class LazyObject:
    """Lazy loading wrapper for large objects"""

    def __init__(self, loader_func: callable, *args, **kwargs):
        self._loader_func = loader_func
        self._loader_args = args
        self._loader_kwargs = kwargs
        self._value = None
        self._loaded = False
        self._lock = threading.Lock()

    def __getattr__(self, name):
        """Proxy attribute access to loaded object"""
        return getattr(self.value, name)

    @property
    def value(self):
        """Get the loaded value (loads if necessary)"""
        if not self._loaded:
            with self._lock:
                if not self._loaded:
                    self._value = self._loader_func(*self._loader_args, **self._loader_kwargs)
                    self._loaded = True
        return self._value

    @property
    def is_loaded(self) -> bool:
        """Check if value has been loaded"""
        return self._loaded

    def unload(self):
        """Unload the value to free memory"""
        with self._lock:
            self._value = None
            self._loaded = False


class StreamingSerializer:
    """Streaming serializer for large datasets"""

    def __init__(self, ser_format: SerializationFormat = SerializationFormat.JSON):
        self.ser_format = ser_format
        self.logger = logging.getLogger(__name__)

    def serialize_stream(
        self, data_iterator: Iterator, output_stream: io.IOBase, chunk_size: int = 1000
    ) -> int:
        """Stream serialize data iterator to output stream"""
        total_items = 0

        if self.ser_format == SerializationFormat.JSON:
            output_stream.write(b"[")
            first_item = True

            for item in data_iterator:
                if not first_item:
                    output_stream.write(b",")

                serialized = json.dumps(item, default=self._json_serializer).encode("utf-8")
                output_stream.write(serialized)
                total_items += 1
                first_item = False

                if total_items % chunk_size == 0:
                    output_stream.flush()

            output_stream.write(b"]")

        elif self.ser_format == SerializationFormat.MSGPACK and MSGPACK_AVAILABLE:
            packer = msgpack.Packer(default=self._msgpack_serializer)

            for item in data_iterator:
                packed = packer.pack(item)
                output_stream.write(packed)
                total_items += 1

                if total_items % chunk_size == 0:
                    output_stream.flush()

        else:
            raise ValueError(f"Streaming not supported for format: {self.ser_format}")

        output_stream.flush()
        return total_items

    def deserialize_stream(self, input_stream: io.IOBase, chunk_size: int = 1000) -> Iterator:
        """Stream deserialize from input stream"""
        if self.ser_format == SerializationFormat.JSON:
            for line in input_stream:
                if line.strip():
                    try:
                        yield json.loads(line.decode("utf-8") if isinstance(line, bytes) else line)
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"Failed to parse JSON line: {e}")

        elif self.ser_format == SerializationFormat.MSGPACK and MSGPACK_AVAILABLE:
            unpacker = msgpack.Unpacker(input_stream, raw=False)
            yield from unpacker

        else:
            raise ValueError(f"Streaming not supported for format: {self.ser_format}")

    def _json_serializer(self, obj):
        """Custom JSON serializer for special types"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif hasattr(obj, "__dict__"):
            return obj.__dict__
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    def _msgpack_serializer(self, obj):
        """Custom MessagePack serializer for special types"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        return obj


class OptimizedSerializer:
    """High-performance serializer with multiple format support"""

    def __init__(
        self,
        default_format: SerializationFormat = SerializationFormat.JSON,
        enable_compression_threshold: int = 1024,
        enable_metrics: bool = True,
    ):
        self.default_format = default_format
        self.enable_compression_threshold = enable_compression_threshold
        self.enable_metrics = enable_metrics

        self.metrics: dict[SerializationFormat, SerializationMetrics] = {}
        self._metrics_lock = threading.Lock()

        self.logger = logging.getLogger(__name__)
        self._validate_format_support()

    def _validate_format_support(self):
        """Validate that required libraries are available"""
        if self.default_format == SerializationFormat.MSGPACK and not MSGPACK_AVAILABLE:
            self.logger.warning("MessagePack not available, falling back to JSON")
            self.default_format = SerializationFormat.JSON

        if self.default_format == SerializationFormat.ORJSON and not ORJSON_AVAILABLE:
            self.logger.warning("orjson not available, falling back to JSON")
            self.default_format = SerializationFormat.JSON

    def serialize(
        self, data, ser_format: SerializationFormat | None = None, compress: bool | None = None
    ) -> bytes:
        """Serialize data to bytes with optional compression"""
        ser_format = ser_format or self.default_format
        start_time = time.time()

        try:
            if ser_format == SerializationFormat.JSON:
                serialized = json.dumps(data, default=self._json_serializer).encode("utf-8")
            elif ser_format == SerializationFormat.ORJSON and ORJSON_AVAILABLE:
                serialized = orjson.dumps(data, default=self._json_serializer)
            elif ser_format == SerializationFormat.MSGPACK and MSGPACK_AVAILABLE:
                serialized = msgpack.packb(data, default=self._msgpack_serializer)
            elif ser_format in [SerializationFormat.GZIP_JSON, SerializationFormat.GZIP_MSGPACK]:
                base_format = (
                    SerializationFormat.JSON
                    if "JSON" in ser_format.value
                    else SerializationFormat.MSGPACK
                )
                uncompressed = self.serialize(data, base_format, compress=False)
                serialized = gzip.compress(uncompressed)
            else:
                raise ValueError(f"Unsupported serialization format: {ser_format}")

            if compress or (
                compress is None and len(serialized) > self.enable_compression_threshold
            ):
                if ser_format not in [
                    SerializationFormat.GZIP_JSON,
                    SerializationFormat.GZIP_MSGPACK,
                ]:
                    serialized = gzip.compress(serialized)

            if self.enable_metrics:
                self._update_serialization_metrics(
                    ser_format, len(serialized), time.time() - start_time
                )

            return serialized

        except Exception as e:
            self.logger.error(f"Serialization failed for format {ser_format}: {e}")
            raise

    def deserialize(
        self,
        data: bytes,
        ser_format: SerializationFormat | None = None,
        decompress: bool | None = None,
    ):
        """Deserialize bytes to Python object"""
        ser_format = ser_format or self.default_format
        start_time = time.time()

        try:
            if decompress or self._is_gzipped(data):
                data = gzip.decompress(data)

            if ser_format == SerializationFormat.JSON:
                result = json.loads(data.decode("utf-8"))
            elif ser_format == SerializationFormat.ORJSON and ORJSON_AVAILABLE:
                result = orjson.loads(data)
            elif ser_format == SerializationFormat.MSGPACK and MSGPACK_AVAILABLE:
                result = msgpack.unpackb(data, raw=False)
            elif ser_format in [SerializationFormat.GZIP_JSON, SerializationFormat.GZIP_MSGPACK]:
                base_format = (
                    SerializationFormat.JSON
                    if "JSON" in ser_format.value
                    else SerializationFormat.MSGPACK
                )
                result = self.deserialize(data, base_format, decompress=False)
            else:
                raise ValueError(f"Unsupported deserialization format: {ser_format}")

            if self.enable_metrics:
                self._update_deserialization_metrics(
                    ser_format, len(data), time.time() - start_time
                )

            return result

        except Exception as e:
            self.logger.error(f"Deserialization failed for format {ser_format}: {e}")
            raise

    def _is_gzipped(self, data: bytes) -> bool:
        """Check if data is gzipped"""
        return data.startswith(b"\x1f\x8b")

    def _json_serializer(self, obj):
        """Custom JSON serializer for special types"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, LazyObject):
            return obj.value
        elif hasattr(obj, "__dict__"):
            return obj.__dict__
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    def _msgpack_serializer(self, obj):
        """Custom MessagePack serializer for special types"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, LazyObject):
            return obj.value
        return obj

    def _update_serialization_metrics(
        self, ser_format: SerializationFormat, size: int, duration: float
    ):
        """Update serialization metrics"""
        with self._metrics_lock:
            if ser_format not in self.metrics:
                self.metrics[ser_format] = SerializationMetrics(ser_format)

            metrics = self.metrics[ser_format]
            metrics.total_serializations += 1
            metrics.total_bytes_serialized += size

            alpha = 0.1
            metrics.avg_serialization_time = (
                alpha * duration + (1 - alpha) * metrics.avg_serialization_time
            )
            metrics.avg_serialized_size = alpha * size + (1 - alpha) * metrics.avg_serialized_size

    def _update_deserialization_metrics(
        self, ser_format: SerializationFormat, size: int, duration: float
    ):
        """Update deserialization metrics"""
        with self._metrics_lock:
            if ser_format not in self.metrics:
                self.metrics[ser_format] = SerializationMetrics(ser_format)

            metrics = self.metrics[ser_format]
            metrics.total_deserializations += 1
            metrics.total_bytes_deserialized += size

            alpha = 0.1
            metrics.avg_deserialization_time = (
                alpha * duration + (1 - alpha) * metrics.avg_deserialization_time
            )

    def get_metrics(
        self, ser_format: SerializationFormat | None = None
    ) -> dict[SerializationFormat, SerializationMetrics]:
        """Get performance metrics"""
        with self._metrics_lock:
            if ser_format:
                return {ser_format: self.metrics.get(ser_format, SerializationMetrics(ser_format))}
            return self.metrics.copy()

    def benchmark_formats(self, test_data, iterations: int = 100) -> dict[str, dict[str, float]]:
        """Benchmark different serialization formats"""
        results = {}
        available_formats = []

        for ser_format in SerializationFormat:
            if ser_format == SerializationFormat.MSGPACK and not MSGPACK_AVAILABLE:
                continue
            elif ser_format == SerializationFormat.ORJSON and not ORJSON_AVAILABLE:
                continue
            available_formats.append(ser_format)

        self.logger.info(
            f"Benchmarking {len(available_formats)} formats with {iterations} iterations"
        )

        for ser_format in available_formats:
            try:
                serialize_times = []
                deserialize_times = []
                sizes = []

                for _ in range(iterations):
                    start = time.time()
                    serialized = self.serialize(test_data, ser_format)
                    serialize_times.append(time.time() - start)
                    sizes.append(len(serialized))

                    start = time.time()
                    self.deserialize(serialized, ser_format)
                    deserialize_times.append(time.time() - start)

                results[ser_format.value] = {
                    "avg_serialize_time": sum(serialize_times) / len(serialize_times),
                    "avg_deserialize_time": sum(deserialize_times) / len(deserialize_times),
                    "avg_size": sum(sizes) / len(sizes),
                }

            except Exception as e:
                self.logger.error(f"Benchmark failed for {ser_format}: {e}")
                results[ser_format.value] = {"error": str(e)}

        return results


class DatabaseResultOptimizer:
    """Optimize serialization of database query results"""

    def __init__(self, serializer: OptimizedSerializer):
        self.serializer = serializer
        self.logger = logging.getLogger(__name__)

    def optimize_cursor_results(
        self, cursor: sqlite3.Cursor, batch_size: int = 1000, lazy_load: bool = True
    ) -> Iterator[dict[str, any]]:
        """Optimize cursor results with batching and optional lazy loading"""
        columns = [desc[0] for desc in cursor.description] if cursor.description else []

        if lazy_load:
            while True:
                batch = cursor.fetchmany(batch_size)
                if not batch:
                    break

                for row in batch:
                    lazy_row = LazyObject(lambda r=row, c=columns: dict(zip(c, r, strict=True)))
                    yield lazy_row
        else:
            while True:
                batch = cursor.fetchmany(batch_size)
                if not batch:
                    break

                for row in batch:
                    yield dict(zip(columns, row, strict=True))

    def serialize_query_results(
        self,
        query_results: list[dict[str, any]],
        ser_format: SerializationFormat = SerializationFormat.MSGPACK,
    ) -> bytes:
        """Serialize query results with optimal format"""
        return self.serializer.serialize(query_results, ser_format)


# Global instances
_default_serializer: OptimizedSerializer | None = None
_streaming_serializer: StreamingSerializer | None = None


def get_serializer() -> OptimizedSerializer:
    """Get the global optimized serializer"""
    global _default_serializer
    if _default_serializer is None:
        if MSGPACK_AVAILABLE:
            default_format = SerializationFormat.MSGPACK
        elif ORJSON_AVAILABLE:
            default_format = SerializationFormat.ORJSON
        else:
            default_format = SerializationFormat.JSON

        _default_serializer = OptimizedSerializer(default_format=default_format)

    return _default_serializer


def get_streaming_serializer() -> StreamingSerializer:
    """Get the global streaming serializer"""
    global _streaming_serializer
    if _streaming_serializer is None:
        ser_format = SerializationFormat.MSGPACK if MSGPACK_AVAILABLE else SerializationFormat.JSON
        _streaming_serializer = StreamingSerializer(ser_format=ser_format)

    return _streaming_serializer


# Convenience functions
def fast_serialize(data, compress: bool = False) -> bytes:
    """Fast serialization using optimal format"""
    return get_serializer().serialize(data, compress=compress)


def fast_deserialize(data: bytes):
    """Fast deserialization using optimal format"""
    return get_serializer().deserialize(data)


def lazy_load(loader_func: callable, *args, **kwargs) -> LazyObject:
    """Create a lazy-loaded object"""
    return LazyObject(loader_func, *args, **kwargs)


# Flask integration helpers
def init_serialization_optimization(app):
    """Initialize serialization optimization for Flask app"""
    serializer = get_serializer()
    streaming_serializer = get_streaming_serializer()

    app.serializer = serializer
    app.streaming_serializer = streaming_serializer
    app.db_optimizer = DatabaseResultOptimizer(serializer)
    app.fast_serialize = fast_serialize
    app.fast_deserialize = fast_deserialize
    app.lazy_load = lazy_load

    return serializer
