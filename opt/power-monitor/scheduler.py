#!/usr/bin/env python3
"""
Scheduler for Power Monitor Nightly Jobs
Runs aggregation and GitHub sync tasks at scheduled times:
- 12:02 AM: Aggregate to weekly.json
- 12:05 AM: Aggregate to monthly.json + sync to GitHub
- 12:15 AM: Aggregate to yearly.json + sync to GitHub
"""
import sys
import time
import logging
from pathlib import Path
from datetime import datetime, time as dt_time
from typing import Callable

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from aggregator import DataAggregator
from github_sync import GitHubSync

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('scheduler')


class NightlyScheduler:
    def __init__(self, data_dir: Path, config_path: Path):
        self.data_dir = Path(data_dir)
        self.config_path = Path(config_path)
        
        self.aggregator = DataAggregator(self.data_dir)
        self.github_sync = GitHubSync(self.config_path)
        
        # Schedule times (hour, minute)
        self.weekly_time = (0, 2)    # 12:02 AM
        self.monthly_time = (0, 5)   # 12:05 AM
        self.yearly_time = (0, 15)   # 12:15 AM
        
        # Track last run dates to avoid double-running
        self.last_weekly_run = None
        self.last_monthly_run = None
        self.last_yearly_run = None
    
    def should_run(self, target_time: tuple, last_run_date: str) -> bool:
        """Check if task should run now."""
        now = datetime.now()
        target_hour, target_minute = target_time
        
        # Check if we're at or past the target time
        current_time = now.time()
        target = dt_time(target_hour, target_minute)
        
        # Get today's date string
        today = now.date().isoformat()
        
        # Run if:
        # 1. Current time is past target time
        # 2. Haven't run today yet
        if current_time >= target and last_run_date != today:
            return True
        
        return False
    
    def run_weekly_task(self):
        """Run weekly aggregation at 12:02 AM."""
        logger.info("=" * 60)
        logger.info("Running weekly aggregation task...")
        try:
            self.aggregator.aggregate_weekly()
            self.last_weekly_run = datetime.now().date().isoformat()
            logger.info("Weekly task completed successfully")
        except Exception as e:
            logger.error(f"Weekly task failed: {e}", exc_info=True)
        logger.info("=" * 60)
    
    def run_monthly_task(self):
        """Run monthly aggregation and GitHub sync at 12:05 AM."""
        logger.info("=" * 60)
        logger.info("Running monthly aggregation and sync task...")
        try:
            self.aggregator.aggregate_monthly()
            
            if self.github_sync.enabled:
                self.github_sync.sync_monthly_to_github(self.data_dir)
            else:
                logger.warning("GitHub sync disabled, skipping monthly sync")
            
            self.last_monthly_run = datetime.now().date().isoformat()
            logger.info("Monthly task completed successfully")
        except Exception as e:
            logger.error(f"Monthly task failed: {e}", exc_info=True)
        logger.info("=" * 60)
    
    def run_yearly_task(self):
        """Run yearly aggregation and GitHub sync at 12:15 AM."""
        logger.info("=" * 60)
        logger.info("Running yearly aggregation and sync task...")
        try:
            self.aggregator.aggregate_yearly()
            
            if self.github_sync.enabled:
                self.github_sync.sync_yearly_to_github(self.data_dir)
            else:
                logger.warning("GitHub sync disabled, skipping yearly sync")
            
            self.last_yearly_run = datetime.now().date().isoformat()
            logger.info("Yearly task completed successfully")
        except Exception as e:
            logger.error(f"Yearly task failed: {e}", exc_info=True)
        logger.info("=" * 60)
    
    def run_once(self):
        """Run all tasks immediately (for testing)."""
        logger.info("Running all tasks immediately...")
        self.run_weekly_task()
        self.run_monthly_task()
        self.run_yearly_task()
    
    def run_daemon(self):
        """Run scheduler daemon - checks every minute for tasks to run."""
        logger.info("Starting nightly scheduler daemon...")
        logger.info(f"Data directory: {self.data_dir}")
        logger.info(f"Config: {self.config_path}")
        logger.info(f"Schedule:")
        logger.info(f"  - Weekly:  {self.weekly_time[0]:02d}:{self.weekly_time[1]:02d}")
        logger.info(f"  - Monthly: {self.monthly_time[0]:02d}:{self.monthly_time[1]:02d}")
        logger.info(f"  - Yearly:  {self.yearly_time[0]:02d}:{self.yearly_time[1]:02d}")
        logger.info("Scheduler is running. Press Ctrl+C to stop.")
        
        try:
            while True:
                # Check weekly task
                if self.should_run(self.weekly_time, self.last_weekly_run):
                    self.run_weekly_task()
                
                # Check monthly task
                if self.should_run(self.monthly_time, self.last_monthly_run):
                    self.run_monthly_task()
                
                # Check yearly task
                if self.should_run(self.yearly_time, self.last_yearly_run):
                    self.run_yearly_task()
                
                # Sleep for 60 seconds before next check
                time.sleep(60)
                
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
        except Exception as e:
            logger.error(f"Scheduler error: {e}", exc_info=True)


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Power Monitor Nightly Scheduler')
    parser.add_argument('--data-dir', type=str, help='Data directory path')
    parser.add_argument('--config', type=str, help='Config file path')
    parser.add_argument('--once', action='store_true', help='Run all tasks once and exit')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    
    args = parser.parse_args()
    
    # Default paths
    repo_root = Path(__file__).resolve().parent.parent.parent
    data_dir = Path(args.data_dir) if args.data_dir else repo_root / 'var' / 'www' / 'html'
    config_path = Path(args.config) if args.config else repo_root / 'opt' / 'power-monitor' / 'config.json'
    
    scheduler = NightlyScheduler(data_dir, config_path)
    
    if args.once:
        scheduler.run_once()
    elif args.daemon:
        scheduler.run_daemon()
    else:
        # Default: run as daemon
        scheduler.run_daemon()


if __name__ == '__main__':
    main()
