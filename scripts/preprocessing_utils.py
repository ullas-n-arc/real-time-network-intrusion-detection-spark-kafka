"""
Utility functions for preprocessing network intrusion detection datasets
Handles: data cleaning, missing values, infinite values, feature scaling, 
class imbalance, and standardization
"""

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    col, when, isnan, isnull, count, lit, lower, trim, 
    regexp_replace, sum as spark_sum, countDistinct
)
from pyspark.sql.types import DoubleType, FloatType, StringType
from pyspark.ml.feature import VectorAssembler, StandardScaler, StringIndexer
from typing import List, Dict, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_spark_session(app_name: str = "NetworkIDSPreprocessing") -> SparkSession:
    """Create and configure Spark session with optimized settings"""
    import os
    import tempfile
    
    # Fix for Java 17+ security manager issue
    os.environ['PYSPARK_SUBMIT_ARGS'] = '--conf spark.driver.extraJavaOptions="-Djava.security.manager=allow" --conf spark.executor.extraJavaOptions="-Djava.security.manager=allow" pyspark-shell'
    
    # Fix for hostname with underscores - use localhost
    os.environ['SPARK_LOCAL_HOSTNAME'] = 'localhost'
    
    # Set temp directory to D drive (more space) instead of C drive
    temp_dir = "D:\\temp\\spark"
    os.makedirs(temp_dir, exist_ok=True)
    os.environ['SPARK_LOCAL_DIRS'] = temp_dir
    
    spark = SparkSession.builder \
        .appName(app_name) \
        .master("local[2]") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .config("spark.driver.memory", "3g") \
        .config("spark.executor.memory", "3g") \
        .config("spark.sql.shuffle.partitions", "100") \
        .config("spark.driver.host", "localhost") \
        .config("spark.driver.bindAddress", "127.0.0.1") \
        .config("spark.driver.extraJavaOptions", "-Djava.security.manager=allow") \
        .config("spark.executor.extraJavaOptions", "-Djava.security.manager=allow") \
        .config("spark.local.dir", temp_dir) \
        .config("spark.driver.maxResultSize", "2g") \
        .config("spark.sql.files.maxPartitionBytes", "134217728") \
        .config("spark.sql.autoBroadcastJoinThreshold", "-1") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    logger.info(f"Spark session created: {app_name}")
    return spark


def clean_column_names(df: DataFrame) -> DataFrame:
    """
    Clean column names by removing spaces, special characters, and standardizing format
    """
    for column in df.columns:
        # Simple cleanup - replace spaces and special chars with underscores
        new_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in column)
        new_name = new_name.lower().strip('_')
        # Remove consecutive underscores
        while '__' in new_name:
            new_name = new_name.replace('__', '_')
        
        if new_name != column:
            df = df.withColumnRenamed(column, new_name)
    
    logger.info(f"Column names cleaned. Total columns: {len(df.columns)}")
    return df


def handle_missing_values(df: DataFrame, strategy: str = "drop", threshold: float = 0.5) -> DataFrame:
    """
    Handle missing values in the dataframe
    
    Args:
        df: Input dataframe
        strategy: 'drop' to remove rows, 'fill_mean' to fill with mean, 'fill_zero' to fill with 0
        threshold: Fraction of missing values allowed per column before dropping
    """
    total_rows = df.count()
    logger.info(f"Total rows before handling missing values: {total_rows}")
    
    # Check for missing values per column
    missing_counts = df.select([
        count(when(isnan(c) | isnull(c), c)).alias(c) 
        for c in df.columns if c.lower() not in ['label', 'attack_cat']
    ])
    
    # Drop columns with too many missing values
    columns_to_drop = []
    for col_name in missing_counts.columns:
        missing_count = missing_counts.select(col_name).first()[0]
        missing_ratio = missing_count / total_rows
        
        if missing_ratio > threshold:
            columns_to_drop.append(col_name)
            logger.info(f"Dropping column {col_name}: {missing_ratio:.2%} missing")
    
    df = df.drop(*columns_to_drop)
    
    # Handle remaining missing values
    if strategy == "drop":
        df = df.dropna()
        logger.info(f"Rows after dropping NaN: {df.count()}")
    
    elif strategy == "fill_zero":
        numeric_cols = [f.name for f in df.schema.fields 
                       if isinstance(f.dataType, (DoubleType, FloatType))
                       and f.name.lower() not in ['label', 'attack_cat']]
        df = df.fillna(0, subset=numeric_cols)
        logger.info("Filled missing numeric values with 0")
    
    elif strategy == "fill_mean":
        numeric_cols = [f.name for f in df.schema.fields 
                       if isinstance(f.dataType, (DoubleType, FloatType))
                       and f.name.lower() not in ['label', 'attack_cat']]
        
        # Calculate means and fill
        means = df.select([col(c) for c in numeric_cols]).summary("mean").collect()[0].asDict()
        fill_values = {col_name: float(means[col_name]) for col_name in numeric_cols if means[col_name] != 'null'}
        df = df.fillna(fill_values)
        logger.info("Filled missing numeric values with column means")
    
    return df


