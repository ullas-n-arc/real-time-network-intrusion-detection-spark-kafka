"""
Preprocessing pipeline for CIC-IDS 2017 dataset
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


def load_cicids2017_data(spark: SparkSession, data_dir: str):
    """Load all CIC-IDS 2017 CSV files"""
    csv_files = [
        "Monday-WorkingHours.pcap_ISCX.csv",
        "Tuesday-WorkingHours.pcap_ISCX.csv",
        "Wednesday-workingHours.pcap_ISCX.csv",
        "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv",
        "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv",
        "Friday-WorkingHours-Morning.pcap_ISCX.csv",
        "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv",
        "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv"
    ]
    
    dfs = []
    for csv_file in csv_files:
        file_path = os.path.join(data_dir, csv_file)
        if os.path.exists(file_path):
            logger.info(f"Loading {csv_file}...")
            df = spark.read.csv(file_path, header=True, inferSchema=True)
            dfs.append(df)
            logger.info(f"Loaded {csv_file} successfully")
        else:
            logger.warning(f"File not found: {file_path}")
    
    if not dfs:
        raise FileNotFoundError("No CIC-IDS 2017 files found")
    
    # Union all dataframes
    combined_df = dfs[0]
    for df in dfs[1:]:
        combined_df = combined_df.union(df)
    
    logger.info(f"All files combined successfully")
    return combined_df


def preprocess_cicids2017(input_dir: str, output_dir: str):
    """
    Main preprocessing pipeline for CIC-IDS 2017 dataset
    """
    logger.info("="*70)
    logger.info("STARTING CIC-IDS 2017 PREPROCESSING")
    logger.info("="*70)
    
    # Create Spark session
    spark = create_spark_session("CIC-IDS-2017-Preprocessing")
    
    try:
        # Load data
        df = load_cicids2017_data(spark, input_dir)
        print_dataset_summary(df, "CIC-IDS 2017 (Raw)")
        
        # Step 1: Clean column names
        logger.info("\nStep 1: Cleaning column names...")
        df = clean_column_names(df)
        
        # Step 2: Standardize label column
        logger.info("\nStep 2: Standardizing label column...")
        df = standardize_label_column(df, label_col="label")
        
        # Step 3: Remove duplicates
        logger.info("\nStep 3: Removing duplicates...")
        df = remove_duplicates(df)
        
        # Step 4: Handle infinite values
        logger.info("\nStep 4: Handling infinite values...")
        df = handle_infinite_values(df)
        
        # Step 5: Handle missing values
        logger.info("\nStep 5: Handling missing values...")
        df = handle_missing_values(df, strategy="fill_zero", threshold=0.5)
        
        # Step 6: Create binary label
        logger.info("\nStep 6: Creating binary label...")
        df = create_binary_label(df, label_col="label", normal_values=["benign"])
        
        # Step 7: Calculate and add class weights
        logger.info("\nStep 7: Calculating class weights...")
        class_weights = calculate_class_weights(df, label_col="label")
        df = add_sample_weights(df, class_weights, label_col="label")
        
        # Step 8: Get feature columns
        logger.info("\nStep 8: Identifying feature columns...")
        feature_cols = get_feature_columns(df)
        logger.info(f"Number of features: {len(feature_cols)}")
        
        # Step 9: Scale features
        logger.info("\nStep 9: Scaling features...")
        df, assembler, scaler = scale_features(df, feature_cols, output_col="scaled_features")
        
        # Step 10: Select final columns for output
        logger.info("\nStep 10: Preparing final dataset...")
        output_columns = feature_cols + ["label", "binary_label", "sample_weight", "features", "scaled_features"]
        df_final = df.select(*[col for col in output_columns if col in df.columns])
        
        print_dataset_summary(df_final, "CIC-IDS 2017 (Processed)")
        
        # Step 11: Save to parquet
        logger.info("\nStep 11: Saving to parquet format...")
        output_path = os.path.join(output_dir, "cicids2017_preprocessed.parquet")
        
        df_final.write.mode("overwrite").parquet(output_path)
        logger.info(f"Saved preprocessed data to: {output_path}")
        
        # Save metadata
        metadata_path = os.path.join(output_dir, "cicids2017_metadata.txt")
        with open(metadata_path, 'w') as f:
            f.write("CIC-IDS 2017 Dataset Preprocessing Metadata\n")
            f.write("="*70 + "\n\n")
            f.write(f"Total Rows: {df_final.count():,}\n")
            f.write(f"Total Features: {len(feature_cols)}\n")
            f.write(f"Feature Columns: {', '.join(feature_cols)}\n\n")
            f.write("Class Weights:\n")
            for label, weight in class_weights.items():
                f.write(f"  {label}: {weight:.4f}\n")
        
        logger.info(f"Saved metadata to: {metadata_path}")
        
        logger.info("\n" + "="*70)
        logger.info("CIC-IDS 2017 PREPROCESSING COMPLETED SUCCESSFULLY")
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
    INPUT_DIR = os.path.join(BASE_DIR, "data", "CSE-CIC-IDS2017")
    OUTPUT_DIR = os.path.join(BASE_DIR, "data", "preprocessed")
    
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Run preprocessing
    preprocess_cicids2017(INPUT_DIR, OUTPUT_DIR)
