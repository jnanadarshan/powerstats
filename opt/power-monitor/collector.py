#!/usr/bin/env python3
"""
Data Collector for Power Monitoring System
Fetches data from Home Assistant, manages state, and generates output files
"""

import json
import os
import sys
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import requests
from jinja2 import Environment, FileSystemLoader, select_autoescape

from config_manager import get_config


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/power-monitor-collector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('collector')


class MaintenanceMode:
    """Manages maintenance mode state"""
    
    def __init__(self, state_file: str):
        self.state_file = state_file
        self._ensure_state_file()
    
    def _ensure_state_file(self):
        """Create state file if it doesn't exist"""
        if not os.path.exists(self.state_file):
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, 'w') as f:
                f.write('maintenance_mode=false\n')
    
    def is_enabled(self) -> bool:
        """Check if maintenance mode is enabled"""
        try:
            with open(self.state_file, 'r') as f:
                content = f.read()
                return 'maintenance_mode=true' in content
        except Exception as e:
            logger.error(f"Error reading maintenance mode: {e}")
            return False
    
    def toggle(self) -> bool:
        """Toggle maintenance mode"""
        current = self.is_enabled()
        new_state = not current
        try:
            with open(self.state_file, 'w') as f:
                f.write(f'maintenance_mode={str(new_state).lower()}\n')
            logger.info(f"Maintenance mode toggled to: {new_state}")
            return new_state
        except Exception as e:
            logger.error(f"Error toggling maintenance mode: {e}")
            raise
    
    def set(self, enabled: bool):
        """Set maintenance mode state"""
        try:
            with open(self.state_file, 'w') as f:
                f.write(f'maintenance_mode={str(enabled).lower()}\n')
            logger.info(f"Maintenance mode set to: {enabled}")
        except Exception as e:
            logger.error(f"Error setting maintenance mode: {e}")
            raise


