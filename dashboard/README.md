# Weather Prediction Dashboard

A Flask-based dashboard to monitor weather queries made through the Weather Prediction MCP server. This app displays real-time statistics, query logs, and analytics for Agent Bricks interactions with weather data.

## Features

- **Real-time Query Monitoring**: View recent weather queries as they happen
- **Usage Statistics**: See which tools are used most, top queried locations, and query trends
- **Umbrella Predictions**: Track how often umbrellas are recommended
- **Auto-refresh**: Dashboard updates automatically every 15 seconds

## Architecture

This dashboard is deployed as a **separate Databricks App** from the MCP server:
- `weather_mcp_server` (in `../mcp_server/`) → Serves MCP tool calls
- `dashboard` (this folder) → Serves the human-facing UI

## Database Schema

The dashboard expects a Lakebase Postgres database with the following table:

```sql
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

-- Create index for performance
CREATE INDEX idx_weather_queries_timestamp ON weather_queries(timestamp DESC);
CREATE INDEX idx_weather_queries_tool ON weather_queries(tool_name);
CREATE INDEX idx_weather_queries_location ON weather_queries(location);
```

### Example Data

```sql
-- Example: Current weather query
INSERT INTO weather_queries (user_email, tool_name, location, query_params, result)
VALUES (
    'user@example.com',
    'get_current_weather',
    'Chicago',
    '{"location": "Chicago"}',
    '{"temperature": 68.5, "conditions": "Partly cloudy", "humidity": 62}'
);

-- Example: Umbrella prediction
INSERT INTO weather_queries (user_email, tool_name, location, query_params, result)
VALUES (
    'user@example.com',
    'predict_umbrella_needed',
    'Seattle',
    '{"location": "Seattle", "date": "2026-08-10"}',
    '{"umbrella_needed": true, "reason": "High precipitation chance (75%)", "precipitation_chance": 75}'
);
```

## Setup Instructions

### 1. Create Lakebase Database

**Note**: The user will manually create the Lakebase database, role, and connection string.

You need:
1. A Lakebase Postgres instance
2. A database (e.g., `weather_analytics`)
3. A native Postgres role with a static password
4. The connection string format:
   ```
   postgresql://role:password@host:5432/database?sslmode=require
   ```

### 2. Store Connection String as Secret

1. Base64-encode your connection string:
   ```bash
   echo -n "postgresql://role:password@host:5432/weather_analytics?sslmode=require" | base64
   ```

2. Store in Databricks secrets:
   ```bash
   databricks secrets create-scope database
   databricks secrets put-secret database lakebase-url --string-value "<base64-encoded-url>"
   ```

   Or via UI:
   - Go to Settings → Secrets
   - Create scope: `database`
   - Add secret: `lakebase-url` with base64-encoded connection string

### 3. Create Database Table

Connect to your Lakebase database and run the schema SQL above to create the `weather_queries` table.

### 4. Deploy Dashboard as Databricks App

1. Navigate to the `dashboard` folder in your Databricks workspace
2. Click "Create App" or use the Databricks CLI
3. The app will use `app.yaml` for configuration
4. Environment variables are set in `app.yaml`:
   - `LAKEBASE_SECRET_SCOPE`: `database`
   - `LAKEBASE_SECRET_KEY`: `lakebase-url`

### 5. Connect MCP Server to Database (Optional)

To automatically log queries, modify your MCP server (`weather_mcp_server.py`) to insert records into the `weather_queries` table after each tool call.

Example logging code:
```python
import lakebase

def log_query(user_email, tool_name, location, query_params, result, error=None):
    """Log a weather query to Lakebase."""
    sql = """
        INSERT INTO weather_queries 
        (user_email, tool_name, location, query_params, result, error)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    lakebase.run_write(sql, (
        user_email,
        tool_name,
        location,
        json.dumps(query_params),
        json.dumps(result) if result else None,
        error
    ))
```

## Local Testing

1. Install dependencies:
   ```bash
   cd dashboard
   pip install -r requirements.txt
   ```

2. Set environment variables:
   ```bash
   export LAKEBASE_SECRET_SCOPE=database
   export LAKEBASE_SECRET_KEY=lakebase-url
   ```

3. Run the Flask app:
   ```bash
   python app.py
   ```

4. Open `http://localhost:8001` in your browser

## API Endpoints

- `GET /` - Dashboard UI
- `GET /api/queries?limit=50` - Get recent weather queries (default: 50)
- `GET /api/statistics` - Get summary statistics
- `GET /api/hourly_trend` - Get hourly query trend for last 24 hours
- `GET /healthz` - Health check endpoint

## Troubleshooting

### "No data yet" / Empty Dashboard

If the dashboard shows no data:
1. Verify the `weather_queries` table exists in your Lakebase database
2. Check that the connection string secret is correctly configured
3. Ensure your MCP server is logging queries to the database
4. Check Flask app logs for connection errors

### Database Connection Errors

```python
# Test your connection string manually:
import lakebase
try:
    result = lakebase.run_query("SELECT 1")
    print("Connection successful:", result)
except Exception as e:
    print("Connection failed:", e)
```

## Security Notes

- Never commit connection strings or passwords to git
- Always store credentials in Databricks secrets
- Use base64 encoding for the connection string in secrets
- Ensure your Lakebase role has minimal necessary permissions (SELECT on `weather_queries`)

## Dashboard Screenshots

The dashboard displays:
- Summary cards: Total queries, top location, umbrella predictions, most used tool
- Tool usage statistics: Breakdown of queries by tool type
- Top locations: Most frequently queried cities
- Recent queries table: Real-time log of weather queries with timestamps, tool names, locations, and results
