""" 
Open-Meteo weather API adapter module.

This module handles all HTTP calls to the Open-Meteo API (https://open-meteo.com/),
a free weather API that requires no signup or API key. It provides:
    - Current weather conditions
    - Multi-day forecast data
    - Geocoding (converting city names to lat/lon coordinates)

All functions return clean dicts ready for the MCP server to forward to agents.
No secrets management is needed since Open-Meteo is completely free and public.

The MCP server tools (weather_mcp_server.py) call these functions to get
weather data without having any HTTP/parsing logic in the @mcp.tool decorators.
"""

import requests
from datetime import datetime, timedelta
from typing import Optional

# Open-Meteo API endpoints
GEOCODING_API = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_API = "https://api.open-meteo.com/v1/forecast"


def _geocode_location(location: str) -> dict:
    """
    Convert a city name to latitude/longitude coordinates using Open-Meteo's
    geocoding API.
    
    Args:
        location: City name (e.g., "Chicago", "Austin, TX", "London")
    
    Returns:
        A dict with 'latitude', 'longitude', 'name', 'country', and 'timezone'.
    
    Raises:
        ValueError: If the location cannot be found.
    """
    params = {
        "name": location,
        "count": 1,
        "language": "en",
        "format": "json"
    }
    
    response = requests.get(GEOCODING_API, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    if "results" not in data or len(data["results"]) == 0:
        raise ValueError(f"Location '{location}' not found. Please provide a valid city name.")
    
    result = data["results"][0]
    return {
        "latitude": result["latitude"],
        "longitude": result["longitude"],
        "name": result["name"],
        "country": result.get("country", "Unknown"),
        "timezone": result.get("timezone", "UTC")
    }


def get_current_weather(location: str) -> dict:
    """
    Get current weather conditions for a location.
    
    Args:
        location: City name or "lat,lon" coordinates (e.g., "Chicago" or "41.85,-87.65")
    
    Returns:
        A dict with:
            - location: Resolved location name
            - temperature: Current temperature in °F
            - conditions: Weather description
            - humidity: Relative humidity (%)
            - wind_speed: Wind speed in mph
            - precipitation: Current precipitation in inches
            - timestamp: ISO timestamp of the observation
    """
    # Parse location
    if "," in location:
        # Assume lat,lon format
        parts = location.split(",")
        lat = float(parts[0].strip())
        lon = float(parts[1].strip())
        location_name = f"{lat},{lon}"
    else:
        # Geocode city name
        geo = _geocode_location(location)
        lat = geo["latitude"]
        lon = geo["longitude"]
        location_name = f"{geo['name']}, {geo['country']}"
    
    # Get current weather
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "auto"
    }
    
    response = requests.get(WEATHER_API, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    current = data["current"]
    
    # Map WMO weather codes to descriptions
    weather_descriptions = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Foggy",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail"
    }
    
    weather_code = current.get("weather_code", 0)
    conditions = weather_descriptions.get(weather_code, "Unknown")
    
    return {
        "location": location_name,
        "temperature": round(current["temperature_2m"], 1),
        "conditions": conditions,
        "humidity": current["relative_humidity_2m"],
        "wind_speed": round(current["wind_speed_10m"], 1),
        "precipitation": current["precipitation"],
        "timestamp": current["time"]
    }


