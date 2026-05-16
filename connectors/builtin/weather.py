"""
OpenMeteo Weather Connector for Aethera
Fetches weather data from the Open-Meteo API.
API: https://api.open-meteo.com/
Free, no API key required. Generous rate limits.
"""
import asyncio
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..connector_base import AetheraConnector, ConnectorConfig, ConnectorResult


class WeatherConnector(AetheraConnector):
    """OpenMeteo weather API connector (free, no key required)."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "https://api.open-meteo.com/v1/")
        self.geocode_url = "https://geocoding-api.open-meteo.com/v1/search"
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limit_lock = asyncio.Lock()
        self._last_request_time: float = 0.0

    def get_config(self) -> ConnectorConfig:
        return ConnectorConfig(
            name="weather",
            version="1.0.0",
            description="OpenMeteo - Free weather data (current, forecast, historical)",
            base_url=self.base_url,
            auth_type="none",
            rate_limit=600,
            timeout=30,
        )

    async def initialize(self) -> bool:
        self._client = httpx.AsyncClient(
            timeout=self.get_config().timeout,
            headers={"Accept": "application/json", "User-Agent": "AetheraAI/1.0"},
        )
        return True

    async def cleanup(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _rate_limited_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        config = self.get_config()
        if config.rate_limit:
            min_interval = 60.0 / config.rate_limit
            async with self._rate_limit_lock:
                now = asyncio.get_event_loop().time()
                elapsed = now - self._last_request_time
                if elapsed < min_interval:
                    await asyncio.sleep(min_interval - elapsed)
                self._last_request_time = asyncio.get_event_loop().time()

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
            reraise=True,
        )
        async def _do_request() -> httpx.Response:
            response = await self._client.request(method, url, **kwargs)
            response.raise_for_status()
            return response

        return await _do_request()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def search(self, query: str = "", **params) -> ConnectorResult:
        """Geocode a location name to coordinates for weather queries.

        Keyword Args:
            limit: Max results (1-10, default 5).
            country: Country code filter (e.g. 'US').
            language: Language for results (default 'en').
        """
        if not query:
            return ConnectorResult(success=False, error="Location search query required")

        qp: Dict[str, Any] = {
            "name": query,
            "count": min(int(params.get("limit", 5)), 10),
            "language": params.get("language", "en"),
            "format": "json",
        }
        if params.get("country"):
            qp["countryCodes"] = params["country"]

        try:
            response = await self._rate_limited_request("GET", self.geocode_url, params=qp)
            data = response.json()
            results = data.get("results", [])

            return ConnectorResult(
                success=True,
                data=[
                    {
                        "name": r.get("name", ""),
                        "country": r.get("country", ""),
                        "country_code": r.get("country_code", ""),
                        "latitude": r.get("latitude", 0.0),
                        "longitude": r.get("longitude", 0.0),
                        "elevation": r.get("elevation", 0.0),
                        "timezone": r.get("timezone", ""),
                        "population": r.get("population", 0),
                        "admin1": r.get("admin1", ""),
                    }
                    for r in results
                ],
                metadata={"source": "OpenMeteo Geocoding", "query": query},
            )
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"Geocoding API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def get(self, item_id: str, **params) -> ConnectorResult:
        """Get weather for a location. item_id can be 'lat,lon' or a place name.

        Args:
            item_id: Location as 'latitude,longitude' (e.g. '40.71,-74.01')
                     or a place name (will be geocoded).
        Keyword Args:
            current: Comma-separated current weather variables
                     (default 'temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code').
            daily: Comma-separated daily forecast variables
                   (default 'weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum').
            hourly: Comma-separated hourly variables (default none).
            forecast_days: Number of forecast days (1-16, default 7).
            past_days: Number of past days (0-92, default 0).
            units: 'metric', 'imperial', or 'uk_hybrid' (default 'metric').
            timezone: Timezone identifier (default 'auto').
        """
        # Determine lat/lon
        lat: Optional[float] = None
        lon: Optional[float] = None

        if "," in item_id:
            parts = item_id.split(",", 1)
            try:
                lat = float(parts[0].strip())
                lon = float(parts[1].strip())
            except ValueError:
                pass

        if lat is None or lon is None:
            # Geocode the place name
            geo_result = await self.search(query=item_id, limit=1)
            if not geo_result.success or not geo_result.data:
                return ConnectorResult(success=False, error=f"Could not geocode '{item_id}'")
            first = geo_result.data[0]
            lat = first.get("latitude", 0.0)
            lon = first.get("longitude", 0.0)

        units = params.get("units", "metric")
        # Open-Meteo uses specific parameter names for unit systems
        temp_unit = "celsius" if units == "metric" else "fahrenheit"
        wind_unit = "kmh" if units == "metric" else "mph"

        qp: Dict[str, Any] = {
            "latitude": lat,
            "longitude": lon,
            "current": params.get(
                "current",
                "temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,weather_code",
            ),
            "temperature_unit": temp_unit,
            "wind_speed_unit": wind_unit,
            "timezone": params.get("timezone", "auto"),
        }

        if params.get("daily"):
            qp["daily"] = params["daily"]
        elif params.get("forecast_days", 7) > 0:
            qp["daily"] = params.get(
                "daily",
                "weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,precipitation_sum",
            )
            qp["forecast_days"] = params.get("forecast_days", 7)

        if params.get("hourly"):
            qp["hourly"] = params["hourly"]

        if params.get("past_days"):
            qp["past_days"] = params["past_days"]

        try:
            response = await self._rate_limited_request("GET", "forecast", params=qp)
            data = response.json()
            return ConnectorResult(
                success=True,
                data=self._normalize_weather(data),
                metadata={
                    "source": "OpenMeteo",
                    "latitude": lat,
                    "longitude": lon,
                    "units": units,
                    "timezone": data.get("timezone", ""),
                },
            )
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"Weather API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def fetch(self, endpoint: str, params: Optional[Dict] = None) -> ConnectorResult:
        params = params or {}
        if endpoint == "search":
            return await self.search(query=params.pop("query", ""), **params)
        if endpoint in ("get", "forecast", "current"):
            location = params.pop("location", params.pop("id", ""))
            return await self.get(location, **params)
        return ConnectorResult(success=False, error=f"Unknown endpoint: {endpoint}")

    @staticmethod
    def _normalize_weather(data: Dict) -> Dict:
        current = data.get("current", {})
        current_units = data.get("current_units", {})
        daily = data.get("daily", {})

        current_weather = {}
        if current:
            for key, value in current.items():
                if key == "time":
                    current_weather["time"] = value
                elif key == "weather_code":
                    current_weather["weather_code"] = value
                    current_weather["weather_description"] = WeatherConnector._weather_code_description(value)
                else:
                    unit = current_units.get(key, "")
                    current_weather[key] = {"value": value, "unit": unit} if unit else value

        daily_forecast = {}
        if daily:
            daily_units = data.get("daily_units", {})
            time_list = daily.get("time", [])
            for key, values in daily.items():
                if key == "time":
                    continue
                if isinstance(values, list) and len(values) == len(time_list):
                    unit = daily_units.get(key, "")
                    daily_forecast[key] = {"values": values, "unit": unit} if unit else values

        return {
            "latitude": data.get("latitude", 0.0),
            "longitude": data.get("longitude", 0.0),
            "elevation": data.get("elevation", 0.0),
            "timezone": data.get("timezone", ""),
            "current": current_weather,
            "daily": daily_forecast,
            "daily_dates": daily.get("time", []),
        }

    @staticmethod
    def _weather_code_description(code: int) -> str:
        """Convert WMO weather code to human-readable description."""
        descriptions = {
            0: "Clear sky",
            1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Foggy", 48: "Depositing rime fog",
            51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
            56: "Light freezing drizzle", 57: "Dense freezing drizzle",
            61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            66: "Light freezing rain", 67: "Heavy freezing rain",
            71: "Slight snowfall", 73: "Moderate snowfall", 75: "Heavy snowfall",
            77: "Snow grains",
            80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
            85: "Slight snow showers", 86: "Heavy snow showers",
            95: "Thunderstorm", 96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail",
        }
        return descriptions.get(code, f"Unknown weather code {code}")

    def to_tool_definition(self) -> Dict[str, Any]:
        config = self.get_config()
        return {
            "type": "connector",
            "name": config.name,
            "description": config.description,
            "base_url": config.base_url,
            "auth_type": config.auth_type,
            "endpoints": [
                {
                    "name": "search",
                    "description": "Geocode a location name to coordinates",
                    "parameters": [
                        {"name": "query", "type": "string", "description": "Location name"},
                        {"name": "country", "type": "string", "description": "Country code filter"},
                    ],
                },
                {
                    "name": "get",
                    "description": "Get weather for a location (lat,lon or place name)",
                    "parameters": [
                        {"name": "location", "type": "string", "required": True, "description": "lat,lon or place name"},
                        {"name": "units", "type": "string", "description": "metric, imperial, uk_hybrid"},
                        {"name": "forecast_days", "type": "integer", "description": "Forecast days (1-16)"},
                    ],
                },
            ],
        }


def register_connector():
    return WeatherConnector, {"base_url": "https://api.open-meteo.com/v1/"}