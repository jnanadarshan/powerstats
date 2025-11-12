#!/usr/bin/env python3
"""
Render test script: renders the Jinja2 dashboard template with sample data
Writes index.html and data.json into the repository web root for local testing.
"""
import json
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone

from jinja2 import Environment, FileSystemLoader, select_autoescape

# Paths
# Compute the repository root dynamically from this script's location so the
# render test works on non-Windows OSes and when the repo is checked out
# elsewhere.
repo_root = Path(__file__).resolve().parents[1]
template_dir = repo_root / 'opt' / 'power-monitor' / 'templates'
web_root = repo_root / 'var' / 'www' / 'html'
web_root.mkdir(parents=True, exist_ok=True)

# Sample data: generate points for the last 7 days (every 10 minutes = 144 points/day)
# Include some power cuts to demonstrate the tracking feature
# Use UTC for generated timestamps but also compute local midnight for 'today' selection
now = datetime.now(timezone.utc)
local_now = datetime.now().astimezone()
local_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
local_midnight_utc = local_midnight.astimezone(timezone.utc)
points = []
total_points = 7 * 144  # 7 days of 10-minute intervals

# Define power cut periods (start_hour, duration_hours)
power_cuts = [
    (50, 2),    # Power cut starting at point 50 (around 3.5 hours), lasting 2 hours (12 points)
    (200, 1.5), # Power cut starting at point 200, lasting 1.5 hours (9 points)
    (500, 0.5), # Short power cut starting at point 500, lasting 30 minutes (3 points)
    (800, 3),   # Longer power cut starting at point 800, lasting 3 hours (18 points)
]

for i in range(total_points):
    t = now - timedelta(minutes=(total_points - i) * 10)
    ts = t.replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    
    # Check if this point is during a power cut
    is_power_cut = False
    for cut_start, cut_duration_hours in power_cuts:
        cut_duration_points = int(cut_duration_hours * 6)  # 6 points per hour (10-min intervals)
        if cut_start <= i < cut_start + cut_duration_points:
            is_power_cut = True
            break
    
    if is_power_cut:
        value = 0  # Power is out
    else:
        # Generate realistic varying power consumption
        # Base load + time-of-day variation + daily cycle + some randomness
        hour_of_day = (i * 10 / 60) % 24
        day_cycle = (i / 144) % 7
        
        # Higher usage during day (6am-10pm), lower at night
        time_factor = 1.0
        if 6 <= hour_of_day < 10:  # Morning ramp-up
            time_factor = 0.7 + (hour_of_day - 6) * 0.075
        elif 10 <= hour_of_day < 18:  # Day time peak
            time_factor = 1.2
        elif 18 <= hour_of_day < 22:  # Evening peak
            time_factor = 1.4
        elif 22 <= hour_of_day or hour_of_day < 6:  # Night time low
            time_factor = 0.5
        
        # Weekly variation (slightly higher on weekdays)
        week_factor = 1.0 + (0.1 if day_cycle < 5 else -0.1)
        
        # Add some randomness
        import random
        random.seed(i)  # Consistent random values
        noise = random.uniform(-20, 20)
        
        base_power = 250  # Base load in watts
        value = round(base_power * time_factor * week_factor + noise, 2)
        value = max(0, value)  # Ensure non-negative
    
    points.append({
        'timestamp': ts,
        'value': value,
        'unit': 'W'
    })

# Data file
data = {
    'data_points': points,
    'last_update': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
}

# Compute today's points (since local midnight) for convenience in the template
today_points = [p for p in points if datetime.fromisoformat(p['timestamp'].replace('Z', '+00:00')) >= local_midnight_utc]
data['today_points'] = today_points

# Write data.json
with open(web_root / 'data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)
print(f"Wrote data.json with {len(points)} points to {web_root / 'data.json'}")

# Render template
env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=select_autoescape(['html', 'xml']))
try:
    template = env.get_template('dashboard.html')
except Exception as e:
    print(f"Error: could not load template: {e}")
    raise

# Simple statistics calculation
values = [p['value'] for p in points]
interval_hours = 1.0
total_kwh = sum(values) * interval_hours / 1000.0
statistics = {
    'current': round(values[-1], 2),
    'average': round(sum(values) / len(values), 2),
    'min': round(min(values), 2),
    'max': round(max(values), 2),
    'total_kwh': round(total_kwh, 2)
}

# For new multi-JSON architecture, write all 4 JSON files instead of embedding data
# The dashboard will fetch these files dynamically
daily_data = {
    'data_points': today_points if today_points else points[-144:],  # Last 24 hours
    'last_update': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
    'date': datetime.now(timezone.utc).date().isoformat()
}

with open(web_root / 'daily.json', 'w', encoding='utf-8') as f:
    json.dump(daily_data, f, indent=2)
print(f"Wrote daily.json with {len(daily_data['data_points'])} points")

# Aggregate to weekly (last 7 days, hourly)
hourly_map = {}
for p in points:
    dt = datetime.fromisoformat(p['timestamp'].replace('Z', '+00:00'))
    hour_key = dt.replace(minute=0, second=0, microsecond=0)
    if hour_key not in hourly_map:
        hourly_map[hour_key] = {'sum': 0, 'count': 0}
    hourly_map[hour_key]['sum'] += p['value']
    hourly_map[hour_key]['count'] += 1

weekly_points = [
    {
        'timestamp': hour.isoformat().replace('+00:00', 'Z'),
        'value': round(data['sum'] / data['count'], 2),
        'unit': 'W'
    }
    for hour, data in sorted(hourly_map.items())
]

weekly_data = {
    'data_points': weekly_points,
    'last_update': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
}

with open(web_root / 'weekly.json', 'w', encoding='utf-8') as f:
    json.dump(weekly_data, f, indent=2)
print(f"Wrote weekly.json with {len(weekly_points)} points")

# Aggregate to monthly (last 30 days, daily) - simulate
daily_map = {}
for p in points:
    dt = datetime.fromisoformat(p['timestamp'].replace('Z', '+00:00'))
    day_key = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    if day_key not in daily_map:
        daily_map[day_key] = {'sum': 0, 'count': 0}
    daily_map[day_key]['sum'] += p['value']
    daily_map[day_key]['count'] += 1

monthly_points = [
    {
        'timestamp': day.isoformat().replace('+00:00', 'Z'),
        'value': round(data['sum'] / data['count'], 2),
        'unit': 'W'
    }
    for day, data in sorted(daily_map.items())[-30:]  # Last 30 days
]

monthly_data = {
    'data_points': monthly_points,
    'last_update': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
}

with open(web_root / 'monthly.json', 'w', encoding='utf-8') as f:
    json.dump(monthly_data, f, indent=2)
print(f"Wrote monthly.json with {len(monthly_points)} points")

# Yearly data (simulate by reusing daily aggregates)
yearly_data = {
    'data_points': monthly_points,  # For testing, reuse monthly
    'last_update': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
}

with open(web_root / 'yearly.json', 'w', encoding='utf-8') as f:
    json.dump(yearly_data, f, indent=2)
print(f"Wrote yearly.json with {len(monthly_points)} points")

# Render dashboard HTML without embedded data (will fetch JSON files dynamically)
html = template.render(
    statistics=statistics,
    last_update=data['last_update'],
    generation_time=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
)

with open(web_root / 'index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f"Wrote index.html to {web_root / 'index.html'}")

print('Render complete.')
