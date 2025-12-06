"""
Flask Dashboard API for Network Intrusion Detection System

Provides REST API endpoints and a simple web dashboard for viewing alerts.
Supports session-based filtering to isolate alerts per streaming session.

Usage:
    python app.py
    python app.py --session <session_id>  # View specific session
    
Endpoints:
    GET  /                   - Dashboard home page
    GET  /api/alerts         - Get recent alerts
    GET  /api/alerts/stats   - Get alert statistics
    GET  /api/alerts/timeline - Get attack timeline
    GET  /api/sessions       - Get list of sessions
    GET  /api/session/current - Get current session info
    POST /api/session/set    - Set current session to view
    GET  /api/health         - Health check
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, render_template_string

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
storage = None

# Dashboard session state (which session to display)
_dashboard_session_id = None


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


# HTML Template for Dashboard
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Network Intrusion Detection Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        header {
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }
        h1 { color: #00d9ff; }
        .header-right { display: flex; align-items: center; gap: 20px; flex-wrap: wrap; }
        .session-info {
            background: rgba(0, 217, 255, 0.1);
            padding: 8px 15px;
            border-radius: 5px;
            border: 1px solid #00d9ff;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .session-label { color: #aaa; font-size: 0.85em; }
        .session-id { color: #00d9ff; font-family: monospace; font-weight: bold; }
        .session-select {
            background: rgba(255,255,255,0.1);
            border: 1px solid #00d9ff;
            color: #fff;
            padding: 8px 12px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.9em;
        }
        .session-select option { background: #1a1a2e; }
        .status { display: flex; align-items: center; gap: 10px; }
        .status-dot {
            width: 12px; height: 12px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        .status-dot.online { background: #00ff88; }
        .status-dot.offline { background: #ff4444; }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: rgba(255,255,255,0.1);
            padding: 25px;
            border-radius: 10px;
            text-align: center;
            transition: transform 0.3s;
        }
        .stat-card:hover { transform: translateY(-5px); }
        .stat-value {
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .stat-label { color: #aaa; font-size: 0.9em; }
        .stat-card.high .stat-value { color: #ff4444; }
        .stat-card.medium .stat-value { color: #ffaa00; }
        .stat-card.low .stat-value { color: #00d9ff; }
        .stat-card.total .stat-value { color: #00ff88; }
        .alerts-section {
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            padding: 20px;
        }
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        h2 { color: #00d9ff; }
        .refresh-btn {
            background: #00d9ff;
            color: #1a1a2e;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
        }
        .refresh-btn:hover { background: #00b8d9; }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        th { color: #00d9ff; font-weight: 600; }
        .severity-badge {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
        }
        .severity-HIGH { background: #ff4444; }
        .severity-MEDIUM { background: #ffaa00; color: #1a1a2e; }
        .severity-LOW { background: #00d9ff; color: #1a1a2e; }
        .attack-type { color: #ff88aa; }
        .no-data {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .chart-card {
            background: rgba(255,255,255,0.05);
            padding: 20px;
            border-radius: 10px;
        }
        .attack-type-list { list-style: none; }
        .attack-type-list li {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .attack-count {
            background: #00d9ff;
            color: #1a1a2e;
            padding: 2px 10px;
            border-radius: 10px;
            font-weight: bold;
        }
        .all-sessions-btn {
            background: transparent;
            border: 1px solid #00d9ff;
            color: #00d9ff;
            padding: 8px 15px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.9em;
        }
        .all-sessions-btn:hover { background: rgba(0, 217, 255, 0.1); }
        .all-sessions-btn.active { background: #00d9ff; color: #1a1a2e; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🛡️ Network Intrusion Detection System</h1>
            <div class="header-right">
                <div class="session-info">
                    <span class="session-label">Session:</span>
                    <select id="session-select" class="session-select" onchange="changeSession()">
                        <option value="">All Sessions</option>
                    </select>
                </div>
                <div class="status">
                    <span class="status-dot" id="status-dot"></span>
                    <span id="status-text">Connecting...</span>
                </div>
            </div>
        </header>

        <div class="stats-grid" id="stats-grid">
            <div class="stat-card total">
                <div class="stat-value" id="total-alerts">-</div>
                <div class="stat-label">Total Alerts (Session)</div>
            </div>
            <div class="stat-card high">
                <div class="stat-value" id="high-severity">-</div>
                <div class="stat-label">High Severity</div>
            </div>
            <div class="stat-card medium">
                <div class="stat-value" id="medium-severity">-</div>
                <div class="stat-label">Medium Severity</div>
            </div>
            <div class="stat-card low">
                <div class="stat-value" id="low-severity">-</div>
                <div class="stat-label">Low Severity</div>
            </div>
        </div>

        <div class="charts-grid">
            <div class="chart-card">
                <h3 style="margin-bottom: 15px; color: #00d9ff;">Attack Types Distribution</h3>
                <ul class="attack-type-list" id="attack-types">
                    <li class="no-data">Loading...</li>
                </ul>
            </div>
        </div>

        <div class="alerts-section">
            <div class="section-header">
                <h2>📋 Recent Alerts</h2>
                <button class="refresh-btn" onclick="loadData()">🔄 Refresh</button>
            </div>
            <table id="alerts-table">
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>Attack Type</th>
                        <th>Severity</th>
                    </tr>
                </thead>
                <tbody id="alerts-body">
                    <tr><td colspan="3" class="no-data">Loading alerts...</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        async function loadData() {
            // Load stats
        let currentSessionId = null;
        
        async function loadSessions() {
            try {
                const sessionsRes = await fetch('/api/sessions');
                const sessions = await sessionsRes.json();
                
                const select = document.getElementById('session-select');
                // Keep the first option (All Sessions)
                select.innerHTML = '<option value="">All Sessions</option>';
                
                sessions.forEach(session => {
                    const option = document.createElement('option');
                    option.value = session.session_id;
                    const status = session.status === 'active' ? '🟢' : '⚪';
                    const startTime = session.started_at ? new Date(session.started_at).toLocaleString() : 'Unknown';
                    option.textContent = `${status} ${session.session_id} (${startTime})`;
                    select.appendChild(option);
                });
                
                // Select current session
                const currentRes = await fetch('/api/session/current');
                const current = await currentRes.json();
                if (current.session_id) {
                    select.value = current.session_id;
                    currentSessionId = current.session_id;
                }
            } catch (e) {
                console.error('Failed to load sessions:', e);
            }
        }
        
        async function changeSession() {
            const select = document.getElementById('session-select');
            const sessionId = select.value;
            
            try {
                await fetch('/api/session/set', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: sessionId || null })
                });
                currentSessionId = sessionId || null;
                loadData();
            } catch (e) {
                console.error('Failed to change session:', e);
            }
        }
        
        async function loadData() {
            // Load stats
            try {
                const statsRes = await fetch('/api/alerts/stats');
                const stats = await statsRes.json();
                
                document.getElementById('total-alerts').textContent = stats.total_alerts || 0;
                document.getElementById('high-severity').textContent = stats.high_severity || 0;
                document.getElementById('medium-severity').textContent = stats.medium_severity || 0;
                document.getElementById('low-severity').textContent = stats.low_severity || 0;
                
                // Update attack types
                const attackTypes = stats.by_attack_type || {};
                const attackList = document.getElementById('attack-types');
                attackList.innerHTML = '';
                
                if (Object.keys(attackTypes).length === 0) {
                    attackList.innerHTML = '<li class="no-data">No attacks detected</li>';
                } else {
                    for (const [type, count] of Object.entries(attackTypes)) {
                        const li = document.createElement('li');
                        li.innerHTML = `<span>${type}</span><span class="attack-count">${count}</span>`;
                        attackList.appendChild(li);
                    }
                }
                
                document.getElementById('status-dot').classList.remove('offline');
                document.getElementById('status-dot').classList.add('online');
                document.getElementById('status-text').textContent = 'Connected';
            } catch (e) {
                document.getElementById('status-dot').classList.remove('online');
                document.getElementById('status-dot').classList.add('offline');
                document.getElementById('status-text').textContent = 'Disconnected';
            }
            
            // Load recent alerts
            try {
                const alertsRes = await fetch('/api/alerts?limit=20');
                const alerts = await alertsRes.json();
                
                const tbody = document.getElementById('alerts-body');
                tbody.innerHTML = '';
                
                if (alerts.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="3" class="no-data">No alerts found</td></tr>';
                } else {
                    alerts.forEach(alert => {
                        const tr = document.createElement('tr');
                        const timestamp = new Date(alert.processed_at).toLocaleString();
                        
                        tr.innerHTML = `
                            <td>${timestamp}</td>
                            <td class="attack-type">${alert.attack_type || 'Unknown'}</td>
                            <td><span class="severity-badge severity-${alert.severity}">${alert.severity}</span></td>
                        `;
                        tbody.appendChild(tr);
                    });
                }
            } catch (e) {
                console.error('Failed to load alerts:', e);
            }
        }
        
        // Load sessions and data on page load
        loadSessions();
        loadData();
        
        // Auto-refresh every 10 seconds
        setInterval(loadData, 10000);
        // Refresh sessions every 30 seconds
        setInterval(loadSessions, 30000);
    </script>
</body>
</html>
"""


@app.route('/')
def dashboard():
    """Render the main dashboard."""
    return render_template_string(DASHBOARD_TEMPLATE)


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


@app.route('/api/attack-types')
def get_attack_types():
    """Get list of known attack types."""
    return jsonify(ATTACK_TYPE_MAPPING)


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
