#!/usr/bin/env python3
"""
System Health Module for Power Monitor
Provides disk usage, memory usage, collection status, and GitHub sync status
"""

import os
import json
import psutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('health')


class SystemHealth:
    """System health monitoring"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize health monitor"""
        if config_path:
            self.config_path = Path(config_path)
        else:
            self.config_path = Path(__file__).parent / 'config.json'
        
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
        return {}
    
    def get_disk_usage(self) -> Dict[str, Any]:
        """Get disk usage for data directory"""
        try:
            data_dir = self.config.get('data', {}).get('directory', '/var/www/html')
            disk = psutil.disk_usage(data_dir)
            
            return {
                'path': data_dir,
                'total_gb': round(disk.total / (1024**3), 2),
                'used_gb': round(disk.used / (1024**3), 2),
                'free_gb': round(disk.free / (1024**3), 2),
                'percent': disk.percent
            }
        except Exception as e:
            logger.error(f"Error getting disk usage: {e}")
            return {
                'path': 'unknown',
                'total_gb': 0,
                'used_gb': 0,
                'free_gb': 0,
                'percent': 0,
                'error': str(e)
            }
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get system memory usage"""
        try:
            mem = psutil.virtual_memory()
            
            return {
                'total_mb': round(mem.total / (1024**2), 2),
                'used_mb': round(mem.used / (1024**2), 2),
                'available_mb': round(mem.available / (1024**2), 2),
                'percent': mem.percent
            }
        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            return {
                'total_mb': 0,
                'used_mb': 0,
                'available_mb': 0,
                'percent': 0,
                'error': str(e)
            }
    
    def get_collection_status(self) -> Dict[str, Any]:
        """Get data collection status and timing"""
        try:
            # Read last update from daily.json
            data_dir = self.config.get('data', {}).get('directory', '/var/www/html')
            daily_file = Path(data_dir) / 'daily.json'
            
            last_update_utc = None
            last_update_ist = None
            
            if daily_file.exists():
                with open(daily_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    last_update_str = data.get('last_update')
                    
                    if last_update_str:
                        # Parse ISO format
                        last_update_utc = datetime.fromisoformat(last_update_str.replace('Z', '+00:00'))
                        
                        # Convert to IST (UTC+5:30)
                        ist_offset = timedelta(hours=5, minutes=30)
                        last_update_ist = last_update_utc + ist_offset
            
            # Collection interval from config
            try:
                from config_manager import get_config
                config = get_config()
                collection_interval_minutes = config.local_collection_interval
            except Exception as e:
                logger.warning(f"Could not read collection interval from config: {e}")
                collection_interval_minutes = 10
            
            # Calculate next collection time
            next_collection_utc = None
            next_collection_ist = None
            seconds_until_next = None
            
            if last_update_utc:
                next_collection_utc = last_update_utc + timedelta(minutes=collection_interval_minutes)
                next_collection_ist = last_update_ist + timedelta(minutes=collection_interval_minutes)
                
                # Calculate countdown
                now_utc = datetime.now(timezone.utc)
                delta = next_collection_utc - now_utc
                seconds_until_next = max(0, int(delta.total_seconds()))
            
            return {
                'last_collection_ist': last_update_ist.strftime('%Y-%m-%d %H:%M:%S IST') if last_update_ist else 'Never',
                'last_collection_utc': last_update_utc.isoformat() if last_update_utc else None,
                'next_collection_ist': next_collection_ist.strftime('%Y-%m-%d %H:%M:%S IST') if next_collection_ist else 'Unknown',
                'seconds_until_next': seconds_until_next,
                'interval_minutes': collection_interval_minutes
            }
        except Exception as e:
            logger.error(f"Error getting collection status: {e}")
            return {
                'last_collection_ist': 'Error',
                'last_collection_utc': None,
                'next_collection_ist': 'Unknown',
                'seconds_until_next': None,
                'interval_minutes': 10,
                'error': str(e)
            }
    
    def get_github_status(self) -> Dict[str, Any]:
        """Get GitHub sync status"""
        try:
            # Check last publish time from state file
            state_file = self.config.get('paths', {}).get('state_file', '/var/lib/power-monitor/state.json')
            state_path = Path(state_file)
            
            last_publish = None
            last_publish_status = 'Unknown'
            
            if state_path.exists():
                try:
                    with open(state_path, 'r', encoding='utf-8') as f:
                        state = json.load(f)
                        last_publish = state.get('last_publish')
                        last_publish_status = state.get('last_publish_status', 'Unknown')
                except Exception as e:
                    logger.warning(f"Could not read state file: {e}")
            
            # Check if GitHub is configured
            github_config = self.config.get('github', {})
            is_configured = bool(github_config.get('token') and github_config.get('repo'))
            
            # Convert last publish to IST if available
            last_publish_ist = None
            if last_publish:
                try:
                    last_pub_dt = datetime.fromisoformat(last_publish.replace('Z', '+00:00'))
                    ist_offset = timedelta(hours=5, minutes=30)
                    last_publish_ist = (last_pub_dt + ist_offset).strftime('%Y-%m-%d %H:%M:%S IST')
                except Exception as e:
                    logger.warning(f"Error parsing last publish time: {e}")
            
            return {
                'configured': is_configured,
                'last_publish_ist': last_publish_ist or 'Never',
                'status': last_publish_status,
                'repo': github_config.get('repo', 'Not configured'),
                'branch': github_config.get('branch', 'main')
            }
        except Exception as e:
            logger.error(f"Error getting GitHub status: {e}")
            return {
                'configured': False,
                'last_publish_ist': 'Error',
                'status': 'Unknown',
                'repo': 'Not configured',
                'branch': 'main',
                'error': str(e)
            }
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get complete health report"""
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'disk': self.get_disk_usage(),
            'memory': self.get_memory_usage(),
            'collection': self.get_collection_status(),
            'github': self.get_github_status()
        }


def main():
    """CLI entry point"""
    import sys
    
    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    health = SystemHealth(config_path)
    report = health.get_health_report()
    
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
