"""
Weather Prediction MCP Server.

Exposes weather forecast tools over MCP (Model Context Protocol) so a
Databricks Agent Bricks agent can call them like any other tool:
    - get_current_weather(location)
    - get_forecast(location, days)
    - predict_umbrella_needed(location, date)
    - get_travel_recommendation(location, date)

These tools are backed by Open-Meteo's free weather API (see weather_broker.py),
which requires no signup, no API key, and supports ~10,000 calls/day for
non-commercial use. Students can wire an Agent Bricks agent to answer
natural-language weather questions without any credentials management.

Deploy this as its own Databricks App (same app.yaml + FastMCP entrypoint
pattern documented at
https://docs.databricks.com/aws/en/agents/mcp-tools/custom-mcp), separate
from any dashboard app, so an Agent Bricks agent (or any MCP client) can
register its URL as an external MCP server.

Run locally:
    python weather_mcp_server.py
"""

import os
import logging
import json
from contextvars import ContextVar

from fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

import weather_broker
import lakebase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("weather-mcp-server")

# Context variable to store request headers for accessing end-user identity
_request_context: ContextVar[dict] = ContextVar('request_context', default={})


def _get_end_user_email() -> str:
    """Get the actual end user's email from request headers, or fallback to service principal."""
    # Try to get from X-Forwarded-User header (Databricks App context)
    headers = _request_context.get()
    forwarded_user = headers.get('x-forwarded-user')
    if forwarded_user:
        return forwarded_user
    
    # Fallback: use service principal (local development or non-App contexts)
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    return w.current_user.me().user_name or 'unknown@databricks.com'


def _log_query(tool_name: str, location: str, query_params: dict, result: dict):
    """Log a weather query to the Lakebase database."""
    try:
        user_email = _get_end_user_email()
        error = result.get('error') if isinstance(result, dict) else None
        
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
            json.dumps(result) if result and not error else None,
            error
        ))
        logger.info(f"Logged query: {tool_name} for {location} by {user_email}")
    except Exception as e:
        # Don't fail the tool call if logging fails
        logger.error(f"Failed to log query: {e}")


