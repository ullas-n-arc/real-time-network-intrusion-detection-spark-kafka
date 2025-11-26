"""
Example script demonstrating how to load and use preprocessed data
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col
import os


def load_preprocessed_data(dataset_name: str):
    """
    Load preprocessed dataset
    
    Args:
        dataset_name: One of 'cicids2017', 'cicids2018', 'unsw_nb15'
    """
    # Create Spark session
    spark = SparkSession.builder \
        .appName(f"Load-{dataset_name}") \
        .config("spark.driver.memory", "4g") \
        .getOrCreate()
    
    # Define paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, "data", "preprocessed")
    
    # Load data
    parquet_path = os.path.join(DATA_DIR, f"{dataset_name}_preprocessed.parquet")
    
    print(f"\nLoading {dataset_name.upper()} dataset...")
    print(f"Path: {parquet_path}")
    
    df = spark.read.parquet(parquet_path)
    
    # Display basic info
    print(f"\n{'='*70}")
    print(f"Dataset: {dataset_name.upper()}")
    print(f"{'='*70}")
    print(f"Total Rows: {df.count():,}")
    print(f"Total Columns: {len(df.columns)}")
    print(f"\nColumn Names:")
    for col_name in df.columns:
        print(f"  - {col_name}")
    
    # Show sample data
    print(f"\n{'-'*70}")
    print("Sample Data (first 5 rows):")
    print(f"{'-'*70}")
    df.select("binary_label", "sample_weight").show(5)
    
    # Show class distribution
    print(f"\n{'-'*70}")
    print("Class Distribution:")
    print(f"{'-'*70}")
    
    if "label" in df.columns:
        df.groupBy("label").count().orderBy("count", ascending=False).show()
    
    if "binary_label" in df.columns:
        df.groupBy("binary_label").count().show()
    
    # Show sample weights distribution
    print(f"\n{'-'*70}")
    print("Sample Weights Summary:")
    print(f"{'-'*70}")
    df.select("sample_weight").summary().show()
    
    spark.stop()
    
    return df


def example_model_training():
    """
    Example showing how to prepare data for model training
    """
    print("\n" + "="*70)
    print("EXAMPLE: Preparing Data for Model Training")
    print("="*70)
    
    # Create Spark session
    spark = SparkSession.builder \
        .appName("ModelTrainingExample") \
        .config("spark.driver.memory", "4g") \
        .getOrCreate()
    
    # Load preprocessed data
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, "data", "preprocessed")
    parquet_path = os.path.join(DATA_DIR, "cicids2017_preprocessed.parquet")
    
    df = spark.read.parquet(parquet_path)
    
    # Split into train/test
    print("\nSplitting data into train/test sets (80/20)...")
    train_df, test_df = df.randomSplit([0.8, 0.2], seed=42)
    
    print(f"Training set size: {train_df.count():,}")
    print(f"Test set size: {test_df.count():,}")
    
    # Select features for training
    print("\nSelecting features for model training...")
    
    # Option 1: Use scaled features vector
    train_features = train_df.select("scaled_features", "binary_label", "sample_weight")
    test_features = test_df.select("scaled_features", "binary_label", "sample_weight")
    
    print("\nTraining data schema:")
    train_features.printSchema()
    
    print("\nSample training data:")
    train_features.show(5, truncate=False)
    
    # Example: Using sample weights in model training
    print("\n" + "-"*70)
    print("Example: Access sample weights for training")
    print("-"*70)
    print("""
# In your model training code, you can use sample weights like this:

from pyspark.ml.classification import LogisticRegression

# Create model with weighted instances
lr = LogisticRegression(
    featuresCol='scaled_features',
    labelCol='binary_label',
    weightCol='sample_weight',  # Use sample weights
    maxIter=100,
    regParam=0.01
)

# Train model
model = lr.fit(train_features)

# Make predictions
predictions = model.transform(test_features)
    """)
    
    spark.stop()


def main():
    """Main function demonstrating data loading"""
    
    print("\n" + "="*70)
    print("PREPROCESSED DATA LOADING EXAMPLES")
    print("="*70)
    
    datasets = ['cicids2017', 'cicids2018', 'unsw_nb15']
    
    print("\nAvailable datasets:")
    for i, ds in enumerate(datasets, 1):
        print(f"{i}. {ds.upper()}")
    
    # Example: Load CIC-IDS 2017
    print("\n" + ">"*70)
    print("Loading CIC-IDS 2017 as an example...")
    print(">"*70)
    
    try:
        load_preprocessed_data('cicids2017')
    except Exception as e:
        print(f"Error loading dataset: {str(e)}")
        print("\nNote: Make sure to run preprocessing first:")
        print("  python scripts/run_preprocessing.py")
    
    # Show model training example
    try:
        example_model_training()
    except Exception as e:
        print(f"Error in model training example: {str(e)}")


if __name__ == "__main__":
    main()
