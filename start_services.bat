@echo off
REM Start the Real-Time Network Intrusion Detection System
REM This script starts all required services

echo ============================================================
echo  Network Intrusion Detection System - Startup Script
echo ============================================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

echo [1/4] Starting infrastructure services (Kafka, MongoDB)...
docker-compose up -d zookeeper kafka mongodb
timeout /t 10 /nobreak >nul

echo [2/4] Starting web interfaces (Kafka UI, Mongo Express)...
docker-compose up -d kafka-ui mongo-express

echo [3/4] Creating Kafka topics...
docker exec nids-kafka kafka-topics --create --if-not-exists --topic network_logs --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
docker exec nids-kafka kafka-topics --create --if-not-exists --topic intrusion_alerts --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1

echo.
echo ============================================================
echo  Services Started Successfully!
echo ============================================================
echo.
echo  Access Points:
echo  - Kafka UI:        http://localhost:8080
echo  - Mongo Express:   http://localhost:8081 (admin/admin123)
echo  - Grafana:         http://localhost:3000 (admin/admin123)
echo.
echo  Next Steps:
echo  1. Start the Kafka producer: python streaming/kafka_producer.py
echo  2. Start Spark streaming: spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 streaming/spark_streaming.py
echo  3. Start the dashboard: python dashboard/app.py
echo.
echo  To stop all services: docker-compose down
echo ============================================================

pause
