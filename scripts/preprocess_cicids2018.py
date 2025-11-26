"""
Preprocessing pipeline for CIC-IDS 2018 dataset
Handles data cleaning, feature engineering, class imbalance, and creates standardized parquet files
"""

import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit
from pyspark.sql.types import DoubleType, StringType
import logging

# Add scripts directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from preprocessing_utils import (
    create_spark_session,
    clean_column_names,
    handle_missing_values,
    handle_infinite_values,
    remove_duplicates,
    calculate_class_weights,
    add_sample_weights,
    standardize_label_column,
    create_binary_label,
    get_feature_columns,
    scale_features,
    print_dataset_summary
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_cicids2018_data(spark: SparkSession, data_dir: str):
    """Load all CIC-IDS 2018 CSV files"""
    csv_files = [
        "02-14-2018.csv",
        "02-15-2018.csv",
        "02-16-2018.csv",
        "02-20-2018.csv",
        "02-21-2018.csv",
        "02-22-2018.csv",
        "02-23-2018.csv",
        "02-28-2018.csv",
        "03-01-2018.csv",
        "03-02-2018.csv"
    ]
    
    dfs = []
    all_columns = set()
    
    # First pass: collect all unique columns
    for csv_file in csv_files:
        file_path = os.path.join(data_dir, csv_file)
        if os.path.exists(file_path):
            logger.info(f"Loading {csv_file}...")
            df = spark.read.csv(file_path, header=True, inferSchema=True)
            all_columns.update(df.columns)
            dfs.append((csv_file, df))
            logger.info(f"Loaded {csv_file} with {len(df.columns)} columns")
        else:
            logger.warning(f"File not found: {file_path}")
    
    if not dfs:
        raise FileNotFoundError("No CIC-IDS 2018 files found")
    
    # Identify columns to drop (ID columns that aren't in all files)
    columns_to_drop = ['Flow ID', 'Src IP', 'Src Port', 'Dst IP']
    logger.info(f"Dropping inconsistent columns: {columns_to_drop}")
    
    # Align schemas by dropping extra columns
    aligned_dfs = []
    for csv_file, df in dfs:
        # Drop extra identifier columns if they exist
        cols_to_remove = [c for c in columns_to_drop if c in df.columns]
        if cols_to_remove:
            df = df.drop(*cols_to_remove)
            logger.info(f"{csv_file}: Dropped {len(cols_to_remove)} columns")
        aligned_dfs.append(df)
    
    # Union all dataframes
    combined_df = aligned_dfs[0]
    for df in aligned_dfs[1:]:
        combined_df = combined_df.union(df)
    
    logger.info(f"All files combined. Final schema has {len(combined_df.columns)} columns")
    return combined_df


def preprocess_cicids2018(input_dir: str, output_dir: str):
    """
    Main preprocessing pipeline for CIC-IDS 2018 dataset
    """
    logger.info("="*70)
    logger.info("STARTING CIC-IDS 2018 PREPROCESSING")
    logger.info("="*70)
    
    # Create Spark session
    spark = create_spark_session("CIC-IDS-2018-Preprocessing")
    
    try:
        # Load data
        df = load_cicids2018_data(spark, input_dir)
        print_dataset_summary(df, "CIC-IDS 2018 (Raw)")
        
        # Step 1: Clean column names
        logger.info("\nStep 1: Cleaning column names...")
        df = clean_column_names(df)
        
        # Step 2: Drop timestamp column if exists (not needed for modeling)
        logger.info("\nStep 2: Dropping timestamp column...")
        if "timestamp" in df.columns:
            df = df.drop("timestamp")
        
        # Step 3: Standardize label column
        logger.info("\nStep 3: Standardizing label column...")
        df = standardize_label_column(df, label_col="label")
        
        # Step 4: Remove duplicates
        logger.info("\nStep 4: Removing duplicates...")
        df = remove_duplicates(df)
        
        # Step 5: Handle infinite values
        logger.info("\nStep 5: Handling infinite values...")
        df = handle_infinite_values(df)
        
        # Step 6: Handle missing values
        logger.info("\nStep 6: Handling missing values...")
        df = handle_missing_values(df, strategy="fill_zero", threshold=0.5)
        
        # Step 7: Create binary label
        logger.info("\nStep 7: Creating binary label...")
        df = create_binary_label(df, label_col="label", normal_values=["benign"])
        
        # Step 8: Calculate and add class weights
        logger.info("\nStep 8: Calculating class weights...")
        class_weights = calculate_class_weights(df, label_col="label")
        df = add_sample_weights(df, class_weights, label_col="label")
        
        # Step 9: Get feature columns
        logger.info("\nStep 9: Identifying feature columns...")
        feature_cols = get_feature_columns(df)
        logger.info(f"Number of features: {len(feature_cols)}")
        
        # Step 10: Scale features
        logger.info("\nStep 10: Scaling features...")
        df, assembler, scaler = scale_features(df, feature_cols, output_col="scaled_features")
        
        # Step 11: Select final columns for output
        logger.info("\nStep 11: Preparing final dataset...")
        output_columns = feature_cols + ["label", "binary_label", "sample_weight", "features", "scaled_features"]
        df_final = df.select(*[col for col in output_columns if col in df.columns])
        
        print_dataset_summary(df_final, "CIC-IDS 2018 (Processed)")
        
        # Step 12: Save to parquet
        logger.info("\nStep 12: Saving to parquet format...")
        output_path = os.path.join(output_dir, "cicids2018_preprocessed.parquet")
        
        df_final.write.mode("overwrite").parquet(output_path)
        logger.info(f"Saved preprocessed data to: {output_path}")
        
        # Save metadata
        metadata_path = os.path.join(output_dir, "cicids2018_metadata.txt")
        with open(metadata_path, 'w') as f:
            f.write("CIC-IDS 2018 Dataset Preprocessing Metadata\n")
            f.write("="*70 + "\n\n")
            f.write(f"Total Rows: {df_final.count():,}\n")
            f.write(f"Total Features: {len(feature_cols)}\n")
            f.write(f"Feature Columns: {', '.join(feature_cols)}\n\n")
            f.write("Class Weights:\n")
            for label, weight in class_weights.items():
                f.write(f"  {label}: {weight:.4f}\n")
        
        logger.info(f"Saved metadata to: {metadata_path}")
        
        logger.info("\n" + "="*70)
        logger.info("CIC-IDS 2018 PREPROCESSING COMPLETED SUCCESSFULLY")
        logger.info("="*70)
        
        return df_final
        
    except Exception as e:
        logger.error(f"Error during preprocessing: {str(e)}")
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    # Define paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    INPUT_DIR = os.path.join(BASE_DIR, "data", "CSE-CIC-IDS2018")
    OUTPUT_DIR = os.path.join(BASE_DIR, "data", "preprocessed")
    
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Run preprocessing
    preprocess_cicids2018(INPUT_DIR, OUTPUT_DIR)
