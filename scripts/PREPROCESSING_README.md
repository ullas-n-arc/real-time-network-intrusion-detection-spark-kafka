# Network Intrusion Detection Dataset Preprocessing

This directory contains preprocessing scripts for three network intrusion detection datasets: CIC-IDS 2017, CIC-IDS 2018, and UNSW-NB15.

## Overview

The preprocessing pipeline performs comprehensive data cleaning, feature engineering, and standardization using PySpark to handle large-scale datasets efficiently.

## Features

### Preprocessing Steps

1. **Data Loading**: Load multiple CSV files and combine them
2. **Column Name Standardization**: Clean and normalize column names
3. **Duplicate Removal**: Remove duplicate rows
4. **Missing Value Handling**: Fill or remove missing values
5. **Infinite Value Handling**: Replace infinite values
6. **Categorical Encoding**: StringIndexer for categorical features
7. **Feature Scaling**: StandardScaler for normalization
8. **Class Imbalance Handling**: Calculate and assign sample weights
9. **Binary Label Creation**: Create binary labels (Normal vs Attack)
10. **Parquet Export**: Save processed data in efficient Parquet format

### Class Imbalance Handling

The major issue addressed in this pipeline is **class imbalance**. The solution includes:

- **Class Weight Calculation**: Weights calculated as `max_count / class_count` (inverse frequency)
- **Sample Weight Column**: Each row assigned a weight based on its class
- **Detailed Logging**: Class distribution and weights logged for transparency
- **Binary Labels**: Support for both binary and multi-class classification

## File Structure

```
scripts/
├── preprocessing_utils.py          # Utility functions for preprocessing
├── preprocess_cicids2017.py        # CIC-IDS 2017 preprocessing
├── preprocess_cicids2018.py        # CIC-IDS 2018 preprocessing
├── preprocess_unsw_nb15.py         # UNSW-NB15 preprocessing
├── run_preprocessing.py            # Main orchestrator script
└── PREPROCESSING_README.md         # This file
```

## Usage

### Option 1: Run All Datasets

```bash
# Using Python directly
python scripts/run_preprocessing.py

# Or using Spark Submit
spark-submit scripts/run_preprocessing.py
```

### Option 2: Run Individual Datasets

```bash
# CIC-IDS 2017
python scripts/preprocess_cicids2017.py

# CIC-IDS 2018
python scripts/preprocess_cicids2018.py

# UNSW-NB15
python scripts/preprocess_unsw_nb15.py
```

## Requirements

- Python 3.7+
- PySpark 3.x
- Java 8 or 11 (for Spark)

Install dependencies:
```bash
pip install pyspark
```

## Input Data Structure

The scripts expect data in the following structure:

```
data/
├── CSE-CIC-IDS2017/
│   ├── Monday-WorkingHours.pcap_ISCX.csv
│   ├── Tuesday-WorkingHours.pcap_ISCX.csv
│   └── ... (other CSV files)
├── CSE-CIC-IDS2018/
│   ├── 02-14-2018.csv
│   ├── 02-15-2018.csv
│   └── ... (other CSV files)
└── UNSW-NB15/
    ├── UNSW_NB15_training-set.csv
    ├── UNSW_NB15_testing-set.csv
    └── ... (other CSV files)
```

## Output Structure

Preprocessed data is saved in:

```
data/preprocessed/
├── cicids2017_preprocessed.parquet/     # Parquet directory
├── cicids2017_metadata.txt              # Metadata file
├── cicids2018_preprocessed.parquet/     # Parquet directory
├── cicids2018_metadata.txt              # Metadata file
├── unsw_nb15_preprocessed.parquet/      # Parquet directory
├── unsw_nb15_metadata.txt               # Metadata file
└── preprocessing_summary.txt            # Overall summary
```

## Output Columns

Each preprocessed dataset includes:

- **Original Features**: All numeric features (cleaned and scaled)
- **label**: Original label (text format)
- **binary_label**: Binary classification label (0=Normal, 1=Attack)
- **sample_weight**: Weight for handling class imbalance
- **features**: Vector of original features
- **scaled_features**: Standardized feature vector

## Loading Preprocessed Data

### Using PySpark

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("LoadData").getOrCreate()

# Load preprocessed data
df = spark.read.parquet("data/preprocessed/cicids2017_preprocessed.parquet")

# Access features and labels
df.select("scaled_features", "binary_label", "sample_weight").show()
```

### Using Pandas

```python
import pandas as pd

# Load preprocessed data
df = pd.read_parquet("data/preprocessed/cicids2017_preprocessed.parquet")

# Access sample weights for training
sample_weights = df['sample_weight'].values
```

## Configuration

### Spark Configuration

The default Spark configuration can be modified in `preprocessing_utils.py`:

```python
spark = SparkSession.builder \
    .appName("NetworkIDSPreprocessing") \
    .config("spark.driver.memory", "4g") \
    .config("spark.executor.memory", "4g") \
    .config("spark.sql.shuffle.partitions", "200") \
    .getOrCreate()
```

### Missing Value Strategy

Change the strategy in individual preprocessing scripts:

```python
# Options: "drop", "fill_zero", "fill_mean"
df = handle_missing_values(df, strategy="fill_zero", threshold=0.5)
```

## Logging

All preprocessing activities are logged to:
- Console output (INFO level)
- `preprocessing.log` file (when using run_preprocessing.py)

## Performance Considerations

- **Memory**: Default configuration uses 4GB for driver and executor
- **Partitions**: Uses 200 shuffle partitions by default
- **Adaptive Query Execution**: Enabled for optimization
- **Processing Time**: Varies by dataset size (typically 5-30 minutes per dataset)

## Dataset-Specific Notes

### CIC-IDS 2017
- Contains 8 CSV files
- Label column: "Label" (renamed to "label")
- Normal class: "BENIGN"
- Attack types: DDoS, PortScan, Bot, Infiltration, etc.

### CIC-IDS 2018
- Contains 10 CSV files
- Label column: "Label" (renamed to "label")
- Normal class: "Benign"
- Includes timestamp column (dropped during preprocessing)

### UNSW-NB15
- Contains training and testing sets, plus raw files
- Label column: "label" (binary) and "attack_cat" (multi-class)
- Normal class: "Normal"
- Has categorical features: proto, service, state

## Troubleshooting

### Out of Memory Errors
Increase Spark memory in `preprocessing_utils.py`:
```python
.config("spark.driver.memory", "8g") \
.config("spark.executor.memory", "8g")
```

### Slow Processing
Reduce data size or increase partitions:
```python
.config("spark.sql.shuffle.partitions", "400")
```

### Column Not Found Errors
Check the original CSV files for column names and update the scripts accordingly.

## License

This preprocessing pipeline is part of the real-time network intrusion detection project.

## Contact

For issues or questions, please refer to the main project README.
