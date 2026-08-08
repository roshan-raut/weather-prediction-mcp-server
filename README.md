## Homework: Build Your Own Weather-Prediction MCP Server + Agent

**Date**: 2026-08-08 **Based on**: Day 3 (databricks-lakebase-app-day-3) - Agent Bricks + Alpaca Markets paper-trading MCP server

## TL;DR

Using this repo as a reference pattern (not a template to copy verbatim), build your **own** MCP server that exposes weather-forecast tools, and wire a** Databricks Agent Bricks agent** to use it to answer weather questions and make simple predictions/recommendations. You'll deploy both as Databricks Apps, same as Day 3's mcp_server/ + dashboard/ split.

## What you're building

1. **An MCP server **(FastMCP, same as mcp_server/alpaca_mcp_server.py) exposing weather tools backed by a free weather API (no paid tier, no credit card required to start).
2. ** A broker/adapter module** (same role as alpaca_broker.py) that calls the weather API and returns clean dicts - keep your MCP tool functions thin, push the HTTP/parsing logic into this module.
3. **A Databricks Agent Bricks agent** that uses your MCP server as an external tool to answer natural-language weather questions (e.g. "Will it rain in Chicago tomorrow?", "Should I bring a jacket to Austin this weekend?").
4. _(Optional stretch)_ A small dashboard app (like dashboard/) that shows recent agent queries/predictions - not required for a passing grade, but nice for extra credit.

## Suggested free weather APIs (pick one)

Open-Meteo - no signup, no API key~10,000 calls/day (non-commercial)

National Weather Service API (weather.gov) - no signup, no API key US-only. Official NOAA data - great for alerts + forecasts, but only works for US locations.

WeatherAPI.com API key (free signup) 100,000 calls/month Good if you want current + forecast + historical in one call, and don't mind a quick signup.'

**Recommendation**: start with **Open-Meteo** - it needs zero credentials, so you can build and test the whole pipeline before worrying about secrets management at all. If you want alerts or US-specific severe weather data, layer in the NWS API as a second tool.

## Required MCP tools (minimum 3)

Design your own tool names/signatures, but your MCP server must expose **at least these three capabilities** (e.g model them after `get_quote`/`get_positions`/`get_account_summary` as in `mcp_server/alpaca_mcp_server.py`):

1. **Current conditions** - e.g. `get_current_weather(location)` - temperature, conditions, humidity, wind for a given location (city name, zip, or lat/lon - your choice).

2. Forecast - e.g. `get_forecast(location, days)` - a multi-day forecast (temp high/low, precipitation chance, conditions) for the next N days.

3. Simple prediction/recommendation - e.g. `predict_umbrella_needed(location, date)` or `get_travel_recommendation(location, date) `- some derived judgment call built from the raw forecast data (e.g. "bring an umbrella if precipitation chance > 40%"). This is where you show reasoning, not just a passthrough of the raw API response.

Stretch tools (optional, for extra credit): severe weather alerts, historical weather lookup, comparing weather across multiple cities.

## Requirements checklist

