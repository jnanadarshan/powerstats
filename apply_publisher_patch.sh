#!/bin/sh
# apply_publisher_patch.sh
# Run this on the device as root to update /opt/power-monitor/publisher.py to include daily.json
# Usage: sudo sh apply_publisher_patch.sh

set -e

PUBLISHER=/opt/power-monitor/publisher.py
if [ ! -f "$PUBLISHER" ]; then
  echo "Error: $PUBLISHER not found. Is the application installed at /opt/power-monitor?"
  exit 1
fi

TS=$(date +%Y%m%d%H%M%S)
BACKUP="${PUBLISHER}.bak.${TS}"
cp "$PUBLISHER" "$BACKUP"
echo "Backup created: $BACKUP"

# Use Python to perform a safe replacement of the files_to_publish block
python3 - <<'PY'
from pathlib import Path
p = Path('/opt/power-monitor/publisher.py')
s = p.read_text()
old = '''files_to_publish = [
            ('index.html', 'index.html', f'Update dashboard - {timestamp}'),
            ('weekly.json', 'weekly.json', f'Update weekly granular data - {timestamp}'),
            ('monthly.json', 'monthly.json', f'Update monthly data - {timestamp}'),
            ('yearly.json', 'yearly.json', f'Update yearly data - {timestamp}')
        ]'''
new = '''files_to_publish = [
            ('index.html', 'index.html', f'Update dashboard - {timestamp}'),
            ('daily.json', 'daily.json', f'Update daily data - {timestamp}'),
            ('weekly.json', 'weekly.json', f'Update weekly granular data - {timestamp}'),
            ('monthly.json', 'monthly.json', f'Update monthly data - {timestamp}'),
            ('yearly.json', 'yearly.json', f'Update yearly data - {timestamp}')
        ]\n        # WARNING: Including `daily.json` will create very frequent commits\n        # because `daily.json` is updated often (potentially every minute).\n        # Be aware of increased GitHub API usage and repository churn.'''

if old in s:
    s = s.replace(old, new)
    p.write_text(s)
    print('publisher.py updated successfully')
else:
    print('Pattern not found. publisher.py may already be modified or format differs. No changes made.')
# Also ensure the main() uses config.data_dir when invoking publish_dashboard
old2 = "if publisher.publish_dashboard(config.web_root):"
new2 = "if publisher.publish_dashboard(config.data_dir):"
if old2 in s:
    s = s.replace(old2, new2)
    p.write_text(s)
    print('Updated publish_dashboard call to use config.data_dir')
else:
    print('publish_dashboard call already uses config.data_dir or differs; no change')
PY

echo "Done. Review /opt/power-monitor/publisher.py and run the publisher to verify:"
echo "  python3 /opt/power-monitor/publisher.py"
