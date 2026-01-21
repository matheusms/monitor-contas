import requests
import json
import os
from datetime import datetime, timedelta

# Configuration
LATITUDE = -22.839445 
LONGITUDE = -43.398826
WEATHER_FILE = "weather_history.json"
BILLS_FILE = "bills_history.json"

def get_start_date():
    """Determines the start date for weather data collection."""
    # 1. Check if we already have weather data
    if os.path.exists(WEATHER_FILE):
        try:
            with open(WEATHER_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data and "daily" in data and "time" in data["daily"]:
                     # Get the last date in the weather history
                    last_date_str = data["daily"]["time"][-1]
                    last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
                    return last_date + timedelta(days=1)
        except Exception as e:
            print(f"Error reading existing weather file: {e}")

    # 2. If no weather data, infer from bills
    if os.path.exists(BILLS_FILE):
        try:
            with open(BILLS_FILE, "r", encoding="utf-8") as f:
                bills = json.load(f)
                if bills:
                    # Find the earliest reading date
                    dates = []
                    for b in bills:
                        # Try parsing various date formats if necessary, but assuming 'leitura_atual' is consistently DD/MM/YYYY
                        try:
                            dates.append(datetime.strptime(b["leitura_atual"], "%d/%m/%Y"))
                        except:
                            pass
                    
                    if dates:
                        earliest_reading = min(dates)
                        # Go back ~35 days from the first reading to cover the consumption period
                        return earliest_reading - timedelta(days=35)
        except Exception as e:
            print(f"Error reading bills file: {e}")
    
    # 3. Default fallback (e.g., 1 year ago)
    return datetime.now() - timedelta(days=365)

def fetch_weather(start_date, end_date):
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "daily": ["temperature_2m_max", "temperature_2m_min", "temperature_2m_mean"],
        "timezone": "America/Sao_Paulo"
    }
    
    print(f"Fetching weather from {params['start_date']} to {params['end_date']}...")
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

def merge_data(existing, new_data):
    if not existing:
        return new_data
    
    # Append new daily data to existing arrays
    for key in existing["daily"]:
        if key in new_data["daily"]:
            existing["daily"][key].extend(new_data["daily"][key])
            
    return existing

def update_weather_data():
    start_date = get_start_date()
    # End date is yesterday (Open-Meteo Archive usually has a few days lag, but let's try yesterday)
    end_date = datetime.now() - timedelta(days=2) 
    
    # Check if we are up to date
    if start_date.date() > end_date.date():
        print("Weather data is already up to date.")
        return True

    try:
        new_weather = fetch_weather(start_date, end_date)
        
        existing_weather = {}
        if os.path.exists(WEATHER_FILE):
            try:
                with open(WEATHER_FILE, "r", encoding="utf-8") as f:
                    existing_weather = json.load(f)
            except:
                pass

        updated_weather = merge_data(existing_weather, new_weather)
        
        with open(WEATHER_FILE, "w", encoding="utf-8") as f:
            json.dump(updated_weather, f, indent=4)
            
        print(f"Weather data saved to '{WEATHER_FILE}'.")
        return True
        
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

if __name__ == "__main__":
    update_weather_data()
