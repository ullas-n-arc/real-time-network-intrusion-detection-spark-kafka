#!/bin/bash
# =============================================================
#  NETWORK INTRUSION DETECTION SYSTEM - MASTER RUNNER
#  One command to run the entire pipeline!
# =============================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Default configuration
DATA_SOURCE="${DATA_SOURCE:-unsw2}"
BATCH_SIZE="${BATCH_SIZE:-50}"
DELAY="${DELAY:-1}"
OUTPUT_MODE="${OUTPUT_MODE:-mongodb}"
DASHBOARD_PORT="${DASHBOARD_PORT:-5000}"

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Functions
print_banner() {
    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}🛡️  Real-Time Network Intrusion Detection System${NC}               ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}     ${MAGENTA}Spark + Kafka + MongoDB + ML Pipeline${NC}                      ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_usage() {
    echo -e "${BOLD}Usage:${NC}"
    echo "  ./run.sh [command] [options]"
    echo ""
    echo -e "${BOLD}Commands:${NC}"
    echo "  start       Start entire pipeline (default)"
    echo "  stop        Stop all services and processes"
    echo "  restart     Stop and start fresh"
    echo "  status      Check status of all components"
    echo "  logs        Show logs from all components"
    echo "  demo        Quick 2-minute demo mode"
    echo "  clean       Clean checkpoints and restart fresh"
    echo ""
    echo -e "${BOLD}Options:${NC}"
    echo "  --data-source  Dataset for Kafka producer (default: unsw2)"
    echo "                   unsw   → UNSW-NB15_1.csv (700K records)"
    echo "                   unsw1  → UNSW-NB15_1.csv (same as unsw)"
    echo "                   unsw2  → UNSW_NB15_testing-set.csv (82K records)"
    echo "                   cicids2017 → CIC-IDS 2017 dataset"
    echo "                 Note: unsw/unsw1/unsw2 all use 'unsw' Spark models"
    echo "  --batch-size   Records per batch (default: 50)"
    echo "  --delay        Seconds between batches (default: 1)"
    echo "  --output       Output mode: all, console, mongodb (default: all)"
    echo "  --port         Dashboard port (default: 5000)"
    echo ""
    echo -e "${BOLD}Examples:${NC}"
    echo "  ./run.sh start                          # Start with unsw2 (default)"
    echo "  ./run.sh start --data-source unsw       # Use full UNSW dataset"
    echo "  ./run.sh start --data-source cicids2017 # Use CIC-IDS 2017 dataset"
    echo "  ./run.sh demo                           # Quick demo (2 min)"
    echo "  ./run.sh stop                           # Stop everything"
    echo ""
}

check_dependencies() {
    echo -e "${CYAN}[1/6] Checking dependencies...${NC}"
    
    local missing=0
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}  ✗ Docker not found${NC}"
        missing=1
    else
        echo -e "${GREEN}  ✓ Docker${NC}"
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        echo -e "${RED}  ✗ Docker Compose not found${NC}"
        missing=1
    else
        echo -e "${GREEN}  ✓ Docker Compose${NC}"
    fi
    
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}  ✗ Python 3 not found${NC}"
        missing=1
    else
        echo -e "${GREEN}  ✓ Python 3 ($(python3 --version 2>&1 | cut -d' ' -f2))${NC}"
    fi
    
    if ! python3 -c "import pyspark" 2>/dev/null; then
        echo -e "${YELLOW}  ⚠ PySpark not installed, installing...${NC}"
        pip install -q pyspark
    else
        echo -e "${GREEN}  ✓ PySpark${NC}"
    fi
    
    if [ $missing -eq 1 ]; then
        echo -e "${RED}Missing dependencies. Please install them first.${NC}"
        exit 1
    fi
}

install_python_deps() {
    echo -e "${CYAN}[2/6] Installing Python dependencies...${NC}"
    pip install -q -r requirements.txt 2>/dev/null || true
    echo -e "${GREEN}  ✓ Dependencies installed${NC}"
}

