"""
Kafka Producer for Network Intrusion Detection System

This module reads network traffic data from CIC-IDS datasets and sends them
to a Kafka topic in real-time simulation mode.

Usage:
    python kafka_producer.py --data-source cicids2017 --rate 100
"""

import json
import time
import argparse
import logging
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Iterator, Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from kafka import KafkaProducer
    from kafka.errors import KafkaError
except ImportError:
    print("ERROR: kafka-python not installed. Run: pip install kafka-python")
    sys.exit(1)

import pandas as pd
import numpy as np

from config import KAFKA_CONFIG, PRODUCER_CONFIG, DATA_DIR, FEATURE_CONFIG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NetworkTrafficProducer:
    """
    Kafka producer that simulates real-time network traffic by reading
    from CIC-IDS datasets and sending records to Kafka.
    """
    
    def __init__(
        self,
        bootstrap_servers: str = KAFKA_CONFIG["bootstrap_servers"],
        topic: str = KAFKA_CONFIG["topic"],
        batch_size: int = PRODUCER_CONFIG["batch_size"],
        delay: float = PRODUCER_CONFIG["delay_between_batches"]
    ):
        """
        Initialize the Kafka producer.
        
        Args:
            bootstrap_servers: Kafka broker addresses
            topic: Kafka topic to produce to
            batch_size: Number of records per batch
            delay: Delay between batches in seconds
        """
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.batch_size = batch_size
        self.delay = delay
        self.producer = None
        self.records_sent = 0
        self.errors = 0
        
    def connect(self) -> bool:
        """Establish connection to Kafka broker."""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',  # Wait for all replicas
                retries=3,
                retry_backoff_ms=1000,
                max_in_flight_requests_per_connection=1,
            )
            logger.info(f"✅ Connected to Kafka at {self.bootstrap_servers}")
            return True
        except KafkaError as e:
            logger.error(f"❌ Failed to connect to Kafka: {e}")
            return False
    
    def close(self):
        """Close the producer connection."""
        if self.producer:
            self.producer.flush()
            self.producer.close()
            logger.info("Producer connection closed")
    
    def send_record(self, record: Dict[str, Any], key: Optional[str] = None) -> bool:
        """
        Send a single record to Kafka.
        
        Args:
            record: Dictionary containing network traffic features
            key: Optional partition key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add metadata
            record['timestamp'] = datetime.now().isoformat()
            record['producer_id'] = os.getpid()
            
            future = self.producer.send(
                self.topic,
                value=record,
                key=key
            )
            # Block for synchronous send (optional, can be async)
            future.get(timeout=10)
            self.records_sent += 1
            return True
        except KafkaError as e:
            logger.error(f"Failed to send record: {e}")
            self.errors += 1
            return False
    
    def send_batch(self, records: list) -> int:
        """
        Send a batch of records to Kafka.
        
        Args:
            records: List of dictionaries containing network traffic features
            
        Returns:
            Number of successfully sent records
        """
        sent = 0
        for record in records:
            # Use source IP as partition key for ordering
            key = record.get('Source IP', str(sent))
            if self.send_record(record, key):
                sent += 1
        self.producer.flush()
        return sent
    
    def load_dataset(self, data_source: str) -> pd.DataFrame:
        """
        Load a CIC-IDS dataset or all preprocessed CSVs.
        
        Args:
            data_source: Name of the dataset ('cicids2017', 'cicids2018', 'unsw', 'preprocessed')
        Returns:
            DataFrame containing the dataset
        """
        dataset_paths = {
            'cicids2017': DATA_DIR / 'CSE-CIC-IDS2017',
            'cicids2018': DATA_DIR / 'CSE-CIC-IDS2018',
            'unsw': DATA_DIR / 'UNSW-NB15',
            'preprocessed': DATA_DIR / 'preprocessed',
        }
        if data_source not in dataset_paths:
            raise ValueError(f"Unknown data source: {data_source}")
        data_path = dataset_paths[data_source]
        if not data_path.exists():
            raise FileNotFoundError(f"Data directory not found: {data_path}")
        # Load CSV files
        csv_files = sorted(data_path.glob("*.csv"))
        if not csv_files:
            raise FileNotFoundError(f"No CSV files found in {data_path}")
        logger.info(f"Found {len(csv_files)} CSV files in {data_path}")
        # Concatenate all CSV files in order
        df_list = []
        for csv_file in csv_files:
            df_part = pd.read_csv(csv_file, low_memory=False)
            logger.info(f"✅ Loaded {len(df_part):,} records from {csv_file.name}")
            df_list.append(df_part)
        df = pd.concat(df_list, ignore_index=True)
        logger.info(f"✅ Total loaded records from all files: {len(df):,}")
        return df
    
    def preprocess_record(self, row: pd.Series) -> Dict[str, Any]:
        """
        Convert a DataFrame row to a dictionary for Kafka.
        Handles NaN values and converts numpy types to Python types.
        
        Args:
            row: Pandas Series representing a single record
            
        Returns:
            Dictionary with cleaned values
        """
        record = {}
        for key, value in row.items():
            # Clean column names (remove leading/trailing spaces)
            clean_key = str(key).strip()
            
            # Handle different data types
            if pd.isna(value):
                record[clean_key] = 0.0
            elif isinstance(value, (np.integer, np.floating)):
                record[clean_key] = float(value)
            elif isinstance(value, np.bool_):
                record[clean_key] = bool(value)
            else:
                record[clean_key] = str(value)
        
        return record
    
    def stream_dataset(
        self,
        df: pd.DataFrame,
        max_records: Optional[int] = None,
        shuffle: bool = True
    ) -> Iterator[Dict[str, Any]]:
        """
        Generator that yields records from the dataset.
        
        Args:
            df: DataFrame to stream
            max_records: Maximum number of records to stream (None for all)
            shuffle: Whether to shuffle the data
            
        Yields:
            Dictionary records
        """
        if shuffle:
            df = df.sample(frac=1, random_state=42).reset_index(drop=True)
        
        if max_records:
            df = df.head(max_records)
        
        for idx, row in df.iterrows():
            yield self.preprocess_record(row)
    
    def run(
        self,
        data_source: str = 'cicids2017',
        max_records: Optional[int] = None,
        shuffle: bool = True
    ):
        """
        Main method to run the producer.
        
        Args:
            data_source: Dataset to use
            max_records: Maximum records to send
            shuffle: Whether to shuffle data
        """
        logger.info("="*60)
        logger.info("Starting Network Traffic Kafka Producer")
        logger.info("="*60)
        
        # Connect to Kafka
        if not self.connect():
            logger.error("Cannot start producer without Kafka connection")
            return
        
        # Load dataset
        try:
            df = self.load_dataset(data_source)
        except Exception as e:
            logger.error(f"Failed to load dataset: {e}")
            self.close()
            return
        
        logger.info(f"📊 Dataset shape: {df.shape}")
        logger.info(f"📊 Columns: {list(df.columns[:10])}...")
        logger.info(f"🚀 Starting to stream data to topic '{self.topic}'")
        logger.info(f"⏱️  Batch size: {self.batch_size}, Delay: {self.delay}s")
        
        start_time = time.time()
        batch = []
        
        try:
            for record in self.stream_dataset(df, max_records, shuffle):
                batch.append(record)
                
                if len(batch) >= self.batch_size:
                    sent = self.send_batch(batch)
                    elapsed = time.time() - start_time
                    rate = self.records_sent / elapsed if elapsed > 0 else 0
                    
                    logger.info(
                        f"📤 Sent batch: {sent}/{len(batch)} records | "
                        f"Total: {self.records_sent:,} | "
                        f"Rate: {rate:.1f} rec/s | "
                        f"Errors: {self.errors}"
                    )
                    
                    batch = []
                    time.sleep(self.delay)
            
            # Send remaining records
            if batch:
                self.send_batch(batch)
        
        except KeyboardInterrupt:
            logger.info("\n⏹️  Producer stopped by user")
        
        finally:
            elapsed = time.time() - start_time
            logger.info("="*60)
            logger.info("Producer Summary")
            logger.info("="*60)
            logger.info(f"✅ Total records sent: {self.records_sent:,}")
            logger.info(f"❌ Total errors: {self.errors}")
            logger.info(f"⏱️  Total time: {elapsed:.2f} seconds")
            logger.info(f"📈 Average rate: {self.records_sent/elapsed:.1f} records/second")
            
            self.close()


def main():
    parser = argparse.ArgumentParser(
        description='Kafka Producer for Network Intrusion Detection'
    )
    parser.add_argument(
        '--data-source',
        type=str,
        default='cicids2017',
        choices=['cicids2017', 'cicids2018', 'unsw', 'preprocessed'],
        help='Dataset to stream'
    )
    parser.add_argument(
        '--bootstrap-servers',
        type=str,
        default=KAFKA_CONFIG["bootstrap_servers"],
        help='Kafka bootstrap servers'
    )
    parser.add_argument(
        '--topic',
        type=str,
        default=KAFKA_CONFIG["topic"],
        help='Kafka topic name'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=PRODUCER_CONFIG["batch_size"],
        help='Records per batch'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=PRODUCER_CONFIG["delay_between_batches"],
        help='Delay between batches (seconds)'
    )
    parser.add_argument(
        '--max-records',
        type=int,
        default=None,
        help='Maximum records to send (default: unlimited)'
    )
    parser.add_argument(
        '--no-shuffle',
        action='store_true',
        help='Do not shuffle the data'
    )
    
    args = parser.parse_args()
    
    producer = NetworkTrafficProducer(
        bootstrap_servers=args.bootstrap_servers,
        topic=args.topic,
        batch_size=args.batch_size,
        delay=args.delay
    )
    
    producer.run(
        data_source=args.data_source,
        max_records=args.max_records,
        shuffle=not args.no_shuffle
    )


if __name__ == "__main__":
    main()
