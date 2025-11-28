"""
Spark Structured Streaming Job for Real-Time Network Intrusion Detection

This module:
1. Reads JSON logs from Kafka topic 'network_logs'
2. Applies feature preprocessing transformations
3. Loads trained ML models
4. Makes real-time predictions
5. Stores alerts in MongoDB

Usage:
    spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 spark_streaming.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import json
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, 
    IntegerType, TimestampType, ArrayType
)
from pyspark.ml import PipelineModel
from pyspark.ml.classification import (
    RandomForestClassificationModel,
    GBTClassificationModel
)
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.linalg import Vectors, VectorUDT

from config import (
    KAFKA_CONFIG, SPARK_CONFIG, STREAMING_CONFIG,
    MODEL_PATHS, FEATURE_CONFIG, ATTACK_TYPE_MAPPING,
    ALERT_CONFIG, MONGODB_CONFIG
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SparkStreamingProcessor:
    """
    Real-time network intrusion detection using Spark Structured Streaming.
    """
    
    def __init__(self):
        """Initialize the streaming processor."""
        self.spark = None
        self.binary_model = None
        self.multiclass_model = None
        self.schema = None
        
    def create_spark_session(self) -> SparkSession:
        """Create and configure Spark session for streaming."""
        logger.info("Creating Spark session...")
        
        # Build packages string
        packages = ",".join(SPARK_CONFIG.get("packages", []))
        
        builder = SparkSession.builder \
            .appName(SPARK_CONFIG["app_name"]) \
            .config("spark.driver.memory", SPARK_CONFIG["driver_memory"]) \
            .config("spark.executor.memory", SPARK_CONFIG["executor_memory"]) \
            .config("spark.sql.shuffle.partitions", SPARK_CONFIG["shuffle_partitions"]) \
            .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
            .config("spark.streaming.stopGracefullyOnShutdown", "true") \
            .config("spark.sql.streaming.checkpointLocation", STREAMING_CONFIG["checkpoint_dir"])
        
        if packages:
            builder = builder.config("spark.jars.packages", packages)
        
        if SPARK_CONFIG.get("master"):
            builder = builder.master(SPARK_CONFIG["master"])
        
        self.spark = builder.getOrCreate()
        self.spark.sparkContext.setLogLevel("WARN")
        
        logger.info(f"✅ Spark session created: {self.spark.version}")
        return self.spark
    
    def define_schema(self) -> StructType:
        """Define the schema for incoming network traffic data."""
        # Build schema from feature configuration
        fields = []
        
        for feature in FEATURE_CONFIG["numeric_features"]:
            fields.append(StructField(feature.strip(), DoubleType(), True))
        
        # Add metadata fields
        fields.extend([
            StructField("Label", StringType(), True),
            StructField("Source IP", StringType(), True),
            StructField("Destination IP", StringType(), True),
            StructField("timestamp", StringType(), True),
            StructField("producer_id", IntegerType(), True),
        ])
        
        self.schema = StructType(fields)
        return self.schema
    
    def load_models(self):
        """Load pre-trained ML models."""
        logger.info("Loading ML models...")
        
        try:
            # Try to load Random Forest binary classifier
            if os.path.exists(MODEL_PATHS["rf_binary"]):
                self.binary_model = RandomForestClassificationModel.load(MODEL_PATHS["rf_binary"])
                logger.info(f"✅ Loaded binary model: {MODEL_PATHS['rf_binary']}")
            else:
                logger.warning(f"⚠️ Binary model not found at {MODEL_PATHS['rf_binary']}")
            
            # Try to load multiclass classifier (improved version first)
            if os.path.exists(MODEL_PATHS.get("rf_multiclass_improved", "")):
                self.multiclass_model = RandomForestClassificationModel.load(
                    MODEL_PATHS["rf_multiclass_improved"]
                )
                logger.info(f"✅ Loaded improved multiclass model")
            elif os.path.exists(MODEL_PATHS["rf_multiclass"]):
                self.multiclass_model = RandomForestClassificationModel.load(
                    MODEL_PATHS["rf_multiclass"]
                )
                logger.info(f"✅ Loaded multiclass model: {MODEL_PATHS['rf_multiclass']}")
            else:
                logger.warning(f"⚠️ Multiclass model not found")
                
        except Exception as e:
            logger.error(f"❌ Error loading models: {e}")
            raise
    
    def read_from_kafka(self) -> DataFrame:
        """Read streaming data from Kafka topic."""
        logger.info(f"Connecting to Kafka topic: {KAFKA_CONFIG['topic']}")
        
        kafka_df = self.spark.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", KAFKA_CONFIG["bootstrap_servers"]) \
            .option("subscribe", KAFKA_CONFIG["topic"]) \
            .option("startingOffsets", "latest") \
            .option("failOnDataLoss", "false") \
            .load()
        
        logger.info("✅ Connected to Kafka stream")
        return kafka_df
    
    def parse_json(self, kafka_df: DataFrame) -> DataFrame:
        """Parse JSON messages from Kafka."""
        # Convert value from bytes to string and parse JSON
        parsed_df = kafka_df.select(
            F.from_json(
                F.col("value").cast("string"),
                self.schema
            ).alias("data"),
            F.col("timestamp").alias("kafka_timestamp")
        ).select("data.*", "kafka_timestamp")
        
        return parsed_df
    
    def preprocess_features(self, df: DataFrame) -> DataFrame:
        """
        Apply feature preprocessing to match training pipeline.
        """
        # Clean column names (remove spaces, special characters)
        for col_name in df.columns:
            clean_name = col_name.strip().replace(" ", "_").replace("/", "_per_")
            if clean_name != col_name:
                df = df.withColumnRenamed(col_name, clean_name)
        
        # Handle missing/infinite values
        numeric_cols = [
            c.strip().replace(" ", "_").replace("/", "_per_") 
            for c in FEATURE_CONFIG["numeric_features"]
        ]
        
        for col in numeric_cols:
            if col in df.columns:
                df = df.withColumn(
                    col,
                    F.when(F.col(col).isNull(), 0.0)
                    .when(F.col(col) == float('inf'), 0.0)
                    .when(F.col(col) == float('-inf'), 0.0)
                    .otherwise(F.col(col))
                )
        
        # Create feature vector
        available_features = [c for c in numeric_cols if c in df.columns]
        
        if available_features:
            assembler = VectorAssembler(
                inputCols=available_features,
                outputCol="features",
                handleInvalid="skip"
            )
            df = assembler.transform(df)
        
        return df
    
    def apply_model(self, df: DataFrame) -> DataFrame:
        """Apply ML models for prediction."""
        result_df = df
        
        # Apply binary classification
        if self.binary_model:
            try:
                result_df = self.binary_model.transform(result_df)
                result_df = result_df.withColumnRenamed("prediction", "binary_prediction")
                result_df = result_df.withColumnRenamed("probability", "binary_probability")
            except Exception as e:
                logger.warning(f"Binary model prediction failed: {e}")
                result_df = result_df.withColumn("binary_prediction", F.lit(-1.0))
        else:
            result_df = result_df.withColumn("binary_prediction", F.lit(-1.0))
        
        # Apply multiclass classification
        if self.multiclass_model:
            try:
                # Need to rename columns to avoid conflict
                result_df = self.multiclass_model.transform(result_df)
                result_df = result_df.withColumnRenamed("prediction", "multiclass_prediction")
            except Exception as e:
                logger.warning(f"Multiclass model prediction failed: {e}")
                result_df = result_df.withColumn("multiclass_prediction", F.lit(-1.0))
        else:
            result_df = result_df.withColumn("multiclass_prediction", F.lit(-1.0))
        
        return result_df
    
    def enrich_predictions(self, df: DataFrame) -> DataFrame:
        """Add attack type labels and severity to predictions."""
        # Map numeric predictions to attack type names
        attack_mapping = F.create_map([
            F.lit(k) for pair in ATTACK_TYPE_MAPPING.items() 
            for k in [float(pair[0]), pair[1]]
        ])
        
        df = df.withColumn(
            "attack_type",
            F.coalesce(
                attack_mapping[F.col("multiclass_prediction")],
                F.lit("Unknown")
            )
        )
        
        # Add is_attack flag
        df = df.withColumn(
            "is_attack",
            F.when(F.col("binary_prediction") == 1.0, True).otherwise(False)
        )
        
        # Add severity level
        high_severity = ALERT_CONFIG["high_severity_types"]
        medium_severity = ALERT_CONFIG["medium_severity_types"]
        
        df = df.withColumn(
            "severity",
            F.when(F.col("attack_type").isin(high_severity), "HIGH")
            .when(F.col("attack_type").isin(medium_severity), "MEDIUM")
            .when(F.col("is_attack"), "LOW")
            .otherwise("NONE")
        )
        
        # Add processing timestamp
        df = df.withColumn("processed_at", F.current_timestamp())
        
        return df
    
    def write_to_console(self, df: DataFrame, output_mode: str = "append"):
        """Write results to console (for debugging)."""
        # Select key columns for display
        display_cols = [
            "kafka_timestamp", "is_attack", "attack_type", 
            "severity", "binary_prediction", "multiclass_prediction"
        ]
        
        available_cols = [c for c in display_cols if c in df.columns]
        
        query = df.select(available_cols) \
            .writeStream \
            .outputMode(output_mode) \
            .format("console") \
            .option("truncate", "false") \
            .trigger(processingTime=STREAMING_CONFIG["trigger_interval"]) \
            .start()
        
        return query
    
    def write_alerts_to_mongodb(self, df: DataFrame):
        """Write alert records to MongoDB using foreachBatch."""
        
        def write_batch_to_mongo(batch_df, batch_id):
            """Write a micro-batch to MongoDB."""
            if batch_df.count() == 0:
                return
            
            # Filter only attack records
            alerts_df = batch_df.filter(F.col("is_attack") == True)
            
            if alerts_df.count() == 0:
                return
            
            # Convert to pandas and insert to MongoDB
            try:
                from pymongo import MongoClient
                
                client = MongoClient(
                    host=MONGODB_CONFIG["host"],
                    port=MONGODB_CONFIG["port"]
                )
                db = client[MONGODB_CONFIG["database"]]
                collection = db[MONGODB_CONFIG["alerts_collection"]]
                
                # Convert to records
                records = alerts_df.toPandas().to_dict('records')
                
                # Add batch metadata
                for record in records:
                    record['batch_id'] = batch_id
                    record['inserted_at'] = datetime.now()
                
                collection.insert_many(records)
                logger.info(f"Batch {batch_id}: Inserted {len(records)} alerts to MongoDB")
                
                client.close()
                
            except Exception as e:
                logger.error(f"Failed to write to MongoDB: {e}")
        
        query = df.writeStream \
            .foreachBatch(write_batch_to_mongo) \
            .outputMode("append") \
            .option("checkpointLocation", f"{STREAMING_CONFIG['checkpoint_dir']}/mongodb") \
            .trigger(processingTime=STREAMING_CONFIG["trigger_interval"]) \
            .start()
        
        return query
    
    def write_to_kafka_alerts(self, df: DataFrame):
        """Write alerts to a separate Kafka topic."""
        # Filter attacks and prepare for Kafka
        alerts_df = df.filter(F.col("is_attack") == True)
        
        # Convert to JSON for Kafka
        json_df = alerts_df.select(
            F.to_json(
                F.struct(
                    "kafka_timestamp", "is_attack", "attack_type",
                    "severity", "processed_at"
                )
            ).alias("value")
        )
        
        query = json_df.writeStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", KAFKA_CONFIG["bootstrap_servers"]) \
            .option("topic", KAFKA_CONFIG["alerts_topic"]) \
            .option("checkpointLocation", f"{STREAMING_CONFIG['checkpoint_dir']}/kafka_alerts") \
            .trigger(processingTime=STREAMING_CONFIG["trigger_interval"]) \
            .start()
        
        return query
    
    def run(self, output_mode: str = "console"):
        """
        Main method to run the streaming pipeline.
        
        Args:
            output_mode: Where to write results ('console', 'mongodb', 'kafka', 'all')
        """
        logger.info("="*60)
        logger.info("Starting Real-Time Network Intrusion Detection")
        logger.info("="*60)
        
        # Initialize
        self.create_spark_session()
        self.define_schema()
        self.load_models()
        
        # Build streaming pipeline
        kafka_df = self.read_from_kafka()
        parsed_df = self.parse_json(kafka_df)
        processed_df = self.preprocess_features(parsed_df)
        predicted_df = self.apply_model(processed_df)
        enriched_df = self.enrich_predictions(predicted_df)
        
        # Start output streams
        queries = []
        
        if output_mode in ["console", "all"]:
            console_query = self.write_to_console(enriched_df)
            queries.append(console_query)
            logger.info("✅ Console output started")
        
        if output_mode in ["mongodb", "all"]:
            try:
                mongo_query = self.write_alerts_to_mongodb(enriched_df)
                queries.append(mongo_query)
                logger.info("✅ MongoDB output started")
            except Exception as e:
                logger.warning(f"MongoDB output not available: {e}")
        
        if output_mode in ["kafka", "all"]:
            try:
                kafka_query = self.write_to_kafka_alerts(enriched_df)
                queries.append(kafka_query)
                logger.info("✅ Kafka alerts output started")
            except Exception as e:
                logger.warning(f"Kafka alerts output not available: {e}")
        
        logger.info("="*60)
        logger.info("🚀 Streaming pipeline running...")
        logger.info("Press Ctrl+C to stop")
        logger.info("="*60)
        
        # Wait for termination
        try:
            for query in queries:
                query.awaitTermination()
        except KeyboardInterrupt:
            logger.info("\n⏹️ Stopping streaming pipeline...")
            for query in queries:
                query.stop()
        finally:
            self.spark.stop()
            logger.info("✅ Spark session stopped")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Spark Streaming for Network Intrusion Detection'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='console',
        choices=['console', 'mongodb', 'kafka', 'all'],
        help='Output destination for predictions'
    )
    
    args = parser.parse_args()
    
    processor = SparkStreamingProcessor()
    processor.run(output_mode=args.output)


if __name__ == "__main__":
    main()
