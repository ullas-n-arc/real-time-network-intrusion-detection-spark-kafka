"""
MongoDB Alert Storage Module for Network Intrusion Detection System

Handles storing and retrieving intrusion alerts from MongoDB.
Supports session-based filtering for isolating alerts per streaming session.
"""

import logging
import uuid
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

# Global session management
_current_session_id: Optional[str] = None
_session_start_time: Optional[datetime] = None


def generate_session_id() -> str:
    """Generate a new unique session ID."""
    return str(uuid.uuid4())[:8]


def get_current_session_id() -> Optional[str]:
    """Get the current active session ID."""
    global _current_session_id
    return _current_session_id


def set_current_session_id(session_id: str) -> None:
    """Set the current active session ID."""
    global _current_session_id, _session_start_time
    _current_session_id = session_id
    _session_start_time = datetime.now()
    logger.info(f"📍 Session ID set to: {session_id}")


def get_session_start_time() -> Optional[datetime]:
    """Get the start time of the current session."""
    global _session_start_time
    return _session_start_time


def start_new_session() -> str:
    """Start a new session and return the session ID."""
    session_id = generate_session_id()
    set_current_session_id(session_id)
    return session_id


def clear_session() -> None:
    """Clear the current session."""
    global _current_session_id, _session_start_time
    _current_session_id = None
    _session_start_time = None
    logger.info("📍 Session cleared")


