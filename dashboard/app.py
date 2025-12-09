"""
Flask Dashboard API for Network Intrusion Detection System

Modern, responsive web dashboard with comprehensive API for monitoring
network intrusion detection alerts in real-time.

Features:
    - Real-time alert monitoring
    - Session-based filtering
    - Advanced analytics and visualizations
    - REST API endpoints
    - Secure, accessible UI

Usage:
    python app.py
    python app.py --session <session_id>  # View specific session
    
Endpoints:
    GET  /                   - Dashboard home page
    GET  /alerts             - Alerts page
    GET  /api/health         - Health check
    GET  /api/alerts         - Get recent alerts
    GET  /api/alerts/stats   - Get alert statistics
    GET  /api/alerts/timeline - Get attack timeline
    GET  /api/sessions       - Get list of sessions
    GET  /api/session/current - Get current session info
    POST /api/session/set    - Set current session to view
    DELETE /api/session/delete - Delete specific session
    DELETE /api/sessions/delete-all - Delete all sessions
    GET  /api/attack-types   - Get attack type mappings
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, render_template, send_from_directory
from flask_cors import CORS
import threading
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from streaming.alert_storage import (
    AlertStorage, 
    get_current_session_id, 
    set_current_session_id,
    clear_session
)
from config import MONGODB_CONFIG, ATTACK_TYPE_MAPPING

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['JSON_SORT_KEYS'] = False

# Enable CORS for API endpoints
CORS(app, resources={r"/api/*": {"origins": "*"}})

storage = None

# Dashboard session state (which session to display)
_dashboard_session_id = None

# Cache for frequently accessed data
_cache = {
    'attack_types': None,
    'sessions': None,
    'last_alert_count': 0,
    'cache_time': None
}
_cache_ttl = 30  # seconds


def get_storage():
    """Get or create storage connection."""
    global storage
    if storage is None:
        storage = AlertStorage()
        if not storage.connect():
            storage = None
            return None
    else:
        # Verify connection is still alive
        try:
            storage.client.admin.command('ping')
        except Exception:
            # Connection lost, reconnect
            storage = AlertStorage()
            if not storage.connect():
                storage = None
                return None
    return storage


def get_dashboard_session_id():
    """Get the session ID to use for dashboard filtering."""
    global _dashboard_session_id
    return _dashboard_session_id


def set_dashboard_session_id(session_id):
    """Set the session ID for dashboard filtering."""
    global _dashboard_session_id
    _dashboard_session_id = session_id


# ============================================
# Security Headers Middleware
# ============================================

@app.after_request
def add_security_headers(response):
    """Add security headers to all responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    # CSP for Chart.js CDN
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
        "style-src 'self' https://fonts.googleapis.com 'unsafe-inline'; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self';"
    )
    return response


