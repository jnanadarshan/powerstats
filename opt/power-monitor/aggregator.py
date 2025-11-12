#!/usr/bin/env python3
"""
Data Aggregator for Power Monitoring System
Processes daily data and updates weekly, monthly, and yearly aggregates.
This script is intended to be run once a day, after midnight.
"""

import json
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

# Since this script is in the same directory as config_manager, we can import it directly.
from config_manager import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/power-monitor-aggregator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('aggregator')

def calculate_daily_summary(daily_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculates the summary of a day's data points."""
    if not daily_data:
        return None

    # Initialize a dictionary to hold lists of values for each metric
    summary_metrics = {
        'power': [], 'voltage': [], 'solar': [], 
        'power_factor': [], 'daily_energy': []
    }
    
    # Use the timestamp from the last record of the day, but set to midnight for consistency
    last_timestamp_str = daily_data[-1]['timestamp']
    summary_date = datetime.fromisoformat(last_timestamp_str).replace(hour=0, minute=0, second=0, microsecond=0)

    for point in daily_data:
        for key in summary_metrics.keys():
            if key in point and isinstance(point[key], (int, float)):
                summary_metrics[key].append(point[key])

    # Calculate final summary values
    final_summary = {'timestamp': summary_date.isoformat()}
    for key, values in summary_metrics.items():
        if not values:
            final_summary[key] = 0
            continue
        
        if key == 'daily_energy':
            # For cumulative energy, we take the maximum value of the day.
            final_summary[key] = round(max(values), 2)
        else:
            # For other metrics, we calculate the average.
            final_summary[key] = round(sum(values) / len(values), 2)
            
    return final_summary

def update_aggregate_file(file_path: str, summary_data: Dict[str, Any], max_days: int):
    """Loads an aggregate file, adds new data, trims it to max_days, and saves it."""
    try:
        # Check if file exists and is not empty
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            with open(file_path, 'r') as f:
                aggregate_data = json.load(f)
        else:
            aggregate_data = []
    except (json.JSONDecodeError, FileNotFoundError):
        logger.warning(f"Could not read or parse {file_path}. Starting with an empty list.")
        aggregate_data = []

    # Add the new daily summary
    aggregate_data.append(summary_data)

    # Sort by timestamp to ensure chronological order
    aggregate_data.sort(key=lambda x: x['timestamp'])
    
    # Remove duplicates for the same day, keeping the latest entry
    unique_data = []
    seen_dates = set()
    # Iterate backwards to prioritize newer entries for a given day
    for point in reversed(aggregate_data):
        date = point['timestamp'][:10] # Extract YYYY-MM-DD
        if date not in seen_dates:
            unique_data.append(point)
            seen_dates.add(date)
    unique_data.reverse() # Restore chronological order

    # Trim the data to the specified maximum number of days
    if len(unique_data) > max_days:
        unique_data = unique_data[-max_days:]

    # Atomically write the updated data back to the file
    temp_file = file_path + '.tmp'
    with open(temp_file, 'w') as f:
        json.dump(unique_data, f, indent=4)
    os.replace(temp_file, file_path)
    
    logger.info(f"Updated {file_path} with data for {summary_data['timestamp'][:10]}. Total points: {len(unique_data)}.")

def main():
    """Main aggregation routine."""
    try:
        config = get_config()
        web_root = Path(config.web_root)
        
        daily_file = web_root / 'daily.json'
        weekly_file = web_root / 'weekly.json'
        monthly_file = web_root / 'monthly.json'
        yearly_file = web_root / 'yearly.json'

        logger.info("Starting daily aggregation process.")

        # 1. Load the detailed daily data
        if not daily_file.exists() or daily_file.stat().st_size == 0:
            logger.warning("daily.json is empty or does not exist. Nothing to aggregate.")
            return 0
            
        with open(daily_file, 'r') as f:
            daily_data = json.load(f)

        # 2. Identify and process data for the previous day
        yesterday = datetime.now() - timedelta(days=1)
        yesterday_str = yesterday.strftime('%Y-%m-%d')
        
        data_for_yesterday = [p for p in daily_data if p['timestamp'].startswith(yesterday_str)]
        
        if not data_for_yesterday:
            logger.info(f"No data found for yesterday ({yesterday_str}) in daily.json. This can happen if the collector hasn't run for a full day yet. Skipping aggregation.")
            return 0

        # 3. Calculate the summary for the previous day
        daily_summary = calculate_daily_summary(data_for_yesterday)
        
        if not daily_summary:
            logger.warning("Failed to generate a daily summary from yesterday's data. Skipping all updates.")
            return 1

        logger.info(f"Generated summary for {yesterday_str}: {daily_summary}")

        # 4. Update the aggregate files with the new daily summary
        update_aggregate_file(str(weekly_file), daily_summary, 7)
        update_aggregate_file(str(monthly_file), daily_summary, 30)
        update_aggregate_file(str(yearly_file), daily_summary, 365)

        logger.info("Aggregation process completed successfully.")
        return 0

    except Exception as e:
        logger.error(f"An unexpected error occurred during aggregation: {e}", exc_info=True)
        return 1

if __name__ == '__main__':
    import sys
    sys.exit(main())
