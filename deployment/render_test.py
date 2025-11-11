#!/usr/bin/env python3
"""
Render test script: renders the Jinja2 dashboard template with sample data
Writes index.html and data.json into the repository web root for local testing.
"""
import json
import os
from pathlib import Path
from datetime import datetime, timedelta

from jinja2 import Environment, FileSystemLoader, select_autoescape

# Paths
repo_root = Path(r"d:\powerstats")
template_dir = repo_root / 'opt' / 'power-monitor' / 'templates'
web_root = repo_root / 'var' / 'www' / 'html'
web_root.mkdir(parents=True, exist_ok=True)

# Sample data: generate points for the last 24 hours every hour
now = datetime.utcnow()
points = []
for i in range(0, 24):
    t = now - timedelta(hours=(23 - i))
    points.append({
        'timestamp': t.replace(microsecond=0).isoformat() + 'Z',
        'value': round(200 + 100 * (i % 5) + (i - 12) * 2.3, 2),
        'unit': 'W'
    })

# Data file
data = {
    'data_points': points,
    'last_update': datetime.utcnow().isoformat()
}

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

html = template.render(
    data_points=json.dumps(points),
    statistics=statistics,
    last_update=data['last_update'],
    generation_time=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
)

with open(web_root / 'index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f"Wrote index.html to {web_root / 'index.html'}")

print('Render complete.')
