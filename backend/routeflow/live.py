"""Live conditions: weather (Open-Meteo, free, no key) and a time-of-day traffic model.

IMPORTANT: public OSRM has no live traffic. Real-time inputs here are
  1. current weather at the hub (Open-Meteo)  -> slows travel in rain/snow/fog/storms
  2. a time-of-day congestion profile         -> an *assumption*, not measured traffic
Both are combined into one multiplier applied to OSRM driving durations.
"""
import os
from datetime import datetime, timedelta, timezone

import requests

from .geo import HEADERS, TIMEOUT, ttl_cache

WEATHER_URL = os.getenv("ROUTEFLOW_WEATHER_URL", "https://api.open-meteo.com/v1/forecast")

WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Freezing fog", 51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    56: "Freezing drizzle", 57: "Freezing drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain",
    66: "Freezing rain", 67: "Freezing rain", 71: "Light snow", 73: "Snow", 75: "Heavy snow",
    77: "Snow grains", 80: "Rain showers", 81: "Rain showers", 82: "Violent rain showers",
    85: "Snow showers", 86: "Heavy snow showers", 95: "Thunderstorm",
    96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}


def weather_factor(precip_mm=0.0, code=0, wind_kmh=0.0):
    """Travel-time multiplier (1.0 = normal) from current weather. Transparent heuristic."""
    f = 1.0
    if precip_mm >= 7.6:
        f += 0.30
    elif precip_mm >= 2.5:
        f += 0.15
    elif precip_mm > 0:
        f += 0.05
    if code in (71, 73, 75, 77, 85, 86):
        f += 0.25
    if code in (95, 96, 99):
        f += 0.30
    if code in (45, 48):
        f += 0.10
    if wind_kmh > 40:
        f += 0.05
    return round(min(f, 1.6), 3)


def traffic_factor(hour, weekday):
    """Congestion multiplier from local hour (0-23) and weekday (0=Mon). Assumed profile."""
    if weekday >= 5:                                   # weekend
        return 1.10 if 11 <= hour < 20 else 1.0
    if 8 <= hour < 11:
        return 1.35
    if 17 <= hour < 21:
        return 1.45
    if 11 <= hour < 17:
        return 1.15
    if hour >= 22 or hour < 6:
        return 0.95
    return 1.05


def hub_now(utc_offset_s=None):
    """Current local time at the hub (naive datetime)."""
    if utc_offset_s is None:
        return datetime.now()
    return (datetime.now(timezone.utc) + timedelta(seconds=utc_offset_s)).replace(tzinfo=None)


@ttl_cache(300)
def fetch_weather(lat, lon):
    """Current weather at (lat, lon). Never raises; ok=False when offline."""
    try:
        r = requests.get(WEATHER_URL, headers=HEADERS, timeout=TIMEOUT, params={
            "latitude": round(lat, 4), "longitude": round(lon, 4), "timezone": "auto",
            "current": "temperature_2m,precipitation,wind_speed_10m,weather_code"})
        r.raise_for_status()
        data = r.json()
        cur = data["current"]
        code = int(cur.get("weather_code", 0))
        precip = float(cur.get("precipitation", 0.0))
        wind = float(cur.get("wind_speed_10m", 0.0))
        return {"ok": True, "description": WEATHER_CODES.get(code, f"Code {code}"),
                "temperature_c": float(cur.get("temperature_2m", 0.0)),
                "precipitation_mm": precip, "wind_kmh": wind,
                "factor": weather_factor(precip, code, wind),
                "utc_offset_s": int(data.get("utc_offset_seconds", 0))}
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return {"ok": False, "description": "Unavailable (offline)", "temperature_c": None,
                "precipitation_mm": 0.0, "wind_kmh": 0.0, "factor": 1.0, "utc_offset_s": None}


def live_context(lat, lon, use_weather=True, use_traffic=True):
    """Everything the planner needs about 'right now' at the hub."""
    w = fetch_weather(lat, lon) if use_weather else {
        "ok": False, "description": "Disabled", "temperature_c": None, "precipitation_mm": 0.0,
        "wind_kmh": 0.0, "factor": 1.0, "utc_offset_s": None}
    now = hub_now(w["utc_offset_s"])
    t_factor = traffic_factor(now.hour, now.weekday()) if use_traffic else 1.0
    w_factor = w["factor"] if use_weather else 1.0
    return {"weather": w, "now": now, "weather_factor": w_factor,
            "traffic_factor": t_factor, "factor": round(w_factor * t_factor, 3)}