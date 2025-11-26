"""
End-to-end example: Load preprocessed data and train a model
Demonstrates how to use sample weights for handling class imbalance
"""

import os
from pyspark.sql import SparkSession
from pyspark.ml.classification import RandomForestClassifier, LogisticRegression
from pyspark.ml.evaluation import BinaryClassificationEvaluator, MulticlassClassificationEvaluator
from pyspark.sql.functions import col
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_spark_session():
    """Create Spark session for model training"""
    return SparkSession.builder \
        .appName("IDS-Model-Training") \
        .config("spark.driver.memory", "4g") \
        .config("spark.executor.memory", "4g") \
        .config("spark.sql.adaptive.enabled", "true") \
        .getOrCreate()


def load_dataset(spark, dataset_name):
    """Load preprocessed dataset"""
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parquet_path = os.path.join(BASE_DIR, "data", "preprocessed", f"{dataset_name}_preprocessed.parquet")
    
    logger.info(f"Loading {dataset_name} from {parquet_path}")
    df = spark.read.parquet(parquet_path)
    logger.info(f"Loaded {df.count():,} rows")
    
    return df


def train_logistic_regression(train_df, test_df, use_weights=True):
    """
    Train Logistic Regression model
    
    Args:
        train_df: Training dataframe
        test_df: Testing dataframe
        use_weights: Whether to use sample weights (important for class imbalance!)
    """
    logger.info("\n" + "="*70)
    logger.info("TRAINING LOGISTIC REGRESSION")
    logger.info(f"Using Sample Weights: {use_weights}")
    logger.info("="*70)
    
    # Configure model
    lr_params = {
        'featuresCol': 'scaled_features',
        'labelCol': 'binary_label',
        'maxIter': 100,
        'regParam': 0.01,
        'elasticNetParam': 0.1
    }
    
    if use_weights:
        lr_params['weightCol'] = 'sample_weight'
    
    lr = LogisticRegression(**lr_params)
    
    # Train model
    logger.info("Training model...")
    model = lr.fit(train_df)
    
    # Make predictions
    logger.info("Making predictions on test set...")
    predictions = model.transform(test_df)
    
    # Evaluate
    evaluate_model(predictions, "Logistic Regression" + (" (Weighted)" if use_weights else " (Unweighted)"))
    
    return model, predictions


def train_random_forest(train_df, test_df, use_weights=True):
    """
    Train Random Forest model
    
    Args:
        train_df: Training dataframe
        test_df: Testing dataframe
        use_weights: Whether to use sample weights
    """
    logger.info("\n" + "="*70)
    logger.info("TRAINING RANDOM FOREST")
    logger.info(f"Using Sample Weights: {use_weights}")
    logger.info("="*70)
    
    # Configure model
    rf_params = {
        'featuresCol': 'scaled_features',
        'labelCol': 'binary_label',
        'numTrees': 100,
        'maxDepth': 10,
        'minInstancesPerNode': 1,
        'seed': 42
    }
    
    if use_weights:
        rf_params['weightCol'] = 'sample_weight'
    
    rf = RandomForestClassifier(**rf_params)
    
    # Train model
    logger.info("Training model...")
    model = rf.fit(train_df)
    
    # Make predictions
    logger.info("Making predictions on test set...")
    predictions = model.transform(test_df)
    
    # Evaluate
    evaluate_model(predictions, "Random Forest" + (" (Weighted)" if use_weights else " (Unweighted)"))
    
    return model, predictions


