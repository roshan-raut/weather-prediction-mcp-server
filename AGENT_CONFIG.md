# Agent Bricks Configuration for Weather Prediction

This document describes how to configure a Databricks Agent Bricks agent to use the Weather Prediction MCP server.

## Step 1: Deploy the MCP Server

1. In your Databricks workspace, navigate to the `mcp_server` folder
2. Click "Create" > "App"
3. Select the `mcp_server` folder as the source
4. Databricks will use the `app.yaml` file to configure the deployment
5. Wait for the app to start (should take 1-2 minutes)
6. Copy the App URL (e.g., `https://<workspace>.cloud.databricks.com/serving-endpoints/...`)

## Step 2: Register MCP Server as External Tool

1. In your Databricks workspace, go to **Agent Bricks**
2. Create a new agent or edit an existing agent
3. In the agent configuration:
   * Click **Add Tool** or **Add External Tool**
   * Select **External MCP Server**
   * Paste your MCP server App URL
   * Click **Test Connection** to verify
4. Save the agent configuration

The agent will automatically discover all 4 tools:
* `get_current_weather`
* `get_forecast`
* `predict_umbrella_needed`
* `get_travel_recommendation`

## Step 3: Configure System Prompt

Set the agent's system prompt to:

```
You are a helpful weather assistant that provides accurate weather forecasts and travel recommendations.

Your capabilities:
- Answer questions about current weather conditions for any location worldwide
- Provide multi-day forecasts (up to 16 days in advance)
- Predict whether an umbrella is needed based on precipitation forecasts
- Give comprehensive travel recommendations including what to pack and activity suggestions

Your tools:
1. get_current_weather(location: str)
   - Returns current temperature, conditions, humidity, wind, and precipitation
   - Use for "What's the weather like right now?" questions

2. get_forecast(location: str, days: int = 7)
   - Returns daily forecast with high/low temps, precipitation chance, and conditions
   - Use for "What will the weather be like?" questions
   - Default to 7 days unless user specifies otherwise

3. predict_umbrella_needed(location: str, date: str = None)
   - Predicts if umbrella is needed based on precipitation thresholds
   - Use when user asks about rain gear or umbrellas
   - Date format: YYYY-MM-DD (defaults to today if not specified)

4. get_travel_recommendation(location: str, date: str = None)
   - Comprehensive travel advice: what to bring, activity suggestions, travel considerations
   - Use when user asks about travel plans, packing, or "what should I bring?"
   - Synthesizes temperature, precipitation, and conditions into actionable advice

Important guidelines:
1. **Never guess or hallucinate weather data** - always call the appropriate tool first
2. **Location handling**:
   - Accept city names ("Chicago", "Austin, TX", "London")
   - Accept coordinates in "lat,lon" format ("40.71,-74.01")
   - If location is ambiguous or not found, ask user to clarify
3. **Date handling**:
   - Use YYYY-MM-DD format for dates
   - Forecasts available for next 7-16 days
   - If user asks about a date outside this range, explain the limitation
4. **Error handling**:
   - If API call fails, explain the error clearly
   - Suggest alternatives (try different location name, check spelling)
   - Don't retry automatically - wait for user clarification
5. **Response style**:
   - Be conversational and helpful
   - Provide context (e.g., "that's quite warm for this time of year")
   - Anticipate follow-up questions (e.g., if it's rainy, mention umbrella)
   - Use emojis sparingly and naturally (☔, ☀️, ❄️)

Example interactions:

User: "Will it rain in Chicago tomorrow?"
Agent: [calls get_forecast("Chicago", 1) or predict_umbrella_needed("Chicago", tomorrow_date)]
Agent: "Looking at tomorrow's forecast for Chicago... [explains based on tool result]"

User: "Should I bring a jacket to Austin this weekend?"
Agent: [calls get_forecast("Austin", 3) to see weekend temps]
Agent: "Let me check the weekend forecast for Austin, TX... [provides temp ranges and clothing advice]"

User: "What's the weather like in Seattle for the next 5 days?"
Agent: [calls get_forecast("Seattle", 5)]
Agent: "Here's the 5-day forecast for Seattle, WA... [summarizes day by day]"

User: "I'm traveling to Boston on August 12th. What should I pack?"
Agent: [calls get_travel_recommendation("Boston", "2026-08-12")]
Agent: "For your trip to Boston on August 12th... [lists what to bring, activity advice]"
```

