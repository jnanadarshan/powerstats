#!/usr/bin/env python3
"""
Data Collector for Power Monitoring System
Fetches data from Home Assistant, manages state, and generates output files
"""

import json
import os
import sys
import logging
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
    
    def __init__(self, url: str, token: str, entity_id: str):
        self.url = url.rstrip('/')
        self.token = token
        self.entity_id = entity_id
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        })
    
    def get_current_state(self) -> Dict[str, Any]:
        """Fetch current state of the entity"""
        try:
            response = self.session.get(
                f'{self.url}/api/states/{self.entity_id}',
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching current state: {e}")
            raise
    
    def get_history(self, start_time: datetime, end_time: Optional[datetime] = None) -> List[Dict]:
        """Fetch historical data for the entity"""
        try:
            params = {
                'filter_entity_id': self.entity_id,
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
            logger.error(f"Error fetching history: {e}")
            raise


class DataManager:
    """Manages data storage and retention"""
    
    def __init__(self, data_file: str, retention_days: int):
        self.data_file = data_file
        self.retention_days = retention_days
        self._ensure_data_file()
    
    def _ensure_data_file(self):
        """Create data file if it doesn't exist"""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        if not os.path.exists(self.data_file):
            self._write_data({'data_points': [], 'last_update': None})
    
    def _write_data(self, data: Dict):
        """Write data to file"""
        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_data(self) -> Dict[str, Any]:
        """Load data from file"""
        try:
            with open(self.data_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            logger.warning("Data file corrupted or missing, initializing new data")
            return {'data_points': [], 'last_update': None}
    
    def add_data_point(self, timestamp: str, value: float, unit: str = 'W'):
        """Add a new data point and maintain retention window"""
        data = self.load_data()
        
        # Add new data point
        data_points = data.get('data_points', [])
        data_points.append({
            'timestamp': timestamp,
            'value': value,
            'unit': unit
        })
        
        # Remove old data outside retention window
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        data_points = [
            dp for dp in data_points
            if datetime.fromisoformat(dp['timestamp'].replace('Z', '+00:00')) > cutoff
        ]
        
        # Sort by timestamp
        data_points.sort(key=lambda x: x['timestamp'])
        
        # Update data
        data['data_points'] = data_points
        data['last_update'] = datetime.now().isoformat()
        
        self._write_data(data)
        logger.info(f"Added data point: {value}{unit} at {timestamp}, total points: {len(data_points)}")
        
        return data
    
    def get_statistics(self, data_points: List[Dict]) -> Dict[str, float]:
        """Calculate statistics from data points"""
        if not data_points:
            return {
                'current': 0,
                'average': 0,
                'min': 0,
                'max': 0,
                'total_kwh': 0
            }
        
        values = [dp['value'] for dp in data_points]
        
        # Calculate total kWh (assuming 10-minute intervals)
        interval_hours = 10 / 60  # 10 minutes in hours
        total_kwh = sum(values) * interval_hours / 1000
        
        return {
            'current': values[-1],
            'average': sum(values) / len(values),
            'min': min(values),
            'max': max(values),
            'total_kwh': round(total_kwh, 2)
        }


class HTMLGenerator:
    """Generates HTML dashboard from data"""
    
    def __init__(self, template_dir: str):
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )
    
    def generate(self, data: Dict[str, Any], output_file: str):
        """Generate HTML file from template"""
        try:
            template = self.env.get_template('dashboard.html')
            
            # Prepare data for template
            data_points = data.get('data_points', [])
            stats = DataManager._get_statistics_static(data_points)
            
            html_content = template.render(
                data_points=json.dumps(data_points),
                statistics=stats,
                last_update=data.get('last_update', 'Never'),
                generation_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            
            with open(output_file, 'w') as f:
                f.write(html_content)
            
            logger.info(f"Generated HTML dashboard: {output_file}")
        except Exception as e:
            logger.error(f"Error generating HTML: {e}")
            raise


# Static method for statistics (for use in HTMLGenerator)
def _get_statistics_static(data_points: List[Dict]) -> Dict[str, float]:
    """Calculate statistics from data points"""
    if not data_points:
        return {
            'current': 0,
            'average': 0,
            'min': 0,
            'max': 0,
            'total_kwh': 0
        }
    
    values = [dp['value'] for dp in data_points]
    interval_hours = 10 / 60
    total_kwh = sum(values) * interval_hours / 1000
    
    return {
        'current': round(values[-1], 2),
        'average': round(sum(values) / len(values), 2),
        'min': round(min(values), 2),
        'max': round(max(values), 2),
        'total_kwh': round(total_kwh, 2)
    }

DataManager._get_statistics_static = staticmethod(_get_statistics_static)


def main():
    """Main collection routine"""
    try:
        # Load configuration
        config = get_config()
        logger.info("Starting data collection")
        
        # Check maintenance mode
        maintenance = MaintenanceMode(config.state_file)
        if maintenance.is_enabled():
            logger.info("Maintenance mode enabled, skipping collection")
            return 0
        
        # Initialize components
        ha_client = HomeAssistantClient(
            config.ha_url,
            config.ha_token,
            config.ha_entity_id
        )
        
        data_manager = DataManager(
            config.data_file,
            config.retention_days
        )
        
        # Fetch current state
        state = ha_client.get_current_state()
        timestamp = state['last_updated']
        value = float(state['state'])
        unit = state['attributes'].get('unit_of_measurement', 'W')
        
        logger.info(f"Fetched current state: {value}{unit}")
        
        # Add data point
        data = data_manager.add_data_point(timestamp, value, unit)
        
        # Generate HTML
        html_gen = HTMLGenerator(
            os.path.join(os.path.dirname(__file__), 'templates')
        )
        html_gen.generate(
            data,
            os.path.join(config.web_root, 'index.html')
        )
        
        logger.info("Collection completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Collection failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