class HomeAssistantClient:
    """Client for fetching data from Home Assistant"""
    
    def __init__(self, url: str, token: str, entities: Optional[Dict[str, str]] = None):
        self.url = url.rstrip('/')
        self.token = token
        self.entities = entities or {}
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        })
    
    def get_current_state(self, entity_id: str) -> Dict[str, Any]:
        """Fetch current state of a specific entity"""
        try:
            response = self.session.get(
                f'{self.url}/api/states/{entity_id}',
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching current state for {entity_id}: {e}")
            raise
    
    def get_all_current_states(self) -> Dict[str, Dict[str, Any]]:
        """Fetch current states of all configured entities"""
        states = {}
        for entity_name, entity_id in self.entities.items():
            if not entity_id:
                logger.warning(f"Entity {entity_name} not configured, skipping")
                continue
            try:
                states[entity_name] = self.get_current_state(entity_id)
                logger.info(f"Fetched {entity_name}: {states[entity_name]['state']}")
            except Exception as e:
                logger.error(f"Failed to fetch {entity_name} ({entity_id}): {e}")
                # Continue with other entities even if one fails
        return states
    
    def get_history(self, entity_id: str, start_time: datetime, end_time: Optional[datetime] = None) -> List[Dict]:
        """Fetch historical data for a specific entity"""
        try:
            params = {
                'filter_entity_id': entity_id,
                'minimal_response': 'true',
                'significant_changes_only': 'false'
            }
            
            # Format timestamps in ISO format
            start_iso = start_time.isoformat()
            params['end_time'] = end_time.isoformat() if end_time else datetime.now().isoformat()
            
            response = self.session.get(
                f'{self.url}/api/history/period/{start_iso}',
                params=params,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            # Return flattened list of states
            return data[0] if data else []
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching history for {entity_id}: {e}")
            raise


class DataManager:
    """Manages data storage - writes to JSON files with time-based retention"""
    
    def __init__(self, data_file: str, max_points: int = 144, retention_hours: int = 24):
        """
        Initialize data manager.
        
        Args:
            data_file: Path to the JSON file to manage
            max_points: Maximum number of data points to keep (used as fallback if smaller than retention)
            retention_hours: How many hours of data to keep (e.g., 24 for daily, 168 for weekly)
        """
        self.data_file = data_file
        self.max_points = max_points
        self.retention_hours = retention_hours
        self._ensure_data_file()
    
    def _ensure_data_file(self):
        """Create data file if it doesn't exist"""
        if not os.path.exists(self.data_file):
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            with open(self.data_file, 'w') as f:
                json.dump([], f)
            # Set permissions so web server can read the file
            try:
                os.chmod(self.data_file, 0o664)  # rw-rw-r--
            except OSError:
                pass  # If chmod fails, continue anyway
    
    def _write_data(self, data: List[Dict]):
        """Write data to file atomically"""
        temp_file = self.data_file + '.tmp'
        with open(temp_file, 'w') as f:
            json.dump(data, f, indent=4)
        # Set permissions on temp file before replacing (readable by web server)
        try:
            os.chmod(temp_file, 0o664)  # rw-rw-r--
        except OSError:
            pass  # If chmod fails, continue anyway
        os.replace(temp_file, self.data_file)
    
    def load_data(self) -> List[Dict[str, Any]]:
        """Load data from file"""
        try:
            with open(self.data_file, 'r') as f:
                # Handle empty file case
                content = f.read()
                if not content:
                    return []
                return json.loads(content)
        except (json.JSONDecodeError, FileNotFoundError):
            logger.warning("Data file corrupted or missing, initializing new data file.")
            self._ensure_data_file()
            return []

    def add_data_point(self, timestamp: str, entities_data: Dict[str, Dict[str, Any]]):
        """Add a new multi-entity data point, trimming old data based on retention period"""
        data_points = self.load_data()
        
        # Build the flat data point object
        new_data_point = {'timestamp': timestamp}
        
        for entity_name, entity_state in entities_data.items():
            try:
                # Use the entity_name as the key (e.g., "power", "voltage")
                value = float(entity_state.get('state', 0))
                new_data_point[entity_name] = round(value, 2)
            except (ValueError, TypeError):
                logger.warning(f"Could not parse value for {entity_name}. Setting to 0.")
                new_data_point[entity_name] = 0
        
        # Append new data
        data_points.append(new_data_point)
        
        # Sort by timestamp to be safe
        data_points.sort(key=lambda x: x['timestamp'])
        
        # Trim data based on retention hours - remove any point older than retention_hours
        cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)
        cutoff_iso = cutoff_time.isoformat()
        data_points = [p for p in data_points if p['timestamp'] >= cutoff_iso]
        
        # Also apply max_points as a hard limit (fallback)
        if len(data_points) > self.max_points:
            data_points = data_points[-self.max_points:]
            
        self._write_data(data_points)
        file_name = os.path.basename(self.data_file)
        logger.info(f"Updated {file_name} at {timestamp}. Total points: {len(data_points)}, retention: {self.retention_hours}h")


def main():
    """Main collection routine"""
    try:
        # Ensure system time is correct after reboot (run once per boot)
        def ensure_time_synced(marker_path='/var/run/power-monitor-time-synced'):
            try:
                if os.path.exists(marker_path):
                    return
                # Prefer to only attempt if ntpd is available
                subprocess.run(['ntpd', '-d', '-q', '-p', 'pool.ntp.org'], check=False)
                # Create marker so we don't run again until reboot
                try:
                    Path(os.path.dirname(marker_path)).mkdir(parents=True, exist_ok=True)
                    Path(marker_path).write_text(datetime.now().isoformat())
                except Exception:
                    logger.debug('Could not write ntp marker file')
            except FileNotFoundError:
                logger.warning('ntpd not found; skipping time sync')
            except Exception as e:
                logger.error(f'Error while syncing time: {e}')

        ensure_time_synced()
        # Load configuration
        config = get_config()
        logger.info("Starting multi-entity data collection")
        
        # Check maintenance mode
        maintenance = MaintenanceMode(config.state_file)
        if maintenance.is_enabled():
            logger.info("Maintenance mode enabled, skipping collection")
            return 0
        
        # Initialize components
        ha_client = HomeAssistantClient(
            config.ha_url,
            config.ha_token,
            config.ha_entities
        )
        
        # The collector only writes to the daily file.
        daily_data_file = os.path.join(config.web_root, 'daily.json')
        
        # Determine how many points to keep in daily.json based on collection
        # interval. Prefer the device-local key `local_collection_interval_minutes`
        # in `data` section of the config; fall back to the legacy
        # `collection_interval_minutes` exposed via config.collection_interval.
        try:
            local_iv = config.get('data.local_collection_interval_minutes')
        except Exception:
            local_iv = None

        if local_iv is None:
            interval_min = config.collection_interval
        else:
            try:
                interval_min = int(local_iv)
            except Exception:
                interval_min = config.collection_interval

        # Sanity-check interval and compute points-per-day
        try:
            interval_min = int(interval_min)
        except Exception:
            interval_min = 10

        if interval_min <= 0:
            interval_min = 10

        points_per_day = max(1, int(24 * 60 / interval_min))
        logger.info(f"Collection interval: {interval_min} minutes -> storing {points_per_day} points in daily.json")

        # Create data managers for both daily and weekly files
        weekly_data_file = os.path.join(config.web_root, 'weekly.json')
        
        # Daily: 24 hours of data at collection interval
        daily_manager = DataManager(
            daily_data_file,
            max_points=points_per_day,
            retention_hours=24
        )
        
        # Weekly: 7 days of granular data (same format as daily)
        # Calculate points for 7 days
        points_per_week = max(1, int(7 * 24 * 60 / interval_min))
        weekly_manager = DataManager(
            weekly_data_file,
            max_points=points_per_week,
            retention_hours=168  # 7 days * 24 hours
        )
        
        # Fetch current states for all entities
        entities_data = ha_client.get_all_current_states()
        
        if not entities_data:
            logger.warning("No data fetched from Home Assistant. Skipping data point addition.")
            return 1

        # Use a consistent timestamp for this collection event
        timestamp = datetime.now().isoformat()
        
        logger.info(f"Fetched states for {len(entities_data)} entities at {timestamp}")
        for entity_name, entity_state in entities_data.items():
            value = entity_state.get('state', 'N/A')
            unit = entity_state.get('attributes', {}).get('unit_of_measurement', '')
            logger.info(f"  {entity_name}: {value}{unit}")
        
        # Add data point to both daily and weekly files
        daily_manager.add_data_point(timestamp, entities_data)
        weekly_manager.add_data_point(timestamp, entities_data)
        
        logger.info("Multi-entity collection completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Collection failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