mcp = FastMCP("weather-prediction")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware to capture HTTP headers containing end-user identity."""
    async def dispatch(self, request: Request, call_next):
        # Capture headers that Databricks injects with user identity
        headers = {
            'x-forwarded-user': request.headers.get('x-forwarded-user'),
            'x-forwarded-email': request.headers.get('x-forwarded-email'),
        }
        _request_context.set(headers)
        response = await call_next(request)
        return response


@mcp.tool
def get_current_weather(location: str) -> dict:
    """
    Get current weather conditions for a given location.
    
    Args:
        location: City name (e.g., "Chicago", "Austin, TX", "London") or
                  lat,lon coordinates (e.g., "41.85,-87.65").
    
    Returns:
        A dict with location name, temperature (°F), conditions, humidity (%),
        wind_speed (mph), precipitation (inches), and ISO timestamp.
    """
    try:
        result = weather_broker.get_current_weather(location)
        _log_query('get_current_weather', location, {'location': location}, result)
        return result
    except ValueError as e:
        result = {"error": str(e)}
        _log_query('get_current_weather', location, {'location': location}, result)
        return result
    except Exception as e:
        logger.exception(f"Error getting current weather for {location}")
        result = {"error": f"Failed to retrieve weather data: {str(e)}"}
        _log_query('get_current_weather', location, {'location': location}, result)
        return result


@mcp.tool
def get_forecast(location: str, days: int = 7) -> dict:
    """
    Get a multi-day weather forecast for a given location.
    
    Args:
        location: City name (e.g., "Chicago", "Austin, TX") or lat,lon coordinates.
        days: Number of days to forecast (1-16, default 7).
    
    Returns:
        A dict with location name and a list of daily forecasts. Each forecast
        includes date, temp_high (°F), temp_low (°F), precipitation_chance (%),
        precipitation_sum (inches), and conditions description.
    """
    try:
        return weather_broker.get_forecast(location, days)
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.exception(f"Error getting forecast for {location}")
        return {"error": f"Failed to retrieve forecast data: {str(e)}"}


@mcp.tool
def predict_umbrella_needed(location: str, date: str = None) -> dict:
    """
    Predict whether an umbrella is needed for a given location and date.
    
    This tool applies reasoning on top of the forecast data:
    - Recommends an umbrella if precipitation chance > 40%
    - Recommends an umbrella if expected precipitation > 0.1 inches
    - Otherwise, no umbrella needed
    
    Args:
        location: City name (e.g., "Chicago") or lat,lon coordinates.
        date: Target date in YYYY-MM-DD format, or None for today.
              Must be within the next 7 days.
    
    Returns:
        A dict with location, date, umbrella_needed (boolean), reason
        (explanation), precipitation_chance (%), precipitation_sum (inches),
        and conditions description.
    """
    try:
        return weather_broker.predict_umbrella_needed(location, date)
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.exception(f"Error predicting umbrella need for {location} on {date}")
        return {"error": f"Failed to generate umbrella prediction: {str(e)}"}


@mcp.tool
def get_travel_recommendation(location: str, date: str = None) -> dict:
    """
    Get a travel recommendation for a given location and date based on weather.
    
    This tool provides actionable advice:
    - What to wear (layers, jacket, light clothing)
    - Whether to bring an umbrella
    - Activity suitability (outdoor activities, indoor backup plans)
    - Travel considerations (delays, road conditions)
    
    Args:
        location: City name (e.g., "Austin", "Seattle") or lat,lon coordinates.
        date: Target date in YYYY-MM-DD format, or None for today.
              Must be within the next 7 days.
    
    Returns:
        A dict with location, date, overall_recommendation, what_to_bring (list),
        activity_advice, and the underlying weather data (temp range, conditions,
        precipitation).
    """
    try:
        # Get the forecast and umbrella prediction
        forecast_data = weather_broker.get_forecast(location, days=7)
        umbrella_data = weather_broker.predict_umbrella_needed(location, date)
        
        # Find the matching day in the forecast
        target_date = umbrella_data["date"]
        matching_day = None
        for day in forecast_data["forecast"]:
            if day["date"] == target_date:
                matching_day = day
                break
        
        if matching_day is None:
            return {"error": f"Could not find forecast for date {target_date}"}
        
        # Build recommendation based on weather
        temp_high = matching_day["temp_high"]
        temp_low = matching_day["temp_low"]
        conditions = matching_day["conditions"]
        precip_chance = matching_day["precipitation_chance"]
        
        what_to_bring = []
        activity_advice = ""
        
        # Temperature-based clothing advice
        if temp_high < 40:
            what_to_bring.append("Heavy winter coat")
            what_to_bring.append("Warm layers")
            activity_advice = "Cold weather - indoor activities recommended, or bundle up for outdoor adventures."
        elif temp_high < 60:
            what_to_bring.append("Jacket or sweater")
            activity_advice = "Cool weather - great for outdoor activities with proper layers."
        elif temp_high < 80:
            what_to_bring.append("Light jacket for evening")
            activity_advice = "Pleasant weather - perfect for outdoor activities and sightseeing."
        else:
            what_to_bring.append("Sunscreen and hat")
            what_to_bring.append("Light, breathable clothing")
            activity_advice = "Hot weather - stay hydrated, seek shade during midday, early morning or evening activities recommended."
        
        # Precipitation-based advice
        if umbrella_data["umbrella_needed"]:
            what_to_bring.append("Umbrella or rain jacket")
            if precip_chance > 70:
                activity_advice += " High chance of rain - have indoor backup plans ready."
            else:
                activity_advice += " Some rain expected - pack rain gear just in case."
        
        # Conditions-based advice
        if "Thunderstorm" in conditions:
            what_to_bring.append("Rain gear")
            activity_advice += " Thunderstorms expected - avoid outdoor activities during storms."
        elif "Snow" in conditions:
            what_to_bring.append("Winter boots and warm clothing")
            activity_advice += " Snowy conditions - allow extra travel time and dress warmly."
        elif "Foggy" in conditions or "fog" in conditions:
            activity_advice += " Foggy conditions - allow extra travel time and drive carefully."
        
        # Overall recommendation
        if temp_high >= 60 and temp_high <= 80 and precip_chance < 30:
            overall = "Excellent travel day! Beautiful weather expected."
        elif precip_chance > 70 or "Thunderstorm" in conditions:
            overall = "Challenging travel day. Weather may impact outdoor plans."
        elif temp_high < 32 or temp_high > 95:
            overall = "Extreme temperatures expected. Plan accordingly."
        else:
            overall = "Good travel day with typical seasonal weather."
        
        result = {
            "location": forecast_data["location"],
            "date": target_date,
            "overall_recommendation": overall,
            "what_to_bring": what_to_bring,
            "activity_advice": activity_advice,
            "weather_summary": {
                "temp_high": temp_high,
                "temp_low": temp_low,
                "conditions": conditions,
                "precipitation_chance": precip_chance,
                "umbrella_needed": umbrella_data["umbrella_needed"]
            }
        }
        _log_query('get_travel_recommendation', location, {'location': location, 'date': date}, result)
        return result
    except ValueError as e:
        result = {"error": str(e)}
        _log_query('get_travel_recommendation', location, {'location': location, 'date': date}, result)
        return result
    except Exception as e:
        logger.exception(f"Error generating travel recommendation for {location} on {date}")
        result = {"error": f"Failed to generate travel recommendation: {str(e)}"}
        _log_query('get_travel_recommendation', location, {'location': location, 'date': date}, result)
        return result


@mcp.tool
def get_current_user() -> dict:
    """
    Get information about the currently authenticated end user accessing the MCP server.
    
    When running as a Databricks App, this returns the actual end user making the
    request (from X-Forwarded-User header), not the service principal running the app.
    
    Returns:
        A dict with user_name (email from X-Forwarded-User header), 
        forwarded_email, and source ("request_header" or "service_principal").
    """
    try:
        # First, try to get the end user from the request headers
        headers = _request_context.get()
        forwarded_user = headers.get('x-forwarded-user')
        forwarded_email = headers.get('x-forwarded-email')
        
        if forwarded_user:
            return {
                "status": "success",
                "user_name": forwarded_user,
                "forwarded_email": forwarded_email,
                "source": "request_header",
            }
        
        # Fallback: return the service principal if headers aren't available
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        user = w.current_user.me()
        return {
            "status": "success",
            "user_name": user.user_name or "unknown@databricks.com",
            "display_name": user.display_name or "Unknown User",
            "source": "service_principal",
        }
    except Exception as e:
        logger.exception("Error getting current user")
        return {"error": f"Failed to get user information: {str(e)}"}


if __name__ == "__main__":
    # Add middleware to capture request headers for end-user identity
    # This must be done before mcp.run() is called
    if hasattr(mcp, 'app') and mcp.app is not None:
        mcp.app.add_middleware(RequestContextMiddleware)
    
    # Databricks Apps route external HTTP traffic to this port via app.yaml;
    # streamable-http is the transport Databricks' MCP client/gateway expects
    port = int(os.getenv("DATABRICKS_APP_PORT", os.getenv("PORT", 8000)))
    mcp.run(transport="http", host="0.0.0.0", port=port)
