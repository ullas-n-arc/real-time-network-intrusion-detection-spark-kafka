# Real-Time Network Intrusion Detection System

## Streaming Pipeline Documentation

This document describes how to set up and run the real-time intrusion detection pipeline.

## Architecture

```
 +-----------------------+
 |   Network Traffic     |
 | (Simulated from CIC)  |
 +-----------+-----------+
             |
       Kafka Producer
             |
   Kafka Topic: network_logs
             |
 +--------+--------+
 | Spark Structured|
 |    Streaming    |
 +--------+--------+
             |
   Feature Engineering + ML Inference
             |
     Intrusion Prediction
             |
 +--------+--------+
 |   MongoDB       |
 | (Alert Storage) |
 +--------+--------+
             |
       Dashboard
   (Flask Web App)
```

## Prerequisites

1. **Docker & Docker Compose** - For running Kafka, MongoDB, and supporting services
2. **Python 3.8+** - With required packages
3. **Java 8/11** - Required for PySpark
4. **Apache Spark 3.x** - For streaming processing

## Quick Start

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Infrastructure Services

```bash
# Windows
start_services.bat

# Linux/Mac
chmod +x start_services.sh
./start_services.sh
```

This starts:
- **Zookeeper** (port 2181) - Kafka coordination
- **Kafka** (port 9092) - Message broker
- **MongoDB** (port 27017) - Alert storage
- **Kafka UI** (port 8080) - Kafka monitoring
- **Mongo Express** (port 8081) - MongoDB web UI
- **Grafana** (port 3000) - Dashboards

### 3. Copy Trained Models

Make sure your trained models are in the `models/` directory:
```
models/
├── rf_binary_classifier/
├── gbt_binary_classifier/
├── rf_multiclass_classifier/
└── rf_multiclass_improved/
```

If models were trained in Google Colab, download them and place in this directory.

### 4. Start the Streaming Pipeline

Open three terminal windows:

**Terminal 1 - Start Spark Streaming Consumer:**
```bash
spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 streaming/spark_streaming.py --output all
```

**Terminal 2 - Start Kafka Producer (Simulates Network Traffic):**
```bash
python streaming/kafka_producer.py --data-source cicids2017 --batch-size 50 --delay 2
```

**Terminal 3 - Start Dashboard:**
```bash
python dashboard/app.py --port 5000
```

### 5. Access the Dashboard

- **NIDS Dashboard**: http://localhost:5000
- **Kafka UI**: http://localhost:8080
- **MongoDB UI**: http://localhost:8081 (admin/admin123)
- **Grafana**: http://localhost:3000 (admin/admin123)

## Components

### 1. Kafka Producer (`streaming/kafka_producer.py`)

Simulates real-time network traffic by reading from CIC-IDS datasets.

```bash
python streaming/kafka_producer.py --help

Options:
  --data-source     Dataset to use (cicids2017, cicids2018, unsw)
  --bootstrap-servers  Kafka servers (default: localhost:9092)
  --topic           Kafka topic (default: network_logs)
  --batch-size      Records per batch (default: 100)
  --delay           Delay between batches in seconds (default: 1.0)
  --max-records     Maximum records to send (default: unlimited)
```

### 2. Spark Streaming Job (`streaming/spark_streaming.py`)

Processes network traffic in real-time using Spark Structured Streaming.

```bash
spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
    streaming/spark_streaming.py --output all

Options:
  --output    Where to write results: console, mongodb, kafka, all
```

### 3. Alert Storage (`streaming/alert_storage.py`)

MongoDB integration for storing and querying intrusion alerts.

### 4. Dashboard (`dashboard/app.py`)

Flask web application with REST API and real-time dashboard.

**API Endpoints:**
- `GET /` - Dashboard home page
- `GET /api/health` - Health check
- `GET /api/alerts` - Get recent alerts
- `GET /api/alerts/stats` - Get alert statistics
- `GET /api/alerts/timeline` - Get attack timeline

## Configuration

Edit `config/config.py` to customize:

- Kafka connection settings
- MongoDB connection settings
- Model paths
- Feature configuration
- Alert thresholds

Environment variables can override defaults:
```bash
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export MONGODB_HOST=localhost
export MONGODB_PORT=27017
```

## Project Structure

```
real-time-network-intrusion-detection-spark-kafka/
├── config/
│   ├── __init__.py
│   └── config.py              # Configuration settings
├── streaming/
│   ├── __init__.py
│   ├── kafka_producer.py      # Kafka producer (Module 3)
│   ├── spark_streaming.py     # Spark streaming job (Module 4)
│   └── alert_storage.py       # MongoDB integration
├── dashboard/
│   ├── __init__.py
│   └── app.py                 # Flask dashboard
├── docker/
│   ├── mongo-init.js          # MongoDB initialization
│   └── grafana/
│       └── provisioning/      # Grafana config
├── models/                    # Trained ML models
├── data/                      # CIC-IDS datasets
├── docker-compose.yml         # Infrastructure services
├── requirements.txt           # Python dependencies
├── start_services.bat         # Windows startup script
└── start_services.sh          # Linux/Mac startup script
```

## Troubleshooting

### Kafka Connection Issues
```bash
# Check if Kafka is running
docker ps | grep kafka

# Check Kafka logs
docker logs nids-kafka
```

### MongoDB Connection Issues
```bash
# Check if MongoDB is running
docker ps | grep mongodb

# Test connection
python -c "from pymongo import MongoClient; MongoClient('localhost', 27017).admin.command('ping')"
```

### Spark Streaming Issues
```bash
# Check if models exist
ls models/

# Run with more verbose logging
spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
    --conf spark.driver.extraJavaOptions=-Dlog4j.configuration=log4j.properties \
    streaming/spark_streaming.py
```

### Model Not Found
If models were trained in Google Colab:
1. Download the model folders from Google Drive
2. Place them in the `models/` directory
3. Ensure the folder structure matches `MODEL_PATHS` in `config/config.py`

## Performance Tuning

### Kafka Producer
- Increase `--batch-size` for higher throughput
- Decrease `--delay` for faster simulation

### Spark Streaming
- Adjust `spark.sql.shuffle.partitions` in config
- Tune `trigger_interval` for latency vs throughput tradeoff

### MongoDB
- Add indexes for frequently queried fields
- Consider time-based partitioning for large datasets

## Next Steps

1. **Real Network Integration**: Replace Kafka producer with real network traffic capture
2. **Enhanced Dashboard**: Add Grafana dashboards for detailed visualization
3. **Alerting**: Integrate with Slack/Email for critical alerts
4. **Model Updates**: Implement online learning for model updates
