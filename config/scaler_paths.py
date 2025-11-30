"""
Scaler model paths for different data sources
"""

from pathlib import Path

# Base models directory
MODELS_DIR = Path(__file__).parent.parent / "models"

# Scaler paths for each data source
SCALER_PATHS = {
    "cicids2017": str(MODELS_DIR / "cicids2017_scaler"),
    "cicids2018": str(MODELS_DIR / "cicids2018_scaler"),
    "unsw": str(MODELS_DIR / "unsw_scaler"),  # Trained with 39 features
}

# Model paths for each data source
MODEL_PATHS = {
    "cicids2017": str(MODELS_DIR / "rf_binary_classifier"),
    "cicids2018": str(MODELS_DIR / "rf_binary_classifier"),
    "unsw": str(MODELS_DIR / "unsw_rf_binary_classifier"),  # Trained on UNSW-NB15
}