def evaluate_model(predictions, model_name):
    """Evaluate model performance"""
    logger.info(f"\n{'='*70}")
    logger.info(f"EVALUATION RESULTS: {model_name}")
    logger.info(f"{'='*70}")
    
    # Binary classification metrics
    evaluator_auc = BinaryClassificationEvaluator(
        labelCol='binary_label',
        rawPredictionCol='rawPrediction',
        metricName='areaUnderROC'
    )
    
    evaluator_pr = BinaryClassificationEvaluator(
        labelCol='binary_label',
        rawPredictionCol='rawPrediction',
        metricName='areaUnderPR'
    )
    
    auc = evaluator_auc.evaluate(predictions)
    pr_auc = evaluator_pr.evaluate(predictions)
    
    # Multi-class metrics
    evaluator_acc = MulticlassClassificationEvaluator(
        labelCol='binary_label',
        predictionCol='prediction',
        metricName='accuracy'
    )
    
    evaluator_f1 = MulticlassClassificationEvaluator(
        labelCol='binary_label',
        predictionCol='prediction',
        metricName='f1'
    )
    
    evaluator_precision = MulticlassClassificationEvaluator(
        labelCol='binary_label',
        predictionCol='prediction',
        metricName='weightedPrecision'
    )
    
    evaluator_recall = MulticlassClassificationEvaluator(
        labelCol='binary_label',
        predictionCol='prediction',
        metricName='weightedRecall'
    )
    
    accuracy = evaluator_acc.evaluate(predictions)
    f1 = evaluator_f1.evaluate(predictions)
    precision = evaluator_precision.evaluate(predictions)
    recall = evaluator_recall.evaluate(predictions)
    
    logger.info(f"AUC-ROC:           {auc:.4f}")
    logger.info(f"AUC-PR:            {pr_auc:.4f}")
    logger.info(f"Accuracy:          {accuracy:.4f}")
    logger.info(f"F1 Score:          {f1:.4f}")
    logger.info(f"Precision:         {precision:.4f}")
    logger.info(f"Recall:            {recall:.4f}")
    
    # Show confusion matrix
    logger.info("\nConfusion Matrix:")
    predictions.groupBy('binary_label', 'prediction').count().orderBy('binary_label', 'prediction').show()
    
    # Show sample predictions
    logger.info("\nSample Predictions:")
    predictions.select('binary_label', 'prediction', 'probability').show(10, truncate=False)


def compare_weighted_vs_unweighted(train_df, test_df):
    """
    Compare model performance with and without sample weights
    Demonstrates the importance of handling class imbalance
    """
    logger.info("\n" + "#"*70)
    logger.info("COMPARISON: WEIGHTED vs UNWEIGHTED TRAINING")
    logger.info("#"*70)
    
    logger.info("\nThis comparison shows the impact of using sample weights")
    logger.info("to handle class imbalance in the training data.\n")
    
    # Train without weights
    logger.info("\n>>> TRAINING WITHOUT SAMPLE WEIGHTS <<<")
    model_unweighted, pred_unweighted = train_logistic_regression(
        train_df, test_df, use_weights=False
    )
    
    # Train with weights
    logger.info("\n>>> TRAINING WITH SAMPLE WEIGHTS <<<")
    model_weighted, pred_weighted = train_logistic_regression(
        train_df, test_df, use_weights=True
    )
    
    logger.info("\n" + "#"*70)
    logger.info("KEY TAKEAWAY:")
    logger.info("Using sample weights typically improves detection of minority classes")
    logger.info("(attacks) while maintaining good overall performance.")
    logger.info("#"*70 + "\n")


def main():
    """Main training pipeline"""
    
    logger.info("="*70)
    logger.info("NETWORK INTRUSION DETECTION - MODEL TRAINING EXAMPLE")
    logger.info("="*70)
    
    # Create Spark session
    spark = create_spark_session()
    
    try:
        # Load preprocessed data
        logger.info("\nStep 1: Loading preprocessed data...")
        df = load_dataset(spark, 'cicids2017')
        
        # Show class distribution
        logger.info("\nClass Distribution:")
        df.groupBy('binary_label').count().show()
        
        # Split data
        logger.info("\nStep 2: Splitting data (80% train, 20% test)...")
        train_df, test_df = df.randomSplit([0.8, 0.2], seed=42)
        
        logger.info(f"Training set: {train_df.count():,} samples")
        logger.info(f"Test set: {test_df.count():,} samples")
        
        # Show sample weights distribution
        logger.info("\nSample Weights in Training Set:")
        train_df.select('sample_weight').summary().show()
        
        # Option 1: Compare weighted vs unweighted
        logger.info("\n" + ">"*70)
        logger.info("DEMONSTRATION: Impact of Sample Weights")
        logger.info(">"*70)
        
        compare_weighted_vs_unweighted(train_df, test_df)
        
        # Option 2: Train Random Forest with weights
        logger.info("\n" + ">"*70)
        logger.info("TRAINING RANDOM FOREST WITH SAMPLE WEIGHTS")
        logger.info(">"*70)
        
        model_rf, predictions_rf = train_random_forest(train_df, test_df, use_weights=True)
        
        logger.info("\n" + "="*70)
        logger.info("TRAINING COMPLETED SUCCESSFULLY!")
        logger.info("="*70)
        
        logger.info("\nNext steps:")
        logger.info("1. Save the trained model for deployment")
        logger.info("2. Test on other datasets (CIC-IDS 2018, UNSW-NB15)")
        logger.info("3. Integrate with Kafka streaming pipeline")
        logger.info("4. Deploy for real-time intrusion detection")
        
    except Exception as e:
        logger.error(f"Error during training: {str(e)}")
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