# ============================================
# Static Files Route
# ============================================

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files with no-cache headers for development."""
    response = send_from_directory('static', filename)
    # Disable caching for JavaScript and CSS files in development
    if filename.endswith(('.js', '.css')):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response


# ============================================
# Page Routes
# ============================================
@app.route('/')
def dashboard():
    """Render the main dashboard page."""
    return render_template('dashboard.html')


@app.route('/alerts')
def alerts_page():
    """Render the alerts page."""
    return render_template('alerts.html')


# ============================================
# API Routes
# ============================================


@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    storage = get_storage()
    mongo_status = "connected" if storage else "disconnected"
    
    return jsonify({
        "status": "healthy",
        "mongodb": mongo_status,
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/alerts')
def get_alerts():
    """
    Get recent alerts.
    
    Query params:
        limit: Maximum number of alerts (default: 100)
        severity: Filter by severity (HIGH, MEDIUM, LOW)
        attack_type: Filter by attack type
        session_id: Filter by session (uses dashboard session if not provided)
    """
    storage = get_storage()
    if not storage:
        return jsonify({"error": "Database not connected"}), 503
    
    limit = request.args.get('limit', 100, type=int)
    severity = request.args.get('severity')
    attack_type = request.args.get('attack_type')
    
    # Use dashboard session if not explicitly provided
    session_id = get_dashboard_session_id()
    session_only = session_id is not None
    
    try:
        alerts = storage.get_recent_alerts(
            limit=limit,
            severity=severity,
            attack_type=attack_type,
            session_id=session_id,
            session_only=session_only
        )
        
        # Convert ObjectId and datetime for JSON serialization
        for alert in alerts:
            alert['_id'] = str(alert['_id'])
            if 'processed_at' in alert and isinstance(alert['processed_at'], datetime):
                alert['processed_at'] = alert['processed_at'].isoformat()
            if 'inserted_at' in alert and isinstance(alert['inserted_at'], datetime):
                alert['inserted_at'] = alert['inserted_at'].isoformat()
        
        return jsonify(alerts)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/alerts/stats')
def get_stats():
    """
    Get alert statistics.
    
    Query params:
        hours: Number of hours to look back (default: 24)
    """
    storage = get_storage()
    if not storage:
        return jsonify({"error": "Database not connected"}), 503
    
    hours = request.args.get('hours', 24, type=int)
    
    # Use dashboard session if set
    session_id = get_dashboard_session_id()
    session_only = session_id is not None
    
    try:
        stats = storage.get_alert_statistics(
            hours=hours,
            session_id=session_id,
            session_only=session_only
        )
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/alerts/timeline')
def get_timeline():
    """
    Get attack timeline.
    
    Query params:
        hours: Number of hours to look back (default: 24)
        interval: Interval in minutes (default: 60)
    """
    storage = get_storage()
    if not storage:
        return jsonify({"error": "Database not connected"}), 503
    
    hours = request.args.get('hours', 24, type=int)
    interval = request.args.get('interval', 60, type=int)
    
    # Use dashboard session if set
    session_id = get_dashboard_session_id()
    session_only = session_id is not None
    
    try:
        timeline = storage.get_attack_timeline(
            hours=hours, 
            interval_minutes=interval,
            session_id=session_id,
            session_only=session_only
        )
        
        # Convert datetime for JSON
        for item in timeline:
            if 'timestamp' in item and isinstance(item['timestamp'], datetime):
                item['timestamp'] = item['timestamp'].isoformat()
        
        return jsonify(timeline)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/sessions')
def get_sessions():
    """Get list of recent sessions."""
    storage = get_storage()
    if not storage:
        return jsonify({"error": "Database not connected"}), 503
    
    try:
        sessions = storage.get_sessions(limit=20)
        return jsonify(sessions)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/session/current')
def get_current_session():
    """Get the current dashboard session."""
    session_id = get_dashboard_session_id()
    return jsonify({
        "session_id": session_id,
        "is_filtered": session_id is not None
    })


@app.route('/api/session/set', methods=['POST'])
def set_session():
    """Set the current dashboard session."""
    data = request.get_json()
    session_id = data.get('session_id') if data else None
    
    set_dashboard_session_id(session_id)
    
    return jsonify({
        "success": True,
        "session_id": session_id,
        "is_filtered": session_id is not None
    })


@app.route('/api/session/delete', methods=['DELETE'])
def delete_session():
    """Delete a specific session and all its alerts."""
    storage = get_storage()
    if not storage:
        return jsonify({"error": "Database not connected"}), 503
    
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({"error": "session_id parameter required"}), 400
    
    try:
        result = storage.delete_session(session_id)
        
        # If the deleted session was the current dashboard session, clear it
        if get_dashboard_session_id() == session_id:
            set_dashboard_session_id(None)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/sessions/delete-all', methods=['DELETE'])
def delete_all_sessions():
    """Delete all sessions and all alerts."""
    storage = get_storage()
    if not storage:
        return jsonify({"error": "Database not connected"}), 503
    
    try:
        result = storage.delete_all_sessions()
        
        # Clear the current dashboard session
        set_dashboard_session_id(None)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/attack-types')
def get_attack_types():
    """Get list of known attack types."""
    return jsonify(ATTACK_TYPE_MAPPING)


@app.route('/api/alerts/export')
def export_alerts():
    """
    Export alerts in CSV or JSON format.
    
    Query params:
        format: 'csv' or 'json' (default: 'json')
        limit: Maximum alerts to export (default: 1000)
        severity: Filter by severity
        attack_type: Filter by attack type
    """
    storage = get_storage()
    if not storage:
        return jsonify({"error": "Database not connected"}), 503
    
    format_type = request.args.get('format', 'json').lower()
    limit = request.args.get('limit', 1000, type=int)
    severity = request.args.get('severity')
    attack_type = request.args.get('attack_type')
    
    session_id = get_dashboard_session_id()
    session_only = session_id is not None
    
    try:
        alerts = storage.get_recent_alerts(
            limit=limit,
            severity=severity,
            attack_type=attack_type,
            session_id=session_id,
            session_only=session_only
        )
        
        if format_type == 'csv':
            import csv
            from io import StringIO
            
            output = StringIO()
            if alerts:
                fieldnames = ['processed_at', 'attack_type', 'severity', 'session_id', 
                             'prediction', 'prediction_score']
                writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                
                for alert in alerts:
                    # Format datetime for CSV
                    if 'processed_at' in alert and isinstance(alert['processed_at'], datetime):
                        alert['processed_at'] = alert['processed_at'].isoformat()
                    writer.writerow(alert)
            
            response = app.response_class(
                response=output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment; filename=nids_alerts_{int(time.time())}.csv'}
            )
            return response
        else:
            # JSON format
            for alert in alerts:
                alert['_id'] = str(alert['_id'])
                if 'processed_at' in alert and isinstance(alert['processed_at'], datetime):
                    alert['processed_at'] = alert['processed_at'].isoformat()
                if 'inserted_at' in alert and isinstance(alert['inserted_at'], datetime):
                    alert['inserted_at'] = alert['inserted_at'].isoformat()
            
            return jsonify(alerts)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/alerts/count')
def get_alert_count():
    """
    Get total alert count and recent count.
    
    Query params:
        minutes: Number of minutes to look back for recent count (default: 5)
    """
    storage = get_storage()
    if not storage:
        return jsonify({"error": "Database not connected"}), 503
    
    minutes = request.args.get('minutes', 5, type=int)
    session_id = get_dashboard_session_id()
    session_only = session_id is not None
    
    try:
        # Total count
        total = storage.get_alert_count(session_id=session_id, session_only=session_only)
        
        # Recent count
        recent_time = datetime.now() - timedelta(minutes=minutes)
        recent = storage.get_alert_count(
            since=recent_time,
            session_id=session_id,
            session_only=session_only
        )
        
        return jsonify({
            "total": total,
            "recent": recent,
            "minutes": minutes,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/alerts/severity-distribution')
def get_severity_distribution():
    """
    Get alert count by severity level.
    
    Query params:
        hours: Number of hours to look back (default: 24)
    """
    storage = get_storage()
    if not storage:
        return jsonify({"error": "Database not connected"}), 503
    
    hours = request.args.get('hours', 24, type=int)
    session_id = get_dashboard_session_id()
    session_only = session_id is not None
    
    try:
        since = datetime.now() - timedelta(hours=hours)
        
        distribution = {
            'high': storage.get_alert_count(
                severity='high',
                since=since,
                session_id=session_id,
                session_only=session_only
            ),
            'medium': storage.get_alert_count(
                severity='medium',
                since=since,
                session_id=session_id,
                session_only=session_only
            ),
            'low': storage.get_alert_count(
                severity='low',
                since=since,
                session_id=session_id,
                session_only=session_only
            )
        }
        
        return jsonify(distribution)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Clear the API cache."""
    global _cache
    _cache = {
        'attack_types': None,
        'sessions': None,
        'last_alert_count': 0,
        'cache_time': None
    }
    return jsonify({"success": True, "message": "Cache cleared"})


@app.route('/api/version')
def get_version():
    """Get application version info."""
    return jsonify({
        "version": "1.0.0",
        "name": "NIDS Dashboard",
        "description": "Network Intrusion Detection System Dashboard",
        "features": [
            "Real-time monitoring",
            "Session filtering",
            "Analytics & reporting",
            "Export capabilities"
        ]
    })


def main():
    """Run the Flask application."""
    import argparse
    
    parser = argparse.ArgumentParser(description='NIDS Dashboard API')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--session', type=str, default=None, 
                        help='Session ID to filter alerts (shows all sessions if not specified)')
    
    args = parser.parse_args()
    
    # Set initial session if provided
    if args.session:
        set_dashboard_session_id(args.session)
    
    print("="*60)
    print("Network Intrusion Detection Dashboard")
    print("="*60)
    print(f"🌐 Dashboard: http://localhost:{args.port}")
    print(f"📊 API: http://localhost:{args.port}/api/alerts")
    if args.session:
        print(f"📍 Filtering by session: {args.session}")
    else:
        print(f"📍 Showing all sessions (select in UI to filter)")
    print("="*60)
    
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
