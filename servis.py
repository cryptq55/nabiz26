"""Kent servisleri: Eskişehir ve 14 ilçe için hava durumu ve namaz vakitleri verisini toplar.

`python servis.py` verileri data/servis.json dosyasına yazar (servis.yml iş akışı 3 saatte bir çalıştırır);
build.py bu dosyadan /hava-durumu ve /namaz-vakitleri sayfalarını üretir.
Kaynaklar: Open-Meteo (anahtarsız, ücretsiz) ve AlAdhan API'nin Diyanet hesap yöntemi (method=13).
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

OUT = Path(__file__).parent / "data" / "servis.json"
TR = timezone(timedelta(hours=3))

# Ad, koordinat (ilçe merkezi). "Eskişehir" kent merkezidir.
PLACES = {
    "Eskişehir": (39.7767, 30.5206), "Odunpazarı": (39.7600, 30.5300), "Tepebaşı": (39.7900, 30.5000),
    "Alpu": (39.7680, 30.9600), "Beylikova": (39.6930, 31.2080), "Çifteler": (39.3800, 31.0400),
    "Günyüzü": (39.3830, 31.8120), "Han": (39.1600, 30.8600), "İnönü": (39.8160, 30.1460),
    "Mahmudiye": (39.5020, 30.9850), "Mihalgazi": (40.0280, 30.5800), "Mihalıççık": (39.8720, 31.5010),
    "Sarıcakaya": (40.0400, 30.6230), "Seyitgazi": (39.4440, 30.6930), "Sivrihisar": (39.4500, 31.5370),
}

WEATHER = {0: ("Açık", "☀️"), 1: ("Az bulutlu", "🌤️"), 2: ("Parçalı bulutlu", "⛅"), 3: ("Kapalı", "☁️"),
           45: ("Sisli", "🌫️"), 48: ("Kırağılı sis", "🌫️"), 51: ("Hafif çisenti", "🌦️"), 53: ("Çisenti", "🌦️"),
           55: ("Yoğun çisenti", "🌦️"), 56: ("Donan çisenti", "🌧️"), 57: ("Donan çisenti", "🌧️"),
           61: ("Hafif yağmur", "🌦️"), 63: ("Yağmur", "🌧️"), 65: ("Kuvvetli yağmur", "🌧️"),
           66: ("Donan yağmur", "🌧️"), 67: ("Donan yağmur", "🌧️"), 71: ("Hafif kar", "🌨️"), 73: ("Kar", "🌨️"),
           75: ("Yoğun kar", "❄️"), 77: ("Kar taneleri", "🌨️"), 80: ("Sağanak", "🌦️"), 81: ("Sağanak", "🌧️"),
           82: ("Kuvvetli sağanak", "⛈️"), 85: ("Kar sağanağı", "🌨️"), 86: ("Kuvvetli kar sağanağı", "❄️"),
           95: ("Gök gürültülü fırtına", "⛈️"), 96: ("Dolu ile fırtına", "⛈️"), 99: ("Dolu ile fırtına", "⛈️")}
HIJRI = ["Muharrem", "Safer", "Rebiülevvel", "Rebiülahir", "Cemaziyelevvel", "Cemaziyelahir", "Recep", "Şaban",
         "Ramazan", "Şevval", "Zilkade", "Zilhicce"]
PRAYERS = [("İmsak", "Imsak"), ("Güneş", "Sunrise"), ("Öğle", "Dhuhr"), ("İkindi", "Asr"), ("Akşam", "Maghrib"), ("Yatsı", "Isha")]


def get(url, **params):
    r = requests.get(url, params=params, headers={"User-Agent": "nabiz26.com"}, timeout=30)
    r.raise_for_status()
    return r.json()


def weather(lat, lon):
    d = get("https://api.open-meteo.com/v1/forecast", latitude=lat, longitude=lon, timezone="Europe/Istanbul",
            forecast_days=7, current="temperature_2m,apparent_temperature,weather_code,wind_speed_10m,relative_humidity_2m",
            daily="weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,wind_speed_10m_max",
            hourly="temperature_2m,weather_code,precipitation_probability")
    c = d["current"]
    days = [{"date": t, "code": d["daily"]["weather_code"][i], "max": round(d["daily"]["temperature_2m_max"][i]),
             "min": round(d["daily"]["temperature_2m_min"][i]), "rain": d["daily"]["precipitation_probability_max"][i],
             "mm": d["daily"]["precipitation_sum"][i], "wind": round(d["daily"]["wind_speed_10m_max"][i])}
            for i, t in enumerate(d["daily"]["time"])]
    now = c["time"][:13]
    hours = [{"time": t[11:16], "temp": round(d["hourly"]["temperature_2m"][i]), "code": d["hourly"]["weather_code"][i],
              "rain": d["hourly"]["precipitation_probability"][i]}
             for i, t in enumerate(d["hourly"]["time"]) if t[:13] >= now][:24:3]
    return {"temp": round(c["temperature_2m"]), "feels": round(c["apparent_temperature"]), "code": c["weather_code"],
            "wind": round(c["wind_speed_10m"]), "humidity": c["relative_humidity_2m"], "days": days, "hours": hours}


def prayer_month(lat, lon, year, month):
    d = get(f"https://api.aladhan.com/v1/calendar/{year}/{month}", latitude=lat, longitude=lon, method=13)
    return [{"date": x["date"]["gregorian"]["date"],  # GG-AA-YYYY
             "hijri": f"{int(x['date']['hijri']['day'])} {HIJRI[x['date']['hijri']['month']['number'] - 1]} {x['date']['hijri']['year']}",
             "times": {tr: x["timings"][en].split(" ")[0] for tr, en in PRAYERS}} for x in d["data"]]


def main():
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    now = datetime.now(TR)
    out = {"updated": now.replace(microsecond=0).isoformat(), "places": {}}
    errors = 0
    for name, (lat, lon) in PLACES.items():
        prev = old.get("places", {}).get(name, {})
        entry = {"lat": lat, "lon": lon}
        try:
            entry["weather"] = weather(lat, lon)
        except Exception as e:  # kaynak geçici olarak yanıt vermezse son veriyle devam
            print(f"[uyarı] hava {name}: {e}", file=sys.stderr)
            entry["weather"] = prev.get("weather")
            errors += 1
        try:
            days = prayer_month(lat, lon, now.year, now.month)
            nxt = now.replace(day=28) + timedelta(days=5)
            days += prayer_month(lat, lon, nxt.year, nxt.month)[:7]  # ay sonunda ertesi günler de hazır olsun
            entry["prayer"] = days
        except Exception as e:
            print(f"[uyarı] namaz {name}: {e}", file=sys.stderr)
            entry["prayer"] = prev.get("prayer")
            errors += 1
        out["places"][name] = entry
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"servis verisi yazıldı: {len(PLACES)} yer, {errors} hata")


if __name__ == "__main__":
    main()
