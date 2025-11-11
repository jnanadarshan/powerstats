#!/bin/sh
# Uninstall script for Power Monitoring System

set -e

echo "================================================"
echo "Power Monitoring System Uninstallation"
echo "================================================"
echo ""

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "Error: This script must be run as root"
    exit 1
fi

echo "This will remove all power monitoring system files and configurations."
read -p "Are you sure? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Uninstallation cancelled."
    exit 0
fi

# Stop lighttpd
echo "Stopping lighttpd..."
rc-service lighttpd stop || true
rc-update del lighttpd default || true

# Remove cron job
echo "Removing cron job..."
crontab -l | grep -v "/opt/power-monitor/collector.py" | crontab - || true

# Remove files
echo "Removing application files..."
rm -rf /opt/power-monitor
rm -f /var/www/html/index.html
rm -f /var/www/html/data.json
rm -f /var/www/html/admin.cgi
rm -f /etc/monitor.conf

# Remove logs
echo "Removing logs..."
rm -f /var/log/power-monitor-collector.log
rm -f /var/log/power-monitor-publisher.log

echo ""
echo "================================================"
echo "Uninstallation Complete!"
echo "================================================"
echo ""
echo "Note: lighttpd package and Python dependencies"
echo "were not removed. Remove them manually if needed:"
echo "  apk del lighttpd python3"
echo ""
