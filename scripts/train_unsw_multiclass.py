"""
Train UNSW-NB15 Multiclass Classifier

Trains a Random Forest classifier to classify specific attack types:
- Normal (0)
- Fuzzers (1)
- Analysis (2)
- Backdoors (3)
- DoS (4)
- Exploits (5)
- Generic (6)
- Reconnaissance (7)
- Shellcode (8)
- Worms (9)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.ml.feature import VectorAssembler, StringIndexer
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.ml import Pipeline
import json

# UNSW-NB15 attack categories
UNSW_ATTACK_MAPPING = {
    "Normal": 0,
    "Fuzzers": 1,
    "Analysis": 2,
    "Backdoors": 3,
    "Backdoor": 3,
    "DoS": 4,
    "Exploits": 5,
    "Generic": 6,
    "Reconnaissance": 7,
    "Shellcode": 8,
    "Worms": 9
}

NUMERIC_FEATURES = [
    "dur", "spkts", "dpkts", "sbytes", "dbytes", "rate", "sttl", "dttl",
    "sload", "dload", "sloss", "dloss", "sinpkt", "dinpkt", "sjit", "djit",
    "swin", "stcpb", "dtcpb", "dwin", "tcprtt", "synack", "ackdat",
    "smean", "dmean", "trans_depth", "response_body_len", "ct_srv_src",
    "ct_state_ttl", "ct_dst_ltm", "ct_src_dport_ltm", "ct_dst_sport_ltm",
    "ct_dst_src_ltm", "is_ftp_login", "ct_ftp_cmd", "ct_flw_http_mthd",
    "ct_src_ltm", "ct_srv_dst", "is_sm_ips_ports"
]


def main():
    print("=" * 60)
    print("UNSW-NB15 Multiclass Attack Classifier Training")
    print("=" * 60)

    # Create Spark session
    spark = SparkSession.builder \
        .appName("UNSW-Multiclass-Training") \
        .config("spark.driver.memory", "4g") \
        .config("spark.sql.shuffle.partitions", "8") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")

    # Load training data
    print("\n📂 Loading training data...")
    train_path = "data/training/UNSW_NB15_training-set.csv"
    test_path = "data/preprocessed/UNSW_NB15_testing-set.csv"
    
    train_df = spark.read.csv(train_path, header=True, inferSchema=True)
    test_df = spark.read.csv(test_path, header=True, inferSchema=True)
    
    print(f"   Training records: {train_df.count():,}")
    print(f"   Testing records: {test_df.count():,}")

    # Show attack category distribution
    print("\n📊 Attack Category Distribution (Training):")
    train_df.groupBy("attack_cat").count().orderBy("count", ascending=False).show()

    # Clean attack_cat column (handle any whitespace)
    train_df = train_df.withColumn("attack_cat", F.trim(F.col("attack_cat")))
    test_df = test_df.withColumn("attack_cat", F.trim(F.col("attack_cat")))
    
    # Replace empty/null with "Normal"
    train_df = train_df.withColumn("attack_cat", 
        F.when(F.col("attack_cat").isNull() | (F.col("attack_cat") == ""), "Normal")
        .otherwise(F.col("attack_cat")))
    test_df = test_df.withColumn("attack_cat", 
        F.when(F.col("attack_cat").isNull() | (F.col("attack_cat") == ""), "Normal")
        .otherwise(F.col("attack_cat")))

    # Create numeric label from attack_cat using StringIndexer
    print("\n🔢 Creating label encoding...")
    indexer = StringIndexer(inputCol="attack_cat", outputCol="attack_label", handleInvalid="keep")
    indexer_model = indexer.fit(train_df)
    
    train_df = indexer_model.transform(train_df)
    test_df = indexer_model.transform(test_df)
    
    # Show the label mapping
    print("   Label mapping:")
    labels = indexer_model.labels
    for i, label in enumerate(labels):
        print(f"     {i}: {label}")

    # Handle missing/null values in features
    print("\n🧹 Cleaning features...")
    for col in NUMERIC_FEATURES:
        if col in train_df.columns:
            train_df = train_df.withColumn(col, 
                F.coalesce(F.col(col).cast("double"), F.lit(0.0)))
            test_df = test_df.withColumn(col, 
                F.coalesce(F.col(col).cast("double"), F.lit(0.0)))

    # Assemble features
    print("\n🔧 Assembling feature vectors...")
    available_features = [c for c in NUMERIC_FEATURES if c in train_df.columns]
    print(f"   Using {len(available_features)} features")
    
    assembler = VectorAssembler(
        inputCols=available_features,
        outputCol="features",
        handleInvalid="keep"
    )
    
    train_df = assembler.transform(train_df)
    test_df = assembler.transform(test_df)

    # Train Random Forest Multiclass Classifier
    print("\n🌲 Training Random Forest Multiclass Classifier...")
    rf = RandomForestClassifier(
        labelCol="attack_label",
        featuresCol="features",
        numTrees=50,
        maxDepth=10,
        seed=42
    )
    
    model = rf.fit(train_df)
    print("   ✅ Model trained successfully!")

    # Make predictions
    print("\n🔮 Making predictions on test set...")
    predictions = model.transform(test_df)

    # Evaluate model
    print("\n📈 Evaluation Results:")
    
    evaluator_acc = MulticlassClassificationEvaluator(
        labelCol="attack_label", 
        predictionCol="prediction",
        metricName="accuracy"
    )
    evaluator_f1 = MulticlassClassificationEvaluator(
        labelCol="attack_label", 
        predictionCol="prediction",
        metricName="f1"
    )
    evaluator_precision = MulticlassClassificationEvaluator(
        labelCol="attack_label", 
        predictionCol="prediction",
        metricName="weightedPrecision"
    )
    evaluator_recall = MulticlassClassificationEvaluator(
        labelCol="attack_label", 
        predictionCol="prediction",
        metricName="weightedRecall"
    )
    
    accuracy = evaluator_acc.evaluate(predictions)
    f1 = evaluator_f1.evaluate(predictions)
    precision = evaluator_precision.evaluate(predictions)
    recall = evaluator_recall.evaluate(predictions)
    
    print(f"   Accuracy:  {accuracy:.4f} ({accuracy*100:.2f}%)")
    print(f"   F1 Score:  {f1:.4f}")
    print(f"   Precision: {precision:.4f}")
    print(f"   Recall:    {recall:.4f}")

    # Save model FIRST before any more processing
    model_path = "models/unsw_rf_multiclass_classifier"
    print(f"\n💾 Saving model to {model_path}...")
    model.write().overwrite().save(model_path)
    
    # Save label mapping
    label_mapping = {labels[i]: i for i in range(len(labels))}
    reverse_mapping = {i: labels[i] for i in range(len(labels))}
    
    with open(f"{model_path}/label_mapping.json", "w") as f:
        json.dump({
            "label_to_index": label_mapping,
            "index_to_label": reverse_mapping
        }, f, indent=2)
    
    print("   ✅ Model and label mapping saved!")

    # Per-class accuracy
    print("\n📊 Per-Class Performance:")
    for i, label in enumerate(labels):
        class_preds = predictions.filter(F.col("attack_label") == i)
        if class_preds.count() > 0:
            class_correct = class_preds.filter(F.col("prediction") == i).count()
            class_total = class_preds.count()
            class_acc = class_correct / class_total if class_total > 0 else 0
            print(f"   {label:15}: {class_acc*100:6.2f}% ({class_correct:,}/{class_total:,})")

    # Summary
    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"Model: Random Forest Multiclass Classifier")
    print(f"Classes: {len(labels)}")
    print(f"Accuracy: {accuracy*100:.2f}%")
    print(f"Model saved to: {model_path}")
    print("=" * 60)

    spark.stop()


if __name__ == "__main__":
    main()
