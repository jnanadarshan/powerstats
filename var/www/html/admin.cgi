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
import time
import hmac
import hashlib


def parse_cookies() -> dict:
    """Parse HTTP_COOKIE env into dict"""
    cookie_header = os.environ.get('HTTP_COOKIE', '')
    cookies = {}
    for part in cookie_header.split(';'):
        if '=' in part:
            k, v = part.strip().split('=', 1)
            cookies[k] = v
    return cookies


def make_session_cookie(username: str, config) -> str:
    """Generate a signed session cookie value: username|timestamp|sig"""
    secret = config.get('admin.session_secret', '') or config.get('admin.password_hash', '') or 'changeme'
    ts = str(int(time.time()))
    payload = f"{username}|{ts}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}|{sig}"


def verify_session_cookie(cookie_val: str, config) -> bool:
    try:
        secret = config.get('admin.session_secret', '') or config.get('admin.password_hash', '') or 'changeme'
        parts = cookie_val.split('|')
        if len(parts) != 3:
            return False
        username, ts, sig = parts
        payload = f"{username}|{ts}"
        expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            return False
        # check timestamp age
        age_minutes = int(config.get('admin.session_timeout_minutes', 1440))
        if int(time.time()) - int(ts) > (age_minutes * 60):
            return False
        return True
    except Exception:
        return False



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


def render_login(message: str = '') -> str:
        """Return a modern login HTML page"""
        message_html = f"<div style='color:#e11d48;padding:10px;border-radius:8px;margin-bottom:12px;background:#fff5f7;border:1px solid #fecaca;'>" + message + "</div>" if message else ''
        return f'''Content-Type: text/html

<!DOCTYPE html>
<html lang="en">
<head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <title>Admin Login - Power Monitor</title>
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" />
        <style>
                body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;display:flex;align-items:center;justify-content:center;margin:0}
                .login{background:#fff;padding:40px;border-radius:14px;box-shadow:0 10px 40px rgba(2,6,23,0.2);width:100%;max-width:420px}
                .login h1{font-size:1.8rem;margin-bottom:8px;color:#0f172a}
                .login p{color:#64748b;margin-bottom:20px}
                input{width:100%;padding:12px;border:1px solid #e2e8f0;border-radius:8px;margin-bottom:12px}
                button{display:inline-block;padding:12px 18px;border-radius:8px;border:none;background:#334155;color:#fff;font-weight:600;cursor:pointer}
                .logo{font-size:2.5rem;margin-bottom:8px}
        </style>
</head>
<body>
    <form class="login" method="post" action="/admin.cgi">
        <div class="logo">⚡</div>
        <h1>Admin Login</h1>
        <p>Authenticate to access the power monitor admin panel.</p>
        {message_html}
        <label>Username</label>
        <input type="text" name="username" required autofocus />
        <label>Password</label>
        <input type="password" name="password" required />
        <div style="display:flex;gap:10px;margin-top:10px;">
            <button type="submit">Sign in</button>
        </div>
    </form>
</body>
</html>
'''


# Due to length constraints, the HTML rendering will be loaded from templates directory
# Creating template file separately
COOKIE_NAME = 'PM_SESS'


def main():
    """Main CGI handler"""
    try:
        form = cgi.FieldStorage()
        config = get_config()
        
        # Handle logout (query or form)
        if 'logout' in form or os.environ.get('QUERY_STRING') == 'logout=1':
            # Clear cookie and show login page
            print(f"Set-Cookie: {COOKIE_NAME}=; HttpOnly; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax")
            print(render_login('You have been logged out.'))
            return
        
        # Check authentication via cookie
        cookies = parse_cookies()
        cookie_val = cookies.get(COOKIE_NAME)
        authenticated = False
        if cookie_val and verify_session_cookie(cookie_val, config):
            authenticated = True
        
        if not authenticated and form.getvalue('username'):
            if check_auth(form, config):
                # Generate session cookie and redirect to dashboard
                username = form.getvalue('username')
                session_val = make_session_cookie(username, config)
                # compute max-age
                max_age = int(config.get('admin.session_timeout_minutes', 1440)) * 60
                print(f"Set-Cookie: {COOKIE_NAME}={session_val}; HttpOnly; Path=/; Max-Age={max_age}; SameSite=Lax")
                # Redirect via 303 See Other
                print("Status: 303 See Other")
                print("Location: /admin.cgi")
                print()
                return
            else:
                # Render login with message
                print(render_login('Invalid credentials'))
                return
        
        if not authenticated:
            # Render modern login page
            print(render_login())
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