start_docker_services() {
    echo -e "${CYAN}[3/6] Starting Docker services (Kafka, MongoDB)...${NC}"
    
    # Check if services are already running
    if docker-compose ps 2>/dev/null | grep -q "Up"; then
        echo -e "${YELLOW}  ⚠ Some services already running${NC}"
    fi
    
    docker-compose up -d
    
    echo -e "${YELLOW}  ⏳ Waiting for services to be healthy...${NC}"
    
    # Wait for MongoDB
    echo -e "${YELLOW}  ⏳ Waiting for MongoDB...${NC}"
    local mongo_retries=30
    while [ $mongo_retries -gt 0 ]; do
        if docker exec nids-mongodb mongosh --quiet --eval "db.adminCommand('ping').ok" nids_db &>/dev/null; then
            echo -e "${GREEN}  ✓ MongoDB is ready${NC}"
            break
        fi
        sleep 1
        mongo_retries=$((mongo_retries - 1))
    done
    
    if [ $mongo_retries -eq 0 ]; then
        echo -e "${RED}  ✗ MongoDB failed to start${NC}"
        echo -e "${YELLOW}  Check logs: docker logs nids-mongodb${NC}"
        exit 1
    fi
    
    # Wait for Kafka
    echo -e "${YELLOW}  ⏳ Waiting for Kafka...${NC}"
    local kafka_retries=30
    while [ $kafka_retries -gt 0 ]; do
        if docker exec nids-kafka kafka-topics --bootstrap-server localhost:9092 --list &>/dev/null; then
            echo -e "${GREEN}  ✓ Kafka is ready${NC}"
            break
        fi
        sleep 1
        kafka_retries=$((kafka_retries - 1))
    done
    
    if [ $kafka_retries -eq 0 ]; then
        echo -e "${RED}  ✗ Kafka failed to start${NC}"
        echo -e "${YELLOW}  Check logs: docker logs nids-kafka${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}  ✓ All Docker services running and healthy${NC}"
}

create_kafka_topics() {
    echo -e "${CYAN}[4/6] Creating Kafka topics...${NC}"
    
    docker exec nids-kafka kafka-topics --create --if-not-exists \
        --topic network_logs \
        --bootstrap-server localhost:9092 \
        --partitions 3 \
        --replication-factor 1 2>/dev/null || true
    
    docker exec nids-kafka kafka-topics --create --if-not-exists \
        --topic intrusion_alerts \
        --bootstrap-server localhost:9092 \
        --partitions 3 \
        --replication-factor 1 2>/dev/null || true
    
    echo -e "${GREEN}  ✓ Kafka topics ready${NC}"
}

start_spark_streaming() {
    echo -e "${CYAN}[5/6] Starting Spark Streaming (ML Consumer)...${NC}"
    
    # Kill any existing Spark streaming process
    pkill -f "spark_streaming.py" 2>/dev/null || true
    sleep 2
    
    # Normalize data source for Spark (unsw1, unsw2 -> unsw)
    SPARK_DATA_SOURCE="$DATA_SOURCE"
    if [[ "$DATA_SOURCE" == "unsw1" || "$DATA_SOURCE" == "unsw2" ]]; then
        SPARK_DATA_SOURCE="unsw"
    fi
    
    # Start Spark streaming in background
    nohup python3 streaming/spark_streaming.py \
        --data-source "$SPARK_DATA_SOURCE" \
        --output "$OUTPUT_MODE" \
        > /tmp/spark_streaming.log 2>&1 &
    
    SPARK_PID=$!
    echo $SPARK_PID > /tmp/nids_spark.pid
    
    # Wait for Spark to initialize
    sleep 10
    
    if ps -p $SPARK_PID > /dev/null 2>&1; then
        echo -e "${GREEN}  ✓ Spark Streaming started (PID: $SPARK_PID)${NC}"
    else
        echo -e "${RED}  ✗ Spark Streaming failed to start${NC}"
        echo -e "${YELLOW}  Check logs: cat /tmp/spark_streaming.log${NC}"
        exit 1
    fi
}

