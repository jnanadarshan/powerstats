#!/usr/bin/env python3
"""
Quick Start Script
Helps generate a basic config.json file interactively
"""

import json
import os
from pathlib import Path


def get_input(prompt, default=None):
    """Get user input with optional default"""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    
    value = input(prompt).strip()
    return value if value else default


def main():
    print("=" * 60)
    print("Power Monitoring System - Configuration Generator")
    print("=" * 60)
    print()
    print("This wizard will help you create a config.json file.")
    print("Press Enter to use default values (shown in brackets).")
    print()
    
    # Home Assistant configuration
    print("--- Home Assistant Configuration ---")
    ha_url = get_input("Home Assistant URL", "http://homeassistant.local:8123")
    ha_token = get_input("Home Assistant Long-Lived Access Token")
    ha_entity = get_input("Power sensor entity ID", "sensor.power_consumption")
    print()
    
    # GitHub configuration
    print("--- GitHub Pages Configuration ---")
    gh_token = get_input("GitHub Personal Access Token")
    gh_owner = get_input("GitHub username/organization")
    gh_repo = get_input("Repository name", "power-stats-pages")
    gh_branch = get_input("Branch name", "main")
    print()
    
    # Data configuration
    print("--- Data Settings ---")
    retention = get_input("Data retention (days)", "7")
    interval = get_input("Collection interval (minutes)", "10")
    print()
    
    # Admin configuration
    print("--- Admin Interface ---")
    admin_user = get_input("Admin username", "admin")
    admin_pass = get_input("Admin password", "changeme")
    print()
    
    # Paths (use defaults for Alpine Linux)
    print("--- File Paths ---")
    use_defaults = get_input("Use default paths for Alpine Linux? (y/n)", "y").lower()
    
    if use_defaults == 'y':
        state_file = "/etc/monitor.conf"
        web_root = "/var/www/html"
        data_file = "/var/www/html/data.json"
    else:
        state_file = get_input("State file path", "/etc/monitor.conf")
        web_root = get_input("Web root directory", "/var/www/html")
        data_file = get_input("Data file path", "/var/www/html/data.json")
    
    # Build configuration dictionary
    config = {
        "homeassistant": {
            "url": ha_url,
            "token": ha_token,
            "entity_id": ha_entity
        },
        "github": {
            "token": gh_token,
            "repo_owner": gh_owner,
            "repo_name": gh_repo,
            "branch": gh_branch
        },
        "data": {
            "retention_days": int(retention),
            "collection_interval_minutes": int(interval)
        },
        "admin": {
            "username": admin_user,
            "password_hash": admin_pass
        },
        "paths": {
            "state_file": state_file,
            "web_root": web_root,
            "data_file": data_file
        }
    }
    
    # Determine output path
    script_dir = Path(__file__).parent
    config_path = script_dir / "opt" / "power-monitor" / "config.json"
    
    # Write configuration
    print()
    print(f"Writing configuration to: {config_path}")
    
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print()
    print("=" * 60)
    print("Configuration file created successfully!")
    print("=" * 60)
    print()
    print("IMPORTANT SECURITY NOTES:")
    print("1. Keep config.json secure - it contains sensitive tokens")
    print("2. Never commit config.json to version control")
    print("3. Change the admin password from default")
    print()
    print("Next steps:")
    print("1. Review the config.json file")
    print("2. Upload to your device at /opt/power-monitor/config.json")
    print("3. Set permissions: chmod 600 /opt/power-monitor/config.json")
    print("4. Run the installation script")
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nConfiguration cancelled.")
    except Exception as e:
        print(f"\nError: {e}")
