"""
Test script to verify weather_broker.py functions work correctly.

Run this locally to test the Open-Meteo API integration before deploying
the MCP server as a Databricks App.

Usage:
    python test_weather.py
"""

import json
import weather_broker

print("\n" + "="*60)
print("Testing Weather Broker Module")
print("="*60)

# Test 1: Get current weather
print("\n[TEST 1] Current weather in Chicago:")
try:
    result = weather_broker.get_current_weather("Chicago")
    print(json.dumps(result, indent=2))
except Exception as e:
    print(f"ERROR: {e}")

# Test 2: Get forecast
print("\n[TEST 2] 3-day forecast for Austin, TX:")
try:
    result = weather_broker.get_forecast("Austin, TX", 3)
    print(json.dumps(result, indent=2))
except Exception as e:
    print(f"ERROR: {e}")

# Test 3: Umbrella prediction
print("\n[TEST 3] Umbrella prediction for Seattle (today):")
try:
    result = weather_broker.predict_umbrella_needed("Seattle")
    print(json.dumps(result, indent=2))
except Exception as e:
    print(f"ERROR: {e}")

# Test 4: Invalid location (error handling)
print("\n[TEST 4] Invalid location (should fail gracefully):")
try:
    result = weather_broker.get_current_weather("XYZ123INVALID")
    print(json.dumps(result, indent=2))
except ValueError as e:
    print(f"✓ Caught expected error: {e}")
except Exception as e:
    print(f"ERROR: Unexpected error: {e}")

# Test 5: Lat/lon coordinates
print("\n[TEST 5] Weather for coordinates (New York: 40.71,-74.01):")
try:
    result = weather_broker.get_current_weather("40.71,-74.01")
    print(json.dumps(result, indent=2))
except Exception as e:
    print(f"ERROR: {e}")

print("\n" + "="*60)
print("Testing Complete!")
print("="*60 + "\n")
