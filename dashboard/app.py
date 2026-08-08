"""
Weather Prediction Dashboard: a Flask app to monitor weather queries made
through the Weather Prediction MCP server.

This app displays:
- Recent weather queries and predictions
- Query statistics (most queried locations, tool usage)
- Weather prediction accuracy tracking

Deploy this as its OWN Databricks App (separate from weather_mcp_server.py) -
one app serves MCP tool calls, the other serves the human-facing UI.

Run locally:
    python app.py
"""

import os
from datetime import datetime, timedelta

from flask import Flask, jsonify, render_template, request

import lakebase

app = Flask(__name__)


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


@app.errorhandler(Exception)
def handle_exception(err):
    """Ensure all unhandled errors return JSON (not an HTML error page)."""
    status_code = getattr(err, "code", 500)
    if not isinstance(status_code, int):
        status_code = 500
    return jsonify({"error": str(err)}), status_code


@app.route("/")
def index():
    """Dashboard UI showing weather query logs and statistics."""
    return render_template("index.html")


@app.route("/api/queries")
def api_queries():
    """
    Get recent weather queries from Lakebase.
    
    Expected table schema:
        CREATE TABLE weather_queries (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT NOW(),
            user_email VARCHAR(255),
            tool_name VARCHAR(100),
            location VARCHAR(255),
            query_params JSONB,
            result JSONB,
            error TEXT
        );
    """
    limit = int(request.args.get("limit", 50))
    
    sql = """
        SELECT 
            id,
            timestamp,
            user_email,
            tool_name,
            location,
            query_params,
            result,
            error
        FROM weather_queries
        ORDER BY timestamp DESC
        LIMIT %s
    """
    
    try:
        rows = lakebase.run_query(sql, (limit,))
        # Convert datetime objects to ISO strings for JSON serialization
        for row in rows:
            if 'timestamp' in row and row['timestamp']:
                row['timestamp'] = row['timestamp'].isoformat()
        return jsonify(rows)
    except Exception as e:
        # If table doesn't exist yet, return empty list
        return jsonify([])


@app.route("/api/statistics")
def api_statistics():
    """
    Get summary statistics from weather queries.
    
    Returns:
    - Total queries
    - Queries by tool
    - Top locations
    - Recent activity trend
    """
    try:
        # Total queries
        total_sql = "SELECT COUNT(*) as total FROM weather_queries"
        total_result = lakebase.run_query(total_sql)
        total_queries = total_result[0]['total'] if total_result else 0
        
        # Queries by tool
        tool_sql = """
            SELECT tool_name, COUNT(*) as count
            FROM weather_queries
            GROUP BY tool_name
            ORDER BY count DESC
        """
        tool_stats = lakebase.run_query(tool_sql)
        
        # Top locations
        location_sql = """
            SELECT location, COUNT(*) as count
            FROM weather_queries
            WHERE location IS NOT NULL
            GROUP BY location
            ORDER BY count DESC
            LIMIT 10
        """
        location_stats = lakebase.run_query(location_sql)
        
        # Recent activity (last 24 hours)
        recent_sql = """
            SELECT COUNT(*) as count
            FROM weather_queries
            WHERE timestamp >= NOW() - INTERVAL '24 hours'
        """
        recent_result = lakebase.run_query(recent_sql)
        recent_queries = recent_result[0]['count'] if recent_result else 0
        
        # Umbrella predictions summary
        umbrella_sql = """
            SELECT 
                (result->>'umbrella_needed')::boolean as umbrella_needed,
                COUNT(*) as count
            FROM weather_queries
            WHERE tool_name = 'predict_umbrella_needed'
              AND result IS NOT NULL
              AND result->>'umbrella_needed' IS NOT NULL
            GROUP BY (result->>'umbrella_needed')::boolean
        """
        umbrella_stats = lakebase.run_query(umbrella_sql)
        
        return jsonify({
            "total_queries": total_queries,
            "recent_24h": recent_queries,
            "by_tool": tool_stats,
            "top_locations": location_stats,
            "umbrella_stats": umbrella_stats
        })
    except Exception as e:
        # If table doesn't exist yet, return empty stats
        return jsonify({
            "total_queries": 0,
            "recent_24h": 0,
            "by_tool": [],
            "top_locations": [],
            "umbrella_stats": []
        })


@app.route("/api/hourly_trend")
def api_hourly_trend():
    """
    Get hourly query trend for the last 24 hours.
    """
    try:
        sql = """
            SELECT 
                DATE_TRUNC('hour', timestamp) as hour,
                COUNT(*) as count
            FROM weather_queries
            WHERE timestamp >= NOW() - INTERVAL '24 hours'
            GROUP BY DATE_TRUNC('hour', timestamp)
            ORDER BY hour
        """
        rows = lakebase.run_query(sql)
        # Convert datetime to ISO string
        for row in rows:
            if 'hour' in row and row['hour']:
                row['hour'] = row['hour'].isoformat()
        return jsonify(rows)
    except Exception as e:
        return jsonify([])


if __name__ == "__main__":
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_RUN_PORT", 8001))
    app.run(debug=True, host=host, port=port)
