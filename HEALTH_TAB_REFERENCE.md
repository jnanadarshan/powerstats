# Health Tab - Quick Reference

## Visual Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  ⚡ Power Monitor              [Today][7 Days][30 Days][365 Days]│
│                                                    [Health][Help] │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  🏥 System Health                                                │
│  Real-time monitoring of system resources and data collection    │
│                                                                   │
│  ┌─────────────────────┐  ┌─────────────────────┐              │
│  │ 💾 Disk Usage       │  │ 🧠 Memory Usage     │              │
│  │      33.3%          │  │      50.2%          │              │
│  │ 0.08 GB used of     │  │ 128.5 MB used of    │              │
│  │ 0.24 GB (0.16 free) │  │ 256 MB (127.5 avail)│              │
│  │ ▓▓▓▓▓░░░░░░░░░░░░░░ │  │ ▓▓▓▓▓▓▓▓▓░░░░░░░░░░ │              │
│  └─────────────────────┘  └─────────────────────┘              │
│                                                                   │
│  📊 Data Collection Status                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Last Collection (IST)  │  Next Collection In  │ Interval │   │
│  │ 2024-01-15 16:00:00    │       8:45          │10 minutes│   │
│  │                        │ 8 minutes remaining  │          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  📤 GitHub Sync Status                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Configuration │    Repository        │ Last Publish (IST)│   │
│  │ ✅ Configured │ username/powerstats  │ 2024-01-15 16:05 │   │
│  │               │                      │                   │   │
│  │    Status: Success ✓                                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  🔄 Auto-refreshing every 10 seconds                             │
│  Last updated: 16:08:30                                          │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Color Coding

### Disk/Memory Progress Bars
- **Green** (< 75%): `▓▓▓▓░░░░░░` Normal operation
- **Orange** (75-89%): `▓▓▓▓▓▓▓▓░░` Warning - consider cleanup
- **Red** (≥ 90%): `▓▓▓▓▓▓▓▓▓▓` Critical - action needed

### Status Indicators
- **✅ Configured**: GitHub is set up correctly (Green)
- **❌ Not Configured**: GitHub needs setup (Red)
- **Success**: Last operation successful (Green)
- **Error/Failed**: Last operation failed (Red)
- **Unknown**: Status not determined (Orange)

## Data Refresh Behavior

### Auto-Refresh (Every 10 seconds)
1. Fetches fresh data from `/health.cgi`
2. Updates all metrics simultaneously
3. Restarts countdown timer
4. Shows "Last updated" timestamp

### Countdown Timer (Every 1 second)
1. Shows time until next data collection
2. Format: `MM:SS` (e.g., `8:45`)
3. Text updates: "8 minutes remaining" → "45 seconds remaining"
4. When reaches 0: Shows "Collecting..."

## Key Features

### 📊 Metrics Displayed
1. **Disk Usage**: Total/Used/Free space in GB + percentage
2. **Memory Usage**: Total/Used/Available in MB + percentage
3. **Last Collection**: When data was last collected (IST timezone)
4. **Next Collection**: Countdown timer to next collection
5. **GitHub Status**: Configuration state and last publish time

### 🔄 Auto-Refresh
- Background fetch every 10 seconds
- No page reload required
- Smooth UI updates
- Visual indicators for refresh status

### ⏱️ Live Countdown
- Real-time countdown timer
- Updates every second
- Shows minutes and seconds
- Automatic reset on data collection

### 🎨 Visual Feedback
- Color-coded progress bars
- Status icons (✅/❌)
- Smooth animations
- Responsive layout

## Access

1. Open dashboard: `http://your-luckfox-ip/`
2. Click **Health** tab in navigation
3. View real-time metrics
4. Leave tab open for continuous monitoring

## Mobile View

On mobile devices (< 768px width):
- Stacked layout (1 column)
- Touch-friendly tap targets
- Optimized font sizes
- Full-width cards

## Troubleshooting Quick Reference

| Issue | Likely Cause | Quick Fix |
|-------|--------------|-----------|
| Health tab shows "Error" | health.cgi not accessible | Check lighttpd running |
| Disk shows 0% | psutil not installed | `apk add py3-psutil` |
| Memory shows 0% | psutil cannot read | Check permissions |
| "Never" for Last Collection | No data collected yet | Run collector manually |
| Countdown not working | daily.json missing | Check data directory |
| GitHub shows "Not Configured" | Missing GitHub token | Edit config.json |
| Auto-refresh stops | JavaScript error | Check browser console |

## API Endpoint

Direct access to health data:
```bash
curl http://localhost/health.cgi | python3 -m json.tool
```

Returns JSON with all metrics shown in the UI.
