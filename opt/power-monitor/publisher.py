#!/usr/bin/env python3
"""
GitHub Publisher for Power Monitoring System
Publishes generated HTML and data to GitHub Pages using GitHub API
"""

import json
import os
import sys
import logging
import base64
from typing import Optional, Dict, Any
import requests

from config_manager import get_config
from collector import MaintenanceMode


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/power-monitor-publisher.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('publisher')


class GitHubPublisher:
    """Handles publishing to GitHub Pages via GitHub API"""
    
    def __init__(self, token: str, owner: str, repo: str, branch: str = 'main'):
        self.token = token
        self.owner = owner
        self.repo = repo
        self.branch = branch
        self.base_url = 'https://api.github.com'
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'PowerStats-Monitor/1.0'
        })
    
    def _get_file_sha(self, file_path: str) -> Optional[str]:
        """Get the SHA of an existing file in the repository"""
        try:
            url = f'{self.base_url}/repos/{self.owner}/{self.repo}/contents/{file_path}'
            params = {'ref': self.branch}
            response = self.session.get(url, params=params)
            
            if response.status_code == 200:
                return response.json()['sha']
            elif response.status_code == 404:
                return None
            else:
                response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting file SHA for {file_path}: {e}")
            return None
    
    def _create_or_update_file(
        self,
        file_path: str,
        content: str,
        commit_message: str
    ) -> bool:
        """Create or update a file in the repository"""
        try:
            url = f'{self.base_url}/repos/{self.owner}/{self.repo}/contents/{file_path}'
            
            # Encode content to base64
            content_bytes = content.encode('utf-8')
            content_base64 = base64.b64encode(content_bytes).decode('utf-8')
            
            # Prepare payload
            payload = {
                'message': commit_message,
                'content': content_base64,
                'branch': self.branch
            }
            
            # Check if file exists and get SHA
            sha = self._get_file_sha(file_path)
            if sha:
                payload['sha'] = sha
                logger.info(f"Updating existing file: {file_path}")
            else:
                logger.info(f"Creating new file: {file_path}")
            
            # Make request
            response = self.session.put(url, json=payload)
            response.raise_for_status()
            
            logger.info(f"Successfully published {file_path}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error publishing {file_path}: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            return False
    
    def publish_file(self, local_path: str, remote_path: str, commit_message: str) -> bool:
        """Read a local file and publish it to GitHub"""
        try:
            with open(local_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return self._create_or_update_file(remote_path, content, commit_message)
            
        except Exception as e:
            logger.error(f"Error reading local file {local_path}: {e}")
            return False
    
    def publish_dashboard(self, web_root: str) -> bool:
        """Publish dashboard files to GitHub Pages (multi-JSON architecture)"""
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # New multi-JSON architecture: publish HTML and all 4 JSON files
        files_to_publish = [
            ('index.html', 'index.html', f'Update dashboard - {timestamp}'),
            ('daily.json', 'daily.json', f'Update daily data - {timestamp}'),
            ('weekly.json', 'weekly.json', f'Update weekly data - {timestamp}'),
            ('monthly.json', 'monthly.json', f'Update monthly data - {timestamp}'),
            ('yearly.json', 'yearly.json', f'Update yearly data - {timestamp}')
        ]
        
        success = True
        for local_name, remote_name, message in files_to_publish:
            local_path = os.path.join(web_root, local_name)
            
            if not os.path.exists(local_path):
                logger.warning(f"File not found: {local_path}, skipping")
                continue
            
            if not self.publish_file(local_path, remote_name, message):
                success = False
        
        return success
    
    def verify_repository(self) -> bool:
        """Verify that the repository exists and is accessible"""
        try:
            url = f'{self.base_url}/repos/{self.owner}/{self.repo}'
            response = self.session.get(url)
            response.raise_for_status()
            
            repo_info = response.json()
            logger.info(f"Repository verified: {repo_info['full_name']}")
            
            # Check if GitHub Pages is enabled
            if repo_info.get('has_pages'):
                logger.info(f"GitHub Pages URL: https://{self.owner}.github.io/{self.repo}/")
            else:
                logger.warning("GitHub Pages may not be enabled for this repository")
            
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error verifying repository: {e}")
            return False


def main():
    """Main publishing routine"""
    try:
        # Load configuration
        config = get_config()
        logger.info("Starting GitHub publishing")
        
        # Check maintenance mode
        maintenance = MaintenanceMode(config.state_file)
        if maintenance.is_enabled():
            logger.info("Maintenance mode enabled, skipping publish")
            return 0
        
        # Initialize publisher
        publisher = GitHubPublisher(
            config.gh_token,
            config.gh_repo_owner,
            config.gh_repo_name,
            config.gh_branch
        )
        
        # Verify repository access
        if not publisher.verify_repository():
            logger.error("Repository verification failed")
            return 1
        
        # Publish dashboard
        if publisher.publish_dashboard(config.web_root):
            logger.info("Publishing completed successfully")
            return 0
        else:
            logger.error("Publishing failed")
            return 1
            
    except Exception as e:
        logger.error(f"Publishing failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
