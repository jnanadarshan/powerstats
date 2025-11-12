#!/usr/bin/env python3
"""
Simple health test without psutil dependency
Useful for debugging health endpoint
"""

import json
import sys
from datetime import datetime, timezone, timedelta

def get_mock_health():
    """Return mock health data for testing"""
    return {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'disk': {
            'path': '/var/www/html',
            'total_gb': 0.24,
            'used_gb': 0.08,
            'free_gb': 0.16,
            'percent': 33.3
        },
        'memory': {
            'total_mb': 256.0,
            'used_mb': 128.5,
            'available_mb': 127.5,
            'percent': 50.2
        },
        'collection': {
            'last_collection_ist': '2024-01-15 16:00:00 IST',
            'last_collection_utc': datetime.now(timezone.utc).isoformat(),
            'next_collection_ist': '2024-01-15 16:10:00 IST',
            'seconds_until_next': 420,
            'interval_minutes': 10
        },
        'github': {
            'configured': True,
            'last_publish_ist': '2024-01-15 16:05:00 IST',
            'status': 'Success',
            'repo': 'username/powerstats-data',
            'branch': 'main'
        }
    }

if __name__ == '__main__':
    print("Content-Type: application/json")
    print("Access-Control-Allow-Origin: *")
    print()
    print(json.dumps(get_mock_health(), indent=2))
