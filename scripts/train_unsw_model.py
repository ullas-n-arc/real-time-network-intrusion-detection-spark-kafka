"""
Train a Random Forest classifier on UNSW-NB15 dataset.

Usage:
    python scripts/train_unsw_model.py
"""

import pandas as pd
import numpy as np
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.ml.feature import VectorAssembler, StandardScaler, StringIndexer
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml.evaluation import BinaryClassificationEvaluator, MulticlassClassificationEvaluator


def main():
    # Paths
    BASE_DIR = Path(__file__).parent.parent
    TRAIN_PATH = BASE_DIR / "data/training/UNSW_NB15_training-set.csv"
    TEST_PATH = BASE_DIR / "data/preprocessed/UNSW_NB15_testing-set.csv"
    MODEL_PATH = BASE_DIR / "models/unsw_rf_binary_classifier"
    SCALER_PATH = BASE_DIR / "models/unsw_scaler"
    
    print("="*60)
    print("Training UNSW-NB15 Model")
    print("="*60)
    
    # Create Spark session
    spark = SparkSession.builder \
        .appName("UNSW-Training") \
        .master("local[*]") \
        .config("spark.driver.memory", "4g") \
        .getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    
    # Load training data
    print("\n📊 Loading training data...")
    train_pdf = pd.read_csv(TRAIN_PATH)
    print(f"Loaded {len(train_pdf)} training records")
    print(f"Attack distribution (training):\n{train_pdf['attack_cat'].value_counts()}")
    
    # Load test data
    print("\n📊 Loading test data...")
    test_pdf = pd.read_csv(TEST_PATH)
    print(f"Loaded {len(test_pdf)} test records")
    print(f"Attack distribution (testing):\n{test_pdf['attack_cat'].value_counts()}")
    
    # Create binary label (0 = Normal, 1 = Attack)
    train_pdf['binary_label'] = (train_pdf['attack_cat'] != 'Normal').astype(int)
    test_pdf['binary_label'] = (test_pdf['attack_cat'] != 'Normal').astype(int)
    
    # Handle infinity and NaN
    train_pdf = train_pdf.replace([np.inf, -np.inf], np.nan)
    train_pdf = train_pdf.fillna(0)
    test_pdf = test_pdf.replace([np.inf, -np.inf], np.nan)
    test_pdf = test_pdf.fillna(0)
    
    # Define numeric features (exclude id, label columns, and categorical)
    exclude_cols = ['id', 'attack_cat', 'label', 'binary_label', 'proto', 'service', 'state']
    numeric_cols = [c for c in train_pdf.columns if c not in exclude_cols]
    
    print(f"\n📊 Using {len(numeric_cols)} numeric features")
    
    # Create Spark DataFrames
    train_df = spark.createDataFrame(train_pdf)
    test_df = spark.createDataFrame(test_pdf)
    
    # Clean column names function
    def clean_columns(df):
        for col_name in df.columns:
            clean_name = col_name.strip().replace(" ", "_").replace("/", "_per_").replace(".", "_dot_")
            if clean_name != col_name:
                df = df.withColumnRenamed(col_name, clean_name)
        return df
    
    train_df = clean_columns(train_df)
    test_df = clean_columns(test_df)
    
    # Handle invalid values for both train and test
    for col in numeric_cols:
        clean_col = col.strip().replace(" ", "_").replace("/", "_per_").replace(".", "_dot_")
        if clean_col in train_df.columns:
            train_df = train_df.withColumn(clean_col,
                F.when(F.col(clean_col).isNull(), 0.0)
                 .when(F.col(clean_col) == float("inf"), 0.0)
                 .when(F.col(clean_col) == float("-inf"), 0.0)
                 .otherwise(F.col(clean_col).cast("double"))
            )
        if clean_col in test_df.columns:
            test_df = test_df.withColumn(clean_col,
                F.when(F.col(clean_col).isNull(), 0.0)
                 .when(F.col(clean_col) == float("inf"), 0.0)
                 .when(F.col(clean_col) == float("-inf"), 0.0)
                 .otherwise(F.col(clean_col).cast("double"))
            )
    
    # Get clean feature names
    clean_numeric_cols = [c.strip().replace(" ", "_").replace("/", "_per_").replace(".", "_dot_") 
                          for c in numeric_cols]
    available_features = [c for c in clean_numeric_cols if c in train_df.columns]
    
    print(f"Available features for training: {len(available_features)}")
    
    # Assemble features
    print("\n🔧 Assembling features...")
    assembler = VectorAssembler(
        inputCols=available_features,
        outputCol="features_raw",
        handleInvalid="skip"
    )
    train_df = assembler.transform(train_df)
    test_df = assembler.transform(test_df)
    
    # Scale features (fit on training data only)
    print("🔧 Scaling features...")
    scaler = StandardScaler(
        inputCol="features_raw",
        outputCol="features",
        withMean=True,
        withStd=True
    )
    scaler_model = scaler.fit(train_df)
    train_df = scaler_model.transform(train_df)
    test_df = scaler_model.transform(test_df)
    
    # Save scaler
    scaler_model.write().overwrite().save(str(SCALER_PATH))
    print(f"✅ Scaler saved to {SCALER_PATH}")
    
    print(f"\n📊 Train: {train_df.count()}, Test: {test_df.count()}")
    
    # Train Random Forest
    print("\n🚀 Training Random Forest classifier...")
    rf = RandomForestClassifier(
        featuresCol="features",
        labelCol="binary_label",
        numTrees=30,
        maxDepth=6,
        seed=42
    )
    
    model = rf.fit(train_df)
    
    # SAVE MODEL IMMEDIATELY after training
    model.write().overwrite().save(str(MODEL_PATH))
    print(f"✅ Model saved to {MODEL_PATH}")
    
    # Save feature list for reference
    import os
    os.makedirs(MODEL_PATH, exist_ok=True)
    feature_file = MODEL_PATH / "feature_names.txt"
    with open(feature_file, 'w') as f:
        for feat in available_features:
            f.write(f"{feat}\n")
    print(f"✅ Feature list saved to {feature_file}")
    
    # Evaluate
    print("\n📈 Evaluating model...")
    predictions = model.transform(test_df)
    
    # Binary metrics
    binary_evaluator = BinaryClassificationEvaluator(
        labelCol="binary_label",
        rawPredictionCol="rawPrediction"
    )
    auc_roc = binary_evaluator.evaluate(predictions, {binary_evaluator.metricName: "areaUnderROC"})
    
    # Multiclass metrics
    multi_evaluator = MulticlassClassificationEvaluator(
        labelCol="binary_label",
        predictionCol="prediction"
    )
    accuracy = multi_evaluator.evaluate(predictions, {multi_evaluator.metricName: "accuracy"})
    f1 = multi_evaluator.evaluate(predictions, {multi_evaluator.metricName: "f1"})
    
    print(f"\n=== MODEL PERFORMANCE ===")
    print(f"AUC-ROC: {auc_roc:.4f}")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"F1 Score: {f1:.4f}")
    
    # Confusion matrix
    print("\n=== CONFUSION MATRIX ===")
    predictions.groupBy("binary_label", "prediction").count().orderBy("binary_label", "prediction").show()
    
    # Per-attack detection (optional, can fail)
    print("\n=== DETECTION BY ATTACK TYPE ===")
    try:
        for cat in ['Normal', 'Generic', 'Exploits', 'Fuzzers', 'DoS', 'Reconnaissance', 'Analysis', 'Backdoor', 'Shellcode', 'Worms']:
            cat_df = predictions.filter(F.col("attack_cat") == cat)
            total = cat_df.count()
            if total > 0:
                detected = cat_df.filter(F.col("prediction") == 1.0).count()
                rate = 100 * detected / total
                print(f"  {cat}: {detected}/{total} ({rate:.1f}%)")
    except Exception as e:
        print(f"  (Detailed analysis skipped: {e})")
    
    spark.stop()
    print("\n✅ Training complete!")


if __name__ == "__main__":
    main()
