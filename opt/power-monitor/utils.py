#!/usr/bin/env python3
"""
Utility Script for Power Monitoring System
Provides common operations and diagnostics
"""

import sys
import os
import json
import argparse
from datetime import datetime
from pathlib import Path

# Add power-monitor to path
sys.path.insert(0, '/opt/power-monitor')

try:
    from config_manager import get_config
    from collector import MaintenanceMode, DataManager
except ImportError:
    print("Warning: Running in development mode")


def check_status():
    """Display system status"""
    print("=" * 60)
    print("Power Monitoring System Status")
    print("=" * 60)
    print()
    
    try:
        config = get_config()
        
        # Maintenance mode
        maintenance = MaintenanceMode(config.state_file)
        mm_status = "ENABLED" if maintenance.is_enabled() else "Disabled"
        print(f"Maintenance Mode: {mm_status}")
        print()
        
        # Data statistics
        if os.path.exists(config.data_file):
            with open(config.data_file, 'r') as f:
                data = json.load(f)
            
            data_points = data.get('data_points', [])
            last_update = data.get('last_update', 'Never')
            
            print(f"Last Update: {last_update}")
            print(f"Data Points: {len(data_points)}")
            
            if data_points:
                values = [dp['value'] for dp in data_points]
                print(f"Current Power: {values[-1]:.2f} W")
                print(f"Average: {sum(values)/len(values):.2f} W")
                print(f"Min: {min(values):.2f} W")
                print(f"Max: {max(values):.2f} W")
        else:
            print("Data file not found - no data collected yet")
        
        print()
        
        # Configuration
        print("Configuration:")
        print(f"  HA URL: {config.ha_url}")
        print(f"  HA Entity: {config.ha_entity_id}")
        print(f"  GitHub: {config.gh_repo_owner}/{config.gh_repo_name}")
        print(f"  Retention: {config.retention_days} days")
        print(f"  Interval: {config.collection_interval} minutes")
        
    except Exception as e:
        print(f"Error checking status: {e}")
        return 1
    
    return 0


def toggle_maintenance():
    """Toggle maintenance mode"""
    try:
        config = get_config()
        maintenance = MaintenanceMode(config.state_file)
        new_state = maintenance.toggle()
        
        status = "ENABLED" if new_state else "DISABLED"
        print(f"Maintenance mode {status}")
        return 0
    except Exception as e:
        print(f"Error toggling maintenance mode: {e}")
        return 1


def enable_maintenance():
    """Enable maintenance mode"""
    try:
        config = get_config()
        maintenance = MaintenanceMode(config.state_file)
        maintenance.set(True)
        print("Maintenance mode ENABLED")
        return 0
    except Exception as e:
        print(f"Error enabling maintenance mode: {e}")
        return 1


def disable_maintenance():
    """Disable maintenance mode"""
    try:
        config = get_config()
        maintenance = MaintenanceMode(config.state_file)
        maintenance.set(False)
        print("Maintenance mode DISABLED")
        return 0
    except Exception as e:
        print(f"Error disabling maintenance mode: {e}")
        return 1


def show_logs(component='collector', lines=20):
    """Display recent log entries"""
    log_files = {
        'collector': '/var/log/power-monitor-collector.log',
        'publisher': '/var/log/power-monitor-publisher.log',
        'web': '/var/log/lighttpd/access.log',
        'error': '/var/log/lighttpd/error.log'
    }
    
    log_file = log_files.get(component)
    if not log_file or not os.path.exists(log_file):
        print(f"Log file not found: {log_file}")
        return 1
    
    print(f"Last {lines} lines from {log_file}:")
    print("=" * 60)
    
    try:
        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            recent = all_lines[-lines:]
            print(''.join(recent))
    except Exception as e:
        print(f"Error reading log: {e}")
        return 1
    
    return 0


def clear_data():
    """Clear all collected data"""
    try:
        config = get_config()
        
        confirm = input("This will delete all collected data. Continue? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled")
            return 0
        
        data_manager = DataManager(config.data_file, config.retention_days)
        data_manager._write_data({'data_points': [], 'last_update': None})
        
        print("Data cleared successfully")
        return 0
    except Exception as e:
        print(f"Error clearing data: {e}")
        return 1


def export_data(output_file=None):
    """Export data to JSON file"""
    try:
        config = get_config()
        
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"power_data_export_{timestamp}.json"
        
        if os.path.exists(config.data_file):
            with open(config.data_file, 'r') as f:
                data = json.load(f)
            
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"Data exported to: {output_file}")
            print(f"Total data points: {len(data.get('data_points', []))}")
            return 0
        else:
            print("No data file found")
            return 1
    except Exception as e:
        print(f"Error exporting data: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description='Power Monitoring System Utility',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s status              # Show system status
  %(prog)s maintenance on      # Enable maintenance mode
  %(prog)s logs collector      # Show collector logs
  %(prog)s export data.json    # Export data to file
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Status command
    subparsers.add_parser('status', help='Show system status')
    
    # Maintenance commands
    maint_parser = subparsers.add_parser('maintenance', help='Control maintenance mode')
    maint_parser.add_argument('action', choices=['on', 'off', 'toggle'],
                              help='Maintenance mode action')
    
    # Logs command
    logs_parser = subparsers.add_parser('logs', help='Show log files')
    logs_parser.add_argument('component', 
                            choices=['collector', 'publisher', 'web', 'error'],
                            default='collector', nargs='?',
                            help='Component to show logs for')
    logs_parser.add_argument('-n', '--lines', type=int, default=20,
                            help='Number of lines to show')
    
    # Data commands
    subparsers.add_parser('clear', help='Clear all collected data')
    
    export_parser = subparsers.add_parser('export', help='Export data to file')
    export_parser.add_argument('output', nargs='?', 
                              help='Output file (default: timestamped)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    if args.command == 'status':
        return check_status()
    
    elif args.command == 'maintenance':
        if args.action == 'on':
            return enable_maintenance()
        elif args.action == 'off':
            return disable_maintenance()
        elif args.action == 'toggle':
            return toggle_maintenance()
    
    elif args.command == 'logs':
        return show_logs(args.component, args.lines)
    
    elif args.command == 'clear':
        return clear_data()
    
    elif args.command == 'export':
        return export_data(args.output)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
