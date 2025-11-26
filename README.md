# Real-Time Network Intrusion Detection System

A real-time Network Intrusion Detection System (NIDS) built using **Apache Kafka**, **Apache Spark Structured Streaming**, and **Spark MLlib**. This system analyzes live network traffic streams, detects malicious activities using machine learning, and provides real-time alerts.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![PySpark](https://img.shields.io/badge/PySpark-3.5.7-orange.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Datasets](#datasets)
- [Installation](#installation)
- [Data Preprocessing](#data-preprocessing)
- [Model Training](#model-training)
- [Real-Time Detection](#real-time-detection)
- [Results](#results)
- [Contributing](#contributing)

## 🎯 Overview

This project implements a complete machine learning pipeline for network intrusion detection:

1. **Data Preprocessing**: Clean, transform, and prepare network traffic data from multiple benchmark datasets
2. **Model Training**: Train ML models (Random Forest, Gradient Boosting, etc.) on preprocessed data
3. **Real-Time Detection**: Deploy models for streaming inference using Kafka and Spark Streaming

## ✨ Features

- **Multi-Dataset Support**: Works with CIC-IDS 2017, CIC-IDS 2018, and UNSW-NB15 datasets
- **Class Imbalance Handling**: Implements inverse frequency sample weights for imbalanced attack classes
- **Optimized Preprocessing**: PySpark-based distributed processing for large-scale data
- **Binary & Multi-Class Detection**: Supports both attack/benign classification and specific attack type identification
- **Cloud-Ready**: Google Colab notebook for cloud-based preprocessing
- **Checkpoint Recovery**: Resume preprocessing if session disconnects

## 📁 Project Structure

```
real-time-network-intrusion-detection-spark-kafka/
├── data/                           # Raw datasets (not tracked in git)
│   ├── CSE-CIC-IDS2017/           # CIC-IDS 2017 CSV files
│   ├── CSE-CIC-IDS2018/           # CIC-IDS 2018 CSV files
│   └── UNSW-NB15/                 # UNSW-NB15 CSV files
├── models/                         # Trained ML models
├── notebooks/
│   └── preprocessing_colab.ipynb  # Google Colab preprocessing notebook
├── scripts/
│   ├── preprocessing_utils.py     # Utility functions for preprocessing
│   ├── preprocess_cicids2017.py   # CIC-IDS 2017 preprocessing script
│   ├── preprocess_cicids2018.py   # CIC-IDS 2018 preprocessing script
│   ├── preprocess_unsw_nb15.py    # UNSW-NB15 preprocessing script
│   ├── run_preprocessing.py       # Main preprocessing runner
│   ├── load_preprocessed_example.py  # Example: loading preprocessed data
│   ├── train_model_example.py     # Example: training ML models
│   └── requirements.txt           # Python dependencies
├── streaming/                      # Spark Streaming components
├── training/                       # Model training scripts
├── utils/                          # Utility modules
├── run_preprocessing.bat          # Windows batch script
├── run_preprocessing.sh           # Linux/Mac shell script
└── README.md
```

## 📊 Datasets

This project uses three benchmark network intrusion detection datasets:

### CIC-IDS 2017
- **Size**: ~2.8 million records, 843 MB
- **Features**: 78 network flow features
- **Attack Types**: 14 types (DoS, DDoS, Brute Force, Web Attacks, Infiltration, Botnet, PortScan, Heartbleed)
- **Source**: [Canadian Institute for Cybersecurity](https://www.unb.ca/cic/datasets/ids-2017.html)

### CIC-IDS 2018
- **Size**: ~16 million records, 6.6 GB
- **Features**: 77 network flow features
- **Attack Types**: 14 types (similar to 2017 with updated attack scenarios)
- **Source**: [Canadian Institute for Cybersecurity](https://www.unb.ca/cic/datasets/ids-2018.html)

### UNSW-NB15
- **Size**: ~2.5 million records, 150 MB
- **Features**: 43 network features
- **Attack Types**: 9 categories (Fuzzers, Analysis, Backdoor, DoS, Exploits, Generic, Reconnaissance, Shellcode, Worms)
- **Source**: [UNSW Sydney](https://research.unsw.edu.au/projects/unsw-nb15-dataset)

## 🛠️ Installation

### Prerequisites
- Python 3.11+
- Java 17+ (for Spark)
- Apache Spark 3.5+

### Local Setup

```bash
# Clone the repository
git clone https://github.com/ullas-n-arc/real-time-network-intrusion-detection-spark-kafka.git
cd real-time-network-intrusion-detection-spark-kafka

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\Activate.ps1  # Windows PowerShell

# Install dependencies
pip install -r scripts/requirements.txt
```

### Google Colab Setup

For large datasets, use the Colab notebook:
1. Upload `notebooks/preprocessing_colab.ipynb` to Google Colab
2. Upload your datasets to Google Drive under `MyDrive/NetworkIDS/`
3. Run all cells sequentially

## 🔧 Data Preprocessing

### Preprocessing Pipeline

Each dataset goes through these steps:
1. **Column Cleaning**: Standardize column names (lowercase, remove special chars)
2. **Deduplication**: Remove duplicate records
3. **Missing Value Handling**: Fill with column means (optimized single-pass)
4. **Infinite Value Handling**: Replace inf/-inf with 0
5. **Binary Label Creation**: 0=benign, 1=attack
6. **Class Weight Calculation**: Inverse frequency weighting
7. **Feature Scaling**: StandardScaler normalization
8. **Parquet Export**: Save processed data

### Run Preprocessing

**Option 1: Google Colab (Recommended for large datasets)**
```
1. Open notebooks/preprocessing_colab.ipynb in Colab
2. Mount Google Drive with your data
3. Run all cells
4. Output saved to: /content/drive/MyDrive/NetworkIDS/output/
```

**Option 2: Local (requires sufficient disk space)**
```bash
# Windows
.\run_preprocessing.bat

# Linux/Mac
./run_preprocessing.sh

# Or directly with Python
python scripts/run_preprocessing.py
```

### Preprocessing Results

| Dataset | Records | Duplicates Removed | Features | Processing Time |
|---------|---------|-------------------|----------|-----------------|
| CIC-IDS 2017 | 2,830,743 | 308,381 | 78 | ~16 minutes |
| CIC-IDS 2018 | 16,232,943 | 433,253 | 77 | ~25 minutes |
| UNSW-NB15 | 257,673 | 0 | 43 | ~1 minute |

### Class Weights (for imbalance handling)

**CIC-IDS 2017:**
- Benign (0): 1.0
- Attack (1): 4.92

**UNSW-NB15:**
- Benign (0): 1.77
- Attack (1): 1.0

## 🤖 Model Training

### Loading Preprocessed Data

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("NIDS-Training") \
    .getOrCreate()

# Load preprocessed data
df = spark.read.parquet("path/to/cicids2017_preprocessed")

# Available columns:
# - features_scaled: Vector of scaled features
# - binary_label: 0=benign, 1=attack
# - sample_weight: Class weight for training
# - label: Original attack type string
```

### Training Example

```python
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml.evaluation import BinaryClassificationEvaluator

# Split data
train, test = df.randomSplit([0.8, 0.2], seed=42)

# Train model with sample weights
rf = RandomForestClassifier(
    featuresCol='features_scaled',
    labelCol='binary_label',
    weightCol='sample_weight',
    numTrees=100
)
model = rf.fit(train)

# Evaluate
predictions = model.transform(test)
evaluator = BinaryClassificationEvaluator(labelCol='binary_label')
auc = evaluator.evaluate(predictions)
print(f"AUC-ROC: {auc:.4f}")
```

## 🚀 Real-Time Detection

*(Coming soon)*

The streaming component will:
1. Ingest network traffic via Kafka
2. Apply preprocessing transformations
3. Run inference using trained models
4. Output alerts for detected intrusions

## 📈 Results

*(Model performance metrics will be added after training)*

## 🔮 Future Work

- [ ] Merge CIC-IDS 2017 + 2018 with unified label schema
- [ ] Multi-class classification for attack type identification
- [ ] Implement Kafka streaming pipeline
- [ ] Add real-time dashboard for monitoring
- [ ] Deploy with Docker/Kubernetes

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📚 References

1. Sharafaldin, I., Lashkari, A. H., & Ghorbani, A. A. (2018). Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic Characterization. ICISSP.
2. Moustafa, N., & Slay, J. (2015). UNSW-NB15: A Comprehensive Data Set for Network Intrusion Detection Systems. MilCIS.

## 👤 Author

**Ullas N**
- GitHub: [@ullas-n-arc](https://github.com/ullas-n-arc)
