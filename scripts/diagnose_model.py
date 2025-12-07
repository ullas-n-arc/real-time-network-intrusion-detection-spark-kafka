"""
Quick diagnostic script to test UNSW models and check data quality
"""
import pandas as pd
from pyspark.sql import SparkSession
from pyspark.ml.classification import RandomForestClassificationModel
from pyspark.ml.feature import StandardScalerModel, VectorAssembler
import sys

print("="*60)
print("UNSW Model & Data Diagnostic")
print("="*60)

# Create Spark session
spark = SparkSession.builder \
    .appName("UNSW-Diagnostic") \
    .config("spark.driver.memory", "2g") \
    .master("local[2]") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

# 1. Check the actual data
print("\n1. Checking UNSW Testing Data...")
df = spark.read.csv("data/preprocessed/UNSW_NB15_testing-set.csv", header=True, inferSchema=True)
print(f"   Total records: {df.count():,}")
print(f"   Columns: {len(df.columns)}")

# Check attack distribution
print("\n2. Attack Type Distribution (attack_cat):")
attack_dist = df.groupBy("attack_cat").count().orderBy("count", ascending=False)
attack_dist.show(20, truncate=False)

print("\n3. Binary Label Distribution:")
df.groupBy("label").count().show()

# 4. Load models and test
print("\n4. Testing Models...")
try:
    binary_model = RandomForestClassificationModel.load("models/unsw_rf_binary_classifier")
    print("   ✅ Binary model loaded")
    
    multiclass_model = RandomForestClassificationModel.load("models/unsw_rf_multiclass_classifier")
    print("   ✅ Multiclass model loaded")
    
    scaler = StandardScalerModel.load("models/unsw_scaler")
    print("   ✅ Scaler loaded")
    
    # Get features
    feature_cols = [
        "dur", "spkts", "dpkts", "sbytes", "dbytes", "rate", "sttl", "dttl",
        "sload", "dload", "sloss", "dloss", "sinpkt", "dinpkt", "sjit", "djit",
        "swin", "stcpb", "dtcpb", "dwin", "tcprtt", "synack", "ackdat",
        "smean", "dmean", "trans_depth", "response_body_len", "ct_srv_src",
        "ct_state_ttl", "ct_dst_ltm", "ct_src_dport_ltm", "ct_dst_sport_ltm",
        "ct_dst_src_ltm", "is_ftp_login", "ct_ftp_cmd", "ct_flw_http_mthd",
        "ct_src_ltm", "ct_srv_dst", "is_sm_ips_ports"
    ]
    
    # Take sample and test
    print("\n5. Testing on Sample Data...")
    sample = df.limit(100).na.fill(0.0)
    
    # Assemble features
    assembler = VectorAssembler(inputCols=feature_cols, outputCol="features_raw")
    sample = assembler.transform(sample)
    
    # Scale (scaler expects 'features_raw' and outputs 'features')
    sample = scaler.transform(sample)
    
    print("   Columns after scaling:", [c for c in sample.columns if 'feature' in c.lower()])
    
    # The scaler outputs 'features', but rename to 'features_scaled' for model compatibility
    if "features" in sample.columns:
        sample = sample.withColumnRenamed("features", "features_scaled")
    
    # Binary prediction - explicitly set to use features_scaled
    from pyspark.ml.param import Param
    binary_model._paramMap[binary_model.getParam('featuresCol')] = 'features_scaled'
    binary_model.setPredictionCol("binary_pred")
    binary_model.setRawPredictionCol("raw_binary_pred")
    binary_model.setProbabilityCol("prob_binary_pred")
    sample = binary_model.transform(sample)
    
    # Multiclass prediction - explicitly set to use features_scaled and different output columns
    multiclass_model._paramMap[multiclass_model.getParam('featuresCol')] = 'features_scaled'
    multiclass_model.setPredictionCol("multiclass_pred")
    multiclass_model.setRawPredictionCol("raw_multiclass_pred")
    multiclass_model.setProbabilityCol("prob_multiclass_pred")
    sample = multiclass_model.transform(sample)
    
    # Show results
    print("\n6. Sample Predictions vs Actual:")
    sample.select("attack_cat", "label", "binary_pred", "multiclass_pred").show(20, truncate=False)
    
    # Count prediction distribution
    print("\n7. Multiclass Prediction Distribution:")
    sample.groupBy("multiclass_pred").count().orderBy("multiclass_pred").show()
    
    print("\n8. Binary Prediction Distribution:")
    sample.groupBy("binary_pred").count().show()
    
    # Check accuracy
    from pyspark.sql import functions as F
    print("\n9. Quick Accuracy Check:")
    correct_binary = sample.filter(F.col("binary_pred") == F.col("label")).count()
    print(f"   Binary accuracy on sample: {correct_binary}/100 = {correct_binary}%")
    
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

spark.stop()
print("\n" + "="*60)
print("Diagnostic Complete")
print("="*60)
