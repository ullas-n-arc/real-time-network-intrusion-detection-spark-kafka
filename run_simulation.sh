#!/bin/bash
# =============================================================
#  NETWORK INTRUSION DETECTION SYSTEM - SIMULATION SCRIPT
#  Run this in GitHub Codespaces or any Linux environment
# =============================================================

set -e

echo "============================================================"
echo " 🛡️  Network Intrusion Detection System - Simulation"
echo "============================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Step 1: Check Docker
echo -e "${CYAN}[1/5] Checking Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker not found! Please install Docker first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker is available${NC}"

# Step 2: Install Python dependencies
echo -e "${CYAN}[2/5] Installing Python dependencies...${NC}"
pip install -q -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Step 3: Start Docker services
echo -e "${CYAN}[3/5] Starting Docker services (Kafka, MongoDB)...${NC}"
docker-compose up -d
echo "Waiting 30 seconds for services to initialize..."
sleep 30
echo -e "${GREEN}✓ Docker services running${NC}"

# Step 4: Create Kafka topics
echo -e "${CYAN}[4/5] Creating Kafka topics...${NC}"
docker exec nids-kafka kafka-topics --create --if-not-exists --topic network_logs --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 2>/dev/null || true
docker exec nids-kafka kafka-topics --create --if-not-exists --topic intrusion_alerts --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 2>/dev/null || true
echo -e "${GREEN}✓ Kafka topics created${NC}"

echo ""
echo "============================================================"
echo -e "${GREEN} ✅ SETUP COMPLETE!${NC}"
echo "============================================================"
echo ""
echo -e "${YELLOW}Now open 3 terminals and run:${NC}"
echo ""
echo -e "${CYAN}Terminal 1 - Spark Streaming (ML Consumer):${NC}"
echo "  spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 streaming/spark_streaming.py --output all"
echo ""
echo -e "${CYAN}Terminal 2 - Kafka Producer (Traffic Simulator):${NC}"
echo "  python streaming/kafka_producer.py --data-source cicids2017 --batch-size 50 --delay 1"
echo ""
echo -e "${CYAN}Terminal 3 - Dashboard:${NC}"
echo "  python dashboard/app.py"
echo ""
echo "============================================================"
echo -e "${GREEN}Access Points:${NC}"
echo "  📊 Dashboard:    http://localhost:5000"
echo "  📡 Kafka UI:     http://localhost:8080"
echo "  🗄️  MongoDB UI:   http://localhost:8081 (admin/admin123)"
echo "============================================================"
