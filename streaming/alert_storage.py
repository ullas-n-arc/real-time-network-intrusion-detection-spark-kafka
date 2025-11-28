"""
MongoDB Alert Storage Module for Network Intrusion Detection System

Handles storing and retrieving intrusion alerts from MongoDB.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

try:
    from pymongo import MongoClient, DESCENDING
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import MONGODB_CONFIG, ATTACK_TYPE_MAPPING

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlertStorage:
    """
    MongoDB storage handler for intrusion detection alerts.
    """
    
    def __init__(self):
        """Initialize MongoDB connection."""
        if not PYMONGO_AVAILABLE:
            raise ImportError("pymongo not installed. Run: pip install pymongo")
        
        self.client = None
        self.db = None
        self.alerts_collection = None
        self.stats_collection = None
        
    def connect(self) -> bool:
        """Establish connection to MongoDB."""
        try:
            connection_string = f"mongodb://{MONGODB_CONFIG['host']}:{MONGODB_CONFIG['port']}"
            
            if MONGODB_CONFIG.get('username') and MONGODB_CONFIG.get('password'):
                connection_string = (
                    f"mongodb://{MONGODB_CONFIG['username']}:{MONGODB_CONFIG['password']}"
                    f"@{MONGODB_CONFIG['host']}:{MONGODB_CONFIG['port']}"
                )
            
            self.client = MongoClient(
                connection_string,
                serverSelectionTimeoutMS=5000
            )
            
            # Test connection
            self.client.admin.command('ping')
            
            self.db = self.client[MONGODB_CONFIG['database']]
            self.alerts_collection = self.db[MONGODB_CONFIG['alerts_collection']]
            self.stats_collection = self.db['alert_statistics']
            
            # Create indexes for efficient queries
            self._create_indexes()
            
            logger.info(f"✅ Connected to MongoDB at {MONGODB_CONFIG['host']}:{MONGODB_CONFIG['port']}")
            return True
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            return False
    
    def _create_indexes(self):
        """Create indexes for efficient querying."""
        # Index on timestamp for time-based queries
        self.alerts_collection.create_index([("processed_at", DESCENDING)])
        self.alerts_collection.create_index([("kafka_timestamp", DESCENDING)])
        
        # Index on attack type and severity
        self.alerts_collection.create_index("attack_type")
        self.alerts_collection.create_index("severity")
        
        # Compound index for common queries
        self.alerts_collection.create_index([
            ("severity", 1),
            ("processed_at", DESCENDING)
        ])
        
        logger.info("✅ MongoDB indexes created")
    
    def close(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
    
    def insert_alert(self, alert: Dict[str, Any]) -> str:
        """
        Insert a single alert into MongoDB.
        
        Args:
            alert: Dictionary containing alert data
            
        Returns:
            Inserted document ID
        """
        alert['inserted_at'] = datetime.now()
        result = self.alerts_collection.insert_one(alert)
        return str(result.inserted_id)
    
    def insert_alerts_batch(self, alerts: List[Dict[str, Any]]) -> List[str]:
        """
        Insert multiple alerts into MongoDB.
        
        Args:
            alerts: List of alert dictionaries
            
        Returns:
            List of inserted document IDs
        """
        if not alerts:
            return []
        
        for alert in alerts:
            alert['inserted_at'] = datetime.now()
        
        result = self.alerts_collection.insert_many(alerts)
        return [str(id) for id in result.inserted_ids]
    
    def get_recent_alerts(
        self,
        limit: int = 100,
        severity: Optional[str] = None,
        attack_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent alerts with optional filtering.
        
        Args:
            limit: Maximum number of alerts to return
            severity: Filter by severity level
            attack_type: Filter by attack type
            
        Returns:
            List of alert documents
        """
        query = {}
        
        if severity:
            query['severity'] = severity
        
        if attack_type:
            query['attack_type'] = attack_type
        
        cursor = self.alerts_collection.find(query) \
            .sort("processed_at", DESCENDING) \
            .limit(limit)
        
        return list(cursor)
    
    def get_alerts_in_timerange(
        self,
        start_time: datetime,
        end_time: datetime = None
    ) -> List[Dict[str, Any]]:
        """
        Get alerts within a time range.
        
        Args:
            start_time: Start of time range
            end_time: End of time range (defaults to now)
            
        Returns:
            List of alert documents
        """
        if end_time is None:
            end_time = datetime.now()
        
        query = {
            "processed_at": {
                "$gte": start_time,
                "$lte": end_time
            }
        }
        
        return list(self.alerts_collection.find(query).sort("processed_at", DESCENDING))
    
    def get_alert_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get aggregated statistics for recent alerts.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with statistics
        """
        since = datetime.now() - timedelta(hours=hours)
        
        pipeline = [
            {"$match": {"processed_at": {"$gte": since}}},
            {"$group": {
                "_id": None,
                "total_alerts": {"$sum": 1},
                "high_severity": {
                    "$sum": {"$cond": [{"$eq": ["$severity", "HIGH"]}, 1, 0]}
                },
                "medium_severity": {
                    "$sum": {"$cond": [{"$eq": ["$severity", "MEDIUM"]}, 1, 0]}
                },
                "low_severity": {
                    "$sum": {"$cond": [{"$eq": ["$severity", "LOW"]}, 1, 0]}
                }
            }}
        ]
        
        result = list(self.alerts_collection.aggregate(pipeline))
        
        if result:
            stats = result[0]
            del stats['_id']
        else:
            stats = {
                "total_alerts": 0,
                "high_severity": 0,
                "medium_severity": 0,
                "low_severity": 0
            }
        
        # Attack type breakdown
        type_pipeline = [
            {"$match": {"processed_at": {"$gte": since}}},
            {"$group": {
                "_id": "$attack_type",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}}
        ]
        
        type_result = list(self.alerts_collection.aggregate(type_pipeline))
        stats['by_attack_type'] = {r['_id']: r['count'] for r in type_result}
        
        stats['time_period_hours'] = hours
        stats['since'] = since.isoformat()
        
        return stats
    
    def get_attack_timeline(
        self,
        hours: int = 24,
        interval_minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Get attack counts grouped by time intervals.
        
        Args:
            hours: Number of hours to look back
            interval_minutes: Size of each interval
            
        Returns:
            List of time buckets with counts
        """
        since = datetime.now() - timedelta(hours=hours)
        
        pipeline = [
            {"$match": {"processed_at": {"$gte": since}}},
            {"$group": {
                "_id": {
                    "$dateTrunc": {
                        "date": "$processed_at",
                        "unit": "minute",
                        "binSize": interval_minutes
                    }
                },
                "count": {"$sum": 1},
                "high_count": {
                    "$sum": {"$cond": [{"$eq": ["$severity", "HIGH"]}, 1, 0]}
                }
            }},
            {"$sort": {"_id": 1}}
        ]
        
        result = list(self.alerts_collection.aggregate(pipeline))
        
        return [
            {
                "timestamp": r['_id'],
                "count": r['count'],
                "high_severity_count": r['high_count']
            }
            for r in result
        ]
    
    def delete_old_alerts(self, days: int = 30) -> int:
        """
        Delete alerts older than specified days.
        
        Args:
            days: Delete alerts older than this many days
            
        Returns:
            Number of deleted documents
        """
        cutoff = datetime.now() - timedelta(days=days)
        result = self.alerts_collection.delete_many({"processed_at": {"$lt": cutoff}})
        logger.info(f"Deleted {result.deleted_count} alerts older than {days} days")
        return result.deleted_count


def main():
    """Test MongoDB connection and operations."""
    storage = AlertStorage()
    
    if not storage.connect():
        print("Failed to connect to MongoDB")
        return
    
    # Insert test alert
    test_alert = {
        "is_attack": True,
        "attack_type": "DDoS",
        "severity": "HIGH",
        "binary_prediction": 1.0,
        "multiclass_prediction": 2.0,
        "processed_at": datetime.now()
    }
    
    alert_id = storage.insert_alert(test_alert)
    print(f"Inserted test alert: {alert_id}")
    
    # Get statistics
    stats = storage.get_alert_statistics(hours=1)
    print(f"\nAlert Statistics (last 1 hour):")
    print(f"  Total alerts: {stats['total_alerts']}")
    print(f"  High severity: {stats['high_severity']}")
    print(f"  By type: {stats['by_attack_type']}")
    
    storage.close()


if __name__ == "__main__":
    main()