def handle_infinite_values(df: DataFrame) -> DataFrame:
    """
    Replace infinite values with None (which will be handled by missing value strategy)
    """
    numeric_cols = [f.name for f in df.schema.fields 
                   if isinstance(f.dataType, (DoubleType, FloatType))
                   and f.name.lower() not in ['label', 'attack_cat']]
    
    for col_name in numeric_cols:
        df = df.withColumn(
            col_name,
            when(col(col_name).isNull() | isnan(col_name), None)
            .when(col(col_name) == float('inf'), None)
            .when(col(col_name) == float('-inf'), None)
            .otherwise(col(col_name))
        )
    
    logger.info("Infinite values replaced with None")
    return df


def remove_duplicates(df: DataFrame) -> DataFrame:
    """Remove duplicate rows"""
    initial_count = df.count()
    df = df.dropDuplicates()
    final_count = df.count()
    duplicates_removed = initial_count - final_count
    
    logger.info(f"Duplicates removed: {duplicates_removed} ({duplicates_removed/initial_count:.2%})")
    return df


def calculate_class_weights(df: DataFrame, label_col: str = "label") -> Dict:
    """
    Calculate class weights for imbalanced datasets
    Returns dictionary of class -> weight
    """
    total_count = df.count()
    class_counts = df.groupBy(label_col).count().collect()
    
    class_weights = {}
    max_count = max([row['count'] for row in class_counts])
    
    logger.info("\n" + "="*50)
    logger.info("CLASS DISTRIBUTION:")
    logger.info("="*50)
    
    for row in class_counts:
        label = row[label_col]
        count = row['count']
        # Calculate weight as max_count / count (inverse frequency)
        weight = max_count / count
        class_weights[label] = weight
        
        percentage = (count / total_count) * 100
        logger.info(f"Class: {label:30s} | Count: {count:10d} | {percentage:6.2f}% | Weight: {weight:.4f}")
    
    logger.info("="*50 + "\n")
    
    return class_weights


def add_sample_weights(df: DataFrame, class_weights: Dict, label_col: str = "label") -> DataFrame:
    """
    Add a 'sample_weight' column based on class weights
    """
    # Create a mapping expression
    weight_expr = None
    for class_label, weight in class_weights.items():
        condition = when(col(label_col) == class_label, lit(weight))
        weight_expr = condition if weight_expr is None else weight_expr.when(col(label_col) == class_label, lit(weight))
    
    weight_expr = weight_expr.otherwise(lit(1.0))
    df = df.withColumn("sample_weight", weight_expr)
    
    logger.info("Sample weights added based on class distribution")
    return df


def standardize_label_column(df: DataFrame, label_col: str = "label") -> DataFrame:
    """
    Standardize label column: trim whitespace, convert to lowercase, clean up
    """
    if label_col in df.columns:
        df = df.withColumn(label_col, trim(lower(col(label_col))))
        
        # Log unique labels
        unique_labels = df.select(label_col).distinct().collect()
        logger.info(f"Unique labels after standardization: {[row[0] for row in unique_labels]}")
    
    return df


