# Config Migration Guide

## Quick Start: Update Your config.json

### Option 1: Multi-Entity Configuration (Recommended)

If you have multiple sensors in Home Assistant, configure all 5 entities:

```json
{
  "home_assistant": {
    "url": "http://homeassistant.local:8123",
    "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "entities": {
      "voltage": "sensor.voltage",
      "daily_energy": "sensor.daily_energy",
      "power": "sensor.live_power",
      "solar": "sensor.solar_power",
      "power_factor": "sensor.power_factor"
    }
  },
  "github": {
    "token": "ghp_xxxxxxxxxxxx",
    "repo": "username/powerstats-data",
    "branch": "main"
  },
  "data": {
    "directory": "/var/www/html",
    "retention_days": 7
  },
  "web": {
    "root": "/var/www/html"
  },
  "paths": {
    "state_file": "/var/lib/power-monitor/state.json"
  }
}
```

### Option 2: Single Sensor (Fallback)

If you only have one power sensor, point all entities to it:

```json
{
  "home_assistant": {
    "url": "http://homeassistant.local:8123",
    "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "entities": {
      "voltage": "sensor.power",
      "daily_energy": "sensor.power",
      "power": "sensor.power",
      "solar": "sensor.power",
      "power_factor": "sensor.power"
    }
  }
}
```

**Note:** The dashboard will simulate voltage and power factor from power readings.

### Option 3: Backward Compatible (Old Format Still Works)

Keep using the old format if you're not ready to migrate:

```json
{
  "home_assistant": {
    "url": "http://homeassistant.local:8123",
    "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "entity_id": "sensor.power"
  }
}
```

**Note:** This still works, but you won't get multi-entity benefits.

## Finding Your Entity IDs in Home Assistant

1. Open Home Assistant web interface
2. Go to **Developer Tools** → **States**
3. Search for your sensors (voltage, power, energy, etc.)
4. Copy the **entity_id** (e.g., `sensor.voltage`)
5. Paste into your config.json

## Common Entity ID Patterns

### Shelly Devices
```json
"voltage": "sensor.shelly_pm_voltage",
"power": "sensor.shelly_pm_power",
"daily_energy": "sensor.shelly_pm_energy"
```

### Tuya/Smart Life Devices
```json
"voltage": "sensor.tuya_voltage",
"power": "sensor.tuya_power",
"power_factor": "sensor.tuya_power_factor"
```

### Sonoff POW Devices
```json
"voltage": "sensor.sonoff_voltage",
"power": "sensor.sonoff_power",
"daily_energy": "sensor.sonoff_energy_today"
```

### Solar Inverters (Generic)
```json
"solar": "sensor.solar_inverter_power",
"daily_energy": "sensor.solar_production_today"
```

## GitHub Configuration

### New Format (Simpler)
```json
"github": {
  "token": "ghp_xxxxxxxxxxxx",
  "repo": "username/repo-name",
  "branch": "main"
}
```

### Old Format (Still Supported)
```json
"github": {
  "token": "ghp_xxxxxxxxxxxx",
  "repo_owner": "username",
  "repo_name": "repo-name",
  "branch": "main"
}
```

## Validation After Update

Test your configuration:

```bash
# Check if collector can read config
python3 /opt/power-monitor/collector.py

# Test Home Assistant connection
sh /root/deployment/test_homeassistant_api.sh \
  "http://homeassistant.local:8123" \
  "your_token" \
  "sensor.voltage"
```

## Troubleshooting

### Error: "Entity not found"
- Check entity_id spelling in Home Assistant
- Verify sensor is available in HA Developer Tools → States
- Ensure entity_id includes the domain prefix (e.g., `sensor.`)

### Error: "Invalid configuration"
- Validate JSON syntax with `python3 -m json.tool config.json`
- Check all required fields are present
- Ensure `entities` is a dict/object, not array

### Dashboard shows simulated data
- This is normal if actual sensors aren't configured
- Update entity IDs to point to real sensors
- Check HA API logs: `tail -f /var/log/power-monitor-collector.log`

## Migration Steps

1. **Backup current config:**
   ```bash
   cp /opt/power-monitor/config.json /opt/power-monitor/config.json.backup
   ```

2. **Update config format:**
   ```bash
   vi /opt/power-monitor/config.json
   # Add "entities" dict with your sensor IDs
   ```

3. **Test configuration:**
   ```bash
   python3 /opt/power-monitor/collector.py
   ```

4. **Monitor logs:**
   ```bash
   tail -f /var/log/power-monitor-collector.log
   ```

5. **Check dashboard:**
   - Open http://your-device/index.html
   - Verify all charts show data
   - Check summary statistics

## Need Help?

- Review logs: `/var/log/power-monitor-collector.log`
- Check HA connection: `deployment/test_homeassistant_api.sh`
- Validate JSON: `python3 -m json.tool config.json`
- Refer to: `MULTI_ENTITY_IMPLEMENTATION.md` for technical details
