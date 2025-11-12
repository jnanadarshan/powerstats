#!/usr/bin/env python3
"""
GitHub Sync Module for Power Monitor
Syncs monthly.json and yearly.json to/from GitHub repository.
Local system only keeps daily.json and weekly.json.
"""
import json
import os
import base64
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import logging

try:
    import requests
except ImportError:
    print("ERROR: requests library not installed. Run: pip install requests")
    exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('github_sync')


class GitHubSync:
    def __init__(self, config_path: Path):
        """Initialize GitHub sync with config from config.json."""
        self.config = self._load_config(config_path)
        
        # GitHub API settings
        self.token = self.config.get('github', {}).get('token')
        self.repo = self.config.get('github', {}).get('repo')  # format: "owner/repo"
        self.branch = self.config.get('github', {}).get('branch', 'main')
        
        if not self.token or not self.repo:
            logger.warning("GitHub token or repo not configured. Sync disabled.")
            self.enabled = False
        else:
            self.enabled = True
            self.api_base = f"https://api.github.com/repos/{self.repo}/contents"
            self.headers = {
                'Authorization': f'token {self.token}',
                'Accept': 'application/vnd.github.v3+json'
            }
    
    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """Load configuration from config.json."""
        if not config_path.exists():
            logger.error(f"Config file not found: {config_path}")
            return {}
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
    
    def fetch_file(self, remote_path: str, local_path: Path) -> bool:
        """
        Fetch a file from GitHub and save it locally.
        Returns True if successful, False otherwise.
        """
        if not self.enabled:
            logger.warning("GitHub sync is disabled")
            return False
        
        url = f"{self.api_base}/{remote_path}"
        params = {'ref': self.branch}
        
        try:
            logger.info(f"Fetching {remote_path} from GitHub...")
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 404:
                logger.info(f"File {remote_path} not found on GitHub (new repo?). Will be created on first push.")
                return False
            
            response.raise_for_status()
            
            # Decode base64 content
            content_base64 = response.json()['content']
            content = base64.b64decode(content_base64).decode('utf-8')
            
            # Save locally
            local_path.parent.mkdir(parents=True, exist_ok=True)
            with open(local_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Successfully fetched {remote_path} to {local_path}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {remote_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error fetching {remote_path}: {e}")
            return False
    
    def push_file(self, local_path: Path, remote_path: str, commit_message: str) -> bool:
        """
        Push a local file to GitHub.
        Returns True if successful, False otherwise.
        """
        if not self.enabled:
            logger.warning("GitHub sync is disabled")
            return False
        
        if not local_path.exists():
            logger.error(f"Local file not found: {local_path}")
            return False
        
        url = f"{self.api_base}/{remote_path}"
        
        try:
            # Read local file
            with open(local_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Encode to base64
            content_base64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            
            # Check if file exists on GitHub to get SHA
            logger.info(f"Pushing {local_path} to GitHub as {remote_path}...")
            get_response = requests.get(
                url,
                headers=self.headers,
                params={'ref': self.branch},
                timeout=30
            )
            
            payload = {
                'message': commit_message,
                'content': content_base64,
                'branch': self.branch
            }
            
            # If file exists, include SHA for update
            if get_response.status_code == 200:
                sha = get_response.json()['sha']
                payload['sha'] = sha
                logger.info(f"Updating existing file (SHA: {sha[:8]}...)")
            else:
                logger.info("Creating new file on GitHub")
            
            # Push to GitHub
            put_response = requests.put(url, headers=self.headers, json=payload, timeout=30)
            put_response.raise_for_status()
            
            logger.info(f"Successfully pushed {remote_path} to GitHub")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error pushing {remote_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error pushing {remote_path}: {e}")
            return False
    
    def sync_monthly_to_github(self, data_dir: Path) -> bool:
        """Fetch monthly.json from GitHub, merge, and push back."""
        local_monthly = data_dir / 'monthly.json'
        remote_path = 'data/monthly.json'
        
        logger.info("Syncing monthly.json to GitHub...")
        
        # Push to GitHub
        commit_msg = f"Update monthly.json - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
        return self.push_file(local_monthly, remote_path, commit_msg)
    
    def sync_yearly_to_github(self, data_dir: Path) -> bool:
        """Fetch yearly.json from GitHub, merge, and push back."""
        local_yearly = data_dir / 'yearly.json'
        remote_path = 'data/yearly.json'
        
        logger.info("Syncing yearly.json to GitHub...")
        
        # Push to GitHub
        commit_msg = f"Update yearly.json - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
        return self.push_file(local_yearly, remote_path, commit_msg)
    
    def fetch_monthly_from_github(self, data_dir: Path) -> bool:
        """Fetch monthly.json from GitHub on startup."""
        local_monthly = data_dir / 'monthly.json'
        remote_path = 'data/monthly.json'
        
        logger.info("Fetching monthly.json from GitHub...")
        return self.fetch_file(remote_path, local_monthly)
    
    def fetch_yearly_from_github(self, data_dir: Path) -> bool:
        """Fetch yearly.json from GitHub on startup."""
        local_yearly = data_dir / 'yearly.json'
        remote_path = 'data/yearly.json'
        
        logger.info("Fetching yearly.json from GitHub...")
        return self.fetch_file(remote_path, local_yearly)


def main():
    """CLI entry point for manual GitHub sync."""
    import sys
    
    # Get paths
    repo_root = Path(__file__).resolve().parent.parent.parent
    config_path = repo_root / 'opt' / 'power-monitor' / 'config.json'
    
    if len(sys.argv) > 1:
        data_dir = Path(sys.argv[1])
    else:
        data_dir = repo_root / 'var' / 'www' / 'html'
    
    sync = GitHubSync(config_path)
    
    if not sync.enabled:
        logger.error("GitHub sync not enabled. Check config.json for github.token and github.repo")
        sys.exit(1)
    
    # Sync operation
    operation = sys.argv[2] if len(sys.argv) > 2 else 'push'
    
    if operation == 'fetch':
        logger.info("Fetching from GitHub...")
        sync.fetch_monthly_from_github(data_dir)
        sync.fetch_yearly_from_github(data_dir)
    elif operation == 'push':
        logger.info("Pushing to GitHub...")
        sync.sync_monthly_to_github(data_dir)
        sync.sync_yearly_to_github(data_dir)
    else:
        logger.error(f"Unknown operation: {operation}. Use 'fetch' or 'push'")
        sys.exit(1)


if __name__ == '__main__':
    main()
