#!/usr/bin/env python3
"""
Generate sample data for local testing of the Power Monitor dashboard.
Populates daily.json, weekly.json, monthly.json, and yearly.json with realistic test data.
"""

import json
from datetime import datetime, timedelta

def generate_daily_data():
    """Generate 24 hours of sample data (one entry per hour)"""
    data = []
    now = datetime.now()
    for i in range(24):
        ts = now - timedelta(hours=24-i)
        # Simulate power consumption with daily pattern
        hour = ts.hour
        base_power = 200 + (100 * abs(12 - hour) / 12)  # peak at noon
        
        data.append({
            "timestamp": ts.isoformat(),
            "power": round(base_power + (30 * (i % 3)), 1),
            "voltage": round(240 + (5 * (i % 2)), 1),
            "daily_energy": round(400 + (20 * i), 1),
            "solar": round(15 * max(0, 12 - abs(12 - hour)) / 12, 2),
            "power_factor": round(0.95 + (0.03 * (i % 2)), 2)
        })
    return data

def generate_weekly_data():
    """Generate 7 days of sample data (one entry per 4 hours)"""
    data = []
    now = datetime.now()
    for i in range(42):  # 7 days * 6 entries per day (4-hour intervals)
        ts = now - timedelta(hours=7*24 - i*4)
        hour = ts.hour
        base_power = 200 + (100 * abs(12 - hour) / 12)
        
        data.append({
            "timestamp": ts.isoformat(),
            "power": round(base_power + (30 * (i % 3)), 1),
            "voltage": round(240 + (5 * (i % 2)), 1),
            "daily_energy": round(400 + (20 * i), 1),
            "solar": round(15 * max(0, 12 - abs(12 - hour)) / 12, 2),
            "power_factor": round(0.95 + (0.03 * (i % 2)), 2)
        })
    return data

def generate_monthly_data():
    """Generate 30 days of sample data (one entry per day)"""
    data = []
    now = datetime.now()
    for i in range(30):
        ts = now - timedelta(days=30-i)
        # Simulate daily average power
        base_power = 250 + (50 * ((ts.day % 10) / 10))
        
        data.append({
            "timestamp": ts.isoformat(),
            "power": round(base_power + (40 * (i % 3)), 1),
            "voltage": round(240 + (5 * (i % 2)), 1),
            "daily_energy": round(5.8 + (0.5 * (i % 5)), 2),
            "solar": round(8 + (3 * (i % 4)), 1),
            "power_factor": 0.95
        })
    return data

def generate_yearly_data():
    """Generate 365 days of sample data (one entry per day)"""
    data = []
    now = datetime.now()
    for i in range(365):
        ts = now - timedelta(days=365-i)
        # Simulate seasonal variation
        month = ts.month
        seasonal = 250 + (80 * abs(6 - month) / 6)  # peak in winter
        
        data.append({
            "timestamp": ts.isoformat(),
            "power": round(seasonal + (30 * (i % 5)), 1),
            "voltage": round(240 + (5 * (i % 2)), 1),
            "daily_energy": round(5.5 + (0.8 * (i % 10)), 2),
            "solar": round(6 + (4 * abs(6 - month) / 6), 1),
            "power_factor": 0.95
        })
    return data

def main():
    """Generate and save all sample data files"""
    output_dir = '/Users/jnanadarshan/Documents/GitHub/powerstats/var/www/html'
    
    files_data = {
        'daily.json': generate_daily_data(),
        'weekly.json': generate_weekly_data(),
        'monthly.json': generate_monthly_data(),
        'yearly.json': generate_yearly_data()
    }
    
    for filename, data in files_data.items():
        filepath = f'{output_dir}/{filename}'
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        print(f'✓ Generated {filename} with {len(data)} data points')

if __name__ == '__main__':
    main()