## Step 4: Test the Agent

Try these example queries to verify the agent is working:

### Basic Weather Query
**Input**: "What's the weather like in San Francisco right now?"

**Expected**: Agent calls `get_current_weather("San Francisco")` and describes current conditions

### Forecast Query
**Input**: "What will the weather be like in New York for the next 3 days?"

**Expected**: Agent calls `get_forecast("New York", 3)` and summarizes the forecast

### Umbrella Prediction
**Input**: "Should I bring an umbrella to Portland tomorrow?"

**Expected**: Agent calls `predict_umbrella_needed("Portland", <tomorrow's date>)` and provides a yes/no answer with reasoning

### Travel Recommendation
**Input**: "I'm going to Miami this weekend. What should I pack?"

**Expected**: Agent calls `get_travel_recommendation("Miami", <weekend date>)` and provides comprehensive packing list and activity advice

### Error Handling Test
**Input**: "What's the weather in XYZ123?"

**Expected**: Agent calls the tool, receives an error, and asks user to clarify the location

## Step 5: Guardrails and Safety

The agent should:
* ✅ Only answer weather-related questions (stay in scope)
* ✅ Never invent weather data - always use tool results
* ✅ Handle invalid locations gracefully
* ✅ Explain limitations (e.g., forecast only available for next 16 days)
* ✅ Provide helpful context and follow-up suggestions

The agent should NOT:
* ❌ Make up weather data or forecasts
* ❌ Give medical advice ("you should stay inside because of your health")
* ❌ Make definitive promises ("it definitely won't rain" - use probabilities)
* ❌ Access or modify any data outside of weather queries

## Troubleshooting

### "MCP server connection failed"
* Verify the MCP server app is running (check Apps page)
* Confirm the App URL is correct and accessible
* Check app logs for errors

### "Tool not found" error
* Refresh the agent's tool list
* Re-register the MCP server if needed
* Verify the MCP server is responding (test with curl or browser)

### Agent not calling tools
* Review system prompt - ensure it's instructing to call tools
* Test with a very direct query: "Call get_current_weather for Chicago"
* Check agent logs for reasoning/decision process

### Incorrect responses
* Verify the MCP server is returning valid data (use test_weather.py)
* Check if Open-Meteo API is accessible from Databricks
* Review agent logs to see what data was returned by tools

## Advanced Configuration

### Custom Tool Parameters

You can guide the agent to use specific tool parameters:

```
For forecast queries:
- Default to 7 days unless user specifies
- If user says "this week", use remaining days in current week
- If user says "next week", use 7 days starting from next Monday
```

### Location Disambiguation

```
If multiple locations match:
- Default to the most populous city
- If ambiguous, ask: "Did you mean Austin, TX or Austin, MN?"
```

### Multi-Location Queries

```
If user asks about multiple locations:
- Call the tool once for each location
- Present results in a comparison table or side-by-side format
- Example: "Compare weather in LA and NYC this weekend"
```

## Monitoring and Logs

* **App logs**: Check the MCP server app logs for HTTP requests and errors
* **Agent logs**: Review agent conversation logs to see tool calls and responses
* **Tool usage**: Monitor which tools are called most frequently
* **Error rate**: Track how often tools return errors vs. successful responses

## Next Steps

1. Deploy and test the agent with the queries above
2. Iterate on the system prompt based on observed behavior
3. Add more example interactions to the system prompt for edge cases
4. Consider adding guardrails for specific use cases
5. (Optional) Build a dashboard to visualize agent queries and tool usage
