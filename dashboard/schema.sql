-- Weather Prediction Dashboard - Database Schema
-- Run this SQL in your Lakebase Postgres database

-- Main table for weather query logs
CREATE TABLE IF NOT EXISTS weather_queries (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    user_email VARCHAR(255),
    tool_name VARCHAR(100) NOT NULL,
    location VARCHAR(255),
    query_params JSONB,
    result JSONB,
    error TEXT,
    execution_time_ms INTEGER,
    CONSTRAINT tool_name_check CHECK (tool_name IN (
        'get_current_weather',
        'get_forecast',
        'predict_umbrella_needed',
        'get_travel_recommendation'
    ))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_weather_queries_timestamp 
    ON weather_queries(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_weather_queries_tool 
    ON weather_queries(tool_name);

CREATE INDEX IF NOT EXISTS idx_weather_queries_location 
    ON weather_queries(location);

CREATE INDEX IF NOT EXISTS idx_weather_queries_user 
    ON weather_queries(user_email);

-- Index for JSONB queries (if you need to filter on result fields)
CREATE INDEX IF NOT EXISTS idx_weather_queries_result_umbrella 
    ON weather_queries((result->>'umbrella_needed')) 
    WHERE tool_name = 'predict_umbrella_needed';

-- Insert sample data for testing (optional)
INSERT INTO weather_queries (user_email, tool_name, location, query_params, result) VALUES
    ('demo@databricks.com', 'get_current_weather', 'Chicago', 
     '{"location": "Chicago"}', 
     '{"temperature": 68.5, "conditions": "Partly cloudy", "humidity": 62, "wind_speed": 8.3}'),
    
    ('demo@databricks.com', 'predict_umbrella_needed', 'Seattle', 
     '{"location": "Seattle", "date": "2026-08-10"}', 
     '{"umbrella_needed": true, "reason": "High precipitation chance (75%)", "precipitation_chance": 75, "precipitation_sum": 0.18}'),
    
    ('demo@databricks.com', 'get_forecast', 'Austin', 
     '{"location": "Austin", "days": 5}', 
     '{"location": "Austin, TX", "forecast": [{"date": "2026-08-10", "temp_high": 92, "temp_low": 73}]}'),
    
    ('demo@databricks.com', 'get_travel_recommendation', 'Boston', 
     '{"location": "Boston", "date": "2026-08-12"}', 
     '{"overall_recommendation": "Excellent travel day! Beautiful weather expected.", "what_to_bring": ["Light jacket"], "weather_summary": {"temp_high": 78, "temp_low": 62}}')
ON CONFLICT DO NOTHING;

-- View for summary statistics (optional, for easier queries)
CREATE OR REPLACE VIEW weather_query_stats AS
SELECT 
    DATE_TRUNC('day', timestamp) as query_date,
    tool_name,
    COUNT(*) as query_count,
    COUNT(DISTINCT location) as unique_locations,
    COUNT(DISTINCT user_email) as unique_users,
    AVG(execution_time_ms) as avg_execution_ms
FROM weather_queries
GROUP BY DATE_TRUNC('day', timestamp), tool_name;

-- View for umbrella prediction summary
CREATE OR REPLACE VIEW umbrella_predictions AS
SELECT 
    location,
    (result->>'umbrella_needed')::boolean as umbrella_needed,
    (result->>'precipitation_chance')::numeric as precipitation_chance,
    timestamp
FROM weather_queries
WHERE tool_name = 'predict_umbrella_needed'
  AND result IS NOT NULL
  AND result->>'umbrella_needed' IS NOT NULL
ORDER BY timestamp DESC;

-- Grant permissions (adjust role name as needed)
-- GRANT SELECT ON weather_queries TO your_readonly_role;
-- GRANT SELECT ON weather_query_stats TO your_readonly_role;
-- GRANT SELECT ON umbrella_predictions TO your_readonly_role;
