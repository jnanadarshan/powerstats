#!/usr/bin/env python3
"""
Configuration Manager for Power Monitoring System
Handles loading, validation, and access to configuration settings
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigManager:
    """Manages configuration loading and validation"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager
        
        Args:
            config_path: Path to config file. If None, searches default locations
        """
        self.config_path = config_path or self._find_config()
        self.config = self._load_config()
        self._validate_config()
    
    def _find_config(self) -> str:
        """Search for config file in standard locations"""
        search_paths = [
            '/opt/power-monitor/config.json',
            './config.json',
            './opt/power-monitor/config.json',
            os.path.join(os.path.dirname(__file__), 'config.json')
        ]
        
        for path in search_paths:
            if os.path.exists(path):
                return path
        
        raise FileNotFoundError(
            f"Config file not found. Searched: {', '.join(search_paths)}\n"
            "Create config.json based on config.example.json"
        )
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file {self.config_path}: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to load config from {self.config_path}: {e}")
    
    def _validate_config(self):
        """Validate required configuration fields"""
        required_sections = ['homeassistant', 'github', 'data', 'paths']
        
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Missing required config section: {section}")
        
        # Validate Home Assistant config
        ha_required = ['url', 'token']
        for field in ha_required:
            if field not in self.config['homeassistant']:
                raise ValueError(f"Missing homeassistant.{field} in config")
        
        # Validate entities (either old single entity_id or new entities dict)
        if 'entities' not in self.config['homeassistant'] and 'entity_id' not in self.config['homeassistant']:
            raise ValueError("Missing homeassistant.entities or homeassistant.entity_id in config")
        
        # Validate GitHub config (support both old and new formats)
        if 'token' not in self.config['github']:
            raise ValueError("Missing github.token in config")
        
        # Support both old format (repo_owner/repo_name) and new format (repo)
        has_old_format = 'repo_owner' in self.config['github'] and 'repo_name' in self.config['github']
        has_new_format = 'repo' in self.config['github']
        
        if not has_old_format and not has_new_format:
            raise ValueError("Missing github.repo or github.repo_owner/repo_name in config")
        
        # Validate paths (data_file is now optional, data_dir can use web_root as fallback)
        path_required = ['state_file', 'web_root']
        for field in path_required:
            if field not in self.config['paths']:
                raise ValueError(f"Missing paths.{field} in config")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        
        Args:
            key: Configuration key in dot notation (e.g., 'homeassistant.url')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    @property
    def ha_url(self) -> str:
        """Home Assistant URL"""
        return self.config['homeassistant']['url']
    
    @property
    def ha_token(self) -> str:
        """Home Assistant token"""
        return self.config['homeassistant']['token']
    
    @property
    def ha_entity_id(self) -> str:
        """Home Assistant entity ID (legacy - use ha_entities for new multi-entity support)"""
        # Fallback to old single entity_id or default to power entity
        return self.config['homeassistant'].get('entity_id', 
               self.config['homeassistant'].get('entities', {}).get('power', ''))
    
    @property
    def ha_entities(self) -> Dict[str, str]:
        """All Home Assistant entity IDs"""
        return self.config['homeassistant'].get('entities', {})
    
    @property
    def ha_voltage_entity(self) -> str:
        """Voltage sensor entity ID"""
        return self.config['homeassistant'].get('entities', {}).get('voltage', '')
    
    @property
    def ha_daily_energy_entity(self) -> str:
        """Daily energy consumption entity ID"""
        return self.config['homeassistant'].get('entities', {}).get('daily_energy', '')
    
    @property
    def ha_power_entity(self) -> str:
        """Live power usage entity ID"""
        return self.config['homeassistant'].get('entities', {}).get('power', '')
    
    @property
    def ha_solar_entity(self) -> str:
        """Solar generation entity ID"""
        return self.config['homeassistant'].get('entities', {}).get('solar', '')
    
    @property
    def ha_power_factor_entity(self) -> str:
        """Power factor entity ID"""
        return self.config['homeassistant'].get('entities', {}).get('power_factor', '')
    
    @property
    def gh_token(self) -> str:
        """GitHub token"""
        return self.config['github']['token']
    
    @property
    def gh_repo_owner(self) -> str:
        """GitHub repository owner"""
        # Support both old format and new format
        if 'repo_owner' in self.config['github']:
            return self.config['github']['repo_owner']
        elif 'repo' in self.config['github']:
            return self.config['github']['repo'].split('/')[0]
        return ''
    
    @property
    def gh_repo_name(self) -> str:
        """GitHub repository name"""
        # Support both old format and new format
        if 'repo_name' in self.config['github']:
            return self.config['github']['repo_name']
        elif 'repo' in self.config['github']:
            return self.config['github']['repo'].split('/')[1]
        return ''
    
    @property
    def gh_branch(self) -> str:
        """GitHub branch"""
        return self.config['github']['branch']
    
    @property
    def retention_days(self) -> int:
        """Data retention in days"""
        return self.config['data'].get('retention_days', 7)
    
    @property
    def collection_interval(self) -> int:
        """Collection interval in minutes (legacy property - prefer local_collection_interval)"""
        return self.config['data'].get('collection_interval_minutes', 10)
    
    @property
    def local_collection_interval(self) -> int:
        """Local collection interval in minutes (device-side data collection frequency)"""
        return self.config['data'].get('local_collection_interval_minutes', 
                                       self.config['data'].get('collection_interval_minutes', 10))
    
    @property
    def publish_interval(self) -> int:
        """Publish interval in minutes (GitHub publishing frequency)"""
        return self.config['data'].get('publish_interval_minutes', 60)
    
    @property
    def state_file(self) -> str:
        """Path to state file"""
        return self.config['paths']['state_file']
    
    @property
    def web_root(self) -> str:
        """Web root directory"""
        return self.config['paths']['web_root']
    
    @property
    def data_file(self) -> str:
        """Path to data JSON file (legacy - use data_dir for new multi-JSON architecture)"""
        return self.config['paths'].get('data_file', '')
    
    @property
    def data_dir(self) -> str:
        """Path to data directory containing daily/weekly/monthly/yearly JSON files"""
        return self.config['paths'].get('data_dir', self.config['paths'].get('web_root', ''))
    
    @property
    def gh_repo(self) -> str:
        """GitHub repository in owner/repo format"""
        return self.config['github'].get('repo', f"{self.gh_repo_owner}/{self.gh_repo_name}")
    
    def reload(self):
        """Reload configuration from file"""
        self.config = self._load_config()
        self._validate_config()


# Convenience function for quick access
_config_instance = None

def get_config(config_path: Optional[str] = None) -> ConfigManager:
    """Get or create singleton configuration instance"""
    global _config_instance
    if _config_instance is None or config_path is not None:
        _config_instance = ConfigManager(config_path)
    return _config_instance


if __name__ == '__main__':
    # Test configuration loading
    try:
        config = ConfigManager()
        print(f"✓ Configuration loaded from: {config.config_path}")
        print(f"✓ Home Assistant: {config.ha_url}")
        print(f"✓ GitHub: {config.gh_repo_owner}/{config.gh_repo_name}")
        print(f"✓ Data retention: {config.retention_days} days")
        print(f"✓ Collection interval: {config.collection_interval} minutes")
    except Exception as e:
        print(f"✗ Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
