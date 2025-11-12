#!/usr/bin/env python3
"""
Health API for Power Monitoring System
Provides JSON endpoint for system health metrics
"""

import cgi
import cgitb
import json
import sys
import os

# Enable CGI error reporting
cgitb.enable()

# Add parent directory to path for imports
sys.path.insert(0, '/opt/power-monitor')


def main():
    """Main CGI handler for health endpoint"""
    try:
        # Set JSON content type
        print("Content-Type: application/json")
        print("Access-Control-Allow-Origin: *")
        print()
        
        # Try to import and use SystemHealth
        try:
            from health import SystemHealth
            health = SystemHealth('/opt/power-monitor/config.json')
            report = health.get_health_report()
        except ImportError:
            # Fallback for when psutil is not available
            import datetime
            report = {
                'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'disk': {
                    'percent': 0,
                    'total_gb': 0,
                    'used_gb': 0,
                    'free_gb': 0,
                    'note': 'psutil not available'
                },
                'memory': {
                    'percent': 0,
                    'total_mb': 0,
                    'used_mb': 0,
                    'available_mb': 0,
                    'note': 'psutil not available'
                },
                'collection': {
                    'last_collection_ist': 'Unable to determine',
                    'next_collection_ist': 'Unable to determine',
                    'seconds_until_next': None,
                    'interval_minutes': 10
                },
                'github': {
                    'configured': False,
                    'last_publish_ist': 'Never',
                    'status': 'Unknown',
                    'repo': 'Not configured'
                }
            }
        
        # Output JSON
        print(json.dumps(report, indent=2))
        
    except Exception as e:
        import traceback
        # Return error as JSON with traceback
        print(json.dumps({
            'error': str(e),
            'traceback': traceback.format_exc(),
            'timestamp': None,
            'disk': {'error': str(e)},
            'memory': {'error': str(e)},
            'collection': {'error': str(e)},
            'github': {'error': str(e)}
        }))


if __name__ == '__main__':
    main()
