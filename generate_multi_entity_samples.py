import json
from datetime import datetime, timedelta
import random

def generate_sample_data():
    """
    Generates realistic, multi-entity sample data for daily, weekly, monthly, and yearly JSON files.
    """
    # --- Daily Data (10-minute intervals for 24 hours) ---
    daily_data = []
    start_of_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    for i in range(144):  # 24 * 6
        timestamp = start_of_day + timedelta(minutes=i * 10)
        hour = timestamp.hour
        
        # Simulate power curve
        if 0 <= hour < 6: power = random.uniform(50, 150)  # Night
        elif 6 <= hour < 9: power = random.uniform(150, 400) # Morning peak
        elif 9 <= hour < 17: power = random.uniform(200, 350) # Day
        elif 17 <= hour < 22: power = random.uniform(350, 600) # Evening peak
        else: power = random.uniform(150, 300) # Late night
        
        # Simulate solar curve
        if 7 <= hour < 18:
            solar = max(0, (-(hour - 12.5)**2 + 36) * random.uniform(15, 25))
        else:
            solar = 0
            
        power -= solar # Net power is consumption minus solar
        
        point = {
            "timestamp": timestamp.isoformat() + "Z",
            "power": round(max(50, power), 2),
            "voltage": round(random.uniform(225.0, 245.0), 2),
            "solar": round(max(0, solar), 2),
            "power_factor": round(random.uniform(0.92, 0.99), 2),
            "daily_energy": round((i / 144) * random.uniform(8, 15), 2)
        }
        daily_data.append(point)

    with open("var/www/html/daily.json", "w") as f:
        json.dump({"data_points": daily_data, "last_update": datetime.now().isoformat() + "Z"}, f, indent=2)
    print(f"Generated daily.json with {len(daily_data)} multi-entity data points.")

    # --- Weekly Data (hourly intervals for 7 days) ---
    weekly_data = []
    start_of_week = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=6)
    for i in range(7 * 24):
        timestamp = start_of_week + timedelta(hours=i)
        hour = timestamp.hour
        
        if 0 <= hour < 6: power = random.uniform(50, 150)
        elif 6 <= hour < 22: power = random.uniform(200, 500)
        else: power = random.uniform(150, 300)
        
        if 7 <= hour < 18: solar = max(0, (-(hour - 12.5)**2 + 30) * random.uniform(15, 25))
        else: solar = 0
        
        point = {
            "timestamp": timestamp.isoformat() + "Z",
            "power": round(max(50, power - solar), 2),
            "voltage": round(random.uniform(228.0, 242.0), 2),
            "solar": round(max(0, solar), 2),
            "power_factor": round(random.uniform(0.94, 0.98), 2),
            "daily_energy": round(random.uniform(5, 20), 2)
        }
        weekly_data.append(point)
        
    with open("var/www/html/weekly.json", "w") as f:
        json.dump({"data_points": weekly_data, "last_update": datetime.now().isoformat() + "Z"}, f, indent=2)
    print(f"Generated weekly.json with {len(weekly_data)} multi-entity data points.")

    # --- Monthly Data (daily intervals for 30 days) ---
    monthly_data = []
    start_of_month = datetime.now().replace(day=1) - timedelta(days=30)
    for i in range(30):
        timestamp = start_of_month + timedelta(days=i)
        point = {
            "timestamp": timestamp.isoformat() + "Z",
            "power": round(random.uniform(150, 400), 2), # Avg daily power
            "voltage": round(random.uniform(230.0, 240.0), 2),
            "solar": round(random.uniform(1000, 5000), 2), # Daily solar total
            "power_factor": round(random.uniform(0.95, 0.97), 2),
            "daily_energy": round(random.uniform(8, 25), 2)
        }
        monthly_data.append(point)

    with open("var/www/html/monthly.json", "w") as f:
        json.dump({"data_points": monthly_data, "last_update": datetime.now().isoformat() + "Z"}, f, indent=2)
    print(f"Generated monthly.json with {len(monthly_data)} multi-entity data points.")

    # --- Yearly Data (daily intervals for 365 days) ---
    yearly_data = []
    start_of_year = datetime.now().replace(month=1, day=1) - timedelta(days=365)
    for i in range(365):
        timestamp = start_of_year + timedelta(days=i)
        month = timestamp.month
        
        if month in [12, 1, 2]: daily_energy = random.uniform(15, 28) # Winter
        elif month in [6, 7, 8]: daily_energy = random.uniform(12, 35) # Summer
        else: daily_energy = random.uniform(10, 22) # Spring/Fall
        
        point = {
            "timestamp": timestamp.isoformat() + "Z",
            "power": round(daily_energy * 1000 / 24, 2), # Rough avg power
            "voltage": round(random.uniform(232.0, 238.0), 2),
            "solar": round(random.uniform(2000, 6000), 2),
            "power_factor": round(random.uniform(0.96, 0.98), 2),
            "daily_energy": round(daily_energy, 2)
        }
        yearly_data.append(point)

    with open("var/www/html/yearly.json", "w") as f:
        json.dump({"data_points": yearly_data, "last_update": datetime.now().isoformat() + "Z"}, f, indent=2)
    print(f"Generated yearly.json with {len(yearly_data)} multi-entity data points.")

if __name__ == "__main__":
    generate_sample_data()
