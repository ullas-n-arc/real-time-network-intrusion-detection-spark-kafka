"""
Configuration settings for the Real-Time Network Intrusion Detection System
"""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"

# Kafka Configuration
KAFKA_CONFIG = {
    "bootstrap_servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
    "topic": os.getenv("KAFKA_TOPIC", "network_logs"),
    "alerts_topic": os.getenv("KAFKA_ALERTS_TOPIC", "intrusion_alerts"),
    "group_id": os.getenv("KAFKA_GROUP_ID", "nids_consumer_group"),
    "auto_offset_reset": "latest",
}

# Spark Configuration
SPARK_CONFIG = {
    "app_name": "NIDS-RealTime-Detection",
    "master": os.getenv("SPARK_MASTER", "local[*]"),
    "driver_memory": "4g",
    "executor_memory": "4g",
    "shuffle_partitions": "100",
    "packages": [
        "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0",
    ]
}

# MongoDB Configuration
MONGODB_CONFIG = {
    "host": os.getenv("MONGODB_HOST", "localhost"),
    "port": int(os.getenv("MONGODB_PORT", 27017)),
    "database": os.getenv("MONGODB_DATABASE", "nids_db"),
    "alerts_collection": os.getenv("MONGODB_ALERTS_COLLECTION", "intrusion_alerts"),
    "username": os.getenv("MONGODB_USERNAME", ""),
    "password": os.getenv("MONGODB_PASSWORD", ""),
}

# Model paths
MODEL_PATHS = {
    "rf_binary": str(MODELS_DIR / "rf_binary_classifier"),
    "gbt_binary": str(MODELS_DIR / "gbt_binary_classifier"),
    "rf_multiclass": str(MODELS_DIR / "rf_multiclass_classifier"),
    "rf_multiclass_improved": str(MODELS_DIR / "rf_multiclass_improved"),
}

# Feature configuration - these should match your training pipeline
FEATURE_CONFIG = {
    "numeric_features": [
        "Destination Port", "Flow Duration", "Total Fwd Packets", "Total Backward Packets",
        "Total Length of Fwd Packets", "Total Length of Bwd Packets", "Fwd Packet Length Max",
        "Fwd Packet Length Min", "Fwd Packet Length Mean", "Fwd Packet Length Std",
        "Bwd Packet Length Max", "Bwd Packet Length Min", "Bwd Packet Length Mean",
        "Bwd Packet Length Std", "Flow Bytes/s", "Flow Packets/s", "Flow IAT Mean",
        "Flow IAT Std", "Flow IAT Max", "Flow IAT Min", "Fwd IAT Total", "Fwd IAT Mean",
        "Fwd IAT Std", "Fwd IAT Max", "Fwd IAT Min", "Bwd IAT Total", "Bwd IAT Mean",
        "Bwd IAT Std", "Bwd IAT Max", "Bwd IAT Min", "Fwd PSH Flags", "Bwd PSH Flags",
        "Fwd URG Flags", "Bwd URG Flags", "Fwd Header Length", "Bwd Header Length",
        "Fwd Packets/s", "Bwd Packets/s", "Min Packet Length", "Max Packet Length",
        "Packet Length Mean", "Packet Length Std", "Packet Length Variance", "FIN Flag Count",
        "SYN Flag Count", "RST Flag Count", "PSH Flag Count", "ACK Flag Count",
        "URG Flag Count", "CWE Flag Count", "ECE Flag Count", "Down/Up Ratio",
        "Average Packet Size", "Avg Fwd Segment Size", "Avg Bwd Segment Size",
        "Fwd Header Length.1", "Fwd Avg Bytes/Bulk", "Fwd Avg Packets/Bulk",
        "Fwd Avg Bulk Rate", "Bwd Avg Bytes/Bulk", "Bwd Avg Packets/Bulk",
        "Bwd Avg Bulk Rate", "Subflow Fwd Packets", "Subflow Fwd Bytes",
        "Subflow Bwd Packets", "Subflow Bwd Bytes", "Init_Win_bytes_forward",
        "Init_Win_bytes_backward", "act_data_pkt_fwd", "min_seg_size_forward",
        "Active Mean", "Active Std", "Active Max", "Active Min", "Idle Mean",
        "Idle Std", "Idle Max", "Idle Min"
    ],
    "label_column": "Label",
}

# Attack type mapping (unified labels)
ATTACK_TYPE_MAPPING = {
    0: "Benign",
    1: "DoS",
    2: "DDoS", 
    3: "PortScan",
    4: "BruteForce",
    5: "WebAttack",
    6: "Infiltration",
    7: "Botnet",
    8: "Heartbleed",
}

# Streaming configuration
STREAMING_CONFIG = {
    "checkpoint_dir": str(BASE_DIR / "checkpoints"),
    "trigger_interval": "5 seconds",  # Process micro-batches every 5 seconds
    "watermark_delay": "10 seconds",
}

# Alert thresholds
ALERT_CONFIG = {
    "prediction_threshold": 0.5,  # For binary classification
    "high_severity_types": ["DDoS", "DoS", "Infiltration", "Heartbleed"],
    "medium_severity_types": ["BruteForce", "WebAttack", "Botnet"],
    "low_severity_types": ["PortScan"],
}

# Producer configuration
PRODUCER_CONFIG = {
    "batch_size": 100,  # Number of records to send in each batch
    "delay_between_batches": 1.0,  # Seconds between batches
    "max_records": None,  # None for unlimited
}
