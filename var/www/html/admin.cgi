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


def render_dashboard(metrics: dict, message: str = '', config=None) -> str:
    """Render the admin dashboard from template"""
    template_path = '/var/www/html/admin_dashboard.html'
    
    # Load template
    try:
        with open(template_path, 'r') as f:
            template = f.read()
    except FileNotFoundError:
        # Fallback if template not found
        return f"Content-Type: text/html\n\n<h1>Template not found: {template_path}</h1>"
    
    # Build replacements
    replacements = {}
    
    # Admin user info
    admin_username = config.get('admin.username', 'admin') if config else 'admin'
    replacements['ADMIN_USER'] = admin_username
    replacements['ADMIN_INITIAL'] = admin_username[0].upper()
    
    # Header status
    if metrics['maintenance_mode']:
        replacements['STATUS_CLASS'] = 'maintenance'
        replacements['STATUS_ICON'] = 'build'
        replacements['STATUS_TEXT'] = 'Maintenance Mode'
    else:
        replacements['STATUS_CLASS'] = 'normal'
        replacements['STATUS_ICON'] = 'check_circle'
        replacements['STATUS_TEXT'] = 'System Normal'
    
    replacements['CURRENT_TIME'] = metrics['current_time']
    
    # Message banner
    if message:
        msg_class = 'success' if 'success' in message.lower() or 'enabled' in message.lower() or 'synced' in message.lower() else 'error'
        msg_icon = 'check_circle' if msg_class == 'success' else 'error'
        replacements['MESSAGE_BANNER'] = f'''<div class="message {msg_class}" style="margin-bottom: 20px;">
            <span class="material-icons">{msg_icon}</span>
            {message}
        </div>'''
    else:
        replacements['MESSAGE_BANNER'] = ''
    
    # Maintenance button
    if metrics['maintenance_mode']:
        replacements['MAINTENANCE_BTN_CLASS'] = 'primary'
        replacements['MAINTENANCE_ICON'] = 'power'
        replacements['MAINTENANCE_TEXT'] = 'Disable Maintenance'
    else:
        replacements['MAINTENANCE_BTN_CLASS'] = 'danger'
        replacements['MAINTENANCE_ICON'] = 'build'
        replacements['MAINTENANCE_TEXT'] = 'Enable Maintenance'
    
    # GitHub disabled state
    replacements['GITHUB_DISABLED'] = '' if metrics['github']['enabled'] else 'disabled title="GitHub not configured"'
    
    # Stats for dashboard cards
    active_files = sum(1 for info in metrics['data_files'].values() if info.get('exists', False))
    total_files = len(metrics['data_files'])
    replacements['ACTIVE_FILES'] = str(active_files)
    replacements['TOTAL_FILES'] = str(total_files)
    replacements['ACTIVE_FILES_PCT'] = str(int((active_files / total_files * 100) if total_files > 0 else 0))
    
    # Data files table rows (dashboard view)
    data_files_html = []
    for filename, info in metrics['data_files'].items():
        if info['exists']:
            badge = '<span class="badge success">Active</span>'
            points = info['points']
            age = info.get('age', 'Unknown')
        else:
            badge = '<span class="badge error">Missing</span>'
            points = 0
            age = 'Never'
        
        data_files_html.append(f'''<tr>
            <td>{filename} {badge}</td>
            <td>{points:,}</td>
            <td style="font-size: 0.85em; color: var(--text-secondary);">{age}</td>
        </tr>''')
    replacements['DATA_FILES_ROWS'] = '\n'.join(data_files_html)
    
    # Data files detailed table (data files section)
    data_files_detailed = []
    for filename, info in metrics['data_files'].items():
        if info['exists']:
            status = '<span class="badge success">Active</span>'
            points = f"{info['points']:,}"
            last_update = info.get('last_update', 'Unknown')
            file_size = info.get('size', '0 B')
            age = info.get('age', 'Unknown')
        else:
            status = '<span class="badge error">Missing</span>'
            points = '0'
            last_update = 'N/A'
            file_size = '0 B'
            age = 'Never'
        
        data_files_detailed.append(f'''<tr>
            <td style="font-weight: 600;">{filename}</td>
            <td>{status}</td>
            <td>{points}</td>
            <td style="font-size: 0.85em;">{last_update}</td>
            <td style="font-size: 0.85em;">{file_size}</td>
            <td style="font-size: 0.85em; color: var(--text-secondary);">{age}</td>
        </tr>''')
    replacements['DATA_FILES_DETAILED_ROWS'] = '\n'.join(data_files_detailed)
    
    # Collection settings
    replacements['COLLECTION_INTERVAL'] = str(metrics['collection']['interval'])
    replacements['PUBLISH_INTERVAL'] = str(metrics['collection']['publish_interval'])
    replacements['RETENTION_DAYS'] = str(metrics['collection']['retention_days'])
    replacements['HEALTH_INTERVAL'] = str(metrics['collection']['health_check_interval'])
    
    # GitHub info
    if metrics['github']['enabled']:
        replacements['GITHUB_STATUS'] = 'Enabled'
        replacements['GITHUB_STATUS_CLASS'] = 'success'
    else:
        replacements['GITHUB_STATUS'] = 'Not Configured'
        replacements['GITHUB_STATUS_CLASS'] = 'error'
    
    github_repo = metrics['github']['repo']
    replacements['GITHUB_REPO'] = github_repo
    replacements['GITHUB_BRANCH'] = metrics['github']['branch']
    
    # Extract owner and repo name from full path
    if '/' in github_repo:
        owner, repo_name = github_repo.split('/', 1)
        replacements['GITHUB_OWNER'] = owner
        replacements['GITHUB_REPO_NAME'] = repo_name
    else:
        replacements['GITHUB_OWNER'] = 'unknown'
        replacements['GITHUB_REPO_NAME'] = github_repo
    
    # System info
    replacements['TOTAL_POINTS'] = f"{metrics['system']['total_data_points']:,}"
    replacements['PYTHON_VERSION'] = metrics['system'].get('python_version', 'Unknown')
    replacements['CRON_JOBS'] = str(metrics['system'].get('cron_jobs', 'Unknown'))
    replacements['WEB_ROOT'] = metrics['system'].get('web_root', '/var/www/html')
    
    # Recent logs (try to load from log file)
    log_content_full = '<div class="log-line" style="color: #888;">No logs available</div>'
    log_content_short = '<div class="log-line" style="color: #888;">No logs available</div>'
    
    # Try to find log files in multiple locations
    log_files_to_check = [
        '/var/log/power-monitor.log',
        '/var/log/power-monitor-collector.log',
        '/var/log/power-monitor-publisher.log',
        '/var/log/power-monitor-scheduler.log',
        '/opt/power-monitor/logs/power-monitor.log',
        '/tmp/power-monitor.log'
    ]
    
    log_file = None
    for potential_log in log_files_to_check:
        if os.path.exists(potential_log):
            log_file = potential_log
            break
    
    if log_file:
        try:
            recent_logs = get_recent_logs(log_file, lines=100)
            if recent_logs:
                # Full logs for logs section
                log_lines_full = []
                for line in recent_logs[-50:]:  # Last 50 lines
                    line = line.strip()
                    if line:
                        if 'ERROR' in line or 'CRITICAL' in line:
                            log_lines_full.append(f'<div class="log-line" style="color: #ef4444;">{line}</div>')
                        elif 'WARNING' in line:
                            log_lines_full.append(f'<div class="log-line" style="color: #f59e0b;">{line}</div>')
                        elif 'INFO' in line:
                            log_lines_full.append(f'<div class="log-line" style="color: #3b82f6;">{line}</div>')
                        else:
                            log_lines_full.append(f'<div class="log-line">{line}</div>')
                log_content_full = '\n'.join(log_lines_full) if log_lines_full else log_content_full
                
                # Short logs for dashboard
                log_lines_short = []
                for line in recent_logs[-20:]:  # Last 20 lines
                    line = line.strip()
                    if line:
                        if 'ERROR' in line or 'CRITICAL' in line:
                            log_lines_short.append(f'<div class="log-line" style="color: #ef4444;">{line}</div>')
                        elif 'WARNING' in line:
                            log_lines_short.append(f'<div class="log-line" style="color: #f59e0b;">{line}</div>')
                        elif 'INFO' in line:
                            log_lines_short.append(f'<div class="log-line" style="color: #3b82f6;">{line}</div>')
                        else:
                            log_lines_short.append(f'<div class="log-line">{line}</div>')
                log_content_short = '\n'.join(log_lines_short) if log_lines_short else log_content_short
        except:
            pass
    else:
        # If no log file found, try to create sample log info
        log_content_full = '<div class="log-line" style="color: #888;">No log files found in:<br>' + '<br>'.join(log_files_to_check) + '</div>'
        log_content_short = '<div class="log-line" style="color: #888;">Logging not yet configured</div>'
    
    replacements['LOG_CONTENT'] = log_content_full
    replacements['LOG_CONTENT_SHORT'] = log_content_short
    
    # Apply all replacements
    output = template
    for key, value in replacements.items():
        output = output.replace('{{' + key + '}}', str(value))
    
    return "Content-Type: text/html\n\n" + output


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
                    # Try multiple common keys for data points
                    points = 0
                    if isinstance(data, dict):
                        # Try 'data_points' key (most common)
                        if 'data_points' in data:
                            points_list = data.get('data_points', [])
                            points = len(points_list) if isinstance(points_list, list) else 0
                        # Try 'data' key as fallback
                        elif 'data' in data:
                            points_list = data.get('data', [])
                            points = len(points_list) if isinstance(points_list, list) else 0
                        # Try 'points' key as fallback
                        elif 'points' in data:
                            points_list = data.get('points', [])
                            points = len(points_list) if isinstance(points_list, list) else 0
                    elif isinstance(data, list):
                        # If the root is a list, count items directly
                        points = len(data)
                    
                    total_points += points
                    metrics['data_files'][filename] = {
                        'exists': True,
                        'points': points,
                        'last_update': data.get('last_update', 'Unknown') if isinstance(data, dict) else 'Unknown',
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
    metrics['system']['web_root'] = web_root
    
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
        
        # Try to check cron jobs - multiple methods for compatibility
        cron_count = 0
        try:
            # Method 1: Try crontab (works on Linux with cron daemon)
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                cron_lines = result.stdout.strip().split('\n')
                active_jobs = [line for line in cron_lines if line and not line.startswith('#')]
                cron_count = len(active_jobs)
        except:
            pass
        
        # Method 2: Check if scheduler.py is running via ps (alternative detection)
        if cron_count == 0:
            try:
                result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=5)
                scheduler_lines = [line for line in result.stdout.split('\n') if 'scheduler.py' in line and 'grep' not in line]
                if scheduler_lines:
                    cron_count = len(scheduler_lines)
            except:
                pass
        
        # Method 3: Check systemd service status for power-monitor-scheduler
        if cron_count == 0:
            try:
                result = subprocess.run(['systemctl', 'is-active', 'power-monitor-scheduler'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and 'active' in result.stdout.lower():
                    cron_count = 1  # Service is active
            except:
                pass
        
        metrics['system']['cron_jobs'] = cron_count if cron_count > 0 else 'Unknown'
            
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
    message_html = (
        '<div style="color:#e11d48;padding:10px;border-radius:8px;margin-bottom:12px;background:#fff5f7;border:1px solid #fecaca;">'
        + message + '</div>'
        if message
        else ''
    )
    header = "Content-Type: text/html\n\n"
    body = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Admin Login - Power Monitor</title>
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" />
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display:flex; align-items:center; justify-content:center; margin:0; }
        .login { background:#fff; padding:40px; border-radius:14px; box-shadow:0 10px 40px rgba(2,6,23,0.2); width:100%; max-width:420px }
        .login h1{ font-size: 1.8rem; margin-bottom: 8px; color: #0f172a }
        .login p{ color: #64748b; margin-bottom: 20px }
        input{ width: 100%; padding: 12px; border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 12px }
        button{ display: inline-block; padding: 12px 18px; border-radius:8px; border:none; background:#334155; color:#fff; font-weight:600; cursor:pointer }
        .logo{ font-size: 2.5rem; margin-bottom: 8px }
    </style>
</head>
<body>
    <form class="login" method="post" action="/admin.cgi">
        <div class="logo">⚡</div>
        <h1>Admin Login</h1>
        <p>Authenticate to access the power monitor admin panel.</p>
        <!--MESSAGE_HTML-->
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
"""
    return header + body.replace('<!--MESSAGE_HTML-->', message_html)


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
        
        # Render dashboard with template
        print(render_dashboard(metrics, message, config))
        
    except Exception as e:
        print("Content-Type: text/html\n")
        print(f"<h1>Error</h1><pre>{str(e)}</pre>")


if __name__ == '__main__':
    main()
