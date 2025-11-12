#!/usr/bin/env python3
"""
Generate realistic sample data for daily.json, weekly.json, monthly.json, and yearly.json
Writes files to: var/www/html

Usage:
    python3 deployment/generate_sample_data.py
"""
from pathlib import Path
from datetime import datetime, timedelta, timezone
import json
import random

repo_root = Path(__file__).resolve().parents[1]
web_root = repo_root / 'var' / 'www' / 'html'
web_root.mkdir(parents=True, exist_ok=True)

now = datetime.now(timezone.utc).replace(microsecond=0)

# Helper to isoformat Z
def z(dt):
    return dt.isoformat().replace('+00:00', 'Z')

# CONFIG
POINT_INTERVAL_MIN = 10  # 10-minute raw points
POINTS_PER_DAY = int(24 * 60 / POINT_INTERVAL_MIN)  # 144
DAYS_WEEK = 7
DAYS_MONTH = 30
DAYS_YEAR = 365

random.seed(12345)

# Generate raw points for the last N days
def generate_raw_points(days):
    total = POINTS_PER_DAY * days
    pts = []
    for i in range(total):
        # timestamp from oldest to newest
        ts = now - timedelta(minutes=(total - 1 - i) * POINT_INTERVAL_MIN)
        # create diurnal pattern: base + day/night + weekly variation + noise
        hour_local = (ts.astimezone().hour + ts.astimezone().minute/60.0)
        # Diurnal multiplier
        if 6 <= hour_local < 10:
            time_factor = 0.8 + (hour_local - 6) * 0.08
        elif 10 <= hour_local < 18:
            time_factor = 1.2
        elif 18 <= hour_local < 22:
            time_factor = 1.4
        else:
            time_factor = 0.55

        # weekly variation: slightly different on weekends
        weekday = ts.astimezone().weekday()
        week_factor = 1.0 + (0.12 if weekday < 5 else -0.05)

        base = 220  # base watts
        noise = random.uniform(-30, 30)
        value = max(0, round(base * time_factor * week_factor + noise, 2))

        pts.append({
            'timestamp': z(ts),
            'value': value,
            'unit': 'W'
        })

    return pts

# Insert some power cuts (zero-value periods) into a raw series in-place
def inject_power_cuts(points, cut_specs):
    # cut_specs: list of (start_index, duration_points)
    for start, dur in cut_specs:
        for i in range(start, min(len(points), start + dur)):
            points[i]['value'] = 0

# Aggregate 10-min points to hourly averages
def aggregate_to_hourly(points):
    hourly = []
    if not points:
        return hourly
    # Group by hour (UTC aligned)
    buckets = {}
    for p in points:
        dt = datetime.fromisoformat(p['timestamp'].replace('Z', '+00:00'))
        hour_key = dt.replace(minute=0, second=0, microsecond=0)
        key = z(hour_key)
        if key not in buckets:
            buckets[key] = {'sum': 0.0, 'count': 0}
        buckets[key]['sum'] += p['value']
        buckets[key]['count'] += 1
    for k in sorted(buckets.keys()):
        b = buckets[k]
        hourly.append({'timestamp': k, 'value': round(b['sum'] / b['count'], 2), 'unit': 'W'})
    return hourly

# Aggregate points to daily averages
def aggregate_to_daily(points):
    days = []
    if not points:
        return days
    buckets = {}
    for p in points:
        dt = datetime.fromisoformat(p['timestamp'].replace('Z', '+00:00'))
        day_key = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        key = z(day_key)
        if key not in buckets:
            buckets[key] = {'sum': 0.0, 'count': 0}
        buckets[key]['sum'] += p['value']
        buckets[key]['count'] += 1
    for k in sorted(buckets.keys()):
        b = buckets[k]
        days.append({'timestamp': k, 'value': round(b['sum'] / b['count'], 2), 'unit': 'W'})
    return days

# Write file atomically
def atomic_write(path: Path, data):
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    tmp.replace(path)

# Generate raw 365 days for good aggregation
raw_365 = generate_raw_points(DAYS_YEAR)
# Add some periodic power cuts across the year: pick some indices
cut_specs = [
    (500, 12),   # cut around day ~3
    (3000, 6),   # short cut
    (10000, 18), # longer cut
    (20000, 24)  # multi-hour cut
]
inject_power_cuts(raw_365, cut_specs)

# daily.json: last 24 hours (144 points)
daily_points = raw_365[-POINTS_PER_DAY:]
daily_data = {
    'data_points': daily_points,
    'last_update': z(now),
    'date': (now.astimezone().date().isoformat())
}
atomic_write(web_root / 'daily.json', daily_data)
print(f'Wrote daily.json with {len(daily_points)} points')

# weekly.json: last 7 days hourly
raw_7 = raw_365[-(POINTS_PER_DAY * DAYS_WEEK):]
weekly_hourly = aggregate_to_hourly(raw_7)
weekly_data = {'data_points': weekly_hourly, 'last_update': z(now)}
atomic_write(web_root / 'weekly.json', weekly_data)
print(f'Wrote weekly.json with {len(weekly_hourly)} hourly points')

# monthly.json: last 30 days daily averages
raw_30 = raw_365[-(POINTS_PER_DAY * DAYS_MONTH):]
monthly_daily = aggregate_to_daily(raw_30)[-DAYS_MONTH:]
monthly_data = {'data_points': monthly_daily, 'last_update': z(now)}
atomic_write(web_root / 'monthly.json', monthly_data)
print(f'Wrote monthly.json with {len(monthly_daily)} daily points')

# yearly.json: last 365 days daily averages
yearly_daily = aggregate_to_daily(raw_365)[-DAYS_YEAR:]
yearly_data = {'data_points': yearly_daily, 'last_update': z(now)}
atomic_write(web_root / 'yearly.json', yearly_data)
print(f'Wrote yearly.json with {len(yearly_daily)} daily points')

# Print sizes
for name in ('daily.json','weekly.json','monthly.json','yearly.json'):
    p = web_root / name
    if p.exists():
        print(p.name, p.stat().st_size, 'bytes')
    else:
        print('Missing', p)

print('Sample data generation complete.')
