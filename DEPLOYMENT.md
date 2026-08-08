# Deployment Guide: Weather Prediction MCP Server

This guide walks through deploying the Weather Prediction MCP server as a Databricks App and connecting it to an Agent Bricks agent.

## Prerequisites

* Databricks workspace (AWS, Azure, or GCP)
* Access to create Databricks Apps
* Access to Agent Bricks (for creating agents)
* No API keys or external accounts needed (Open-Meteo is public)

## Step-by-Step Deployment

### Part 1: Local Testing (Optional but Recommended)

Before deploying to Databricks, test the MCP server locally to verify it works.

1. **Install dependencies**:
   ```bash
   cd mcp_server
   pip install -r requirements.txt
   ```

2. **Run the test suite**:
   ```bash
   python test_weather.py
   ```
   
   You should see output for 5 test cases:
   * Current weather in Chicago
   * 3-day forecast for Austin, TX
   * Umbrella prediction for Seattle
   * Error handling for invalid location (should fail gracefully)
   * Weather for coordinates (New York)

3. **Start the MCP server locally**:
   ```bash
   python weather_mcp_server.py
   ```
   
   Server will start on `http://localhost:8000`

4. **Test the MCP endpoint** (in another terminal):
   ```bash
   curl http://localhost:8000/mcp/v1/tools
   ```
   
   You should see a JSON response listing the 4 tools.

### Part 2: Deploy MCP Server as Databricks App

1. **Navigate to the mcp_server folder in Databricks**:
   * Open your Databricks workspace
   * Go to Workspace > Users > [your email] > weather-prediction-mcp-server > mcp_server

2. **Create a Databricks App from this folder**:
   * Right-click on the `mcp_server` folder
   * Select **Create App** (or **Deploy as App**)
   * Databricks will detect `app.yaml` and use it for configuration

3. **Configure app settings** (if prompted):
   * **Name**: `weather-mcp-server` (or your preferred name)
   * **Compute**: Use default (serverless recommended)
   * **Permissions**: Set who can access this MCP server (default: only you)
   * No environment variables or secrets needed

4. **Start the app**:
   * Click **Start** or **Deploy**
   * Wait 1-2 minutes for the app to initialize
   * Once running, you'll see a status indicator: ✅ Running

5. **Copy the App URL**:
   * Click on the app to view details
   * Copy the **App URL** (looks like: `https://<workspace-id>.cloud.databricks.com/serving-endpoints/<app-id>`)
   * You'll need this URL in the next step

6. **Test the deployed MCP server**:
   * Open the App URL in your browser
   * You should see MCP server information or a test page
   * Or test with curl: `curl <YOUR_APP_URL>/mcp/v1/tools`

### Part 3: Create Agent Bricks Agent

1. **Open Agent Bricks**:
   * In your Databricks workspace, navigate to **Agent Bricks** (or **AI > Agent Bricks**)
   * Click **Create Agent**

2. **Configure basic agent settings**:
   * **Name**: "Weather Assistant" (or your preferred name)
   * **Description**: "Provides weather forecasts and travel recommendations"

3. **Add the MCP server as an external tool**:
   * In the agent configuration, find the **Tools** section
   * Click **Add Tool** > **External MCP Server**
   * Paste your MCP server App URL from Part 2, Step 5
   * Click **Test Connection**
   * If successful, you should see all 4 tools discovered:
     - `get_current_weather`
     - `get_forecast`
     - `predict_umbrella_needed`
     - `get_travel_recommendation`

4. **Configure the system prompt**:
   * Copy the system prompt from `AGENT_CONFIG.md`
   * Paste it into the **System Prompt** field
   * (Alternatively, start with a simpler prompt and iterate)

5. **Save the agent**:
   * Click **Save** or **Create Agent**
   * The agent is now ready to use

### Part 4: Test the Agent

1. **Open the agent's chat interface**:
   * Click on your newly created agent
   * Open the chat or playground interface

2. **Test with example queries**:

   **Test 1: Current Weather**
   ```
   User: "What's the weather like in Chicago right now?"
   ```
   Expected: Agent calls `get_current_weather("Chicago")` and describes conditions

   **Test 2: Multi-day Forecast**
   ```
   User: "What will the weather be like in Austin for the next 5 days?"
   ```
   Expected: Agent calls `get_forecast("Austin", 5)` and summarizes each day

   **Test 3: Umbrella Prediction**
   ```
   User: "Should I bring an umbrella to Seattle tomorrow?"
   ```
   Expected: Agent calls `predict_umbrella_needed("Seattle", <tomorrow's date>)` and gives yes/no with reasoning

   **Test 4: Travel Recommendation**
   ```
   User: "I'm traveling to Miami this weekend. What should I pack?"
   ```
   Expected: Agent calls `get_travel_recommendation("Miami", <weekend date>)` and provides comprehensive advice

   **Test 5: Error Handling**
   ```
   User: "What's the weather in INVALIDCITY12345?"
   ```
   Expected: Agent handles the error gracefully and asks for clarification

3. **Review agent responses**:
   * Verify the agent is calling the correct tools
   * Check that responses are accurate and helpful
   * Ensure error handling works as expected

### Part 5: Iterate and Improve

Based on testing, you may want to:

1. **Refine the system prompt**:
   * Add more examples for edge cases
   * Clarify when to use each tool
   * Adjust tone and verbosity