def get_forecast(location: str, days: int = 7) -> dict:
    """
    Get multi-day weather forecast for a location.
    
    Args:
        location: City name or "lat,lon" coordinates
        days: Number of days to forecast (1-16, default 7)
    
    Returns:
        A dict with:
            - location: Resolved location name
            - forecast: List of daily forecasts, each with:
                - date: Date string (YYYY-MM-DD)
                - temp_high: High temperature in °F
                - temp_low: Low temperature in °F
                - precipitation_chance: Probability of precipitation (%)
                - precipitation_sum: Total precipitation in inches
                - conditions: Weather description
    """
    # Validate days
    if days < 1 or days > 16:
        raise ValueError("Days must be between 1 and 16")
    
    # Parse location
    if "," in location:
        parts = location.split(",")
        lat = float(parts[0].strip())
        lon = float(parts[1].strip())
        location_name = f"{lat},{lon}"
    else:
        geo = _geocode_location(location)
        lat = geo["latitude"]
        lon = geo["longitude"]
        location_name = f"{geo['name']}, {geo['country']}"
    
    # Get forecast
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,weather_code",
        "temperature_unit": "fahrenheit",
        "precipitation_unit": "inch",
        "timezone": "auto",
        "forecast_days": days
    }
    
    response = requests.get(WEATHER_API, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    daily = data["daily"]
    
    # Weather code descriptions (same as current weather)
    weather_descriptions = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Foggy", 48: "Depositing rime fog",
        51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
        61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
        80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
        95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
    }
    
    forecast = []
    for i in range(len(daily["time"])):
        weather_code = daily["weather_code"][i]
        conditions = weather_descriptions.get(weather_code, "Unknown")
        
        forecast.append({
            "date": daily["time"][i],
            "temp_high": round(daily["temperature_2m_max"][i], 1),
            "temp_low": round(daily["temperature_2m_min"][i], 1),
            "precipitation_chance": daily["precipitation_probability_max"][i],
            "precipitation_sum": round(daily["precipitation_sum"][i], 2),
            "conditions": conditions
        })
    
    return {
        "location": location_name,
        "forecast": forecast
    }


def predict_umbrella_needed(location: str, date: Optional[str] = None) -> dict:
    """
    Predict whether an umbrella is needed for a given location and date.
    
    This is a derived judgment based on the forecast data. The logic:
    - If precipitation chance > 40%, recommend an umbrella
    - If precipitation sum > 0.1 inches, recommend an umbrella
    - Otherwise, no umbrella needed
    
    Args:
        location: City name or "lat,lon" coordinates
        date: Date string (YYYY-MM-DD), or None for today
    
    Returns:
        A dict with:
            - location: Resolved location name
            - date: Date of the prediction
            - umbrella_needed: Boolean recommendation
            - reason: Explanation of the recommendation
            - precipitation_chance: Precipitation probability (%)
            - precipitation_sum: Expected precipitation in inches
            - conditions: Weather description
    """
    # Get forecast for the next 7 days
    forecast_data = get_forecast(location, days=7)
    
    # Parse target date
    if date is None:
        target_date = datetime.now().strftime("%Y-%m-%d")
    else:
        # Validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
            target_date = date
        except ValueError:
            raise ValueError(f"Invalid date format: {date}. Use YYYY-MM-DD.")
    
    # Find the matching forecast day
    matching_day = None
    for day in forecast_data["forecast"]:
        if day["date"] == target_date:
            matching_day = day
            break
    
    if matching_day is None:
        raise ValueError(f"Date {target_date} is not in the available forecast range (next 7 days).")
    
    # Apply umbrella logic
    precip_chance = matching_day["precipitation_chance"]
    precip_sum = matching_day["precipitation_sum"]
    
    umbrella_needed = False
    reasons = []
    
    if precip_chance > 40:
        umbrella_needed = True
        reasons.append(f"precipitation chance is {precip_chance}% (threshold: 40%)")
    
    if precip_sum > 0.1:
        umbrella_needed = True
        reasons.append(f"expected precipitation is {precip_sum} inches (threshold: 0.1 inches)")
    
    if not umbrella_needed:
        reason = f"Low chance of rain ({precip_chance}%) and minimal precipitation expected ({precip_sum} inches)."
    else:
        reason = "Bring an umbrella: " + " and ".join(reasons) + "."
    
    return {
        "location": forecast_data["location"],
        "date": target_date,
        "umbrella_needed": umbrella_needed,
        "reason": reason,
        "precipitation_chance": precip_chance,
        "precipitation_sum": precip_sum,
        "conditions": matching_day["conditions"]
    }
