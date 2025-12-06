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
from pyspark.ml.feature import VectorAssembler, StandardScalerModel

from config import (
    KAFKA_CONFIG, SPARK_CONFIG, STREAMING_CONFIG,
    MODEL_PATHS, FEATURE_CONFIG, UNSW_FEATURE_CONFIG, ATTACK_TYPE_MAPPING,
    ALERT_CONFIG, MONGODB_CONFIG, SCALER_PATHS, DATASET_MODEL_PATHS
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
    """

    def __init__(self, data_source="cicids2017"):
        """Initialize the streaming processor."""
        self.spark = None
        self.binary_model = None
        self.multiclass_model = None
        self.schema = None
        self.scaler_model = None
        self.data_source = data_source

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
        """Define the schema for incoming network traffic data."""
        fields = []

        # Choose features based on data source
        if self.data_source == "unsw":
            feature_list = UNSW_FEATURE_CONFIG["numeric_features"]
            # Add id field first (sent by producer but not used for prediction)
            fields.append(StructField("id", DoubleType(), True))
        else:
            feature_list = FEATURE_CONFIG["numeric_features"]

        # Numeric feature fields
        for feature in feature_list:
            fields.append(StructField(feature.strip(), DoubleType(), True))

        # Metadata fields based on data source
        if self.data_source == "unsw":
            fields.extend([
                StructField("attack_cat", StringType(), True),
                StructField("label", DoubleType(), True),  # Producer sends as float
                StructField("proto", StringType(), True),
                StructField("service", StringType(), True),
                StructField("state", StringType(), True),
                StructField("timestamp", StringType(), True),
                StructField("producer_id", IntegerType(), True),
            ])
        else:
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
            # Load binary model based on data source
            model_path = DATASET_MODEL_PATHS.get(self.data_source, MODEL_PATHS["rf_binary"])
            if os.path.exists(model_path):
                self.binary_model = RandomForestClassificationModel.load(model_path)
                logger.info(f"✅ Loaded binary model: {model_path}")
            else:
                # Fallback to default
                if os.path.exists(MODEL_PATHS["rf_binary"]):
                    self.binary_model = RandomForestClassificationModel.load(MODEL_PATHS["rf_binary"])
                    logger.info(f"✅ Loaded fallback binary model: {MODEL_PATHS['rf_binary']}")
                else:
                    logger.warning(f"⚠️ Binary model not found at {model_path}")

            # Multiclass classifier
            if self.data_source == "unsw":
                # Load UNSW multiclass model
                unsw_multiclass_path = MODEL_PATHS.get("unsw_multiclass", "")
                if os.path.exists(unsw_multiclass_path):
                    self.multiclass_model = RandomForestClassificationModel.load(unsw_multiclass_path)
                    logger.info(f"✅ Loaded UNSW multiclass model: {unsw_multiclass_path}")
                else:
                    logger.warning(f"⚠️ UNSW multiclass model not found at {unsw_multiclass_path}")
            else:
                # CIC-IDS multiclass
                if os.path.exists(MODEL_PATHS.get("rf_multiclass_improved", "")):
                    self.multiclass_model = RandomForestClassificationModel.load(
                        MODEL_PATHS["rf_multiclass_improved"]
                    )
                    logger.info("✅ Loaded improved multiclass model")
                elif os.path.exists(MODEL_PATHS["rf_multiclass"]):
                    self.multiclass_model = RandomForestClassificationModel.load(
                        MODEL_PATHS["rf_multiclass"]
                    )
                    logger.info(f"✅ Loaded multiclass model: {MODEL_PATHS['rf_multiclass']}")
                else:
                    logger.warning("⚠️ Multiclass model not found")

            # Load scaler model for the data source
            scaler_path = SCALER_PATHS.get(self.data_source)
            if scaler_path and os.path.exists(scaler_path):
                self.scaler_model = StandardScalerModel.load(scaler_path)
                logger.info(f"✅ Loaded scaler model: {scaler_path}")
            else:
                logger.warning(f"⚠️ Scaler model not found for data source: {self.data_source}")

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
                outputCol="features_raw",
                handleInvalid="keep"  # "keep" is faster than "skip"
            )
            df = assembler.transform(df)

            # Apply scaler if available
            if self.scaler_model:
                input_col = self.scaler_model.getInputCol()
                
                # Ensure input column matches what scaler expects
                if "features_raw" in df.columns and input_col != "features_raw":
                    df = df.withColumnRenamed("features_raw", input_col)
                
                df = self.scaler_model.transform(df)
            else:
                # No scaler - rename features_raw to features for model
                df = df.withColumnRenamed("features_raw", "features")

        return df

    def apply_model(self, df: DataFrame) -> DataFrame:
        """Apply ML models for prediction."""
        result_df = df

        # Binary classification
        if self.binary_model:
            try:
                features_col = "features" if "features" in result_df.columns else "features_scaled"
                self.binary_model.setFeaturesCol(features_col)
                self.binary_model.setPredictionCol("binary_prediction")
                result_df = self.binary_model.transform(result_df)
                # Drop intermediate columns to reduce memory
                if "rawPrediction" in result_df.columns:
                    result_df = result_df.drop("rawPrediction")
                if "probability" in result_df.columns:
                    result_df = result_df.drop("probability")
            except Exception as e:
                logger.warning(f"Binary model prediction failed: {e}")
                result_df = result_df.withColumn("binary_prediction", F.lit(-1.0))
        else:
            result_df = result_df.withColumn("binary_prediction", F.lit(-1.0))

        # Multiclass classification (for all datasets including UNSW)
        if self.multiclass_model:
            try:
                features_col = "features" if "features" in result_df.columns else "features_scaled"
                self.multiclass_model.setFeaturesCol(features_col)
                self.multiclass_model.setPredictionCol("multiclass_prediction")
                result_df = self.multiclass_model.transform(result_df)
                if "rawPrediction" in result_df.columns:
                    result_df = result_df.drop("rawPrediction")
                if "probability" in result_df.columns:
                    result_df = result_df.drop("probability")
            except Exception as e:
                logger.warning(f"Multiclass model prediction failed: {e}")
                result_df = result_df.withColumn("multiclass_prediction", F.lit(-1.0))
        else:
            result_df = result_df.withColumn("multiclass_prediction", F.lit(-1.0))

        return result_df

    def enrich_predictions(self, df: DataFrame) -> DataFrame:
        """Add attack type labels and severity to predictions."""

        # Choose attack mapping based on data source
        if self.data_source == "unsw":
            attack_mapping = UNSW_ATTACK_TYPE_MAPPING
        else:
            attack_mapping = ATTACK_TYPE_MAPPING

        # Build CASE expression for attack type mapping
        attack_type_col = F.lit("Unknown")
        for k, v in attack_mapping.items():
            attack_type_col = F.when(
                F.col("multiclass_prediction") == float(k),
                F.lit(v)
            ).otherwise(attack_type_col)

        df = df.withColumn("attack_type", attack_type_col)

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
                mongo_columns = [
                    "is_attack", "attack_type", "severity", 
                    "binary_prediction", "multiclass_prediction",
                    "processed_at", "kafka_timestamp"
                ]
                # Add optional source columns if present
                for col in ["attack_cat", "label", "proto", "service", "state"]:
                    if col in alerts_df.columns:
                        mongo_columns.append(col)
                
                available_cols = [c for c in mongo_columns if c in alerts_df.columns]
                alerts_subset = alerts_df.select(available_cols)
                
                records = alerts_subset.toPandas().to_dict("records")

                for record in records:
                    record["batch_id"] = batch_id
                    record["inserted_at"] = datetime.now()
                    # Convert any remaining non-serializable types
                    for key, val in list(record.items()):
                        if hasattr(val, 'item'):  # numpy types
                            record[key] = val.item()
                        elif str(type(val)) == "<class 'pandas._libs.tslibs.timestamps.Timestamp'>":
                            record[key] = val.to_pydatetime()

                if records:
                    collection.insert_many(records)
                    logger.info(f"Batch {batch_id}: Inserted {len(records)} alerts to MongoDB")

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
        logger.info("=" * 60)

        # Initialize
        self.data_source = data_source
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

        logger.info("=" * 60)
        logger.info("🚀 Streaming pipeline running...")
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

    args = parser.parse_args()

    processor = SparkStreamingProcessor(data_source=args.data_source)
    processor.run(output_mode=args.output, data_source=args.data_source)


if __name__ == "__main__":
    main()