2. **Adjust tool behavior** (if needed):
   * Edit `weather_broker.py` to change thresholds (e.g., umbrella at 30% instead of 40%)
   * Add new derived tools (e.g., `check_severe_weather_alerts`)
   * Redeploy the MCP server app after changes

3. **Monitor usage**:
   * Check app logs for tool call patterns
   * Review agent conversation logs
   * Identify common user queries and optimize for them

## Verification Checklist

Before submitting, verify:

* ☐ MCP server deployed and running as Databricks App
* ☐ MCP server URL accessible and returns tool list
* ☐ Agent Bricks agent created with MCP server registered
* ☐ All 4 tools visible in agent configuration
* ☐ System prompt configured
* ☐ Tested at least 3 different query types
* ☐ Error handling works (invalid location)
* ☐ Agent doesn't hallucinate weather data
* ☐ No secrets or API keys committed to repo

## Common Issues and Solutions

### Issue: MCP server fails to start

**Symptoms**: App shows error status, logs show import errors

**Solutions**:
* Check `requirements.txt` - ensure all dependencies are listed
* Verify `app.yaml` command points to correct file: `weather_mcp_server.py`
* Check app logs for specific error messages
* Ensure Python syntax is valid (run `python -m py_compile weather_mcp_server.py` locally)

### Issue: Agent can't connect to MCP server

**Symptoms**: "Connection failed" when adding external MCP tool

**Solutions**:
* Verify the app is running (check Apps page)
* Confirm the App URL is correct (copy it again from the app details)
* Check app permissions - ensure the agent's service principal can access the app
* Test the URL directly in browser or with curl

### Issue: Tools return errors

**Symptoms**: Tools are registered but return "Failed to retrieve weather data"

**Solutions**:
* Check if Open-Meteo API is accessible from Databricks (try `curl https://api.open-meteo.com` from a notebook)
* Review MCP server logs for detailed error messages
* Test `weather_broker.py` functions directly in a notebook
* Verify location names are valid (try "Chicago" or "New York" as simple tests)

### Issue: Agent doesn't call tools

**Symptoms**: Agent responds without calling any tools, or hallucinates data

**Solutions**:
* Review system prompt - ensure it explicitly instructs to call tools
* Add more directive language: "You MUST call the appropriate tool before answering"
* Test with very direct query: "Call get_current_weather for Chicago and tell me the result"
* Check agent logs to see reasoning process

### Issue: Invalid date format errors

**Symptoms**: Date-based tools fail with "Invalid date format"

**Solutions**:
* System prompt should specify YYYY-MM-DD format
* Add examples in system prompt: "Use format 2026-08-10, not August 10 or 8/10/26"
* Consider adding date parsing logic in `weather_broker.py` to handle more formats

## Monitoring and Maintenance

### Daily Checks
* MCP server app status (should be running)
* No unusual errors in app logs

### Weekly Review
* Agent conversation logs - identify common queries
* Tool usage patterns - which tools are most/least used
* Error rate - how often do tools fail

### Monthly Maintenance
* Update dependencies if needed (`requirements.txt`)
* Review and refine system prompt based on usage
* Consider adding new tools based on user requests
* Check Open-Meteo API status/changes

## Scaling Considerations

### High Usage
If your agent becomes heavily used:
* Monitor Open-Meteo API rate limits (~10,000 calls/day)
* Consider caching recent weather results (5-10 minute TTL)
* Add request throttling if needed
* Consider upgrading to a paid weather API for higher limits

### Multiple Agents
To use the same MCP server with multiple agents:
* Keep the MCP server as a shared service
* Configure permissions to allow all agents to access
* Each agent can have different system prompts but use the same tools

### Custom Tools
To add more weather capabilities:
1. Add functions to `weather_broker.py`
2. Expose them as `@mcp.tool` in `weather_mcp_server.py`
3. Redeploy the app
4. Update agent system prompt to describe new tools

## Next Steps

Once deployed and tested:

1. **Document your setup**:
   * Take screenshots of successful agent interactions
   * Record the MCP server URL
   * Save the final system prompt

2. **Share your work**:
   * Push code to your repo (ensure `.gitignore` is working)
   * Include screenshots in README
   * Share the app URL (if workspace access available)

3. **Optional stretch goals**:
   * Build a dashboard to visualize agent queries
   * Add more advanced tools (severe weather alerts, historical data)
   * Integrate multiple weather APIs for redundancy
   * Create a demo video showing the agent in action

## Support Resources

* [Databricks Apps Documentation](https://docs.databricks.com/apps/)
* [Agent Bricks Documentation](https://docs.databricks.com/agents/)
* [FastMCP Documentation](https://github.com/jlowin/fastmcp)
* [Open-Meteo API Documentation](https://open-meteo.com/en/docs)

## Submission Checklist

When ready to submit:

* ☐ All code pushed to repo
* ☐ `.gitignore` configured (no secrets committed)
* ☐ README.md updated with:
  - Architecture diagram or description
  - List of tools and what they do
  - Setup instructions
  - Which weather API used (Open-Meteo)
  - Authentication method (none needed)
* ☐ AGENT_CONFIG.md with system prompt
* ☐ At least 3 screenshots/pastes of agent interactions showing:
  - Natural language questions
  - Tool calls made
  - Final answers provided
* ☐ MCP server deployed and accessible
* ☐ Agent Bricks agent configured and tested

Congratulations! You've successfully built and deployed a weather prediction MCP server with an Agent Bricks agent. 🎉
