#!/bin/bash
# Shell script to run preprocessing pipeline on Linux/Mac
# Real-time Network Intrusion Detection Dataset Preprocessing

echo "========================================"
echo "Network IDS Data Preprocessing"
echo "========================================"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.7 or higher"
    exit 1
fi

echo "Python detected successfully"
echo ""

# Check if PySpark is installed
if ! python3 -c "import pyspark" &> /dev/null; then
    echo "WARNING: PySpark is not installed"
    echo "Installing PySpark..."
    pip3 install pyspark
    echo ""
fi

echo "========================================"
echo "Starting Preprocessing Pipeline"
echo "========================================"
echo ""
echo "This will preprocess all three datasets:"
echo "  1. CIC-IDS 2017"
echo "  2. CIC-IDS 2018"
echo "  3. UNSW-NB15"
echo ""
echo "Estimated time: 30-60 minutes"
echo ""
read -p "Press Enter to continue..."

# Run preprocessing
python3 scripts/run_preprocessing.py

if [ $? -ne 0 ]; then
    echo ""
    echo "========================================"
    echo "ERROR: Preprocessing failed!"
    echo "========================================"
    echo "Please check preprocessing.log for details"
    exit 1
fi

echo ""
echo "========================================"
echo "Preprocessing Completed Successfully!"
echo "========================================"
echo ""
echo "Output location: data/preprocessed/"
echo ""
echo "Files generated:"
echo "  - cicids2017_preprocessed.parquet"
echo "  - cicids2018_preprocessed.parquet"
echo "  - unsw_nb15_preprocessed.parquet"
echo "  - Metadata files (*.txt)"
echo ""
echo "Next steps:"
echo "  1. Review metadata files in data/preprocessed/"
echo "  2. Load data with: python3 scripts/load_preprocessed_example.py"
echo "  3. Train models with: python3 scripts/train_model_example.py"
echo ""
