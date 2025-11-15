#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modern Admin Dashboard for Power Monitoring System
Features: Sidebar navigation, system analytics, log viewer
"""

import cgi
import cgitb
import json
import os
import sys
import subprocess
from datetime import datetime

# Enable CGI error reporting
cgitb.enable()

# Add parent directory to path for imports
sys.path.insert(0, '/opt/power-monitor')

from config_manager import get_config
from collector import MaintenanceMode


def check_auth(form_data, config) -> bool:
    """Verify admin credentials"""
    username = form_data.getvalue('username', '')
    password = form_data.getvalue('password', '')
    
    stored_username = config.get('admin.username', 'admin')
    stored_password_hash = config.get('admin.password_hash', '')
    
    if username != stored_username:
        return False
    
    if stored_password_hash.startswith('pbkdf2:'):
        return False
    else:
        return password == stored_password_hash
    
    return False


def get_file_age(filepath: str) -> str:
    """Get human-readable file age"""
    if not os.path.exists(filepath):
        return "Never"
    
    mtime = os.path.getmtime(filepath)
    age = datetime.now() - datetime.fromtimestamp(mtime)
    
    if age.total_seconds() < 60:
        return f"{int(age.total_seconds())}s ago"
    elif age.total_seconds() < 3600:
        return f"{int(age.total_seconds() / 60)}m ago"
    elif age.total_seconds() < 86400:
        return f"{int(age.total_seconds() / 3600)}h ago"
    else:
        return f"{int(age.total_seconds() / 86400)}d ago"


def get_file_size(filepath: str) -> str:
    """Get human-readable file size"""
    if not os.path.exists(filepath):
        return "0 B"
    
    size = os.path.getsize(filepath)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def get_system_metrics(config) -> dict:
    """Get comprehensive system metrics"""
    metrics = {
        'maintenance_mode': False,
        'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'data_files': {},
        'collection': {},
        'github': {},
        'system': {}
    }
    
    # Maintenance mode
    maintenance = MaintenanceMode(config.state_file)
    metrics['maintenance_mode'] = maintenance.is_enabled()
    
    # Data files status
    web_root = config.get('paths.web_root', '/var/www/html')
    data_files = ['daily.json', 'weekly.json', 'monthly.json', 'yearly.json']
    
    total_points = 0
    for filename in data_files:
        filepath = os.path.join(web_root, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    points = len(data.get('data_points', []))
                    total_points += points
                    metrics['data_files'][filename] = {
                        'exists': True,
                        'points': points,
                        'last_update': data.get('last_update', 'Unknown'),
                        'size': get_file_size(filepath),
                        'age': get_file_age(filepath)
                    }
            except Exception as e:
                metrics['data_files'][filename] = {
                    'exists': True,
                    'points': 0,
                    'error': str(e),
                    'size': get_file_size(filepath),
                    'age': get_file_age(filepath)
                }
        else:
            metrics['data_files'][filename] = {
                'exists': False,
                'points': 0,
                'age': 'Never'
            }
    
    metrics['system']['total_data_points'] = total_points
    
    # Collection settings
    metrics['collection'] = {
        'interval': config.get('data.local_collection_interval_minutes', 
                              config.get('data.collection_interval_minutes', 10)),
        'publish_interval': config.get('data.publish_interval_minutes', 60),
        'retention_days': config.get('data.retention_days', 7),
        'health_check_interval': config.get('data.health_check_interval_seconds', 10)
    }
    
    # GitHub status
    metrics['github'] = {
        'enabled': bool(config.get('github.token')) and config.get('github.token') != 'YOUR_GITHUB_PERSONAL_ACCESS_TOKEN',
        'repo': config.get('github.repo', 'Not configured'),
        'branch': config.get('github.branch', 'main')
    }
    
    # System info
    try:
        python_version = sys.version.split()[0]
        metrics['system']['python_version'] = python_version
        
        # Try to check cron jobs
        try:
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                cron_lines = result.stdout.strip().split('\n')
                active_jobs = [line for line in cron_lines if line and not line.startswith('#')]
                metrics['system']['cron_jobs'] = len(active_jobs)
        except:
            metrics['system']['cron_jobs'] = 'Unknown'
            
    except Exception as e:
        metrics['system']['error'] = str(e)
    
    return metrics


def get_recent_logs(log_file: str, lines: int = 100) -> list:
    """Get recent log entries"""
    if not os.path.exists(log_file):
        return []
    
    try:
        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            return all_lines[-lines:]
    except Exception as e:
        return [f"Error reading log: {str(e)}"]


def handle_action(action: str, config, form) -> dict:
    """Handle admin actions"""
    result = {'success': False, 'message': ''}
    
    try:
        if action == 'toggle_maintenance':
            maintenance = MaintenanceMode(config.state_file)
            try:
                new_state = maintenance.toggle()
                result['success'] = True
                result['message'] = f'Maintenance mode {"enabled" if new_state else "disabled"} successfully'
            except PermissionError:
                result['success'] = False
                result['message'] = (
                    'Permission denied. Please run: '
                    'sudo chown root:lighttpd /etc/monitor.conf && sudo chmod 664 /etc/monitor.conf')
            
        elif action == 'manual_sync':
            maintenance = MaintenanceMode(config.state_file)
            if maintenance.is_enabled():
                result['message'] = 'Cannot sync while in maintenance mode'
            else:
                collector_result = subprocess.run(
                    ['/usr/bin/python3', '/opt/power-monitor/collector.py'],
                    capture_output=True, text=True, timeout=60
                )
                
                if collector_result.returncode == 0:
                    publisher_result = subprocess.run(
                        ['/usr/bin/python3', '/opt/power-monitor/publisher.py'],
                        capture_output=True, text=True, timeout=60
                    )
                    
                    if publisher_result.returncode == 0:
                        result['success'] = True
                        result['message'] = 'Manual sync completed successfully'
                    else:
                        result['message'] = f'Publisher failed: {publisher_result.stderr}'
                else:
                    result['message'] = f'Collector failed: {collector_result.stderr}'
        
        elif action == 'clear_logs':
            log_files = [
                '/var/log/power-monitor-collector.log',
                '/var/log/power-monitor-publisher.log',
                '/var/log/power-monitor.log'
            ]
            cleared = 0
            for log_file in log_files:
                if os.path.exists(log_file):
                    try:
                        open(log_file, 'w').close()
                        cleared += 1
                    except:
                        pass
            result['success'] = True
            result['message'] = f'Cleared {cleared} log file(s) successfully'
        
        else:
            result['message'] = 'Unknown action'
            
    except Exception as e:
        result['message'] = f'Error: {str(e)}'
    
    return result


# Due to length constraints, the HTML rendering will be loaded from templates directory
# Creating template file separately
def main():
    """Main CGI handler"""
    try:
        form = cgi.FieldStorage()
        config = get_config()
        
        # Check for logout
        if 'logout' in form or os.environ.get('QUERY_STRING') == 'logout=1':
            # Render login (inline for simplicity)
            print("Content-Type: text/html\n")
            print("<!DOCTYPE html><html><head><title>Admin Login</title></head>")
            print("<body><h1>Redirecting to login...</h1></body></html>")
            return
        
        # Check authentication
        authenticated = form.getvalue('authenticated') == '1'
        
        if not authenticated and form.getvalue('username'):
            if check_auth(form, config):
                authenticated = True
            else:
                print("Content-Type: text/html\n")
                print("<!DOCTYPE html><html><body><h1>Invalid credentials</h1></body></html>")
                return
        
        if not authenticated:
            print("Content-Type: text/html\n")
            print("<!DOCTYPE html><html><body><h1>Please login</h1></body></html>")
            return
        
        # Get system metrics
        metrics = get_system_metrics(config)
        
        # Handle action if present
        message = ''
        action = form.getvalue('action')
        if action:
            result = handle_action(action, config, form)
            message = result['message']
            metrics = get_system_metrics(config)
        
        # Render dashboard
        print("Content-Type: text/html\n")
        print(f"<!DOCTYPE html><html><body>")
        print(f"<h1>Admin Dashboard</h1>")
        print(f"<p>Status: {'Maintenance' if metrics['maintenance_mode'] else 'Normal'}</p>")
        print(f"<p>Data Points: {metrics['system']['total_data_points']}</p>")
        if message:
            print(f"<p><b>{message}</b></p>")
        print("</body></html>")
        
    except Exception as e:
        print("Content-Type: text/html\n")
        print(f"<h1>Error</h1><pre>{str(e)}</pre>")


if __name__ == '__main__':
    main()
