#!/bin/sh
# Quick fix script for permission issues with /var/www/html
# Run this as root: sudo sh fix_permissions.sh

set -e

echo "Fixing permissions for Power Monitor system..."

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "Error: This script must be run as root"
    echo "Please run: sudo sh fix_permissions.sh"
    exit 1
fi

# Fix /var/www/html directory permissions
echo "Setting /var/www/html permissions..."
if id -u lighttpd > /dev/null 2>&1; then
    chown -R root:lighttpd /var/www/html
    chmod 775 /var/www/html
    echo "✓ Set /var/www/html ownership to root:lighttpd with 775 permissions"
else
    chmod 755 /var/www/html
    echo "✓ Set /var/www/html to 755 permissions (lighttpd user not found)"
fi

# Fix JSON file permissions if they exist
echo "Setting JSON file permissions..."
if ls /var/www/html/*.json >/dev/null 2>&1; then
    if id -u lighttpd > /dev/null 2>&1; then
        chown root:lighttpd /var/www/html/*.json
        chmod 664 /var/www/html/*.json
        echo "✓ Set JSON file permissions to 664 (rw-rw-r--)"
    else
        chmod 644 /var/www/html/*.json
        echo "✓ Set JSON file permissions to 644 (rw-r--r--)"
    fi
else
    echo "  No JSON files found yet (will be created on next collection)"
fi

# Remove any .tmp files that might be stuck
if ls /var/www/html/*.tmp >/dev/null 2>&1; then
    echo "Cleaning up temporary files..."
    rm -f /var/www/html/*.tmp
    echo "✓ Removed temporary files"
fi

# Fix log file permissions
echo "Setting log file permissions..."
if [ -f /var/log/power-monitor-collector.log ]; then
    if id -u lighttpd > /dev/null 2>&1; then
        chown lighttpd:lighttpd /var/log/power-monitor-collector.log
        chmod 644 /var/log/power-monitor-collector.log
    else
        chmod 666 /var/log/power-monitor-collector.log
    fi
    echo "✓ Fixed collector log permissions"
fi

if [ -f /var/log/power-monitor-publisher.log ]; then
    if id -u lighttpd > /dev/null 2>&1; then
        chown lighttpd:lighttpd /var/log/power-monitor-publisher.log
        chmod 644 /var/log/power-monitor-publisher.log
    else
        chmod 666 /var/log/power-monitor-publisher.log
    fi
    echo "✓ Fixed publisher log permissions"
fi

# Fix monitor.conf permissions
if [ -f /etc/monitor.conf ]; then
    if id -u lighttpd > /dev/null 2>&1; then
        chown root:lighttpd /etc/monitor.conf
        chmod 664 /etc/monitor.conf
    else
        chmod 644 /etc/monitor.conf
    fi
    echo "✓ Fixed monitor.conf permissions"
fi

echo ""
echo "================================================"
echo "Permissions fixed successfully!"
echo "================================================"
echo ""
echo "You can now run the collector manually to test:"
echo "  python3 /opt/power-monitor/collector.py"
echo ""
echo "Or wait for the next cron job to run automatically."
echo ""
