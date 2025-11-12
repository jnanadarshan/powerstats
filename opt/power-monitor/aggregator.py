#!/usr/bin/env python3
"""
Data Aggregator for Power Monitor
Handles aggregation of daily data into weekly, monthly, and yearly JSON files.
Runs at scheduled times:
- 12:02 AM: Aggregate last 24h into weekly.json (rolling 7 days)
- 12:05 AM: Aggregate last 24h into monthly.json (rolling 30 days)
- 12:15 AM: Aggregate last 24h into yearly.json (rolling 365 days)
"""
import json
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('aggregator')


class DataAggregator:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.daily_file = self.data_dir / 'daily.json'
        self.weekly_file = self.data_dir / 'weekly.json'
        self.monthly_file = self.data_dir / 'monthly.json'
        self.yearly_file = self.data_dir / 'yearly.json'
    
    def load_json(self, filepath: Path) -> Dict[str, Any]:
        """Load JSON file or return empty structure."""
        if not filepath.exists():
            return {'data_points': [], 'last_update': None}
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {filepath}: {e}")
            return {'data_points': [], 'last_update': None}
    
    def save_json(self, filepath: Path, data: Dict[str, Any]):
        """Save JSON file atomically."""
        temp_file = filepath.with_suffix('.tmp')
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            temp_file.replace(filepath)
            logger.info(f"Saved {filepath} with {len(data.get('data_points', []))} points")
        except Exception as e:
            logger.error(f"Error saving {filepath}: {e}")
            if temp_file.exists():
                temp_file.unlink()
    
    def aggregate_to_hourly(self, data_points: List[Dict]) -> List[Dict]:
        """Aggregate 10-minute data points into hourly averages."""
        if not data_points:
            return []
        
        hourly_map = {}
        for point in data_points:
            # Round timestamp to hour
            dt = datetime.fromisoformat(point['timestamp'].replace('Z', '+00:00'))
            hour_key = dt.replace(minute=0, second=0, microsecond=0).isoformat().replace('+00:00', 'Z')
            
            if hour_key not in hourly_map:
                hourly_map[hour_key] = {'values': [], 'timestamp': hour_key}
            
            hourly_map[hour_key]['values'].append(point['value'])
        
        # Calculate hourly averages
        hourly_points = []
        for hour_key in sorted(hourly_map.keys()):
            values = hourly_map[hour_key]['values']
            hourly_points.append({
                'timestamp': hour_key,
                'value': round(sum(values) / len(values), 2),
                'unit': 'W'
            })
        
        return hourly_points
    
    def aggregate_to_daily(self, data_points: List[Dict]) -> List[Dict]:
        """Aggregate data points into daily averages."""
        if not data_points:
            return []
        
        daily_map = {}
        for point in data_points:
            # Round timestamp to day
            dt = datetime.fromisoformat(point['timestamp'].replace('Z', '+00:00'))
            day_key = dt.replace(hour=0, minute=0, second=0, microsecond=0).isoformat().replace('+00:00', 'Z')
            
            if day_key not in daily_map:
                daily_map[day_key] = {'values': [], 'timestamp': day_key}
            
            daily_map[day_key]['values'].append(point['value'])
        
        # Calculate daily averages
        daily_points = []
        for day_key in sorted(daily_map.keys()):
            values = daily_map[day_key]['values']
            daily_points.append({
                'timestamp': day_key,
                'value': round(sum(values) / len(values), 2),
                'unit': 'W'
            })
        
        return daily_points
    
    def filter_last_n_days(self, data_points: List[Dict], days: int) -> List[Dict]:
        """Keep only data points from the last N days."""
        if not data_points:
            return []
        
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=days)
        
        filtered = [
            point for point in data_points
            if datetime.fromisoformat(point['timestamp'].replace('Z', '+00:00')) >= cutoff
        ]
        
        return filtered
    
    def aggregate_weekly(self):
        """
        Aggregate yesterday's daily data into weekly.json (rolling 7 days).
        Called at 12:02 AM daily.
        """
        logger.info("Starting weekly aggregation...")
        
        # Load yesterday's daily data
        daily_data = self.load_json(self.daily_file)
        if not daily_data['data_points']:
            logger.warning("No daily data to aggregate")
            return
        
        # Load existing weekly data
        weekly_data = self.load_json(self.weekly_file)
        
        # Aggregate daily data to hourly for the week view
        new_hourly = self.aggregate_to_hourly(daily_data['data_points'])
        
        # Merge with existing weekly data
        all_points = weekly_data['data_points'] + new_hourly
        
        # Keep only last 7 days
        filtered_points = self.filter_last_n_days(all_points, 7)
        
        # Save weekly data
        weekly_data['data_points'] = filtered_points
        weekly_data['last_update'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        self.save_json(self.weekly_file, weekly_data)
        
        logger.info(f"Weekly aggregation complete: {len(filtered_points)} hourly points")
    
    def aggregate_monthly(self):
        """
        Aggregate yesterday's daily data into monthly.json (rolling 30 days).
        Called at 12:05 AM daily.
        """
        logger.info("Starting monthly aggregation...")
        
        # Load yesterday's daily data
        daily_data = self.load_json(self.daily_file)
        if not daily_data['data_points']:
            logger.warning("No daily data to aggregate")
            return
        
        # Load existing monthly data
        monthly_data = self.load_json(self.monthly_file)
        
        # Aggregate yesterday's data to a single daily average
        yesterday_avg = self.aggregate_to_daily(daily_data['data_points'])
        
        # Merge with existing monthly data
        all_points = monthly_data['data_points'] + yesterday_avg
        
        # Keep only last 30 days
        filtered_points = self.filter_last_n_days(all_points, 30)
        
        # Save monthly data
        monthly_data['data_points'] = filtered_points
        monthly_data['last_update'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        self.save_json(self.monthly_file, monthly_data)
        
        logger.info(f"Monthly aggregation complete: {len(filtered_points)} daily points")
    
    def aggregate_yearly(self):
        """
        Aggregate yesterday's daily data into yearly.json (rolling 365 days).
        Called at 12:15 AM daily.
        """
        logger.info("Starting yearly aggregation...")
        
        # Load yesterday's daily data
        daily_data = self.load_json(self.daily_file)
        if not daily_data['data_points']:
            logger.warning("No daily data to aggregate")
            return
        
        # Load existing yearly data
        yearly_data = self.load_json(self.yearly_file)
        
        # Aggregate yesterday's data to a single daily average
        yesterday_avg = self.aggregate_to_daily(daily_data['data_points'])
        
        # Merge with existing yearly data
        all_points = yearly_data['data_points'] + yesterday_avg
        
        # Keep only last 365 days
        filtered_points = self.filter_last_n_days(all_points, 365)
        
        # Save yearly data
        yearly_data['data_points'] = filtered_points
        yearly_data['last_update'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        self.save_json(self.yearly_file, yearly_data)
        
        logger.info(f"Yearly aggregation complete: {len(filtered_points)} daily points")


def main():
    """CLI entry point for manual aggregation."""
    import sys
    
    # Get data directory from args or use default
    if len(sys.argv) > 1:
        data_dir = Path(sys.argv[1])
    else:
        data_dir = Path(__file__).resolve().parent.parent.parent / 'var' / 'www' / 'html'
    
    aggregator = DataAggregator(data_dir)
    
    # Run all aggregations
    logger.info("Running manual aggregation for all periods...")
    aggregator.aggregate_weekly()
    aggregator.aggregate_monthly()
    aggregator.aggregate_yearly()
    logger.info("All aggregations complete!")


if __name__ == '__main__':
    main()
