# Cron Jobs Tab - Implementation Complete

## Overview
Added a new "Cron Jobs" tab to the admin panel that displays all scheduled jobs and their schedules in an organized table format.

## Changes Made

### 1. **admin.cgi** - New Functions

#### `get_cron_jobs_detailed()` (Line ~535)
- Retrieves detailed cron job information from multiple sources
- Methods used (in order):
  1. `crontab -l` - Standard Linux/Alpine cron
  2. `/etc/crontabs/root` - Alpine Linux root crontab location
  3. Systemd services (`power-monitor-scheduler`, `power-monitor-collector`)
- Returns list of cron jobs with schedule, source, and type

#### `format_cron_schedule(cron_line: str)` (Line ~575)
- Parses cron schedule line into structured components
- Extracts: minute, hour, day, month, day-of-week, command
- Returns formatted dict for display

#### `render_cron_jobs_table()` (Line ~590)
- Generates HTML table of cron jobs
- Features:
  - Color-coded badges by job type (Systemd, Root Cron, User Cron)
  - Monospace font for schedules
  - Source information displayed
  - Responsive table layout
- Returns empty state message if no jobs found

### 2. **admin.cgi** - Updated `render_dashboard()`
- Added line ~357: `replacements['CRON_JOBS_TABLE'] = render_cron_jobs_table()`
- Populates `{{CRON_JOBS_TABLE}}` placeholder in template

### 3. **admin_dashboard.html** - New Tab & Section

#### Navigation Updates
- Added titles entry: `'cron-jobs': 'Scheduled Jobs (Cron)'`
- Added sidebar navigation item:
  ```html
  <a class="nav-item" onclick="showSection('cron-jobs')">
      <span class="material-icons">schedule</span>
      <span>Cron Jobs</span>
  </a>
  ```

#### New Content Section (Lines 1135-1176)
- Full `<div id="cron-jobs">` content section
- Includes:
  - Main title and description
  - Cron jobs table placeholder `{{CRON_JOBS_TABLE}}`
  - Info box explaining job types:
    - User Cron: from `crontab -l`
    - Root Cron: from `/etc/crontabs/root`
    - Systemd: managed services
  - Help box with typical cron schedule format explanation

## Features

### Cron Job Detection (Multi-method)
| Method | Source | OS | Priority |
|--------|--------|----|----|
| 1 | `crontab -l` | Linux/Alpine | Primary |
| 2 | `/etc/crontabs/root` | Alpine | Secondary |
| 3 | systemd services | Any | Tertiary |

### Display Information
- **Schedule**: Full cron line (e.g., `*/5 * * * * /opt/power-monitor/collector.py`)
- **Type Badge**: Visual indicator (Systemd/Root Cron/User Cron)
- **Source**: Where the job is configured

### Job Type Color Coding
| Type | Color | Badge |
|------|-------|-------|
| Systemd | Green (#10b981) | Systemd |
| Root Cron | Blue (#3b82f6) | Root Cron |
| User Cron | Purple (#8b5cf6) | User Cron |

## User Interface

### Tab Location
- Position: Between "System Logs" and "Settings" in sidebar
- Icon: Material Icons `schedule`
- Label: "Cron Jobs"

### Tab Content
1. **Table Section**
   - Headers: Schedule | Type | Source
   - Shows all detected cron jobs
   - Responsive horizontal scrolling on mobile

2. **Information Box (Green)**
   - Explains three types of cron jobs
   - Color-coded for quick reference

3. **Help Box (Blue)**
   - Shows typical cron schedule format
   - Provides example explanation
   - Helps users understand job schedules

## Technical Details

### Alpine Linux Compatibility
- Primary method uses `/etc/crontabs/root` (Alpine path)
- Falls back to standard `crontab -l`
- Detects crond daemon if no jobs found

### Error Handling
- All subprocess calls wrapped in try-except
- Graceful degradation if cron tools unavailable
- Displays "No cron jobs found" if nothing detected

### Performance
- Lightweight subprocess calls (5-second timeout each)
- Table rendered once on dashboard load
- No database queries or heavy processing

## Testing Checklist
- ✅ Python syntax validates
- ✅ Template loads without errors
- ✅ Tab shows in sidebar navigation
- ✅ Clicking tab displays cron jobs section
- ✅ Table renders correctly
- ✅ Fallback to empty state works
- ✅ All functions error-handled

## Example Output

### Alpine System with Scheduled Jobs
```
Schedule                                              Type        Source
*/5 * * * * /usr/bin/python3 /opt/power-monitor...  User Cron   crontab -l
0 0 * * * /opt/power-monitor/aggregator.py         Root Cron   /etc/crontabs/root
Systemd service: power-monitor-scheduler (active)   Systemd     systemd
```

### System with No Cron Jobs
```
No cron jobs found
```

## Future Enhancements
1. Add "Add New Cron Job" form
2. Edit/delete existing cron jobs
3. Enable/disable jobs without deletion
4. Real-time schedule prediction
5. Cron job execution history
6. Failed job alerts