def create_binary_label(df: DataFrame, label_col: str = "label", 
                       normal_values: List[str] = ["benign", "normal"]) -> DataFrame:
    """
    Create a binary label column (0 for normal, 1 for attack)
    """
    normal_values_lower = [v.lower() for v in normal_values]
    
    df = df.withColumn(
        "binary_label",
        when(lower(col(label_col)).isin(normal_values_lower), 0).otherwise(1)
    )
    
    logger.info("Binary label column created (0=Normal, 1=Attack)")
    return df


def encode_categorical_features(df: DataFrame, categorical_cols: List[str]) -> Tuple[DataFrame, Dict]:
    """
    Encode categorical features using StringIndexer
    Returns the transformed dataframe and a dictionary of indexers
    """
    indexers = {}
    
    for col_name in categorical_cols:
        if col_name in df.columns:
            indexer = StringIndexer(inputCol=col_name, outputCol=f"{col_name}_indexed", handleInvalid="keep")
            indexer_model = indexer.fit(df)
            df = indexer_model.transform(df)
            indexers[col_name] = indexer_model
            
            logger.info(f"Encoded categorical column: {col_name}")
    
    return df, indexers


def scale_features(df: DataFrame, feature_cols: List[str], 
                   output_col: str = "scaled_features") -> Tuple[DataFrame, VectorAssembler, StandardScaler]:
    """
    Scale numeric features using StandardScaler
    Returns the transformed dataframe, assembler, and scaler
    """
    # Assemble features into a vector
    assembler = VectorAssembler(inputCols=feature_cols, outputCol="features", handleInvalid="skip")
    df = assembler.transform(df)
    
    # Scale features
    scaler = StandardScaler(inputCol="features", outputCol=output_col, withStd=True, withMean=True)
    scaler_model = scaler.fit(df)
    df = scaler_model.transform(df)
    
    logger.info(f"Features scaled: {len(feature_cols)} columns")
    return df, assembler, scaler_model


def remove_low_variance_features(df: DataFrame, variance_threshold: float = 0.01) -> DataFrame:
    """
    Remove features with variance below threshold (quasi-constant features)
    """
    numeric_cols = [f.name for f in df.schema.fields 
                   if isinstance(f.dataType, (DoubleType, FloatType))
                   and f.name.lower() not in ['label', 'attack_cat', 'sample_weight', 'binary_label']]
    
    low_variance_cols = []
    
    for col_name in numeric_cols:
        variance = df.select(col_name).summary("stddev").collect()[0][0]
        try:
            variance_val = float(variance)
            if variance_val < variance_threshold:
                low_variance_cols.append(col_name)
        except (ValueError, TypeError):
            continue
    
    if low_variance_cols:
        df = df.drop(*low_variance_cols)
        logger.info(f"Removed {len(low_variance_cols)} low-variance features")
    
    return df


def get_feature_columns(df: DataFrame, exclude_cols: List[str] = None) -> List[str]:
    """
    Get list of numeric feature columns, excluding specified columns
    """
    if exclude_cols is None:
        exclude_cols = ['label', 'attack_cat', 'sample_weight', 'binary_label', 
                       'features', 'scaled_features', 'id', 'timestamp']
    
    exclude_cols_lower = [c.lower() for c in exclude_cols]
    
    feature_cols = [
        f.name for f in df.schema.fields 
        if isinstance(f.dataType, (DoubleType, FloatType))
        and f.name.lower() not in exclude_cols_lower
        and not f.name.endswith('_indexed')
    ]
    
    logger.info(f"Feature columns identified: {len(feature_cols)}")
    return feature_cols


def print_dataset_summary(df: DataFrame, dataset_name: str):
    """Print comprehensive summary of the dataset"""
    logger.info("\n" + "="*70)
    logger.info(f"DATASET SUMMARY: {dataset_name}")
    logger.info("="*70)
    logger.info(f"Total Rows: {df.count():,}")
    logger.info(f"Total Columns: {len(df.columns)}")
    logger.info(f"Columns: {', '.join(df.columns[:10])}{'...' if len(df.columns) > 10 else ''}")
    logger.info("="*70 + "\n")
