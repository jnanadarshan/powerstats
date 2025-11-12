#!/bin/sh
# =============================================================================
# Power Monitoring System - Uninstallation Script
# For Luckfox Pico Max with Alpine Linux
# =============================================================================
#
# This script will:
# 1. Stop all services
# 2. Remove cron jobs
# 3. Remove application files
# 4. Remove configuration files
# 5. Optionally remove installed packages
#
# Usage: sh uninstall.sh
#
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo "${RED}[ERROR]${NC} $1"
}

# Banner
clear
cat << 'EOF'
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║      Power Monitoring System Uninstallation              ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

EOF

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    log_error "This script must be run as root"
    echo "Please run: sudo sh uninstall.sh"
    exit 1
fi

# Confirmation prompt
echo ""
log_warn "This will remove the Power Monitoring System from your device."
echo ""
echo -n "Are you sure you want to continue? (yes/no): "
read CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    log_info "Uninstallation cancelled."
    exit 0
fi

# =============================================================================
# STEP 1: Stop Services
# =============================================================================

echo ""
log_info "=== STEP 1: Stopping Services ==="

if rc-service lighttpd status > /dev/null 2>&1; then
    log_info "Stopping lighttpd..."
    rc-service lighttpd stop || log_warn "Failed to stop lighttpd"
    log_success "lighttpd stopped"
else
    log_info "lighttpd is not running"
fi

# Remove from boot
if rc-update show default | grep -q lighttpd; then
    log_info "Removing lighttpd from startup..."
    rc-update del lighttpd default || log_warn "Failed to remove from startup"
    log_success "Removed from startup"
fi

# =============================================================================
# STEP 2: Remove Cron Jobs
# =============================================================================

echo ""
log_info "=== STEP 2: Removing Cron Jobs ==="

# Remove power-monitor cron entries
if crontab -l 2>/dev/null | grep -q 'power-monitor'; then
    log_info "Removing power-monitor cron jobs..."
    crontab -l 2>/dev/null | grep -v 'power-monitor' | crontab - || true
    log_success "Cron jobs removed"
else
    log_info "No power-monitor cron jobs found"
fi

# =============================================================================
# STEP 3: Remove Application Files
# =============================================================================

echo ""
log_info "=== STEP 3: Removing Application Files ==="

# Remove application directory
if [ -d "/opt/power-monitor" ]; then
    log_info "Removing /opt/power-monitor..."
    rm -rf /opt/power-monitor
    log_success "Application files removed"
else
    log_info "Application directory not found"
fi

# Remove web files
if [ -d "/var/www/html" ]; then
    log_info "Removing web files..."
    rm -f /var/www/html/index.html
    rm -f /var/www/html/admin.cgi
    rm -f /var/www/html/*.json
    log_success "Web files removed"
fi

# Remove configuration symlink
if [ -L "/root/config.json" ]; then
    log_info "Removing config symlink..."
    rm -f /root/config.json
    log_success "Symlink removed"
fi

# =============================================================================
# STEP 4: Remove Configuration and State Files
# =============================================================================

echo ""
log_info "=== STEP 4: Removing Configuration Files ==="

# Remove state file
if [ -f "/etc/monitor.conf" ]; then
    log_info "Removing state file..."
    rm -f /etc/monitor.conf
    log_success "State file removed"
fi

# Remove lighttpd config (backup first)
if [ -f "/etc/lighttpd/lighttpd.conf" ]; then
    log_info "Backing up lighttpd config..."
    cp /etc/lighttpd/lighttpd.conf /etc/lighttpd/lighttpd.conf.backup 2>/dev/null || true
    log_info "Removing lighttpd config..."
    rm -f /etc/lighttpd/lighttpd.conf
    log_success "Config backed up and removed"
fi

# =============================================================================
# STEP 5: Remove Log Files
# =============================================================================

echo ""
log_info "=== STEP 5: Removing Log Files ==="

if [ -f "/var/log/power-monitor-collector.log" ]; then
    rm -f /var/log/power-monitor-collector.log
    log_success "Collector log removed"
fi

if [ -f "/var/log/power-monitor-publisher.log" ]; then
    rm -f /var/log/power-monitor-publisher.log
    log_success "Publisher log removed"
fi

if [ -d "/var/log/lighttpd" ]; then
    log_info "Removing lighttpd logs..."
    rm -rf /var/log/lighttpd
    log_success "Web server logs removed"
fi

# =============================================================================
# STEP 6: Optional Package Removal
# =============================================================================

echo ""
log_info "=== STEP 6: Package Removal (Optional) ==="
echo ""
log_warn "The following packages were installed by the Power Monitor:"
echo "  - python3"
echo "  - py3-requests"
echo "  - lighttpd"
echo "  - curl"
echo ""
echo "Removing these packages may affect other applications."
echo -n "Do you want to remove these packages? (yes/no): "
read REMOVE_PACKAGES

if [ "$REMOVE_PACKAGES" = "yes" ]; then
    log_info "Removing packages..."
    apk del lighttpd py3-requests 2>/dev/null || log_warn "Some packages could not be removed"
    log_success "Packages removed (python3 and curl kept as they may be system dependencies)"
else
    log_info "Packages kept (can be removed manually with: apk del lighttpd py3-requests)"
fi

# =============================================================================
# Cleanup Complete
# =============================================================================

echo ""
echo ""
cat << 'EOF'
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║            Uninstallation Complete! ✓                     ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF

echo ""
log_success "Power Monitoring System has been removed from your device"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  What Was Removed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  ✓ Application files (/opt/power-monitor/)"
echo "  ✓ Web dashboard files"
echo "  ✓ Cron jobs"
echo "  ✓ lighttpd service (stopped and disabled)"
echo "  ✓ Configuration files"
echo "  ✓ Log files"
echo "  ✓ State files"
echo ""

if [ "$REMOVE_PACKAGES" = "yes" ]; then
    echo "  ✓ System packages (lighttpd, py3-requests)"
    echo ""
else
    echo "  ℹ System packages were NOT removed"
    echo ""
    echo "  To manually remove packages:"
    echo "    apk del lighttpd py3-requests"
    echo ""
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Remaining Files"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  The following may still exist:"
echo "    - /etc/lighttpd/lighttpd.conf.backup (config backup)"
echo "    - Python3 and curl (system utilities)"
echo ""
echo "  To completely clean Alpine package cache:"
echo "    rm -rf /var/cache/apk/*"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

log_info "To reinstall, run: sh install.sh"
echo ""
