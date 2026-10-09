import requests

lat, lon = 28.6139, 77.2090  # abhi Delhi

w = requests.get(
    "https://api.open-meteo.com/v1/forecast",
    params={"latitude": lat, "longitude": lon,
            "current": "temperature_2m,precipitation"},
    timeout=15,
)
a = requests.get(
    "https://air-quality-api.open-meteo.com/v1/air-quality",
    params={"latitude": lat, "longitude": lon,
            "current": "pm2_5,pm10,us_aqi"},
    timeout=15,
)

print("Weather status:", w.status_code)
print("Air status:", a.status_code)
print(w.json().get("current"))
print(a.json().get("current"))