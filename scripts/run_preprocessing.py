"""
Main preprocessing orchestrator
Runs all dataset preprocessing pipelines and generates standardized parquet files
"""

import os
import sys
import logging
from datetime import datetime

# Add scripts directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import preprocessing modules
from preprocess_cicids2017 import preprocess_cicids2017
from preprocess_cicids2018 import preprocess_cicids2018
from preprocess_unsw_nb15 import preprocess_unsw_nb15

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('preprocessing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    """
    Run all preprocessing pipelines
    """
    start_time = datetime.now()
    
    logger.info("="*80)
    logger.info("NETWORK INTRUSION DETECTION DATASET PREPROCESSING")
    logger.info("="*80)
    logger.info(f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*80 + "\n")
    
    # Define base directories
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    OUTPUT_DIR = os.path.join(DATA_DIR, "preprocessed")
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    logger.info(f"Output directory: {OUTPUT_DIR}\n")
    
    datasets_processed = []
    datasets_failed = []
    
    # Dataset 1: CIC-IDS 2017
    try:
        logger.info("\n" + ">"*80)
        logger.info("DATASET 1/3: CIC-IDS 2017")
        logger.info(">"*80 + "\n")
        
        input_dir = os.path.join(DATA_DIR, "CSE-CIC-IDS2017")
        preprocess_cicids2017(input_dir, OUTPUT_DIR)
        datasets_processed.append("CIC-IDS 2017")
        
        logger.info("\n" + "✓"*80)
        logger.info("CIC-IDS 2017 COMPLETED SUCCESSFULLY")
        logger.info("✓"*80 + "\n")
        
    except Exception as e:
        logger.error(f"Failed to preprocess CIC-IDS 2017: {str(e)}")
        datasets_failed.append(("CIC-IDS 2017", str(e)))
    
    # Dataset 2: CIC-IDS 2018
    try:
        logger.info("\n" + ">"*80)
        logger.info("DATASET 2/3: CIC-IDS 2018")
        logger.info(">"*80 + "\n")
        
        input_dir = os.path.join(DATA_DIR, "CSE-CIC-IDS2018")
        preprocess_cicids2018(input_dir, OUTPUT_DIR)
        datasets_processed.append("CIC-IDS 2018")
        
        logger.info("\n" + "✓"*80)
        logger.info("CIC-IDS 2018 COMPLETED SUCCESSFULLY")
        logger.info("✓"*80 + "\n")
        
    except Exception as e:
        logger.error(f"Failed to preprocess CIC-IDS 2018: {str(e)}")
        datasets_failed.append(("CIC-IDS 2018", str(e)))
    
    # Dataset 3: UNSW-NB15
    try:
        logger.info("\n" + ">"*80)
        logger.info("DATASET 3/3: UNSW-NB15")
        logger.info(">"*80 + "\n")
        
        input_dir = os.path.join(DATA_DIR, "UNSW-NB15")
        preprocess_unsw_nb15(input_dir, OUTPUT_DIR)
        datasets_processed.append("UNSW-NB15")
        
        logger.info("\n" + "✓"*80)
        logger.info("UNSW-NB15 COMPLETED SUCCESSFULLY")
        logger.info("✓"*80 + "\n")
        
    except Exception as e:
        logger.error(f"Failed to preprocess UNSW-NB15: {str(e)}")
        datasets_failed.append(("UNSW-NB15", str(e)))
    
    # Final summary
    end_time = datetime.now()
    duration = end_time - start_time
    
    logger.info("\n" + "="*80)
    logger.info("PREPROCESSING SUMMARY")
    logger.info("="*80)
    logger.info(f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Duration: {duration}")
    logger.info("-"*80)
    logger.info(f"Datasets Processed Successfully: {len(datasets_processed)}/3")
    for dataset in datasets_processed:
        logger.info(f"  ✓ {dataset}")
    
    if datasets_failed:
        logger.info(f"\nDatasets Failed: {len(datasets_failed)}/3")
        for dataset, error in datasets_failed:
            logger.info(f"  ✗ {dataset}: {error}")
    
    logger.info("-"*80)
    logger.info(f"Output Location: {OUTPUT_DIR}")
    logger.info("="*80)
    
    # Generate summary report
    summary_path = os.path.join(OUTPUT_DIR, "preprocessing_summary.txt")
    with open(summary_path, 'w') as f:
        f.write("Network Intrusion Detection Dataset Preprocessing Summary\n")
        f.write("="*80 + "\n\n")
        f.write(f"Preprocessing Date: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Duration: {duration}\n\n")
        f.write(f"Successfully Processed: {len(datasets_processed)}/3 datasets\n")
        for dataset in datasets_processed:
            f.write(f"  - {dataset}\n")
        
        if datasets_failed:
            f.write(f"\nFailed: {len(datasets_failed)}/3 datasets\n")
            for dataset, error in datasets_failed:
                f.write(f"  - {dataset}: {error}\n")
        
        f.write("\n" + "="*80 + "\n")
        f.write("Preprocessing Steps Applied:\n")
        f.write("  1. Column name standardization\n")
        f.write("  2. Duplicate removal\n")
        f.write("  3. Infinite value handling\n")
        f.write("  4. Missing value imputation\n")
        f.write("  5. Categorical feature encoding\n")
        f.write("  6. Binary label creation\n")
        f.write("  7. Class weight calculation (for imbalance)\n")
        f.write("  8. Sample weight assignment\n")
        f.write("  9. Feature scaling (StandardScaler)\n")
        f.write("  10. Parquet file generation\n")
        f.write("\n" + "="*80 + "\n")
        f.write("Output Files:\n")
        f.write("  - cicids2017_preprocessed.parquet\n")
        f.write("  - cicids2017_metadata.txt\n")
        f.write("  - cicids2018_preprocessed.parquet\n")
        f.write("  - cicids2018_metadata.txt\n")
        f.write("  - unsw_nb15_preprocessed.parquet\n")
        f.write("  - unsw_nb15_metadata.txt\n")
        f.write("\n" + "="*80 + "\n")
    
    logger.info(f"\nSummary report saved to: {summary_path}")
    
    return len(datasets_failed) == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
