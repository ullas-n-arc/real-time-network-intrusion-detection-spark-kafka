@echo off
REM Batch script to run preprocessing pipeline on Windows
REM Real-time Network Intrusion Detection Dataset Preprocessing

echo ========================================
echo Network IDS Data Preprocessing
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7 or higher
    pause
    exit /b 1
)

echo Python detected successfully
echo.

REM Check if PySpark is installed
python -c "import pyspark" >nul 2>&1
if errorlevel 1 (
    echo WARNING: PySpark is not installed
    echo Installing PySpark...
    pip install pyspark
    echo.
)

echo ========================================
echo Starting Preprocessing Pipeline
echo ========================================
echo.
echo This will preprocess all three datasets:
echo   1. CIC-IDS 2017
echo   2. CIC-IDS 2018
echo   3. UNSW-NB15
echo.
echo Estimated time: 30-60 minutes
echo.
pause

REM Run preprocessing
python scripts\run_preprocessing.py

if errorlevel 1 (
    echo.
    echo ========================================
    echo ERROR: Preprocessing failed!
    echo ========================================
    echo Please check preprocessing.log for details
    pause
    exit /b 1
)

echo.
echo ========================================
echo Preprocessing Completed Successfully!
echo ========================================
echo.
echo Output location: data\preprocessed\
echo.
echo Files generated:
echo   - cicids2017_preprocessed.parquet
echo   - cicids2018_preprocessed.parquet
echo   - unsw_nb15_preprocessed.parquet
echo   - Metadata files (*.txt)
echo.
echo Next steps:
echo   1. Review metadata files in data\preprocessed\
echo   2. Load data with: python scripts\load_preprocessed_example.py
echo   3. Train models with: python scripts\train_model_example.py
echo.
pause
