"""
Preprocessing pipeline for UNSW-NB15 dataset
Handles data cleaning, feature engineering, class imbalance, and creates standardized parquet files
"""

import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, when
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
    encode_categorical_features,
    print_dataset_summary
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_unsw_nb15_data(spark: SparkSession, data_dir: str):
    """Load UNSW-NB15 training and testing CSV files"""
    
    # Option 1: Load training and testing sets
    train_path = os.path.join(data_dir, "UNSW_NB15_training-set.csv")
    test_path = os.path.join(data_dir, "UNSW_NB15_testing-set.csv")
    
    dfs = []
    
    if os.path.exists(train_path):
        logger.info(f"Loading training set...")
        df_train = spark.read.csv(train_path, header=True, inferSchema=True)
        dfs.append(df_train)
        logger.info(f"Loaded {df_train.count():,} rows from training set")
    
    if os.path.exists(test_path):
        logger.info(f"Loading testing set...")
        df_test = spark.read.csv(test_path, header=True, inferSchema=True)
        dfs.append(df_test)
        logger.info(f"Loaded {df_test.count():,} rows from testing set")
    
    # Option 2: Also try to load the full dataset files if available
    full_files = [
        "UNSW-NB15_1.csv",
        "UNSW-NB15_2.csv",
        "UNSW-NB15_3.csv",
        "UNSW-NB15_4.csv"
    ]
    
    for csv_file in full_files:
        file_path = os.path.join(data_dir, csv_file)
        if os.path.exists(file_path):
            logger.info(f"Loading {csv_file}...")
            df = spark.read.csv(file_path, header=False, inferSchema=True)
            
            # These files don't have headers, need to add column names
            # Based on UNSW-NB15 dataset documentation
            column_names = [
                'srcip', 'sport', 'dstip', 'dsport', 'proto', 'state', 'dur', 'sbytes', 'dbytes',
                'sttl', 'dttl', 'sloss', 'dloss', 'service', 'sload', 'dload', 'spkts', 'dpkts',
                'swin', 'dwin', 'stcpb', 'dtcpb', 'smeansz', 'dmeansz', 'trans_depth',
                'res_bdy_len', 'sjit', 'djit', 'stime', 'ltime', 'sintpkt', 'dintpkt',
                'tcprtt', 'synack', 'ackdat', 'is_sm_ips_ports', 'ct_state_ttl', 'ct_flw_http_mthd',
                'is_ftp_login', 'ct_ftp_cmd', 'ct_srv_src', 'ct_srv_dst', 'ct_dst_ltm',
                'ct_src_ltm', 'ct_src_dport_ltm', 'ct_dst_sport_ltm', 'ct_dst_src_ltm',
                'attack_cat', 'label'
            ]
            
            # Rename columns if the count matches
            if len(df.columns) == len(column_names):
                for old_col, new_col in zip(df.columns, column_names):
                    df = df.withColumnRenamed(old_col, new_col)
            
            dfs.append(df)
            logger.info(f"Loaded {df.count():,} rows from {csv_file}")
    
    if not dfs:
        raise FileNotFoundError("No UNSW-NB15 files found")
    
    # Union all dataframes
    combined_df = dfs[0]
    for df in dfs[1:]:
        # Make sure columns match before union
        if set(df.columns) == set(combined_df.columns):
            combined_df = combined_df.union(df)
        else:
            logger.warning(f"Skipping dataframe due to column mismatch")
    
    logger.info(f"Total rows after combining all files: {combined_df.count():,}")
    return combined_df


