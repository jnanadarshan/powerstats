# Weekly Data Restructuring - Complete Refactor

## Overview
The weekly data collection and storage has been restructured to eliminate aggregation and instead maintain granular data with time-based retention.

## Key Changes

### 1. **collector.py** - Direct Weekly Data Writing
- **Before**: Only wrote to `daily.json`
- **After**: Now writes to both `daily.json` and `weekly.json`

**DataManager Class Updates**:
- Added `retention_hours` parameter (default: 24 for daily, 168 for weekly)
- `add_data_point()` now trims based on retention period instead of fixed max_points
- Removes any data point older than `retention_hours`
- File logs include retention period info: `"Updated {file}.  Total points: {count}, retention: {hours}h"`

**Data Flow**:
```python
# Weekly manager configured for 7-day retention (168 hours)
points_per_week = max(1, int(7 * 24 * 60 / interval_min))
weekly_manager = DataManager(
    weekly_data_file,
    max_points=points_per_week,
    retention_hours=168  # 7 days * 24 hours
)
```

**Result**: 
- `weekly.json` = granular data (same format as `daily.json`)
- `daily.json` = last 24 hours at collection interval
- `weekly.json` = last 7 days at collection interval
- Both updated **simultaneously** on every collector run

### 2. **scheduler.py** - Removed Weekly Aggregation
**Changes**:
- Removed `self.weekly_time = (0, 2)` (12:02 AM task)
- Removed `self.last_weekly_run` tracking
- `run_weekly_task()` converted to stub (backwards compatibility)
- Removed weekly task check from `run_daemon()` loop
- Updated `run_once()` to skip weekly task
- Updated schedule logging to reflect new times

**Current Schedule**:
- `12:05 AM` - Monthly aggregation (weekly.json → monthly.json)
- `12:15 AM` - Yearly aggregation (monthly.json → yearly.json)

**Daemon Log Output**:
```
Schedule:
  - Monthly: 00:05 (aggregates weekly.json → monthly.json)
  - Yearly:  00:15 (aggregates monthly.json → yearly.json)
Note: weekly.json is updated directly by collector.py (granular data, 7-day retention)
```

### 3. **aggregator.py** - Monthly/Yearly Aggregation Only
**Changes**:
- Removed weekly aggregation logic
- `update_aggregate_file(str(weekly_file), daily_summary, 7)` removed
- Kept monthly and yearly aggregations intact
- Updated docstring to reflect new behavior

**Flow**:
- Reads `daily.json` (yesterday's granular data)
- Calculates daily summary (averages & max)
- Updates `monthly.json` (30 day summaries)
- Updates `yearly.json` (365 day summaries)

### 4. **publisher.py** - Updated Comments
- Added note: "weekly.json contains granular data (7-day retention), not aggregated summaries"
- Updated commit message: "Update weekly granular data" (instead of "Update weekly data")

## Data Format Comparison

### Before (Aggregated)
```json
// weekly.json - 7 summary records (one per day)
[
  {"timestamp": "2025-11-08T00:00:00", "power": 250.5, "voltage": 238.2, ...},
  {"timestamp": "2025-11-09T00:00:00", "power": 248.3, "voltage": 237.8, ...},
  // ... 5 more daily summaries
]
```

### After (Granular)
```json
// weekly.json - granular records for 7 days (same as daily format)
[
  {"timestamp": "2025-11-08T00:00:00", "power": 250.5, "voltage": 238.2, ...},
  {"timestamp": "2025-11-08T00:10:00", "power": 251.2, "voltage": 238.5, ...},
  {"timestamp": "2025-11-08T00:20:00", "power": 249.8, "voltage": 237.9, ...},
  // ... many more points at collection interval
]
```

## Advantages
1. **Consistency**: All files use same granular format
2. **Real-time Updates**: Weekly data updates immediately with collector runs (not delayed to midnight)
3. **No Aggregation Loss**: Granular data preserves all detail (vs. daily summaries)
4. **Simpler Scheduler**: Only 2 scheduled tasks instead of 3
5. **Flexible Retention**: Easy to adjust retention period for any file
6. **Scale Friendly**: UI can plot 7 days of granular data or create on-the-fly summaries

## Retention Policy
| File | Retention | Format | Updated By | Records |
|------|-----------|--------|-----------|---------|
| daily.json | 24 hours | Granular | collector.py | ~144 (at 10-min interval) |
| weekly.json | 7 days (168h) | Granular | collector.py | ~1008 (at 10-min interval) |
| monthly.json | 30 days | Daily summary | aggregator.py at 12:05 AM | 30 |
| yearly.json | 365 days | Daily summary | aggregator.py at 12:15 AM | 365 |

## Migration Notes
- No data migration needed (collector and scheduler work independently)
- Existing `daily.json` continues as-is
- First `weekly.json` update by collector will start fresh with current data
- Monthly/yearly aggregations will continue seamlessly
- Old aggregated weekly.json on device will be overwritten on first collector run

## Implementation Status
✅ All Python files syntax validated
✅ collector.py: DataManager updated with retention_hours
✅ scheduler.py: Weekly task removed, daemon updated
✅ aggregator.py: Weekly aggregation removed
✅ publisher.py: Comments updated