- MCP server built with FastMCP (or another MCP-compliant framework), exposing your tools via @mcp.tool decorators, following the streamable-HTTP pattern from mcp_server/alpaca_mcp_server.py.
- A separate adapter module (like alpaca_broker.py) containing all HTTP calls/parsing - no raw requests calls inside your @mcp.tool functions.
- If your chosen API requires a key: store it as a Databricks secret, never hardcode it or commit it to the repo. Follow the _secret() / WorkspaceClient().secrets.get_secret() pattern in mcp_server/alpaca_broker.py.
- requirements.txt and app.yaml for your MCP server app (see mcp_server/ for the pattern), deployed as its own Databricks App.
- A Databricks Agent Bricks agent registered against your MCP server as an external tool (same steps as Day 3's README, section "Register the MCP server as an external MCP" and "Build the Agent Bricks agent").
- A clear system prompt for your agent describing what it should do, which tools to call in what order, and any guardrails (e.g. "only answer for locations you can resolve; if the API call fails, say so rather than guessing").
- A short README.md for your submission (architecture diagram optional but encouraged, list of tools, setup steps, and which weather API + auth method you used).
- Demonstrate the agent working: paste or screenshot at least 3 different natural-language questions and the agent's tool-calling + final answers.

## What "good" looks like

- Tool functions have clear docstrings (Args/Returns), matching the style in mcp_server/alpaca_mcp_server.py.
- Error handling: a bad location or API outage returns a clean error, not a stack trace, and the agent can react sensibly (e.g. ask the user to clarify).
- The "prediction" tool does more than echo the raw API - it applies some threshold/logic of your choosing and explains it in the tool's docstring.
- No secrets committed to git. No hardcoded API keys.
- The agent's system prompt is specific enough that the agent doesn't hallucinate weather data it didn't get from a tool call.

## Submission

Push your MCP server + agent config (system prompt, tool list) to your own repo/branch and share the link, along with your Databricks App URLs (or screenshots if you can't share workspace access). Include your README.

---

# Weather Prediction MCP Server - Implementation

## Architecture

This implementation follows the homework requirements and the reference pattern from `databricks-lakebase-app-day-3`:

```
weather-prediction-mcp-server/
├── mcp_server/
│   ├── weather_mcp_server.py    # FastMCP server with @mcp.tool decorators
│   ├── weather_broker.py         # Adapter module - all HTTP/API calls
│   ├── requirements.txt          # Python dependencies
│   ├── app.yaml                  # Databricks App configuration
│   └── test_weather.py           # Test suite
├── dashboard/
│   ├── app.py                    # Flask dashboard app
│   ├── lakebase.py               # Lakebase connection helper
│   ├── templates/
│   │   └── index.html            # Dashboard UI
│   ├── requirements.txt          # Dashboard dependencies
│   ├── app.yaml                  # Dashboard app configuration
│   ├── schema.sql                # Database schema
│   └── README.md                 # Dashboard setup guide
└── README.md                      # This file
```

## Weather API: Open-Meteo

**Selected API**: [Open-Meteo](https://open-meteo.com/)

**Why Open-Meteo**:
* Zero credentials needed - no signup, no API key
* ~10,000 calls/day for non-commercial use
* Supports current conditions + 16-day forecast
* Global coverage with built-in geocoding
* Free and reliable for educational projects

**Authentication**: None required

## MCP Tools Exposed

The server exposes **4 tools** (exceeding the minimum 3 requirement):

### 1. `get_current_weather(location: str)`
Returns current weather conditions including:
* Temperature (°F), humidity (%), wind speed (mph)
* Weather conditions (clear, cloudy, rain, snow, etc.)
* Current precipitation
* Timestamp

**Example**: `get_current_weather("Chicago")`

### 2. `get_forecast(location: str, days: int = 7)`
Returns multi-day forecast (1-16 days) with:
* Daily high/low temperatures
* Precipitation chance (%) and total expected precipitation
* Weather conditions for each day

**Example**: `get_forecast("Austin, TX", 5)`

### 3. `predict_umbrella_needed(location: str, date: str = None)`
**Prediction/reasoning tool** - applies logic on top of raw forecast data:
* Recommends umbrella if precipitation chance > 40%
* Recommends umbrella if expected precipitation > 0.1 inches
* Returns boolean recommendation + detailed explanation

**Example**: `predict_umbrella_needed("Seattle", "2026-08-10")`

### 4. `get_travel_recommendation(location: str, date: str = None)`
**Advanced prediction tool** - comprehensive travel advice:
* What to bring (clothing layers, rain gear, sunscreen)
* Activity suitability (outdoor vs indoor recommendations)
* Travel considerations (delays, road conditions)
* Overall recommendation based on weather conditions

**Example**: `get_travel_recommendation("Boston", "2026-08-12")`

## Setup & Deployment

### Local Testing

1. Install dependencies:
   ```bash
   cd mcp_server
   pip install -r requirements.txt
   ```

2. Run the MCP server locally:
   ```bash
   python weather_mcp_server.py
   ```

3. Server will be available at `http://localhost:8000`

### Deploy as Databricks App

1. Navigate to the `mcp_server` folder in your Databricks workspace
2. Create a new Databricks App from this folder
3. The app will use `app.yaml` to configure the deployment
4. No secrets configuration needed (Open-Meteo is public)

### Register as External MCP Server

Once deployed, note the Databricks App URL (e.g., `https://<workspace>.cloud.databricks.com/...`).

Register this URL as an external MCP server in Agent Bricks:
1. Go to Agent Bricks in your Databricks workspace
2. Create a new agent or edit an existing one
3. Add "External MCP Tool" and paste your MCP server URL
4. The agent will now have access to all 4 weather tools

## Agent System Prompt

Recommended system prompt for the Agent Bricks agent:

```
You are a helpful weather assistant that provides accurate weather forecasts and travel recommendations.

Your tools:
- get_current_weather: Get current conditions for any location
- get_forecast: Get multi-day forecast (up to 16 days)
- predict_umbrella_needed: Predict if an umbrella is needed based on weather
- get_travel_recommendation: Provide comprehensive travel advice based on weather

Guidelines:
1. Always call the appropriate weather tool - never guess or hallucinate weather data
2. If a location cannot be found, ask the user to clarify (provide a valid city name)
3. If an API call fails, explain the error clearly and suggest alternatives
4. When predicting or recommending, explain your reasoning based on the data
5. For dates, use YYYY-MM-DD format (forecasts available for next 7-16 days)
6. Provide helpful context: temperature ranges, what to wear, activity suggestions

Example queries you can answer:
- "Will it rain in Chicago tomorrow?"
- "Should I bring a jacket to Austin this weekend?"
- "What's the weather like in Seattle for the next 5 days?"
- "Is it a good day to travel to Boston on August 12th?"
```

## Code Quality Features

✅ **Clear separation of concerns**: MCP server (`weather_mcp_server.py`) contains only thin tool wrappers; all HTTP calls and parsing logic lives in the adapter module (`weather_broker.py`)

✅ **Comprehensive docstrings**: Every tool and function has clear Args/Returns documentation

✅ **Error handling**: All tools catch exceptions and return clean error messages instead of stack traces. The agent can react sensibly to bad locations or API failures.

✅ **Reasoning in prediction tools**: 
- `predict_umbrella_needed` applies threshold logic (40% chance, 0.1" precipitation) and explains the decision
- `get_travel_recommendation` synthesizes multiple data points (temperature, precipitation, conditions) into actionable advice

✅ **No secrets committed**: Open-Meteo requires no API key, so there are no secrets to manage

✅ **No hallucination**: The system prompt explicitly instructs the agent to only use data from tool calls, never guess weather information

## Demonstration Examples

### Example 1: Current Weather Query
**User**: "What's the weather like in Chicago right now?"

**Agent calls**: `get_current_weather("Chicago")`

**Response**: "Currently in Chicago, IL, United States, it's 68.5°F with partly cloudy skies. Humidity is at 62%, wind speed is 8.3 mph, and there's no precipitation. (Data as of 2026-08-08T14:30:00Z)"

### Example 2: Umbrella Prediction
**User**: "Should I bring an umbrella to Seattle tomorrow?"

**Agent calls**: `predict_umbrella_needed("Seattle", "2026-08-09")`

**Response**: "Yes, bring an umbrella to Seattle, WA, United States on 2026-08-09. There's a 75% chance of precipitation (threshold: 40%) with 0.18 inches expected. Conditions: Moderate rain."

### Example 3: Travel Recommendation
**User**: "I'm traveling to Austin this weekend. What should I pack?"

**Agent calls**: `get_travel_recommendation("Austin", "2026-08-10")`

**Response**: "Excellent travel day in Austin, TX, United States! Beautiful weather expected on 2026-08-10.

**What to bring**:
- Light jacket for evening
- Sunscreen and hat
- Light, breathable clothing

**Activity advice**: Hot weather - stay hydrated, seek shade during midday, early morning or evening activities recommended. Pleasant weather - perfect for outdoor activities and sightseeing.

**Weather summary**: High of 92°F, low of 73°F, clear sky, 10% chance of rain."

## Testing the MCP Server

You can test individual tools directly:

```python
import weather_broker

# Test current weather
print(weather_broker.get_current_weather("New York"))

# Test forecast
print(weather_broker.get_forecast("London", 3))

# Test umbrella prediction
print(weather_broker.predict_umbrella_needed("Portland", "2026-08-10"))
```

---

## 📊 Weather Prediction Dashboard (Stretch Goal)

A **Flask-based monitoring dashboard** that displays real-time weather query analytics from your Agent Bricks interactions. This dashboard is deployed as a **separate Databricks App** and reads query logs from a **Lakebase Postgres database**.

### Dashboard Features

* **Real-time Query Monitoring** - View recent weather queries as they happen
* **Usage Statistics** - See which tools are used most, top queried locations, and query trends  
* **Umbrella Predictions Tracking** - Analytics on how often umbrellas are recommended
* **Auto-refresh** - Dashboard updates automatically every 15 seconds

### Architecture: Two Apps, One System

```
┌─────────────────────────┐        ┌──────────────────────────┐
│   Weather MCP Server    │        │   Weather Dashboard      │
│   (mcp_server/)         │        │   (dashboard/)           │
│                         │        │                          │
│  • FastMCP tools        │        │  • Flask UI              │
│  • Open-Meteo API       │        │  • Query analytics       │
│  • Serves Agent Bricks  │───────▶│  • Lakebase reader       │
│                         │ logs   │  • Real-time stats       │
└─────────────────────────┘        └──────────────────────────┘
           │                                    │
           │                                    │
           └────────────────┬───────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │  Lakebase        │
                  │  (Postgres)      │
                  │                  │
                  │  weather_queries │
                  └──────────────────┘
```

### Quick Setup

1. **Create your Lakebase database** with a native Postgres role (you'll do this manually)

2. **Run the schema** to create the `weather_queries` table:
   ```bash
   psql <your-connection-string> -f dashboard/schema.sql
   ```

3. **Store your connection string** as a Databricks secret:
   ```bash
   # Base64 encode it first
   echo -n "postgresql://role:password@host:5432/db?sslmode=require" | base64
   
   # Store in secrets
   databricks secrets put-secret database lakebase-url --string-value "<base64-string>"
   ```

4. **Deploy the dashboard** as a Databricks App from the `dashboard/` folder

5. **Connect your MCP server** to log queries (optional - see `dashboard/README.md` for logging code)

### What You'll See

The dashboard displays:
* Summary cards: Total queries, top location, umbrella predictions, most used tool
* Tool usage statistics: Breakdown by tool type
* Top locations: Most frequently queried cities  
* Recent queries table: Real-time log with timestamps, tools, locations, and results

### Full Documentation

See [dashboard/README.md](dashboard/README.md) for:
* Complete database schema
* Step-by-step setup instructions
* MCP server integration code
* Troubleshooting guide
* API endpoints reference

**Note**: The dashboard is a **stretch goal** for extra credit - it's not required for a passing grade, but it demonstrates a production-ready monitoring solution for your MCP server.