def preprocess_unsw_nb15(input_dir: str, output_dir: str):
    """
    Main preprocessing pipeline for UNSW-NB15 dataset
    """
    logger.info("="*70)
    logger.info("STARTING UNSW-NB15 PREPROCESSING")
    logger.info("="*70)
    
    # Create Spark session
    spark = create_spark_session("UNSW-NB15-Preprocessing")
    
    try:
        # Load data
        df = load_unsw_nb15_data(spark, input_dir)
        print_dataset_summary(df, "UNSW-NB15 (Raw)")
        
        # Step 1: Clean column names
        logger.info("\nStep 1: Cleaning column names...")
        df = clean_column_names(df)
        
        # Step 2: Drop unnecessary columns (IP addresses, timestamps)
        logger.info("\nStep 2: Dropping unnecessary columns...")
        cols_to_drop = ['srcip', 'dstip', 'stime', 'ltime', 'id']
        existing_cols_to_drop = [c for c in cols_to_drop if c in df.columns]
        if existing_cols_to_drop:
            df = df.drop(*existing_cols_to_drop)
            logger.info(f"Dropped columns: {', '.join(existing_cols_to_drop)}")
        
        # Step 3: Identify categorical columns
        logger.info("\nStep 3: Encoding categorical features...")
        categorical_cols = ['proto', 'service', 'state']
        existing_categorical = [c for c in categorical_cols if c in df.columns]
        
        if existing_categorical:
            df, indexers = encode_categorical_features(df, existing_categorical)
        
        # Step 4: Standardize label column
        logger.info("\nStep 4: Standardizing label column...")
        # UNSW-NB15 has both 'label' (binary) and 'attack_cat' (multi-class)
        if 'attack_cat' in df.columns:
            df = standardize_label_column(df, label_col="attack_cat")
        
        if 'label' in df.columns:
            # Create text label from binary label
            df = df.withColumn("label_text", 
                             when(col("label") == 0, lit("normal")).otherwise(col("attack_cat")))
        else:
            df = df.withColumn("label_text", col("attack_cat"))
        
        # Step 5: Remove duplicates
        logger.info("\nStep 5: Removing duplicates...")
        df = remove_duplicates(df)
        
        # Step 6: Handle infinite values
        logger.info("\nStep 6: Handling infinite values...")
        df = handle_infinite_values(df)
        
        # Step 7: Handle missing values
        logger.info("\nStep 7: Handling missing values...")
        df = handle_missing_values(df, strategy="fill_zero", threshold=0.5)
        
        # Step 8: Create binary label if it doesn't exist
        logger.info("\nStep 8: Creating/validating binary label...")
        if 'label' not in df.columns:
            df = create_binary_label(df, label_col="label_text", normal_values=["normal", "benign"])
            df = df.withColumnRenamed("binary_label", "label")
        else:
            # Ensure label is numeric
            df = df.withColumn("label", col("label").cast("integer"))
        
        # Step 9: Calculate and add class weights
        logger.info("\nStep 9: Calculating class weights...")
        if 'label_text' in df.columns:
            class_weights = calculate_class_weights(df, label_col="label_text")
            df = add_sample_weights(df, class_weights, label_col="label_text")
        else:
            class_weights = calculate_class_weights(df, label_col="label")
            df = add_sample_weights(df, class_weights, label_col="label")
        
        # Step 10: Get feature columns
        logger.info("\nStep 10: Identifying feature columns...")
        exclude_cols = ['label', 'attack_cat', 'label_text', 'sample_weight', 'binary_label', 
                       'features', 'scaled_features']
        feature_cols = get_feature_columns(df, exclude_cols=exclude_cols)
        logger.info(f"Number of features: {len(feature_cols)}")
        
        # Step 11: Scale features
        logger.info("\nStep 11: Scaling features...")
        df, assembler, scaler = scale_features(df, feature_cols, output_col="scaled_features")
        
        # Step 12: Select final columns for output
        logger.info("\nStep 12: Preparing final dataset...")
        output_columns = feature_cols + ["label", "sample_weight", "features", "scaled_features"]
        if 'label_text' in df.columns:
            output_columns.append("label_text")
        if 'attack_cat' in df.columns:
            output_columns.append("attack_cat")
        
        df_final = df.select(*[col for col in output_columns if col in df.columns])
        
        print_dataset_summary(df_final, "UNSW-NB15 (Processed)")
        
        # Step 13: Save to parquet
        logger.info("\nStep 13: Saving to parquet format...")
        output_path = os.path.join(output_dir, "unsw_nb15_preprocessed.parquet")
        
        df_final.write.mode("overwrite").parquet(output_path)
        logger.info(f"Saved preprocessed data to: {output_path}")
        
        # Save metadata
        metadata_path = os.path.join(output_dir, "unsw_nb15_metadata.txt")
        with open(metadata_path, 'w') as f:
            f.write("UNSW-NB15 Dataset Preprocessing Metadata\n")
            f.write("="*70 + "\n\n")
            f.write(f"Total Rows: {df_final.count():,}\n")
            f.write(f"Total Features: {len(feature_cols)}\n")
            f.write(f"Feature Columns: {', '.join(feature_cols)}\n\n")
            f.write("Class Weights:\n")
            for label, weight in class_weights.items():
                f.write(f"  {label}: {weight:.4f}\n")
        
        logger.info(f"Saved metadata to: {metadata_path}")
        
        logger.info("\n" + "="*70)
        logger.info("UNSW-NB15 PREPROCESSING COMPLETED SUCCESSFULLY")
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
    INPUT_DIR = os.path.join(BASE_DIR, "data", "UNSW-NB15")
    OUTPUT_DIR = os.path.join(BASE_DIR, "data", "preprocessed")
    
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Run preprocessing
    preprocess_unsw_nb15(INPUT_DIR, OUTPUT_DIR)
