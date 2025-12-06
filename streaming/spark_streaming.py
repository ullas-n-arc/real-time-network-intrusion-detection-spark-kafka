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
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType,
    IntegerType
)
from pyspark.ml.classification import (
    RandomForestClassificationModel,
    GBTClassificationModel
)
from pyspark.ml.feature import VectorAssembler

from config import (
    KAFKA_CONFIG, SPARK_CONFIG, STREAMING_CONFIG,
    MODEL_PATHS, FEATURE_CONFIG, UNSW_FEATURE_CONFIG, ATTACK_TYPE_MAPPING,
    ALERT_CONFIG, MONGODB_CONFIG
)

from streaming.alert_storage import (
    start_new_session, get_current_session_id, clear_session
)

# Try to import UNSW attack mapping
try:
    from config import UNSW_ATTACK_TYPE_MAPPING
except ImportError:
    UNSW_ATTACK_TYPE_MAPPING = ATTACK_TYPE_MAPPING

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SparkStreamingProcessor:
    """
    Real-time network intrusion detection using Spark Structured Streaming.
    
    For UNSW dataset: Uses two-stage detection
        1. GBT binary model to detect attack vs normal (87% accuracy)
        2. Only if attack detected, apply RF multiclass for attack type (67% accuracy)
    
    For CIC-IDS dataset: Uses RF models for both stages
    """

    def __init__(self, data_source="cicids2017", session_id: str = None):
        """
        Initialize the streaming processor.
        
        Args:
            data_source: Dataset to use for model selection
            session_id: Optional session ID. If not provided, a new session will be created.
        """
        self.spark = None
        self.binary_model = None
        self.multiclass_model = None
        self.gbt_binary_model = None  # GBT for UNSW binary detection
        self.schema = None
        self.scaler_model = None
        self.data_source = data_source
        
        # Session management
        if session_id:
            from streaming.alert_storage import set_current_session_id
            set_current_session_id(session_id)
            self.session_id = session_id
        else:
            self.session_id = start_new_session()
        
        logger.info(f"📍 Streaming session ID: {self.session_id}")

    def create_spark_session(self) -> SparkSession:
        """Create and configure Spark session for streaming with optimized settings."""
        logger.info("Creating Spark session...")

        # Build packages string
        packages = ",".join(SPARK_CONFIG.get("packages", []))

        builder = (
            SparkSession.builder
            .appName(SPARK_CONFIG["app_name"])
            .config("spark.driver.memory", "2g")
            .config("spark.executor.memory", "2g")
            # Reduce shuffle partitions for local mode - key optimization
            .config("spark.sql.shuffle.partitions", "2")
            .config("spark.default.parallelism", "2")
            # Use Kryo serialization for faster serialization
            .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
            .config("spark.kryoserializer.buffer.max", "512m")
            # Streaming optimizations
            .config("spark.streaming.stopGracefullyOnShutdown", "true")
            .config("spark.sql.streaming.checkpointLocation", STREAMING_CONFIG["checkpoint_dir"])
            # Reduce overhead
            .config("spark.driver.maxResultSize", "512m")
            # Enable adaptive query execution for better performance
            .config("spark.sql.adaptive.enabled", "true")
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
            .config("spark.sql.adaptive.skewJoin.enabled", "true")
            # Reduce network timeouts for faster failure detection
            .config("spark.network.timeout", "120s")
            .config("spark.executor.heartbeatInterval", "20s")
            # Optimize Kafka reading
            .config("spark.streaming.kafka.maxRatePerPartition", "1000")
            # Reduce logging overhead
            .config("spark.sql.streaming.metricsEnabled", "false")
            # Memory management
            .config("spark.memory.fraction", "0.8")
            .config("spark.memory.storageFraction", "0.3")
        )

        if packages:
            builder = builder.config("spark.jars.packages", packages)

        if SPARK_CONFIG.get("master"):
            builder = builder.master(SPARK_CONFIG["master"])

        self.spark = builder.getOrCreate()
        self.spark.sparkContext.setLogLevel("WARN")

        logger.info(f"✅ Spark session created: {self.spark.version}")
        return self.spark

    def define_schema(self) -> StructType:
        """
        Define the schema for incoming network traffic data.
        
        Note: Labels are NOT included - this is realistic for production
        where we're detecting unknown attacks in real-time.
        """
        fields = []

        # Choose features based on data source
        if self.data_source == "unsw":
            feature_list = UNSW_FEATURE_CONFIG["numeric_features"]
            # Add id field first (optional, for tracking)
            fields.append(StructField("id", DoubleType(), True))
        else:
            feature_list = FEATURE_CONFIG["numeric_features"]

        # Numeric feature fields (the actual network traffic features)
        for feature in feature_list:
            fields.append(StructField(feature.strip(), DoubleType(), True))

        # Metadata fields based on data source (NO LABELS - realistic scenario)
        if self.data_source == "unsw":
            fields.extend([
                # Categorical features (for context, not prediction)
                StructField("proto", StringType(), True),
                StructField("service", StringType(), True),
                StructField("state", StringType(), True),
                # Metadata
                StructField("timestamp", StringType(), True),
                StructField("producer_id", IntegerType(), True),
            ])
        else:
            fields.extend([
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
            if self.data_source == "unsw":
                # UNSW: Load GBT binary model (87% accuracy, 94% AUC-ROC)
                gbt_binary_path = MODEL_PATHS.get("unsw_gbt_binary", "")
                if os.path.exists(gbt_binary_path):
                    self.gbt_binary_model = GBTClassificationModel.load(gbt_binary_path)
                    logger.info(f"✅ Loaded UNSW GBT binary classifier: {gbt_binary_path}")
                else:
                    logger.warning(f"⚠️ UNSW GBT binary classifier not found at {gbt_binary_path}")
                    # Fallback to RF binary
                    rf_binary_path = MODEL_PATHS.get("unsw_rf_binary", "")
                    if os.path.exists(rf_binary_path):
                        self.binary_model = RandomForestClassificationModel.load(rf_binary_path)
                        logger.info(f"✅ Loaded UNSW RF binary classifier as fallback: {rf_binary_path}")

                # Load UNSW multiclass model (for attack type classification)
                multiclass_path = MODEL_PATHS.get("unsw_multiclass", "")
                if os.path.exists(multiclass_path):
                    self.multiclass_model = RandomForestClassificationModel.load(multiclass_path)
                    logger.info(f"✅ Loaded UNSW multiclass classifier: {multiclass_path}")
                else:
                    logger.warning(f"⚠️ UNSW multiclass classifier not found at {multiclass_path}")
                    
            else:
                # CIC-IDS: Load RF binary classifier
                binary_path = MODEL_PATHS["rf_binary"]
                if os.path.exists(binary_path):
                    self.binary_model = RandomForestClassificationModel.load(binary_path)
                    logger.info(f"✅ Loaded binary classifier: {binary_path}")
                else:
                    logger.warning(f"⚠️ Binary classifier not found at {binary_path}")

                # CIC-IDS multiclass - prefer improved model
                improved_path = MODEL_PATHS.get("rf_multiclass_improved", "")
                if os.path.exists(improved_path):
                    self.multiclass_model = RandomForestClassificationModel.load(improved_path)
                    logger.info(f"✅ Loaded improved multiclass classifier: {improved_path}")
                elif os.path.exists(MODEL_PATHS["rf_multiclass"]):
                    self.multiclass_model = RandomForestClassificationModel.load(MODEL_PATHS["rf_multiclass"])
                    logger.info(f"✅ Loaded multiclass classifier: {MODEL_PATHS['rf_multiclass']}")
                else:
                    logger.warning("⚠️ Multiclass classifier not found")

            # Scaler model is not needed - models were trained without scaling
            self.scaler_model = None
            logger.info("ℹ️ Scaler model not required for this configuration")

        except Exception as e:
            logger.error(f"❌ Error loading models: {e}")
            raise

    def read_from_kafka(self) -> DataFrame:
        """Read streaming data from Kafka topic with optimized settings."""
        logger.info(f"Connecting to Kafka topic: {KAFKA_CONFIG['topic']}")

        kafka_df = (
            self.spark.readStream
            .format("kafka")
            .option("kafka.bootstrap.servers", KAFKA_CONFIG["bootstrap_servers"])
            .option("subscribe", KAFKA_CONFIG["topic"])
            .option("startingOffsets", "latest")  # Start from latest for faster startup
            .option("failOnDataLoss", "false")
            .option("maxOffsetsPerTrigger", "500")  # Limit records per batch for faster processing
            .option("kafka.fetch.min.bytes", "1")  # Don't wait for large batches
            .option("kafka.fetch.max.wait.ms", "100")  # Reduce wait time
            .load()
        )

        logger.info("✅ Connected to Kafka stream")
        return kafka_df

    def parse_json(self, kafka_df: DataFrame) -> DataFrame:
        """Parse JSON messages from Kafka."""
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
        Optimized for streaming performance.
        """
        # 1) Clean column names (spaces, slashes, dots) - do all renames at once
        rename_map = {}
        for col_name in df.columns:
            clean_name = (
                col_name.strip()
                .replace(" ", "_")
                .replace("/", "_per_")
                .replace(".", "_dot_")
            )
            if clean_name != col_name:
                rename_map[col_name] = clean_name
        
        # Apply all renames at once
        for old_name, new_name in rename_map.items():
            df = df.withColumnRenamed(old_name, new_name)

        # 2) Choose features based on data source
        if self.data_source == "unsw":
            numeric_cols = UNSW_FEATURE_CONFIG["numeric_features"]
        else:
            numeric_cols = [
                c.strip()
                 .replace(" ", "_")
                 .replace("/", "_per_")
                 .replace(".", "_dot_")
                for c in FEATURE_CONFIG["numeric_features"]
            ]

        # 3) Handle missing / infinite values - use coalesce and nanvl for efficiency
        available_features = [c for c in numeric_cols if c in df.columns]
        
        # Build a single select expression for all columns to avoid multiple withColumn calls
        select_exprs = []
        for col_name in df.columns:
            if col_name in available_features:
                # Replace null/inf with 0.0 efficiently
                select_exprs.append(
                    F.coalesce(
                        F.nanvl(F.col(col_name), F.lit(0.0)),
                        F.lit(0.0)
                    ).alias(col_name)
                )
            else:
                select_exprs.append(F.col(col_name))
        
        df = df.select(select_exprs)

        # 4) Assemble features vector

        if available_features:
            assembler = VectorAssembler(
                inputCols=available_features,
                outputCol="features",
                handleInvalid="keep"  # "keep" is faster than "skip"
            )
            df = assembler.transform(df)

        return df

    def apply_model(self, df: DataFrame) -> DataFrame:
        """
        Apply ML models for prediction.
        
        For UNSW: Two-stage detection
            Stage 1: GBT binary model (attack vs normal)
            Stage 2: Only if attack, apply RF multiclass for attack type
        
        For CIC-IDS: Apply both binary and multiclass to all records
        """
        result_df = df

        # Stage 1: Binary classification (attack vs benign)
        if self.data_source == "unsw" and self.gbt_binary_model:
            # UNSW: Use GBT binary model (87% accuracy, 94% AUC-ROC)
            try:
                self.gbt_binary_model.setFeaturesCol("features")
                self.gbt_binary_model.setPredictionCol("binary_prediction")
                result_df = self.gbt_binary_model.transform(result_df)
                # Drop intermediate columns to reduce memory
                if "rawPrediction" in result_df.columns:
                    result_df = result_df.drop("rawPrediction")
                if "probability" in result_df.columns:
                    result_df = result_df.drop("probability")
                logger.debug("✅ UNSW GBT binary classification applied")
            except Exception as e:
                logger.warning(f"GBT binary model prediction failed: {e}")
                result_df = result_df.withColumn("binary_prediction", F.lit(-1.0))
        elif self.binary_model:
            # CIC-IDS or fallback: Use RF binary model
            try:
                self.binary_model.setFeaturesCol("features")
                self.binary_model.setPredictionCol("binary_prediction")
                result_df = self.binary_model.transform(result_df)
                if "rawPrediction" in result_df.columns:
                    result_df = result_df.drop("rawPrediction")
                if "probability" in result_df.columns:
                    result_df = result_df.drop("probability")
                logger.debug("✅ Binary classification applied")
            except Exception as e:
                logger.warning(f"Binary model prediction failed: {e}")
                result_df = result_df.withColumn("binary_prediction", F.lit(-1.0))
        else:
            result_df = result_df.withColumn("binary_prediction", F.lit(-1.0))

        # Stage 2: Multiclass classification (attack type)
        # For UNSW: Only apply to records predicted as attacks (cascaded approach)
        # For CIC-IDS: Apply to all records
        if self.multiclass_model:
            try:
                if self.data_source == "unsw":
                    # UNSW: Cascaded approach - only classify attacks
                    # This saves compute resources by not classifying normal traffic
                    self.multiclass_model.setFeaturesCol("features")
                    self.multiclass_model.setPredictionCol("multiclass_raw")
                    
                    # Apply multiclass to all but only use result for attacks
                    result_df = self.multiclass_model.transform(result_df)
                    
                    # Set multiclass_prediction to 0 (Normal) if binary says normal
                    # Otherwise use the multiclass model prediction
                    result_df = result_df.withColumn(
                        "multiclass_prediction",
                        F.when(F.col("binary_prediction") == 0.0, F.lit(0.0))  # Normal
                         .otherwise(F.col("multiclass_raw"))  # Use multiclass prediction for attacks
                    )
                    
                    # Drop intermediate columns
                    result_df = result_df.drop("multiclass_raw")
                    if "rawPrediction" in result_df.columns:
                        result_df = result_df.drop("rawPrediction")
                    if "probability" in result_df.columns:
                        result_df = result_df.drop("probability")
                    
                    logger.debug("✅ UNSW cascaded multiclass classification applied")
                else:
                    # CIC-IDS: Apply multiclass to all records
                    self.multiclass_model.setFeaturesCol("features")
                    self.multiclass_model.setPredictionCol("multiclass_prediction")
                    result_df = self.multiclass_model.transform(result_df)
                    if "rawPrediction" in result_df.columns:
                        result_df = result_df.drop("rawPrediction")
                    if "probability" in result_df.columns:
                        result_df = result_df.drop("probability")
                    logger.debug("✅ Multiclass classification applied")
            except Exception as e:
                logger.warning(f"Multiclass model prediction failed: {e}")
                result_df = result_df.withColumn("multiclass_prediction", F.lit(-1.0))
        else:
            result_df = result_df.withColumn("multiclass_prediction", F.lit(-1.0))

        return result_df

    def enrich_predictions(self, df: DataFrame) -> DataFrame:
        """
        Add attack type labels and severity to predictions.
        
        Attack type is derived purely from model predictions (no ground truth labels).
        """

        # Choose attack mapping based on data source
        if self.data_source == "unsw":
            attack_mapping = UNSW_ATTACK_TYPE_MAPPING
        else:
            attack_mapping = ATTACK_TYPE_MAPPING

        # Build CASE expression for attack type mapping from multiclass prediction
        predicted_attack_type = F.lit("Unknown")
        for k, v in attack_mapping.items():
            predicted_attack_type = F.when(
                F.col("multiclass_prediction") == float(k),
                F.lit(v)
            ).otherwise(predicted_attack_type)

        # Attack type comes purely from model prediction (realistic scenario)
        df = df.withColumn("attack_type", predicted_attack_type)

        # Add is_attack flag from binary prediction
        df = df.withColumn(
            "is_attack",
            F.when(F.col("binary_prediction") == 1.0, F.lit(True)).otherwise(F.lit(False))
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

        # Processing timestamp
        df = df.withColumn("processed_at", F.current_timestamp())

        return df

    def write_to_console(self, df: DataFrame, output_mode: str = "append"):
        """Write results to console for monitoring."""
        # Select meaningful columns for display
        display_cols = [
            "is_attack", "attack_type", "severity", "processed_at"
        ]

        available_cols = [c for c in display_cols if c in df.columns]

        query = (
            df.select(available_cols)
              .writeStream
              .outputMode(output_mode)
              .format("console")
              .option("truncate", "false")
              .option("numRows", "20")
              .trigger(processingTime="2 seconds")
              .start()
        )

        return query

    def write_alerts_to_mongodb(self, df: DataFrame):
        """Write alert records to MongoDB using foreachBatch."""
        
        # Capture session_id for use in the closure
        session_id = self.session_id

        def write_batch_to_mongo(batch_df, batch_id):
            """Write a micro-batch to MongoDB."""
            if batch_df.count() == 0:
                return

            alerts_df = batch_df.filter(F.col("is_attack") == True)
            if alerts_df.count() == 0:
                return

            try:
                from pymongo import MongoClient

                client = MongoClient(
                    host=MONGODB_CONFIG["host"],
                    port=MONGODB_CONFIG["port"]
                )
                db = client[MONGODB_CONFIG["database"]]
                collection = db[MONGODB_CONFIG["alerts_collection"]]

                # Select only serializable columns for MongoDB (exclude Vector types)
                # No ground truth labels - only model predictions (realistic)
                mongo_columns = [
                    "is_attack", "attack_type", "severity", 
                    "binary_prediction", "multiclass_prediction",
                    "processed_at", "kafka_timestamp"
                ]
                # Add optional context columns if present (no labels)
                for col in ["proto", "service", "state", "Source_IP", "Destination_IP"]:
                    if col in alerts_df.columns:
                        mongo_columns.append(col)
                
                available_cols = [c for c in mongo_columns if c in alerts_df.columns]
                alerts_subset = alerts_df.select(available_cols)
                
                records = alerts_subset.toPandas().to_dict("records")

                for record in records:
                    record["batch_id"] = batch_id
                    record["inserted_at"] = datetime.now()
                    record["session_id"] = session_id  # Add session ID to each record
                    # Convert any remaining non-serializable types
                    for key, val in list(record.items()):
                        if hasattr(val, 'item'):  # numpy types
                            record[key] = val.item()
                        elif str(type(val)) == "<class 'pandas._libs.tslibs.timestamps.Timestamp'>":
                            record[key] = val.to_pydatetime()

                if records:
                    collection.insert_many(records)
                    logger.info(f"Batch {batch_id}: Inserted {len(records)} alerts to MongoDB (session: {session_id})")

                client.close()

            except Exception as e:
                logger.error(f"Failed to write to MongoDB: {e}")
                import traceback
                logger.error(traceback.format_exc())

        query = (
            df.writeStream
              .foreachBatch(write_batch_to_mongo)
              .outputMode("append")
              .option("checkpointLocation", f"{STREAMING_CONFIG['checkpoint_dir']}/mongodb")
              .trigger(processingTime=STREAMING_CONFIG["trigger_interval"])
              .start()
        )

        return query

    def write_to_kafka_alerts(self, df: DataFrame):
        """Write alerts to a separate Kafka topic."""
        alerts_df = df.filter(F.col("is_attack") == True)

        json_df = alerts_df.select(
            F.to_json(
                F.struct(
                    "kafka_timestamp", "is_attack", "attack_type",
                    "severity", "processed_at"
                )
            ).alias("value")
        )

        query = (
            json_df.writeStream
                   .format("kafka")
                   .option("kafka.bootstrap.servers", KAFKA_CONFIG["bootstrap_servers"])
                   .option("topic", KAFKA_CONFIG["alerts_topic"])
                   .option("checkpointLocation", f"{STREAMING_CONFIG['checkpoint_dir']}/kafka_alerts")
                   .trigger(processingTime=STREAMING_CONFIG["trigger_interval"])
                   .start()
        )

        return query

    def run(self, output_mode: str = "console", data_source: str = "cicids2017"):
        """
        Main method to run the streaming pipeline.

        Args:
            output_mode: Where to write results ('console', 'mongodb', 'kafka', 'all')
            data_source: Which dataset/scaler to use
        """
        logger.info("=" * 60)
        logger.info("Starting Real-Time Network Intrusion Detection")
        logger.info(f"📍 Session ID: {self.session_id}")
        logger.info("=" * 60)

        # Register session in MongoDB if using mongodb output
        if output_mode in ["mongodb", "all"]:
            try:
                from streaming.alert_storage import AlertStorage
                storage = AlertStorage(session_id=self.session_id)
                if storage.connect():
                    storage.register_session(
                        self.session_id, 
                        {"data_source": data_source, "output_mode": output_mode}
                    )
                    storage.close()
            except Exception as e:
                logger.warning(f"Could not register session: {e}")

        # Initialize
        self.data_source = data_source
        self.create_spark_session()
        self.define_schema()
        self.load_models()
        
        # Log the detection mode
        if self.data_source == "unsw":
            logger.info("🔍 UNSW Mode: Two-Stage Cascaded Detection")
            logger.info("   Stage 1: GBT Binary Model (87% accuracy)")
            logger.info("   Stage 2: RF Multiclass (only if attack detected)")
        else:
            logger.info(f"🔍 {data_source.upper()} Mode: Parallel Detection")

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

        logger.info("=" * 60)
        logger.info("🚀 Streaming pipeline running...")
        logger.info(f"📍 Session ID: {self.session_id}")
        logger.info("📊 View dashboard: python dashboard/app.py")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 60)

        # Wait for termination
        try:
            for query in queries:
                query.awaitTermination()
        except KeyboardInterrupt:
            logger.info("\n⏹️ Stopping streaming pipeline...")
            for query in queries:
                query.stop()
        finally:
            # End session in MongoDB
            if output_mode in ["mongodb", "all"]:
                try:
                    from streaming.alert_storage import AlertStorage
                    storage = AlertStorage(session_id=self.session_id)
                    if storage.connect():
                        storage.end_session(self.session_id)
                        storage.close()
                except Exception as e:
                    logger.warning(f"Could not end session: {e}")
            
            clear_session()
            self.spark.stop()
            logger.info("✅ Spark session stopped")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Spark Streaming for Network Intrusion Detection"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="console",
        choices=["console", "mongodb", "kafka", "all"],
        help="Output destination for predictions",
    )
    parser.add_argument(
        "--data-source",
        type=str,
        default="cicids2017",
        choices=["cicids2017", "cicids2018", "unsw"],
        help="Dataset to determine which scaler to use",
    )
    parser.add_argument(
        "--session-id",
        type=str,
        default=None,
        help="Optional session ID (auto-generated if not provided)",
    )

    args = parser.parse_args()

    processor = SparkStreamingProcessor(data_source=args.data_source, session_id=args.session_id)
    processor.run(output_mode=args.output, data_source=args.data_source)


if __name__ == "__main__":
    main()
