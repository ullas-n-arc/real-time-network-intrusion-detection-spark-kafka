# 🛡️ Real-Time Network Intrusion Detection System

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![PySpark](https://img.shields.io/badge/PySpark-3.5.0-orange.svg)](https://spark.apache.org/)
[![Kafka](https://img.shields.io/badge/Kafka-7.5.0-black.svg)](https://kafka.apache.org/)
[![MongoDB](https://img.shields.io/badge/MongoDB-7.0-green.svg)](https://www.mongodb.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A production-ready **real-time Network Intrusion Detection System (NIDS)** that uses machine learning to detect cyber attacks as they happen. Built with **Apache Kafka**, **Apache Spark Structured Streaming**, **Spark MLlib**, and **MongoDB**.

## ✨ Highlights

| Feature | Description |
|---------|-------------|
| 🎯 **87-98% Accuracy** | High detection rates across benchmark datasets |
| ⚡ **Real-Time** | Sub-second latency with Spark Structured Streaming |
| 📊 **Multi-Dataset** | CIC-IDS 2017/2018, **UNSW-NB15** support |
| 🤖 **Dual Classification** | Binary (Attack/Benign) + Multi-class (10 Attack Types) |
| 🐳 **One-Command Deploy** | Fully containerized with Docker Compose |
| 📈 **Live Dashboard** | Real-time visualization of threats |

---

## 🚀 Quick Start

### One Command to Run Everything

```bash
# Clone and enter directory
git clone https://github.com/ullas-n-arc/real-time-network-intrusion-detection-spark-kafka.git
cd real-time-network-intrusion-detection-spark-kafka

# Make script executable and run
chmod +x run.sh
./run.sh start
```

That's it! The script handles everything:
- ✅ Checks dependencies (Docker, Python, PySpark)
- ✅ Starts Docker services (Kafka, MongoDB, Kafka UI, Mongo Express, Grafana)
- ✅ Creates Kafka topics (`network_logs`, `intrusion_alerts`)
- ✅ Launches Spark ML streaming consumer
- ✅ Starts traffic simulator (Kafka producer)
- ✅ Opens dashboard

### Access the System

| Service | URL | Description |
|---------|-----|-------------|
| 📊 **Dashboard** | http://localhost:5000 | Real-time alerts & stats |
| 📡 **Kafka UI** | http://localhost:8080 | Monitor Kafka topics |
| 🗄️ **MongoDB UI** | http://localhost:8081 | Browse alerts database |
| 📈 **Grafana** | http://localhost:3000 | Custom dashboards (admin/admin123) |

### Script Commands

```bash
./run.sh start              # Start entire pipeline
./run.sh stop               # Stop all services
./run.sh restart            # Restart everything
./run.sh status             # Check component status
./run.sh logs               # View recent logs
./run.sh demo               # 2-minute demo mode
./run.sh clean              # Clear checkpoints
```

### Options

```bash
./run.sh start --data-source unsw        # Use UNSW-NB15 dataset (default)
./run.sh start --data-source cicids2017  # Use CIC-IDS 2017 dataset
./run.sh start --batch-size 100          # 100 records per batch
./run.sh start --delay 0.5               # 0.5s between batches
./run.sh start --output mongodb          # Only write to MongoDB
./run.sh start --output all              # Write to console + MongoDB (default)
```

---

## 📐 Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Network Data   │────▶│  Kafka Broker   │────▶│ Spark Streaming │
│  (CSV/Parquet)  │     │  (Topic Queue)  │     │ (ML Inference)  │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                        ┌─────────────────┐              │
                        │   Dashboard     │◀─────────────┤
                        │   (Flask)       │              │
                        └─────────────────┘              ▼
                                                ┌─────────────────┐
                                                │    MongoDB      │
                                                │   (Alerts)      │
                                                └─────────────────┘
```

**Data Flow:**
1. **Kafka Producer** reads network traffic data (CSV) and streams to Kafka topic
2. **Kafka Broker** queues messages in `network_logs` topic
3. **Spark Streaming** consumes data, applies ML models for real-time classification
4. **Alerts** are stored in MongoDB and displayed on the Flask dashboard

---

## 📊 Datasets

This system supports three major network intrusion detection datasets:

### UNSW-NB15 (Primary Dataset)

| Property | Value |
|----------|-------|
| **Source** | University of New South Wales |
| **Records** | ~2.5 million |
| **Features** | 39 numeric features |
| **Attack Types** | 9 categories + Normal |
| **Download** | [UNSW-NB15 Dataset](https://research.unsw.edu.au/projects/unsw-nb15-dataset) |

**Attack Categories in UNSW-NB15:**

| ID | Attack Type | Description |
|----|-------------|-------------|
| 0 | **Normal** | Benign network traffic |
| 1 | **Fuzzers** | Attempting to crash programs by feeding random data |
| 2 | **Analysis** | Port scans, spam, HTML file penetrations |
| 3 | **Backdoor** | Unauthorized remote access bypassing authentication |
| 4 | **DoS** | Denial of Service attacks |
| 5 | **Exploits** | Exploiting known vulnerabilities |
| 6 | **Generic** | Techniques that work against all block ciphers |
| 7 | **Reconnaissance** | Information gathering attacks |
| 8 | **Shellcode** | Small code used as payload in exploitation |
| 9 | **Worms** | Self-replicating malware |

**Features (39 numeric):**
```
dur, spkts, dpkts, sbytes, dbytes, rate, sttl, dttl, sload, dload, 
sloss, dloss, sinpkt, dinpkt, sjit, djit, swin, stcpb, dtcpb, dwin, 
tcprtt, synack, ackdat, smean, dmean, trans_depth, response_body_len, 
ct_srv_src, ct_state_ttl, ct_dst_ltm, ct_src_dport_ltm, ct_dst_sport_ltm, 
ct_dst_src_ltm, is_ftp_login, ct_ftp_cmd, ct_flw_http_mthd, ct_src_ltm, 
ct_srv_dst, is_sm_ips_ports
```

### CIC-IDS 2017/2018

| Property | CIC-IDS 2017 | CIC-IDS 2018 |
|----------|--------------|--------------|
| **Source** | Canadian Institute for Cybersecurity |
| **Records** | 2.8 million | 16 million |
| **Features** | 78 | 77 |
| **Attack Types** | 14 types | 14 types |
| **Download** | [CIC-IDS 2017](https://www.unb.ca/cic/datasets/ids-2017.html) | [CIC-IDS 2018](https://www.unb.ca/cic/datasets/ids-2018.html) |

---

## 🤖 ML Models

### Model Performance

#### UNSW-NB15 Models

| Model | Task | Accuracy | F1 Score | AUC-ROC | AUC-PR |
|-------|------|----------|----------|---------|--------|
| **GBT Binary** | Attack/Normal | **87.13%** | 0.870 | **0.943** | 0.950 |
| RF Binary | Attack/Normal | 79.08% | 0.791 | 0.905 | 0.922 |
| RF Multiclass | 10 Classes | 67.66% | 0.713 | - | - |

#### CIC-IDS Models

| Model | Task | Accuracy | F1 Score | AUC-ROC |
|-------|------|----------|----------|---------|
| **GBT Binary** | Attack/Normal | **98.17%** | 0.982 | 0.985 |
| RF Binary | Attack/Normal | 97.15% | 0.972 | 0.976 |

### Two-Stage Detection Pipeline

For **UNSW-NB15**, the system uses a two-stage detection approach:

1. **Stage 1: Binary Detection** (GBT Model)
   - Determines if traffic is Attack or Normal
   - High accuracy (87%) with excellent AUC-ROC (0.943)
   
2. **Stage 2: Attack Classification** (RF Multiclass)
   - Only triggered if Stage 1 detects an attack
   - Classifies into one of 9 attack categories

### Severity Classification

| Severity | Attack Types | Color |
|----------|-------------|-------|
| 🟢 **NONE** | Normal, Benign | Green |
| 🟡 **LOW** | Reconnaissance, Analysis | Yellow |
| 🟠 **MEDIUM** | Fuzzers, DoS, Exploits, Generic | Orange |
| 🔴 **HIGH** | Backdoor, Shellcode, Worms | Red |
| 🔥 **CRITICAL** | Infiltration, Botnet | Dark Red |

---

## 📁 Project Structure

```
real-time-network-intrusion-detection-spark-kafka/
├── run.sh                       # 🚀 Master automation script
│
├── config/                      # ⚙️ Configuration
│   ├── config.py               # Kafka, MongoDB, Spark, ML settings
│   └── scaler_paths.py         # Dataset-specific model paths
│
├── streaming/                   # 🌊 Real-time Components
│   ├── spark_streaming.py      # Spark ML consumer (main detection)
│   ├── kafka_producer.py       # Network traffic simulator
│   └── alert_storage.py        # MongoDB alert writer
│
├── dashboard/                   # 📊 Web Interface
│   └── app.py                  # Flask REST API & Dashboard UI
│
├── models/                      # 🤖 Trained ML Models
│   ├── unsw_gbt_binary_classifier/    # UNSW GBT binary (87% acc)
│   ├── unsw_rf_binary_classifier/     # UNSW RF binary (79% acc)
│   ├── unsw_rf_multiclass_classifier/ # UNSW RF multiclass (67% acc)
│   ├── rf_binary_classifier/          # CIC-IDS RF binary
│   ├── gbt_binary_classifier/         # CIC-IDS GBT binary
│   ├── unsw_training_results.json     # UNSW model metrics
│   ├── unsw_feature_names.json        # UNSW feature list (39)
│   └── unsw_label_mapping.json        # Attack type mappings
│
├── scripts/                     # 🔧 Preprocessing & Training
│   ├── preprocess_unsw_nb15.py        # UNSW-NB15 preprocessing
│   ├── preprocess_cicids2017.py       # CIC-IDS 2017 preprocessing
│   ├── preprocess_cicids2018.py       # CIC-IDS 2018 preprocessing
│   ├── preprocessing_utils.py         # Shared preprocessing functions
│   ├── run_preprocessing.py           # Interactive preprocessing runner
│   ├── train_model_example.py         # Model training example
│   └── diagnose_model.py              # Model debugging utility
│
├── notebooks/                   # 📓 Jupyter Notebooks
│   ├── unsw_model_training.ipynb      # UNSW model training notebook
│   ├── model_training.ipynb           # CIC-IDS model training
│   ├── preprocessing_colab.ipynb      # Google Colab preprocessing
│   ├── label_harmonization.ipynb      # Label standardization
│   └── visualization.ipynb            # Data visualization
│
├── data/                        # 📂 Datasets (gitignored)
│   ├── UNSW-NB15/                     # UNSW-NB15 raw CSV files
│   ├── CSE-CIC-IDS2017/               # CIC-IDS 2017 raw files
│   ├── training/                       # Training split
│   ├── testing/                        # Testing split
│   └── preprocessed/                   # Ready-to-stream files
│
├── docker/                      # 🐳 Docker Configuration
│   ├── mongo-init.js                  # MongoDB initialization
│   └── grafana/                       # Grafana dashboards
│
├── docker-compose.yml           # Infrastructure stack
├── Dockerfile.spark             # Spark container (optional)
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# Kafka
export KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
export KAFKA_TOPIC="network_logs"

# MongoDB  
export MONGODB_HOST="localhost"
export MONGODB_PORT="27017"
export MONGODB_DATABASE="nids_db"

# Spark
export SPARK_MASTER="local[*]"
```

### Key Configuration Files

#### `config/config.py`
- `KAFKA_CONFIG`: Broker address, topic names
- `MONGODB_CONFIG`: Connection settings
- `SPARK_CONFIG`: Memory, parallelism settings
- `UNSW_FEATURE_CONFIG`: 39 UNSW-NB15 features
- `UNSW_ATTACK_TYPE_MAPPING`: Attack label mappings
- `ALERT_CONFIG`: Severity classifications

#### `config/scaler_paths.py`
- Dataset-specific model and scaler paths

---

## 🔧 Manual Setup

If you prefer manual control over each component:

### 1. Start Infrastructure

```bash
docker-compose up -d
```

### 2. Start Spark Streaming (Terminal 1)

```bash
# For UNSW-NB15 dataset
python3 streaming/spark_streaming.py --data-source unsw --output all

# For CIC-IDS 2017
python3 streaming/spark_streaming.py --data-source cicids2017 --output all
```

### 3. Start Kafka Producer (Terminal 2)

```bash
# Stream UNSW-NB15 data
python3 streaming/kafka_producer.py --data-source unsw --batch-size 50 --delay 1

# Stream from testing set
python3 streaming/kafka_producer.py --data-source unsw2 --batch-size 100 --delay 0.5
```

### 4. Start Dashboard (Terminal 3)

```bash
python3 dashboard/app.py
```

---

## 📊 Data Preprocessing

### UNSW-NB15 Preprocessing

```bash
# Option 1: Run directly
python scripts/preprocess_unsw_nb15.py

# Option 2: Interactive menu
python scripts/run_preprocessing.py
```

**Preprocessing Steps:**
1. Load UNSW-NB15 training and testing CSV files
2. Clean column names
3. Drop unnecessary columns (IPs, timestamps)
4. Encode categorical features (proto, service, state)
5. Handle missing/infinite values
6. Create binary labels
7. Calculate class weights (for imbalanced data)
8. Scale features using StandardScaler
9. Export to Parquet format

### CIC-IDS Preprocessing

```bash
python scripts/preprocess_cicids2017.py
python scripts/preprocess_cicids2018.py
```

For large datasets (16M+ records), use Google Colab:
- Open `notebooks/preprocessing_colab.ipynb`
- Upload to Google Colab
- Run with GPU runtime

---

## 🐛 Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| Kafka connection refused | `docker-compose restart kafka` |
| MongoDB write errors | Check `docker logs nids-mongodb` |
| No data in dashboard | Ensure `--output all` is set |
| Model not found | Check `models/` directory exists |
| UNSW data not loading | Verify CSV files in `data/UNSW-NB15/` |
| Feature mismatch | Models expect 39 features for UNSW |

### Useful Commands

```bash
# Check all service status
./run.sh status

# View logs
./run.sh logs

# Clean restart
./run.sh clean && ./run.sh start

# Check MongoDB alerts
docker exec nids-mongodb mongosh nids_db --eval "db.alerts.countDocuments({})"

# List Kafka topics
docker exec nids-kafka kafka-topics --bootstrap-server localhost:9092 --list

# Monitor Kafka consumer
docker exec nids-kafka kafka-console-consumer \
    --bootstrap-server localhost:9092 \
    --topic network_logs --from-beginning --max-messages 5
```

### Model Diagnostics

```bash
# Check model structure and features
python scripts/diagnose_model.py
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [PREPROCESSING_GUIDE.md](PREPROCESSING_GUIDE.md) | Detailed preprocessing documentation |
| [STREAMING_GUIDE.md](STREAMING_GUIDE.md) | Streaming pipeline details |
| [PREPROCESSING_SUMMARY.md](PREPROCESSING_SUMMARY.md) | Quick preprocessing reference |
| [scripts/PREPROCESSING_README.md](scripts/PREPROCESSING_README.md) | Script-level documentation |

---

## 🔬 Model Training

### Train UNSW-NB15 Models

Use the Jupyter notebook for interactive training:
```bash
jupyter notebook notebooks/unsw_model_training.ipynb
```

Or use the script:
```bash
python scripts/train_model_example.py
```

### Model Architecture

**Binary Classification (GBT):**
- Algorithm: Gradient Boosted Trees
- Features: 39 numeric features
- Output: Attack (1) or Normal (0)
- Best for: Initial threat detection

**Multiclass Classification (RF):**
- Algorithm: Random Forest
- Features: 39 numeric features  
- Output: 10 classes (Normal + 9 attack types)
- Best for: Attack categorization

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push: `git push origin feature/amazing`
5. Open Pull Request

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file.

---

## 👤 Author

**Ullas N** - [@ullas-n-arc](https://github.com/ullas-n-arc)

---

## 🙏 Acknowledgments

- **UNSW-NB15 Dataset**: Moustafa, Nour, and Jill Slay. "UNSW-NB15: a comprehensive data set for network intrusion detection systems." Military Communications and Information Systems Conference (MilCIS), 2015.
- **CIC-IDS Datasets**: Canadian Institute for Cybersecurity, University of New Brunswick.

---

<div align="center">

**⭐ Star this repo if you find it useful!**

Made with ❤️ for the cybersecurity community

</div>
