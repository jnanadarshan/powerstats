# Weekly Data Flow - Visual Guide

## Collection Phase (Every 10 minutes via collector.py)

```
Home Assistant API
    ↓
HomeAssistantClient.get_all_current_states()
    ↓
    timestamp + 5 entities: {power, voltage, solar, power_factor, daily_energy}
    ↓
    ┌─────────────────────────────────────┐
    │   DataManager (24h retention)       │
    │   ↓ daily_manager.add_data_point()  │
    │   → daily.json (trimmed to 24h)     │
    │   ~144 granular points              │
    └─────────────────────────────────────┘
    ↓
    ┌─────────────────────────────────────┐
    │   DataManager (168h retention)      │
    │   ↓ weekly_manager.add_data_point() │
    │   → weekly.json (trimmed to 7 days) │
    │   ~1008 granular points             │
    └─────────────────────────────────────┘
```

## Aggregation Phase (12:05 AM via aggregator.py)

```
daily.json (yesterday's granular data)
    ↓
calculate_daily_summary(yesterday_data)
    ↓
Summary: {timestamp (midnight), power (avg), voltage (avg), solar (avg), 
          power_factor (avg), daily_energy (max)}
    ↓
    ┌─────────────────────────────────────┐
    │   update_aggregate_file()           │
    │   max_days = 30                     │
    │   → monthly.json                    │
    │   One summary per day (30 days)     │
    └─────────────────────────────────────┘
```

## Final Aggregation Phase (12:15 AM via aggregator.py)

```
monthly.json (yesterday's summary)
    ↓
append to yearly.json
    ↓
    ┌─────────────────────────────────────┐
    │   update_aggregate_file()           │
    │   max_days = 365                    │
    │   → yearly.json                     │
    │   One summary per day (365 days)    │
    └─────────────────────────────────────┘
```

## Publishing Phase (12:05+ AM via publisher.py)

```
GitHub API
    ↓
    ├─ weekly.json  (granular, 7 days) ← NEW: granular instead of aggregated
    ├─ monthly.json (summaries, 30 days)
    └─ yearly.json  (summaries, 365 days)
    
Note: daily.json kept local only (to prevent merge conflicts)
```

---

## Data Point Examples

### daily.json Point
```json
{
  "timestamp": "2025-11-15T14:23:45.123456",
  "power": 2450.5,
  "voltage": 238.2,
  "solar": 120.3,
  "power_factor": 0.95,
  "daily_energy": 45.2
}
```

### weekly.json Point (SAME FORMAT - Granular)
```json
{
  "timestamp": "2025-11-15T14:23:45.123456",
  "power": 2450.5,
  "voltage": 238.2,
  "solar": 120.3,
  "power_factor": 0.95,
  "daily_energy": 45.2
}
```

### monthly.json Point (Aggregated - Daily Summary)
```json
{
  "timestamp": "2025-11-15T00:00:00",
  "power": 2400.2,          // Average for the day
  "voltage": 238.5,         // Average for the day
  "solar": 115.8,           // Average for the day
  "power_factor": 0.945,    // Average for the day
  "daily_energy": 65.3      // Max for the day
}
```

### yearly.json Point (Aggregated - Daily Summary)
```json
{
  "timestamp": "2025-11-15T00:00:00",
  "power": 2400.2,          // Same as monthly
  "voltage": 238.5,         // Same as monthly
  "solar": 115.8,           // Same as monthly
  "power_factor": 0.945,    // Same as monthly
  "daily_energy": 65.3      // Same as monthly
}
```

---

## Retention Timeline (Collection Interval = 10 minutes)

```
Daily retention (24 hours):
1440 minutes ÷ 10 min/point = 144 points
Timeline: [now - 24h] ────────────────── [now]

Weekly retention (7 days):
10080 minutes ÷ 10 min/point = 1008 points
Timeline: [now - 7d] ──────────────────────────────────── [now]
         ^          ^         ^         ^         ^         ^
       -7d       -5d       -3d       -1d       now

Monthly aggregation (30 day summaries):
Timeline: [now - 30d] ──────────────────────────────── [now]
          *         *        *        *        *        * = one summary per day

Yearly aggregation (365 day summaries):
Timeline: [now - 365d] ───────────────────────────────────────────── [now]
          *              *               *               *        * = one summary per day
```

---

## Scheduler Timeline

```
EVERY 10 MINUTES (Collection)
├─ Collector runs
├─ Updates daily.json (24h window)
├─ Updates weekly.json (7d window)
└─ Publishes daily to index.html

EVERY NIGHT:
├─ 12:05 AM (Monthly aggregation)
│  └─ Reads yesterday from daily.json
│     Creates summary
│     Updates monthly.json (30 summaries)
│     Syncs to GitHub
│
└─ 12:15 AM (Yearly aggregation)
   └─ Reads yesterday from daily.json
      Creates summary
      Updates yearly.json (365 summaries)
      Syncs to GitHub
```

