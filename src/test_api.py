import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = (os.getenv("OPENWEATHER_API_KEY") or "").strip().strip('"').strip("'")
if not API_KEY:
    raise SystemExit(".env mein OPENWEATHER_API_KEY nahi mili")

print("Key length:", len(API_KEY))
print("Starts:", API_KEY[:4], "Ends:", API_KEY[-4:])

lat, lon = 28.6139, 77.2090  # abhi Delhi

w = requests.get(
    "https://api.openweathermap.org/data/2.5/weather",
    params={"lat": lat, "lon": lon, "appid": API_KEY, "units": "metric"},
    timeout=15,
)
a = requests.get(
    "https://api.openweathermap.org/data/2.5/air_pollution",
    params={"lat": lat, "lon": lon, "appid": API_KEY},
    timeout=15,
)

print("Weather status:", w.status_code)
print("Air status:", a.status_code)

if w.ok and a.ok:
    weather = w.json()
    air = a.json()["list"][0]
    print("Temp:", weather["main"]["temp"], "°C")
    print("AQI (1-5):", air["main"]["aqi"])
    print("PM2.5:", air["components"]["pm2_5"])
else:
    print(w.text)
    print(a.text)