start_kafka_producer() {
    echo -e "${CYAN}[6/6] Starting Kafka Producer (Traffic Simulator)...${NC}"
    
    # Kill any existing producer
    pkill -f "kafka_producer.py" 2>/dev/null || true
    sleep 1
    
    # Start Kafka producer in background
    nohup python3 streaming/kafka_producer.py \
        --data-source "$DATA_SOURCE" \
        --batch-size "$BATCH_SIZE" \
        --delay "$DELAY" \
        > /tmp/kafka_producer.log 2>&1 &
    
    PRODUCER_PID=$!
    echo $PRODUCER_PID > /tmp/nids_producer.pid
    
    sleep 3
    
    if ps -p $PRODUCER_PID > /dev/null 2>&1; then
        echo -e "${GREEN}  ✓ Kafka Producer started (PID: $PRODUCER_PID)${NC}"
    else
        echo -e "${RED}  ✗ Kafka Producer failed to start${NC}"
        echo -e "${YELLOW}  Check logs: cat /tmp/kafka_producer.log${NC}"
        exit 1
    fi
}

start_dashboard() {
    echo -e "${CYAN}[+] Starting Dashboard...${NC}"
    
    # Kill any existing dashboard
    pkill -f "dashboard/app.py" 2>/dev/null || true
    sleep 1
    
    # Start dashboard in background
    nohup python3 dashboard/app.py --port "$DASHBOARD_PORT" \
        > /tmp/dashboard.log 2>&1 &
    
    DASHBOARD_PID=$!
    echo $DASHBOARD_PID > /tmp/nids_dashboard.pid
    
    sleep 3
    
    if ps -p $DASHBOARD_PID > /dev/null 2>&1; then
        echo -e "${GREEN}  ✓ Dashboard started (PID: $DASHBOARD_PID)${NC}"
    else
        echo -e "${RED}  ✗ Dashboard failed to start${NC}"
        echo -e "${YELLOW}  Check logs: cat /tmp/dashboard.log${NC}"
    fi
}

print_success() {
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}  ${BOLD}✅ NIDS Pipeline Started Successfully!${NC}                      ${GREEN}║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BOLD}📊 Access Points:${NC}"
    echo -e "   ${CYAN}Dashboard:${NC}      http://localhost:${DASHBOARD_PORT}"
    echo -e "   ${CYAN}Kafka UI:${NC}       http://localhost:8080"
    echo -e "   ${CYAN}MongoDB UI:${NC}     http://localhost:8081"
    echo -e "   ${CYAN}Grafana:${NC}        http://localhost:3000 (admin/admin123)"
    echo ""
    echo -e "${BOLD}📝 Log Files:${NC}"
    echo -e "   Spark:     /tmp/spark_streaming.log"
    echo -e "   Producer:  /tmp/kafka_producer.log"
    echo -e "   Dashboard: /tmp/dashboard.log"
    echo ""
    echo -e "${BOLD}⚙️  Configuration:${NC}"
    echo -e "   Dataset:     ${DATA_SOURCE}"
    echo -e "   Batch Size:  ${BATCH_SIZE} records"
    echo -e "   Delay:       ${DELAY}s between batches"
    echo -e "   Output:      ${OUTPUT_MODE}"
    echo ""
    echo -e "${YELLOW}To stop the pipeline:${NC} ./run.sh stop"
    echo ""
}

stop_all() {
    echo -e "${CYAN}Stopping NIDS Pipeline...${NC}"
    
    # Stop Python processes
    pkill -f "spark_streaming.py" 2>/dev/null || true
    pkill -f "kafka_producer.py" 2>/dev/null || true
    pkill -f "dashboard/app.py" 2>/dev/null || true
    
    # Remove PID files
    rm -f /tmp/nids_*.pid
    
    echo -e "${GREEN}  ✓ Python processes stopped${NC}"
    
    # Stop Docker services
    echo -e "${YELLOW}  Stopping Docker services...${NC}"
    docker-compose down 2>/dev/null || true
    
    echo -e "${GREEN}  ✓ All services stopped${NC}"
}