class AlertStorage:
    """
    MongoDB storage handler for intrusion detection alerts.
    Supports session-based filtering to isolate alerts per streaming session.
    """
    
    def __init__(self, session_id: Optional[str] = None):
        """
        Initialize MongoDB connection.
        
        Args:
            session_id: Optional session ID for filtering alerts. 
                       If not provided, uses the global current session.
        """
        if not PYMONGO_AVAILABLE:
            raise ImportError("pymongo not installed. Run: pip install pymongo")
        
        self.client = None
        self.db = None
        self.alerts_collection = None
        self.stats_collection = None
        self.sessions_collection = None
        self._session_id = session_id
        
    @property
    def session_id(self) -> Optional[str]:
        """Get the session ID, falling back to global session."""
        return self._session_id or get_current_session_id()
    
    @session_id.setter
    def session_id(self, value: str):
        """Set the session ID for this storage instance."""
        self._session_id = value
        
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
            self.sessions_collection = self.db['sessions']
            
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
        
        # Index on session_id for session-based filtering
        self.alerts_collection.create_index("session_id")
        
        # Compound index for common queries
        self.alerts_collection.create_index([
            ("severity", 1),
            ("processed_at", DESCENDING)
        ])
        
        # Compound index for session-based queries
        self.alerts_collection.create_index([
            ("session_id", 1),
            ("processed_at", DESCENDING)
        ])
        
        logger.info("✅ MongoDB indexes created")
    
    def close(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
    
    def insert_alert(self, alert: Dict[str, Any], session_id: Optional[str] = None) -> str:
        """
        Insert a single alert into MongoDB.
        
        Args:
            alert: Dictionary containing alert data
            session_id: Optional session ID (uses instance/global session if not provided)
            
        Returns:
            Inserted document ID
        """
        alert['inserted_at'] = datetime.now()
        # Add session ID to alert
        alert['session_id'] = session_id or self.session_id
        result = self.alerts_collection.insert_one(alert)
        return str(result.inserted_id)
    
    def insert_alerts_batch(self, alerts: List[Dict[str, Any]], session_id: Optional[str] = None) -> List[str]:
        """
        Insert multiple alerts into MongoDB.
        
        Args:
            alerts: List of alert dictionaries
            session_id: Optional session ID (uses instance/global session if not provided)
            
        Returns:
            List of inserted document IDs
        """
        if not alerts:
            return []
        
        sid = session_id or self.session_id
        for alert in alerts:
            alert['inserted_at'] = datetime.now()
            alert['session_id'] = sid
        
        result = self.alerts_collection.insert_many(alerts)
        return [str(id) for id in result.inserted_ids]
    
    def get_recent_alerts(
        self,
        limit: int = 100,
        severity: Optional[str] = None,
        attack_type: Optional[str] = None,
        session_id: Optional[str] = None,
        session_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get recent alerts with optional filtering.
        
        Args:
            limit: Maximum number of alerts to return
            severity: Filter by severity level
            attack_type: Filter by attack type
            session_id: Filter by specific session ID
            session_only: If True, only return alerts from current session
            
        Returns:
            List of alert documents
        """
        query = {}
        
        # Session filtering
        if session_only:
            sid = session_id or self.session_id
            if sid:
                query['session_id'] = sid
        elif session_id:
            query['session_id'] = session_id
        
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
        end_time: datetime = None,
        session_id: Optional[str] = None,
        session_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get alerts within a time range.
        
        Args:
            start_time: Start of time range
            end_time: End of time range (defaults to now)
            session_id: Filter by specific session ID
            session_only: If True, only return alerts from current session
            
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
        
        # Session filtering
        if session_only:
            sid = session_id or self.session_id
            if sid:
                query['session_id'] = sid
        elif session_id:
            query['session_id'] = session_id
        
        return list(self.alerts_collection.find(query).sort("processed_at", DESCENDING))
    
    def get_alert_statistics(
        self,
        hours: int = 24,
        session_id: Optional[str] = None,
        session_only: bool = True
    ) -> Dict[str, Any]:
        """
        Get aggregated statistics for recent alerts.
        
        Args:
            hours: Number of hours to look back
            session_id: Filter by specific session ID
            session_only: If True, only return stats from current session
            
        Returns:
            Dictionary with statistics
        """
        since = datetime.now() - timedelta(hours=hours)
        
        match_query = {"processed_at": {"$gte": since}}
        
        # Session filtering
        if session_only:
            sid = session_id or self.session_id
            if sid:
                match_query['session_id'] = sid
        elif session_id:
            match_query['session_id'] = session_id
        
        pipeline = [
            {"$match": match_query},
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
            {"$match": match_query},
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
        stats['session_id'] = session_id or self.session_id
        
        return stats
    
    def get_attack_timeline(
        self,
        hours: int = 24,
        interval_minutes: int = 60,
        session_id: Optional[str] = None,
        session_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get attack counts grouped by time intervals.
        
        Args:
            hours: Number of hours to look back
            interval_minutes: Size of each interval
            session_id: Filter by specific session ID
            session_only: If True, only return timeline from current session
            
        Returns:
            List of time buckets with counts
        """
        since = datetime.now() - timedelta(hours=hours)
        
        match_query = {"processed_at": {"$gte": since}}
        
        # Session filtering
        if session_only:
            sid = session_id or self.session_id
            if sid:
                match_query['session_id'] = sid
        elif session_id:
            match_query['session_id'] = session_id
        
        pipeline = [
            {"$match": match_query},
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
    
    def clear_session_alerts(self, session_id: Optional[str] = None) -> int:
        """
        Delete all alerts for a specific session.
        
        Args:
            session_id: Session ID to clear. Uses current session if not provided.
            
        Returns:
            Number of deleted documents
        """
        sid = session_id or self.session_id
        if not sid:
            logger.warning("No session ID provided for clearing alerts")
            return 0
        
        result = self.alerts_collection.delete_many({"session_id": sid})
        logger.info(f"Deleted {result.deleted_count} alerts for session {sid}")
        return result.deleted_count
    
    def register_session(self, session_id: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Register a new session in the sessions collection.
        
        Args:
            session_id: Unique session identifier
            metadata: Optional metadata about the session (data source, etc.)
            
        Returns:
            Inserted session document ID
        """
        session_doc = {
            "session_id": session_id,
            "started_at": datetime.now(),
            "status": "active",
            "metadata": metadata or {}
        }
        result = self.sessions_collection.insert_one(session_doc)
        logger.info(f"📍 Registered session: {session_id}")
        return str(result.inserted_id)
    
    def end_session(self, session_id: Optional[str] = None) -> bool:
        """
        Mark a session as ended.
        
        Args:
            session_id: Session to end. Uses current session if not provided.
            
        Returns:
            True if session was found and updated
        """
        sid = session_id or self.session_id
        if not sid:
            return False
        
        result = self.sessions_collection.update_one(
            {"session_id": sid},
            {
                "$set": {
                    "status": "ended",
                    "ended_at": datetime.now()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"📍 Session ended: {sid}")
            return True
        return False
    
    def get_sessions(self, limit: int = 10, active_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get list of recent sessions.
        
        Args:
            limit: Maximum number of sessions to return
            active_only: Only return active sessions
            
        Returns:
            List of session documents
        """
        query = {}
        if active_only:
            query["status"] = "active"
        
        cursor = self.sessions_collection.find(query) \
            .sort("started_at", DESCENDING) \
            .limit(limit)
        
        sessions = []
        for session in cursor:
            session['_id'] = str(session['_id'])
            if 'started_at' in session and isinstance(session['started_at'], datetime):
                session['started_at'] = session['started_at'].isoformat()
            if 'ended_at' in session and isinstance(session['ended_at'], datetime):
                session['ended_at'] = session['ended_at'].isoformat()
            sessions.append(session)
        
        return sessions
    
    def get_session_info(self, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific session.
        
        Args:
            session_id: Session to get info for. Uses current session if not provided.
            
        Returns:
            Session document or None
        """
        sid = session_id or self.session_id
        if not sid:
            return None
        
        session = self.sessions_collection.find_one({"session_id": sid})
        if session:
            session['_id'] = str(session['_id'])
            if 'started_at' in session and isinstance(session['started_at'], datetime):
                session['started_at'] = session['started_at'].isoformat()
            if 'ended_at' in session and isinstance(session['ended_at'], datetime):
                session['ended_at'] = session['ended_at'].isoformat()
        
        return session
    
    def delete_session(self, session_id: str) -> Dict[str, Any]:
        """
        Delete a session and all its associated alerts.
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            Dictionary with deletion results
        """
        if not session_id:
            return {"success": False, "error": "No session ID provided"}
        
        result = {
            "session_id": session_id,
            "alerts_deleted": 0,
            "session_deleted": False,
            "success": False
        }
        
        try:
            # Delete all alerts for this session
            alerts_result = self.alerts_collection.delete_many({"session_id": session_id})
            result["alerts_deleted"] = alerts_result.deleted_count
            
            # Delete the session document
            session_result = self.sessions_collection.delete_one({"session_id": session_id})
            result["session_deleted"] = session_result.deleted_count > 0
            
            result["success"] = True
            logger.info(f"🗑️ Deleted session {session_id}: {result['alerts_deleted']} alerts removed")
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Failed to delete session {session_id}: {e}")
        
        return result
    
    def delete_all_sessions(self) -> Dict[str, Any]:
        """
        Delete all sessions and all alerts.
        
        Returns:
            Dictionary with deletion results
        """
        result = {
            "alerts_deleted": 0,
            "sessions_deleted": 0,
            "success": False
        }
        
        try:
            # Delete all alerts
            alerts_result = self.alerts_collection.delete_many({})
            result["alerts_deleted"] = alerts_result.deleted_count
            
            # Delete all sessions
            sessions_result = self.sessions_collection.delete_many({})
            result["sessions_deleted"] = sessions_result.deleted_count
            
            result["success"] = True
            logger.info(f"🗑️ Deleted all data: {result['alerts_deleted']} alerts, {result['sessions_deleted']} sessions")
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Failed to delete all sessions: {e}")
        
        return result


def main():
    """Test MongoDB connection and operations."""
    # Start a new session for testing
    session_id = start_new_session()
    print(f"Started test session: {session_id}")
    
    storage = AlertStorage()
    
    if not storage.connect():
        print("Failed to connect to MongoDB")
        return
    
    # Register the session
    storage.register_session(session_id, {"data_source": "test"})
    
    # Insert test alert (will automatically use current session)
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
    
    # Get statistics (will only show current session alerts)
    stats = storage.get_alert_statistics(hours=1)
    print(f"\nAlert Statistics (session {session_id}, last 1 hour):")
    print(f"  Total alerts: {stats['total_alerts']}")
    print(f"  High severity: {stats['high_severity']}")
    print(f"  By type: {stats['by_attack_type']}")
    
    # End session
    storage.end_session()
    
    storage.close()
    clear_session()


if __name__ == "__main__":
    main()
