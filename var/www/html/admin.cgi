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
    replacements['CRON_STATUS'] = str(metrics['system'].get('cron_status', 'Unable to detect'))
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
    
    # Load config data for setup wizard
    try:
        config_data = get_config_for_display()
        replacements['CONFIG_HA_URL'] = config_data.get('homeassistant', {}).get('url', '')
        replacements['CONFIG_HA_TOKEN'] = config_data.get('homeassistant', {}).get('token', '')
        replacements['CONFIG_HA_VOLTAGE_ENTITY'] = config_data.get('homeassistant', {}).get('entities', {}).get('voltage', '')
        replacements['CONFIG_HA_POWER_ENTITY'] = config_data.get('homeassistant', {}).get('entities', {}).get('power', '')
        replacements['CONFIG_HA_SOLAR_ENTITY'] = config_data.get('homeassistant', {}).get('entities', {}).get('solar', '')
        replacements['CONFIG_HA_PF_ENTITY'] = config_data.get('homeassistant', {}).get('entities', {}).get('power_factor', '')
        replacements['CONFIG_HA_ENERGY_ENTITY'] = config_data.get('homeassistant', {}).get('entities', {}).get('daily_energy', '')
        replacements['CONFIG_GH_TOKEN'] = config_data.get('github', {}).get('token', '')
        replacements['CONFIG_GH_REPO'] = config_data.get('github', {}).get('repo', '')
        replacements['CONFIG_GH_BRANCH'] = config_data.get('github', {}).get('branch', 'main')
        replacements['CONFIG_GH_USER_NAME'] = config_data.get('github', {}).get('user', {}).get('name', '')
        replacements['CONFIG_GH_USER_EMAIL'] = config_data.get('github', {}).get('user', {}).get('email', '')
        replacements['CONFIG_COLLECTION_INTERVAL'] = str(config_data.get('data', {}).get('local_collection_interval_minutes', 10))
        replacements['CONFIG_PUBLISH_INTERVAL'] = str(config_data.get('data', {}).get('publish_interval_minutes', 60))
        replacements['CONFIG_RETENTION_DAYS'] = str(config_data.get('data', {}).get('retention_days', 7))
        replacements['CONFIG_HEALTH_INTERVAL'] = str(config_data.get('data', {}).get('health_check_interval_seconds', 10))
        replacements['CONFIG_ADMIN_USERNAME'] = config_data.get('admin', {}).get('username', 'admin')
        replacements['CONFIG_UL_THRESHOLD'] = str(config_data.get('voltage_threshold', {}).get('UL', 250))
        replacements['CONFIG_LL_THRESHOLD'] = str(config_data.get('voltage_threshold', {}).get('LL', 220))
    except Exception as e:
        # If config can't be loaded, use defaults
        replacements.update({f'CONFIG_{k}': '' for k in [
            'HA_URL', 'HA_TOKEN', 'HA_VOLTAGE_ENTITY', 'HA_POWER_ENTITY', 'HA_SOLAR_ENTITY', 'HA_PF_ENTITY', 'HA_ENERGY_ENTITY',
            'GH_TOKEN', 'GH_REPO', 'GH_BRANCH', 'GH_USER_NAME', 'GH_USER_EMAIL',
            'COLLECTION_INTERVAL', 'PUBLISH_INTERVAL', 'RETENTION_DAYS', 'HEALTH_INTERVAL',
            'ADMIN_USERNAME', 'UL_THRESHOLD', 'LL_THRESHOLD'
        ]})
    
    # Load cron jobs for display
    try:
        replacements['CRON_JOBS_TABLE'] = render_cron_jobs_table()
    except Exception as e:
        replacements['CRON_JOBS_TABLE'] = f'<div style="color: #ef4444;">Error loading cron jobs: {str(e)}</div>'
    
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
        
        # Try to check cron jobs - multiple methods for compatibility with Alpine
        cron_jobs = []
        cron_status = "Not found"
        
        try:
            # Method 1: Try crontab -l (primary method for Alpine Linux)
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                cron_lines = result.stdout.strip().split('\n')
                # Filter out comments and empty lines
                active_jobs = [line.strip() for line in cron_lines if line.strip() and not line.strip().startswith('#')]
                if active_jobs:
                    cron_jobs = active_jobs
                    cron_status = f"Found {len(active_jobs)} job(s)"
        except Exception as e1:
            # crontab might not be available or user might not have cron
            pass
        
        # Method 2: Check if scheduler.py process is running
        if not cron_jobs:
            try:
                result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=5)
                scheduler_lines = [line for line in result.stdout.split('\n') 
                                 if 'scheduler.py' in line and 'grep' not in line and 'admin.cgi' not in line]
                if scheduler_lines:
                    cron_jobs = scheduler_lines
                    cron_status = f"Scheduler running ({len(scheduler_lines)} process)"
            except Exception as e2:
                pass
        
        # Method 3: Check systemd service status
        if not cron_jobs:
            try:
                result = subprocess.run(['systemctl', 'is-active', 'power-monitor-scheduler'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and 'active' in result.stdout.lower():
                    cron_jobs = ['systemd service: power-monitor-scheduler']
                    cron_status = "Service active"
            except Exception as e3:
                pass
        
        # Method 4: Check /etc/crontabs (Alpine Linux crontab location)
        if not cron_jobs:
            try:
                root_crontab = '/etc/crontabs/root'
                if os.path.exists(root_crontab):
                    with open(root_crontab, 'r') as f:
                        lines = f.read().strip().split('\n')
                        active_jobs = [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]
                        if active_jobs:
                            cron_jobs = active_jobs
                            cron_status = f"Found {len(active_jobs)} job(s) in /etc/crontabs/root"
            except Exception as e4:
                pass
        
        # Method 5: Check for crond daemon running
        if not cron_jobs:
            try:
                result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=5)
                crond_lines = [line for line in result.stdout.split('\n') if 'crond' in line and 'grep' not in line]
                if crond_lines:
                    cron_status = "Cron daemon running"
            except:
                pass
        
        # Set metrics based on what was found
        if cron_jobs:
            metrics['system']['cron_jobs'] = len(cron_jobs)
            metrics['system']['cron_status'] = cron_status
        else:
            metrics['system']['cron_jobs'] = "Unknown"
            metrics['system']['cron_status'] = "Unable to detect"
            
    except Exception as e:
        metrics['system']['error'] = str(e)
        metrics['system']['cron_jobs'] = "Error"
    
    return metrics


def get_cron_jobs_detailed() -> list:
    """Get detailed cron job information with schedules"""
    cron_jobs = []
    
    try:
        # Try crontab -l first
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    cron_jobs.append({
                        'schedule': line,
                        'source': 'crontab -l',
                        'type': 'user_cron'
                    })
    except Exception:
        pass
    
    # Try /etc/crontabs/root (Alpine)
    if not cron_jobs:
        try:
            root_crontab = '/etc/crontabs/root'
            if os.path.exists(root_crontab):
                with open(root_crontab, 'r') as f:
                    lines = f.read().strip().split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            cron_jobs.append({
                                'schedule': line,
                                'source': '/etc/crontabs/root',
                                'type': 'root_cron'
                            })
        except Exception:
            pass
    
    # Check for systemd services
    try:
        services_to_check = ['power-monitor-scheduler', 'power-monitor-collector']
        for service in services_to_check:
            result = subprocess.run(
                ['systemctl', 'is-active', service],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and 'active' in result.stdout.lower():
                # Get timer info if it exists
                try:
                    timer_result = subprocess.run(
                        ['systemctl', 'list-timers', service],
                        capture_output=True, text=True, timeout=5
                    )
                    if timer_result.returncode == 0:
                        cron_jobs.append({
                            'schedule': f'Systemd service: {service} (active)',
                            'source': 'systemd',
                            'type': 'systemd_service'
                        })
                except:
                    cron_jobs.append({
                        'schedule': f'Systemd service: {service} (active)',
                        'source': 'systemd',
                        'type': 'systemd_service'
                    })
    except Exception:
        pass
    
    return cron_jobs


def format_cron_schedule(cron_line: str) -> dict:
    """Parse and format cron schedule for display"""
    parts = cron_line.split()
    if len(parts) < 5:
        return {'minute': 'N/A', 'hour': 'N/A', 'day': 'N/A', 'month': 'N/A', 'dow': 'N/A', 'command': cron_line}
    
    return {
        'minute': parts[0] if parts[0] != '*' else 'Every minute',
        'hour': parts[1] if parts[1] != '*' else 'Every hour',
        'day': parts[2] if parts[2] != '*' else 'Every day',
        'month': parts[3] if parts[3] != '*' else 'Every month',
        'dow': parts[4] if parts[4] != '*' else 'Every day',
        'command': ' '.join(parts[5:]) if len(parts) > 5 else 'N/A'
    }


def render_cron_jobs_table() -> str:
    """Render cron jobs as an HTML table for display in the UI.

    Uses `get_cron_jobs_detailed()` to obtain a list of cron jobs and
    returns an HTML snippet (string). On error returns a small error
    message HTML block so the caller can embed it directly in the
    template.
    """
    try:
        jobs = get_cron_jobs_detailed()
        if not jobs:
            return '<div style="color: #64748b;">No cron jobs found</div>'

        html = []
        html.append('<table class="data-files-table" style="width:100%;border-collapse:collapse;">')
        html.append('<thead><tr><th style="text-align:left;padding:8px;border-bottom:1px solid var(--border);">Schedule</th>'
                    '<th style="text-align:left;padding:8px;border-bottom:1px solid var(--border);">Source</th>'
                    '<th style="text-align:left;padding:8px;border-bottom:1px solid var(--border);">Type</th></tr></thead>')
        html.append('<tbody>')

        for job in jobs:
            schedule = job.get('schedule', '')
            source = job.get('source', '')
            jtype = job.get('type', '')
            html.append(f'<tr>\n<td style="padding:8px;border-bottom:1px solid var(--border);font-weight:600;">{schedule}</td>'
                        f'<td style="padding:8px;border-bottom:1px solid var(--border);">{source}</td>'
                        f'<td style="padding:8px;border-bottom:1px solid var(--border);">{jtype}</td></tr>')

        html.append('</tbody></table>')
        return '\n'.join(html)
    except Exception as e:
        return f'<div style="color: #ef4444;">Error loading cron jobs: {str(e)}</div>'


def get_config_for_display(config_path: str = '/opt/power-monitor/config.json') -> dict:
    """Load config and prepare for display"""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        return {}


def save_config_from_form(form_data, config_path: str = '/opt/power-monitor/config.json') -> tuple:
    """Save config fields from form data"""
    try:
        # Load current config
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Update fields from form
        field_mapping = {
            'ha_url': 'homeassistant.url',
            'ha_token': 'homeassistant.token',
            'ha_voltage_entity': 'homeassistant.entities.voltage',
            'ha_power_entity': 'homeassistant.entities.power',
            'ha_solar_entity': 'homeassistant.entities.solar',
            'ha_pf_entity': 'homeassistant.entities.power_factor',
            'ha_energy_entity': 'homeassistant.entities.daily_energy',
            'gh_token': 'github.token',
            'gh_repo': 'github.repo',
            'gh_branch': 'github.branch',
            'gh_user_name': 'github.user.name',
            'gh_user_email': 'github.user.email',
            'collection_interval': 'data.local_collection_interval_minutes',
            'publish_interval': 'data.publish_interval_minutes',
            'retention_days': 'data.retention_days',
            'health_interval': 'data.health_check_interval_seconds',
            'admin_username': 'admin.username',
            'ul_threshold': 'voltage_threshold.UL',
            'll_threshold': 'voltage_threshold.LL'
        }
        
        for form_key, config_key in field_mapping.items():
            value = form_data.getvalue(form_key, '').strip()
            if value:
                # Navigate nested keys
                keys = config_key.split('.')
                current = config
                for key in keys[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                current[keys[-1]] = value
        
        # Write updated config (atomically)
        temp_path = config_path + '.tmp'
        with open(temp_path, 'w') as f:
            json.dump(config, f, indent=2)
        os.replace(temp_path, config_path)
        
        return True, 'Configuration saved successfully'
    except Exception as e:
        return False, f'Error saving config: {str(e)}'


def restart_services() -> tuple:
    """Restart power monitor services"""
    try:
        # Restart scheduler
        result = subprocess.run(
            ['systemctl', 'restart', 'power-monitor-scheduler'],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode != 0:
            return False, f'Failed to restart scheduler: {result.stderr}'
        
        return True, 'Services restarted successfully. Changes will take effect shortly.'
    except Exception as e:
        return False, f'Error restarting services: {str(e)}'


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
        
        elif action == 'save_config':
            success, message = save_config_from_form(form)
            if success:
                result['success'] = True
                result['message'] = message
            else:
                result['message'] = message
        
        elif action == 'restart_services':
            success, message = restart_services()
            result['success'] = success
            result['message'] = message
        
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
