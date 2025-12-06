"""
Streaming module for Real-Time Network Intrusion Detection
"""

from .kafka_producer import NetworkTrafficProducer
from .spark_streaming import SparkStreamingProcessor
from .alert_storage import (
    AlertStorage,
    start_new_session,
    get_current_session_id,
    set_current_session_id,
    clear_session,
    generate_session_id
)

__all__ = [
    "NetworkTrafficProducer",
    "SparkStreamingProcessor", 
    "AlertStorage",
    "start_new_session",
    "get_current_session_id",
    "set_current_session_id",
    "clear_session",
    "generate_session_id",
]
