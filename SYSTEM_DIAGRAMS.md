# System Flow Diagram

## Data Collection Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     EVERY 10 MINUTES (CRON)                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌─────────────────┐
                    │  collector.py   │
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │ Check           │
                    │ Maintenance     │
                    │ Mode?           │
                    └────┬────────┬───┘
                         │        │
                    YES  │        │ NO
                         ↓        ↓
                   ┌──────────┐  ┌───────────────────┐
                   │  SKIP    │  │ Fetch from Home   │
                   │  EXIT    │  │ Assistant API     │
                   └──────────┘  └─────────┬─────────┘
                                           ↓
                                  ┌─────────────────┐
                                  │ Update data.json│
                                  │ (7-day window)  │
                                  └────────┬────────┘
                                           ↓
                                  ┌─────────────────┐
                                  │ Generate HTML   │
                                  │ from template   │
                                  └────────┬────────┘
                                           ↓
                                  ┌─────────────────┐
                                  │ Write to        │
                                  │ /var/www/html/  │
                                  └────────┬────────┘
                                           ↓
                                  ┌─────────────────┐
                                  │  publisher.py   │
                                  └────────┬────────┘
                                           ↓
                                  ┌─────────────────┐
                                  │ Push to GitHub  │
                                  │ Pages via API   │
                                  └─────────────────┘
```

## User Access Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                             │
└───────────────────────┬──────────────────────────────────────────┘
                        │
         ┌──────────────┴──────────────┐
         │                             │
         ↓                             ↓
┌────────────────┐           ┌─────────────────┐
│ Dashboard      │           │ Admin Panel     │
│ /index.html    │           │ /admin.cgi      │
└────────┬───────┘           └────────┬────────┘
         │                            │
         ↓                            ↓
┌────────────────┐           ┌─────────────────┐
│ View Charts    │           │ Authenticate    │
│ Statistics     │           └────────┬────────┘
│ (Chart.js)     │                    │
└────────────────┘                    ↓
                              ┌─────────────────┐
                              │ Toggle Maint.   │
                              │ Manual Sync     │
                              │ View Status     │
                              └─────────────────┘
```

## Component Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    LUCKFOX PICO MAX                            │
│                    Alpine Linux (256MB RAM)                    │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              lighttpd (Web Server)                   │    │
│  │              Port 80                                 │    │
│  │  ┌────────────────┐    ┌───────────────────────┐    │    │
│  │  │ Static Files   │    │ CGI Support           │    │    │
│  │  │ - index.html   │    │ - admin.cgi           │    │    │
│  │  │ - data.json    │    │ - Python execution    │    │    │
│  │  └────────────────┘    └───────────────────────┘    │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              Python Scripts                          │    │
│  │                                                      │    │
│  │  ┌─────────────────────────────────────────────┐    │    │
│  │  │ collector.py                                │    │    │
│  │  │ - Fetch HA data                             │    │    │
│  │  │ - Update JSON                               │    │    │
│  │  │ - Generate HTML                             │    │    │
│  │  └─────────────────────────────────────────────┘    │    │
│  │                                                      │    │
│  │  ┌─────────────────────────────────────────────┐    │    │
│  │  │ publisher.py                                │    │    │
│  │  │ - Push to GitHub                            │    │    │
│  │  │ - Update Pages                              │    │    │
│  │  └─────────────────────────────────────────────┘    │    │
│  │                                                      │    │
│  │  ┌─────────────────────────────────────────────┐    │    │
│  │  │ config_manager.py                           │    │    │
│  │  │ - Load config                               │    │    │
│  │  │ - Validate settings                         │    │    │
│  │  └─────────────────────────────────────────────┘    │    │
│  │                                                      │    │
│  │  ┌─────────────────────────────────────────────┐    │    │
│  │  │ utils.py                                    │    │    │
│  │  │ - CLI management                            │    │    │
│  │  │ - Status checks                             │    │    │
│  │  └─────────────────────────────────────────────┘    │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              Storage                                 │    │
│  │  /etc/monitor.conf       - State file               │    │
│  │  /opt/power-monitor/     - Application              │    │
│  │  /var/www/html/          - Web root                 │    │
│  │  /var/log/               - Logs                     │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                                │
└────────────────────────────────────────────────────────────────┘
         │                                    │
         ↓                                    ↓
┌─────────────────┐                  ┌─────────────────┐
│ Home Assistant  │                  │ GitHub Pages    │
│ REST API        │                  │ API             │
└─────────────────┘                  └─────────────────┘
```

## Data Structure

```
data.json
├── data_points[]
│   ├── timestamp: "2025-11-11T10:00:00Z"
│   ├── value: 1234.56
│   └── unit: "W"
├── last_update: "2025-11-11T10:05:00"
└── (automatic 7-day retention)

Statistics (calculated)
├── current: Latest value
├── average: Mean of all points
├── min: Minimum value
├── max: Maximum value
└── total_kwh: Energy consumption
```

## File Dependencies

```
collector.py
    ├── imports config_manager.py
    ├── reads /opt/power-monitor/config.json
    ├── checks /etc/monitor.conf
    ├── uses templates/dashboard.html
    ├── writes /var/www/html/data.json
    ├── writes /var/www/html/index.html
    └── logs to /var/log/power-monitor-collector.log

publisher.py
    ├── imports config_manager.py
    ├── reads /opt/power-monitor/config.json
    ├── checks /etc/monitor.conf
    ├── reads /var/www/html/data.json
    ├── reads /var/www/html/index.html
    └── logs to /var/log/power-monitor-publisher.log

admin.cgi
    ├── imports config_manager.py
    ├── imports collector.py (MaintenanceMode)
    ├── reads/writes /etc/monitor.conf
    ├── executes collector.py
    └── executes publisher.py

utils.py
    ├── imports config_manager.py
    ├── imports collector.py
    ├── reads all log files
    └── performs system operations
```

## Maintenance Mode Flow

```
Admin Action
     ↓
┌─────────────────┐
│ Toggle Switch   │
│ in admin.cgi    │
└────────┬────────┘
         ↓
┌─────────────────┐
│ Write to        │
│ monitor.conf    │
│ maintenance=true│
└────────┬────────┘
         ↓
┌─────────────────────────────┐
│ Next Cron Execution         │
└────────┬────────────────────┘
         ↓
┌─────────────────┐
│ collector.py    │
│ checks file     │
│ → SKIP          │
└────────┬────────┘
         ↓
┌─────────────────┐
│ publisher.py    │
│ checks file     │
│ → SKIP          │
└─────────────────┘

Manual Disable
     ↓
┌─────────────────┐
│ Toggle Switch   │
│ maintenance=false│
└────────┬────────┘
         ↓
┌─────────────────┐
│ Next Cron       │
│ → RESUME        │
└─────────────────┘
```

## Resource Timeline (10-minute cycle)

```
Minute 0:00 - Cron triggers collector.py
         ↓
Minute 0:00-0:03 - collector.py executes
    - RAM usage: 43MB → 58MB (peak)
    - Fetch data (2-5 seconds)
    - Process & write (1 second)
         ↓
Minute 0:03 - collector.py completes
         ↓
Minute 0:03-0:08 - publisher.py executes
    - RAM usage: 43MB → 53MB (peak)
    - GitHub API calls (3-5 seconds)
         ↓
Minute 0:08 - publisher.py completes
         ↓
Minute 0:08-10:00 - Idle
    - RAM usage: 43MB (baseline)
    - lighttpd serving requests
         ↓
Minute 10:00 - Repeat cycle
```