show_status() {
    echo -e "${BOLD}📊 NIDS Pipeline Status${NC}"
    echo ""
    
    # Docker services
    echo -e "${CYAN}Docker Services:${NC}"
    if docker-compose ps 2>/dev/null | grep -q "Up"; then
        docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || docker-compose ps
    else
        echo -e "  ${RED}Not running${NC}"
    fi
    echo ""
    
    # Python processes
    echo -e "${CYAN}Python Processes:${NC}"
    
    if pgrep -f "spark_streaming.py" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ Spark Streaming${NC} (PID: $(pgrep -f spark_streaming.py))"
    else
        echo -e "  ${RED}✗ Spark Streaming${NC}"
    fi
    
    if pgrep -f "kafka_producer.py" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ Kafka Producer${NC} (PID: $(pgrep -f kafka_producer.py))"
    else
        echo -e "  ${RED}✗ Kafka Producer${NC}"
    fi
    
    if pgrep -f "dashboard/app.py" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ Dashboard${NC} (PID: $(pgrep -f 'dashboard/app.py'))"
    else
        echo -e "  ${RED}✗ Dashboard${NC}"
    fi
    
    echo ""
    
    # MongoDB alerts count
    if docker exec nids-mongodb mongosh --quiet nids_db --eval "db.alerts.countDocuments({})" 2>/dev/null; then
        ALERT_COUNT=$(docker exec nids-mongodb mongosh --quiet nids_db --eval "db.alerts.countDocuments({})" 2>/dev/null)
        echo -e "${CYAN}MongoDB Alerts:${NC} $ALERT_COUNT"
    fi
}

show_logs() {
    echo -e "${BOLD}📝 Recent Logs${NC}"
    echo ""
    
    echo -e "${CYAN}=== Spark Streaming (last 20 lines) ===${NC}"
    tail -20 /tmp/spark_streaming.log 2>/dev/null || echo "No logs available"
    echo ""
    
    echo -e "${CYAN}=== Kafka Producer (last 20 lines) ===${NC}"
    tail -20 /tmp/kafka_producer.log 2>/dev/null || echo "No logs available"
    echo ""
    
    echo -e "${CYAN}=== Dashboard (last 10 lines) ===${NC}"
    tail -10 /tmp/dashboard.log 2>/dev/null || echo "No logs available"
}

clean_checkpoints() {
    echo -e "${CYAN}Cleaning checkpoints...${NC}"
    
    # Stop services first
    stop_all
    
    # Clean checkpoint directories
    rm -rf checkpoints/*
    mkdir -p checkpoints
    
    echo -e "${GREEN}  ✓ Checkpoints cleaned${NC}"
}

run_demo() {
    echo -e "${MAGENTA}🎬 Running 2-minute demo...${NC}"
    
    DATA_SOURCE="unsw"
    BATCH_SIZE="100"
    DELAY="0.5"
    OUTPUT_MODE="all"
    
    run_start
    
    echo ""
    echo -e "${YELLOW}Demo will run for 2 minutes with high throughput...${NC}"
    echo -e "${YELLOW}Open http://localhost:5000 to see live detections!${NC}"
    echo ""
    echo -e "Press Ctrl+C to stop early, or wait for auto-stop."
    
    sleep 120
    
    echo ""
    echo -e "${CYAN}Demo complete! Stopping services...${NC}"
    stop_all
}

run_start() {
    print_banner
    check_dependencies
    install_python_deps
    start_docker_services
    create_kafka_topics
    start_spark_streaming
    start_kafka_producer
    start_dashboard
    print_success
}

# Parse command line arguments
COMMAND="${1:-start}"
shift || true

while [[ $# -gt 0 ]]; do
    case $1 in
        --data-source)
            DATA_SOURCE="$2"
            shift 2
            ;;
        --batch-size)
            BATCH_SIZE="$2"
            shift 2
            ;;
        --delay)
            DELAY="$2"
            shift 2
            ;;
        --output)
            OUTPUT_MODE="$2"
            shift 2
            ;;
        --port)
            DASHBOARD_PORT="$2"
            shift 2
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            print_usage
            exit 1
            ;;
    esac
done

# Execute command
case $COMMAND in
    start)
        run_start
        ;;
    stop)
        stop_all
        ;;
    restart)
        stop_all
        sleep 3
        run_start
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    demo)
        run_demo
        ;;
    clean)
        clean_checkpoints
        ;;
    help|-h|--help)
        print_usage
        ;;
    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        print_usage
        exit 1
        ;;
esac
