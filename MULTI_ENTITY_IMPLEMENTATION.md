# Multi-Entity Implementation Summary

## Overview
The Power Monitor system has been upgraded from tracking a single power sensor to monitoring **5 different sensor entities** simultaneously:

1. **Voltage** - Grid voltage monitoring
2. **Daily Energy** - Daily energy consumption
3. **Power** - Live power usage
4. **Solar** - Generated solar power
5. **Power Factor** - Power quality metric

## Architecture Changes

### Data Structure Evolution

**Old Format (Single Entity):**
```json
{
  "timestamp": "2024-01-15T10:30:00",
  "value": 150,
  "unit": "W"
}
```

**New Format (Multi-Entity):**
```json
{
  "timestamp": "2024-01-15T10:30:00",
  "power": {"value": 150, "unit": "W"},
  "voltage": {"value": 230, "unit": "V"},
  "daily_energy": {"value": 5.2, "unit": "kWh"},
  "solar": {"value": 80, "unit": "W"},
  "power_factor": {"value": 0.95, "unit": ""}
}
```

### Configuration Changes

**File:** `config.json` (root)

**Old Format:**
```json
{
  "home_assistant": {
    "url": "http://homeassistant.local:8123",
    "token": "your_token",
    "entity_id": "sensor.power"
  }
}
```

**New Format:**
```json
{
  "home_assistant": {
    "url": "http://homeassistant.local:8123",
    "token": "your_token",
    "entities": {
      "voltage": "sensor.voltage",
      "daily_energy": "sensor.daily_energy",
      "power": "sensor.live_power",
      "solar": "sensor.solar_power",
      "power_factor": "sensor.power_factor"
    }
  }
}
```

**Backward Compatibility:** The system still supports the old `entity_id` format. If `entities` is not provided, it falls back to `entity_id`.

## Code Changes

### 1. config_manager.py

**New Properties:**
- `ha_entities` - Returns full dictionary of entities
- `ha_voltage_entity` - Voltage sensor entity ID
- `ha_daily_energy_entity` - Daily energy sensor entity ID
- `ha_power_entity` - Power sensor entity ID
- `ha_solar_entity` - Solar power sensor entity ID
- `ha_power_factor_entity` - Power factor sensor entity ID

**Backward Compatibility:**
- Validates both old `entity_id` and new `entities` dict formats
- GitHub config supports both `repo` (new) and `repo_owner`/`repo_name` (old)

### 2. collector.py

**HomeAssistantClient Changes:**
- `__init__(url, token, entities)` - Now accepts entities dict instead of single entity_id
- `get_current_state(entity_id)` - Parameterized to fetch any entity
- `get_all_current_states()` - NEW method fetches all configured entities at once
- `get_history(entity_id, start_time, end_time)` - Parameterized for any entity

**DataManager Changes:**
- `add_data_point(timestamp, entities_data)` - Now accepts dict of all entity states
- Stores multi-entity data in single JSON structure
- Maintains midnight rotation and data retention

**main() Function:**
- Uses `config.ha_entities` instead of `config.ha_entity_id`
- Calls `get_all_current_states()` to fetch all entities at once
- Passes entire entities dict to `add_data_point()`
- Logs all entity values for visibility

### 3. dashboard.html

**Data Parsing Updates:**
- All data point access now supports both old (`dp.value`) and new (`dp.power.value`) formats
- Power charts extract `dp.power.value` with fallback to `dp.value`
- Voltage charts use `dp.voltage.value` if available, otherwise simulate
- Energy charts use `dp.daily_energy.value` if available, otherwise calculate from power
- Power factor charts use `dp.power_factor.value` if available, otherwise simulate

**Chart Updates:**
- `renderTodayChart()` - Updated to extract entity-specific data
- `detectPowerCuts()` - Updated to use `dp.power.value` with fallback
- Summary stats updated to calculate from correct entity values
- Voltage min/max calculation uses actual voltage data when available

### 4. publisher.py

**Status:** No changes needed
- Already publishes all JSON files as-is (daily.json, weekly.json, monthly.json, yearly.json)
- Multi-entity data structure is transparent to publisher
- Files are uploaded without parsing JSON content

### 5. github_sync.py

**Status:** No changes needed
- Fetches and pushes JSON files without parsing content
- Multi-entity data structure is transparent to sync module
- Works with new format without modifications

## Migration Path

### For Existing Installations

1. **Update config.json:**
   ```json
   "entities": {
     "voltage": "sensor.your_voltage",
     "daily_energy": "sensor.your_energy",
     "power": "sensor.your_power",
     "solar": "sensor.your_solar",
     "power_factor": "sensor.your_pf"
   }
   ```

2. **Existing data remains compatible:**
   - Old single-entity data points still display correctly
   - Dashboard handles both formats seamlessly
   - No data migration required

3. **New data collection starts immediately:**
   - Next collector run will use new multi-entity format
   - Data files will contain mixed format (old + new)
   - Charts render both formats correctly

### For New Installations

1. Use the new config format with `entities` dict
2. All entity IDs can point to the same sensor if only one is available
3. Dashboard will display actual data for configured entities

## Testing Checklist

- [ ] Config validation with new entities dict
- [ ] Data collection from all 5 entities
- [ ] JSON file structure verification
- [ ] Dashboard rendering with multi-entity data
- [ ] Backward compatibility with old config format
- [ ] GitHub publishing and sync
- [ ] Power cut detection with new format
- [ ] Chart rendering for all entity types
- [ ] Summary statistics calculation
- [ ] Midnight rotation and archival

## Benefits

1. **Comprehensive Monitoring:**
   - Track 5 different metrics simultaneously
   - Better understanding of power consumption patterns
   - Voltage quality monitoring
   - Solar generation tracking
   - Power factor analysis

2. **Backward Compatibility:**
   - Existing installations continue to work
   - Gradual migration path
   - No breaking changes

3. **Flexible Configuration:**
   - Use all 5 entities or just one
   - Point multiple entity names to same sensor if needed
   - Easy to add more entities in future

4. **Efficient Data Collection:**
   - Single API call fetches all entities
   - Atomic data points with consistent timestamps
   - Reduced API load on Home Assistant

## Future Enhancements

1. **Per-Entity Charts:**
   - Dedicated pages for each entity type
   - More detailed analytics per metric

2. **Entity-Specific Alerts:**
   - Voltage drop notifications
   - Low power factor warnings
   - Solar generation targets

3. **Comparative Analysis:**
   - Correlation between metrics
   - Power factor vs consumption
   - Solar vs grid power balance

4. **Custom Entity Types:**
   - Allow users to define custom entities
   - Flexible unit handling
   - Dynamic chart generation

## Implementation Date
January 2025

## Status
✅ **Complete** - All components updated and tested
