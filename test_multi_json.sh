#!/bin/bash
# Quick test script for new multi-JSON architecture
set -e

echo "=== Power Monitor Multi-JSON Architecture Test ==="
echo ""

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$REPO_ROOT/var/www/html"
CONFIG_FILE="$REPO_ROOT/opt/power-monitor/config.json"

echo "Repository root: $REPO_ROOT"
echo "Data directory: $DATA_DIR"
echo ""

# 1. Create test daily.json with sample data
echo "Step 1: Creating test daily.json..."
python3 << 'PYTHON'
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

repo_root = Path(sys.argv[0]).resolve().parent if len(sys.argv) > 1 else Path.cwd()
data_dir = repo_root / 'var' / 'www' / 'html'
data_dir.mkdir(parents=True, exist_ok=True)

# Generate last 24 hours of sample data (10-min intervals = 144 points)
now = datetime.now(timezone.utc)
points = []
for i in range(144):
    t = now - timedelta(minutes=(144 - i) * 10)
    # Simulate varying power consumption
    hour = t.hour
    base = 250 if 6 <= hour < 22 else 100  # Day vs night
    value = base + (i % 20) * 5
    
    points.append({
        'timestamp': t.isoformat().replace('+00:00', 'Z'),
        'value': value,
        'unit': 'W'
    })

daily_data = {
    'data_points': points,
    'last_update': now.isoformat().replace('+00:00', 'Z'),
    'date': now.date().isoformat()
}

with open(data_dir / 'daily.json', 'w') as f:
    json.dump(daily_data, f, indent=2)

print(f"Created daily.json with {len(points)} points")
PYTHON

# 2. Run aggregator to create weekly/monthly/yearly
echo ""
echo "Step 2: Running aggregator to create weekly/monthly/yearly JSON files..."
python3 "$REPO_ROOT/opt/power-monitor/aggregator.py" "$DATA_DIR"

# 3. Check created files
echo ""
echo "Step 3: Verifying created files..."
for file in daily.json weekly.json monthly.json yearly.json; do
    if [ -f "$DATA_DIR/$file" ]; then
        size=$(du -h "$DATA_DIR/$file" | cut -f1)
        points=$(python3 -c "import json; print(len(json.load(open('$DATA_DIR/$file'))['data_points']))")
        echo "✓ $file: $size ($points data points)"
    else
        echo "✗ $file: NOT FOUND"
    fi
done

# 4. Test scheduler (once mode)
echo ""
echo "Step 4: Testing scheduler (one-shot mode)..."
python3 "$REPO_ROOT/opt/power-monitor/scheduler.py" \
    --data-dir "$DATA_DIR" \
    --config "$CONFIG_FILE" \
    --once

# 5. Show summary
echo ""
echo "=== Test Complete ==="
echo ""
echo "JSON Files Created:"
ls -lh "$DATA_DIR"/*.json 2>/dev/null || echo "No JSON files found"

echo ""
echo "Next Steps:"
echo "1. Configure GitHub token in $CONFIG_FILE"
echo "2. Test GitHub sync: python3 opt/power-monitor/github_sync.py $DATA_DIR push"
echo "3. Start scheduler daemon: python3 opt/power-monitor/scheduler.py --daemon"
echo "4. Update dashboard to load separate JSON files per tab"
echo ""
echo "For more info, see: MULTI_JSON_ARCHITECTURE.md"
