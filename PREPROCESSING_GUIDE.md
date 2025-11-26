# Data Preprocessing Quick Start Guide

## Overview

This project includes comprehensive PySpark-based preprocessing pipelines for three network intrusion detection datasets:
- **CIC-IDS 2017** (CSE-CIC-IDS2017)
- **CIC-IDS 2018** (CSE-CIC-IDS2018)  
- **UNSW-NB15**

## Key Features

✅ **Class Imbalance Handling**: Automatic calculation and assignment of sample weights based on class distribution  
✅ **Complete Data Cleaning**: Missing values, infinite values, duplicates, and outliers  
✅ **Feature Engineering**: Standardization, scaling, categorical encoding  
✅ **Standardized Output**: Parquet format for efficient storage and fast loading  
✅ **Detailed Logging**: Complete visibility into preprocessing steps and class distributions  
✅ **Metadata Generation**: Automatic metadata files with feature lists and class weights  

## Prerequisites

1. **Python 3.7+**
2. **Apache Spark 3.x** (included in the `spark/` directory)
3. **PySpark library**

## Installation

### Step 1: Install PySpark

```bash
pip install pyspark
```

Or install all requirements:

```bash
pip install -r scripts/requirements.txt
```

### Step 2: Verify Spark Installation

The project includes Spark in the `spark/` directory. Verify it's accessible:

```bash
# Windows
.\spark\bin\spark-submit --version

# Linux/Mac
./spark/bin/spark-submit --version
```

## Running the Preprocessing

### Option 1: Preprocess All Datasets (Recommended)

Run the main orchestrator script to preprocess all three datasets:

```bash
cd d:\Coding\real-time-network-intrusion-detection-spark-kafka

# Using Python
python scripts/run_preprocessing.py

# Or using Spark Submit
spark\bin\spark-submit scripts\run_preprocessing.py
```

### Option 2: Preprocess Individual Datasets

Process specific datasets:

```bash
# CIC-IDS 2017 only
python scripts/preprocess_cicids2017.py

# CIC-IDS 2018 only
python scripts/preprocess_cicids2018.py

# UNSW-NB15 only
python scripts/preprocess_unsw_nb15.py
```

## Expected Output

After successful preprocessing, you'll find:

```
data/preprocessed/
├── cicids2017_preprocessed.parquet/     # Preprocessed CIC-IDS 2017
├── cicids2017_metadata.txt              # Feature list and class weights
├── cicids2018_preprocessed.parquet/     # Preprocessed CIC-IDS 2018
├── cicids2018_metadata.txt              # Feature list and class weights
├── unsw_nb15_preprocessed.parquet/      # Preprocessed UNSW-NB15
├── unsw_nb15_metadata.txt               # Feature list and class weights
└── preprocessing_summary.txt            # Overall summary
```

## Preprocessing Steps Performed

1. ✅ **Column Name Standardization** - Clean and normalize column names
2. ✅ **Duplicate Removal** - Remove duplicate rows
3. ✅ **Infinite Value Handling** - Replace infinite values with None
4. ✅ **Missing Value Imputation** - Fill with zeros or drop columns
5. ✅ **Categorical Encoding** - StringIndexer for categorical features
6. ✅ **Binary Label Creation** - Create binary labels (Normal=0, Attack=1)
7. ✅ **Class Weight Calculation** - Calculate inverse frequency weights
8. ✅ **Sample Weight Assignment** - Assign weights to each sample
9. ✅ **Feature Scaling** - StandardScaler for normalization
10. ✅ **Parquet Export** - Save in efficient columnar format

## Class Imbalance Solution

The preprocessing pipeline addresses class imbalance through:

### 1. Class Weight Calculation
```python
weight = max_count / class_count
```

### 2. Sample Weight Column
Each row receives a weight based on its class label. Minority classes get higher weights.

### 3. Example Class Distribution Output
```
==================================================
CLASS DISTRIBUTION:
==================================================
Class: benign                    | Count:    2273097 | 83.15% | Weight: 1.0000
Class: ddos                      | Count:     128027 |  4.68% | Weight: 17.7559
Class: portscan                  | Count:     158930 |  5.81% | Weight: 14.3030
Class: bot                       | Count:       1966 |  0.07% | Weight: 1155.9970
==================================================
```

## Loading Preprocessed Data

### Using the Example Script

```bash
python scripts/load_preprocessed_example.py
```

### In Your Code

```python
from pyspark.sql import SparkSession

# Create Spark session
spark = SparkSession.builder \
    .appName("LoadData") \
    .config("spark.driver.memory", "4g") \
    .getOrCreate()

# Load preprocessed data
df = spark.read.parquet("data/preprocessed/cicids2017_preprocessed.parquet")

# Access features and labels with weights
training_data = df.select("scaled_features", "binary_label", "sample_weight")

# Use in model training
from pyspark.ml.classification import LogisticRegression

lr = LogisticRegression(
    featuresCol='scaled_features',
    labelCol='binary_label',
    weightCol='sample_weight',  # Important: Use sample weights!
    maxIter=100
)

model = lr.fit(training_data)
```

## Output Columns

Each preprocessed dataset includes:

| Column | Description |
|--------|-------------|
| `{feature_name}` | Original numeric features (multiple columns) |
| `label` | Original text label (e.g., "benign", "ddos") |
| `binary_label` | Binary label (0=Normal, 1=Attack) |
| `sample_weight` | Weight for handling class imbalance |
| `features` | Vector of original features (for PySpark ML) |
| `scaled_features` | Standardized feature vector (recommended for models) |

## Processing Time Estimates

| Dataset | Approximate Time | Rows |
|---------|-----------------|------|
| CIC-IDS 2017 | 10-20 minutes | ~2.8M |
| CIC-IDS 2018 | 15-30 minutes | ~3.5M |
| UNSW-NB15 | 5-10 minutes | ~250K |

*Times may vary based on system resources*

## Troubleshooting

### Out of Memory Errors

Edit `scripts/preprocessing_utils.py` and increase memory:

```python
spark = SparkSession.builder \
    .config("spark.driver.memory", "8g") \
    .config("spark.executor.memory", "8g") \
    .getOrCreate()
```

### Slow Processing

Increase parallelism in `preprocessing_utils.py`:

```python
.config("spark.sql.shuffle.partitions", "400")
```

### File Not Found

Verify your data is in the correct location:
```
data/
├── CSE-CIC-IDS2017/
├── CSE-CIC-IDS2018/
└── UNSW-NB15/
```

## Next Steps

After preprocessing:

1. **Load the data** using the example script
2. **Train models** using the `scaled_features` and `sample_weight` columns
3. **Evaluate** on test sets with proper class weight consideration
4. **Deploy** with Kafka and Spark Streaming (see main README)

## Additional Documentation

- **Detailed preprocessing guide**: `scripts/PREPROCESSING_README.md`
- **Utility functions**: `scripts/preprocessing_utils.py`
- **Example usage**: `scripts/load_preprocessed_example.py`

## Support

For issues or questions:
1. Check the logs in `preprocessing.log`
2. Review metadata files in `data/preprocessed/`
3. Refer to the detailed README in `scripts/PREPROCESSING_README.md`

---

**Happy Training! 🚀**
