#!/bin/sh
# =============================================================================
# Power Monitoring System - Complete Installation Script
# For Luckfox Pico Max with Alpine Linux
# =============================================================================
#
# This script will:
# 1. Install Python and dependencies
# 2. Download necessary application files
# 3. Install and configure lighttpd web server
# 4. Setup auto-start on reboot
# 5. Configure GitHub
# 6. Setup Home Assistant connection
# 7. Create interactive config.json
#
# Usage: sh install.sh
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
║        Power Monitoring System Installation               ║
║        for Luckfox Pico Max - Alpine Linux                ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

EOF

# =============================================================================
# STEP 0: Pre-flight Checks
# =============================================================================

log_info "Running pre-flight checks..."

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    log_error "This script must be run as root"
    echo "Please run: sudo sh install.sh"
    exit 1
fi

log_success "Running as root"

# Check internet connectivity
log_info "Checking internet connectivity..."
if ! ping -c 1 -W 5 8.8.8.8 > /dev/null 2>&1; then
    log_error "No internet connection detected"
    exit 1
fi
log_success "Internet connectivity verified"

# =============================================================================
# STEP 1: Install Python and Dependencies
# =============================================================================

echo ""
log_info "=== STEP 1: Installing Python and Dependencies ==="

log_info "Updating package repositories..."
apk update

log_info "Installing required system packages..."
# Install only essential packages - minimize storage footprint
apk add --no-cache \
    python3 \
    py3-requests \
    lighttpd \
    curl

# Note: We use Alpine's py3-requests instead of pip to avoid externally-managed-environment error
# py3-jinja2 is not needed as we use simple string formatting in templates
log_info "Installed packages:"
apk info -s python3 py3-requests lighttpd curl | grep 'size' || echo "Package info not available"

log_success "Python and dependencies installed"

# =============================================================================
# STEP 2: Pull Down Application Files
# =============================================================================

echo ""
log_info "=== STEP 2: Setting Up Application Files ==="

# Create directory structure
log_info "Creating directory structure..."
mkdir -p /opt/power-monitor/templates
mkdir -p /var/www/html
mkdir -p /var/log/lighttpd
mkdir -p /etc

# Determine script location
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
log_info "Installation running from: $SCRIPT_DIR"

# Check if we're in the repo or need to clone
if [ -f "$SCRIPT_DIR/opt/power-monitor/collector.py" ]; then
    log_info "Found local repository files"
    
    # Copy application files
    log_info "Copying application files..."
    cp "$SCRIPT_DIR"/opt/power-monitor/*.py /opt/power-monitor/
    cp "$SCRIPT_DIR"/opt/power-monitor/config.example.json /opt/power-monitor/
    cp "$SCRIPT_DIR"/opt/power-monitor/templates/dashboard.html /opt/power-monitor/templates/
    cp "$SCRIPT_DIR"/var/www/html/index.html /var/www/html/ 2>/dev/null || \
        cp "$SCRIPT_DIR"/opt/power-monitor/templates/dashboard.html /var/www/html/index.html
    cp "$SCRIPT_DIR"/var/www/html/admin.cgi /var/www/html/
    
else
    log_info "Local files not found, cloning from GitHub..."
    echo -n "Enter GitHub repository URL (e.g., https://github.com/user/powerstats.git): "
    read REPO_URL
    
    TEMP_DIR="/tmp/powerstats-install"
    rm -rf "$TEMP_DIR"
    git clone "$REPO_URL" "$TEMP_DIR"
    
    # Copy files from cloned repo
    cp "$TEMP_DIR"/opt/power-monitor/*.py /opt/power-monitor/
    cp "$TEMP_DIR"/opt/power-monitor/config.example.json /opt/power-monitor/
    cp "$TEMP_DIR"/opt/power-monitor/templates/dashboard.html /opt/power-monitor/templates/
    cp "$TEMP_DIR"/var/www/html/index.html /var/www/html/ 2>/dev/null || \
        cp "$TEMP_DIR"/opt/power-monitor/templates/dashboard.html /var/www/html/index.html
    cp "$TEMP_DIR"/var/www/html/admin.cgi /var/www/html/
    
    rm -rf "$TEMP_DIR"
fi

# Set permissions
log_info "Setting permissions..."
chmod +x /opt/power-monitor/*.py
chmod +x /var/www/html/admin.cgi
chmod 755 /opt/power-monitor
chmod 755 /var/www/html
chmod 644 /opt/power-monitor/templates/dashboard.html

log_success "Application files installed"

# =============================================================================
# STEP 3: Install and Configure lighttpd
# =============================================================================

echo ""
log_info "=== STEP 3: Configuring lighttpd Web Server ==="

log_info "Creating lighttpd configuration..."
cat > /etc/lighttpd/lighttpd.conf << 'LIGHTTPD_EOF'
server.document-root = "/var/www/html"
server.port = 80
server.username = "lighttpd"
server.groupname = "lighttpd"

# Enable required modules
server.modules = (
    "mod_access",
    "mod_cgi",
    "mod_accesslog",
    "mod_setenv"
)

# CGI configuration for admin interface
cgi.assign = ( ".cgi" => "/usr/bin/python3" )

# Access log
accesslog.filename = "/var/log/lighttpd/access.log"

# MIME types
mimetype.assign = (
    ".html" => "text/html",
    ".htm" => "text/html",
    ".json" => "application/json",
    ".css" => "text/css",
    ".js" => "application/javascript",
    ".png" => "image/png",
    ".jpg" => "image/jpeg",
    ".jpeg" => "image/jpeg",
    ".gif" => "image/gif",
    ".svg" => "image/svg+xml",
    ".ico" => "image/x-icon"
)

# Index files
index-file.names = ( "index.html", "index.htm" )

# Enable directory listing (optional, set to "disable" for production)
dir-listing.activate = "disable"

# Security: hide server version
server.tag = "webserver"
LIGHTTPD_EOF

# Create lighttpd log directory
mkdir -p /var/log/lighttpd
chown lighttpd:lighttpd /var/log/lighttpd

log_success "lighttpd configured"

# =============================================================================
# STEP 4: Setup Auto-Start on Reboot
# =============================================================================

echo ""
log_info "=== STEP 4: Configuring Auto-Start on Reboot ==="

# Create systemd-style cron jobs for collection and publishing
log_info "Setting up cron jobs for data collection..."

# Remove existing power-monitor cron jobs
crontab -l 2>/dev/null | grep -v 'power-monitor' > /tmp/crontab.tmp || true

# Add new cron jobs (every 10 minutes)
cat >> /tmp/crontab.tmp << 'CRON_EOF'
# Power Monitor - Data Collection (every 10 minutes)
*/10 * * * * /usr/bin/python3 /opt/power-monitor/collector.py >> /var/log/power-monitor-collector.log 2>&1

# Power Monitor - Data Publishing (every 10 minutes, offset by 5 min)
5,15,25,35,45,55 * * * * /usr/bin/python3 /opt/power-monitor/publisher.py >> /var/log/power-monitor-publisher.log 2>&1
CRON_EOF

crontab /tmp/crontab.tmp
rm /tmp/crontab.tmp

log_success "Cron jobs installed"

# Enable lighttpd to start on boot
log_info "Enabling lighttpd to start on boot..."
rc-update add lighttpd default

log_success "Auto-start configured"

# =============================================================================
# STEP 5: Setup GitHub
# =============================================================================

echo ""
log_info "=== STEP 5: GitHub Configuration ==="

# Configure git user (needed for commits)
echo ""
echo -n "Enter your Git username: "
read GIT_USER
echo -n "Enter your Git email: "
read GIT_EMAIL

git config --global user.name "$GIT_USER"
git config --global user.email "$GIT_EMAIL"

log_success "Git configured with user: $GIT_USER <$GIT_EMAIL>"

# Get GitHub token
echo ""
log_info "GitHub Personal Access Token Setup"
echo "You need a Personal Access Token with 'repo' permissions."
echo "Create one at: https://github.com/settings/tokens/new"
echo ""
echo -n "Enter your GitHub Personal Access Token: "
read -s GITHUB_TOKEN
echo ""

# Get GitHub repository
echo -n "Enter your GitHub repository (format: username/repo-name): "
read GITHUB_REPO

# Get GitHub branch
echo -n "Enter the branch name (default: main): "
read GITHUB_BRANCH
GITHUB_BRANCH=${GITHUB_BRANCH:-main}

# =============================================================================
# STEP 6: Test GitHub Connection
# =============================================================================

echo ""
log_info "=== STEP 6: Testing GitHub Connection ==="

log_info "Verifying GitHub credentials..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: token $GITHUB_TOKEN" \
    "https://api.github.com/repos/$GITHUB_REPO")

if [ "$HTTP_CODE" = "200" ]; then
    log_success "GitHub authentication successful!"
    log_success "Repository '$GITHUB_REPO' is accessible"
elif [ "$HTTP_CODE" = "404" ]; then
    log_error "Repository not found. Please check the repository name."
    log_warn "Continuing installation, but GitHub sync will fail until corrected."
elif [ "$HTTP_CODE" = "401" ]; then
    log_error "GitHub authentication failed. Please check your token."
    log_warn "Continuing installation, but GitHub sync will fail until corrected."
else
    log_warn "Unexpected response from GitHub (HTTP $HTTP_CODE)"
    log_warn "Continuing installation, but please verify GitHub settings."
fi

# =============================================================================
# STEP 7: Home Assistant Configuration
# =============================================================================

echo ""
log_info "=== STEP 7: Home Assistant Configuration ==="

echo ""
echo -n "Enter your Home Assistant URL (e.g., http://homeassistant.local:8123): "
read HA_URL

echo ""
log_info "Home Assistant Long-Lived Access Token"
echo "Create one at: $HA_URL/profile (scroll to bottom)"
echo ""
echo -n "Enter your Home Assistant Access Token: "
read -s HA_TOKEN
echo ""

echo ""
echo -n "Enter the Power Sensor Entity ID (e.g., sensor.power_consumption): "
read HA_ENTITY

# =============================================================================
# STEP 8: Test Home Assistant Connection
# =============================================================================

echo ""
log_info "=== STEP 8: Testing Home Assistant Connection ==="

log_info "Verifying Home Assistant credentials..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $HA_TOKEN" \
    -H "Content-Type: application/json" \
    "$HA_URL/api/")

if [ "$HTTP_CODE" = "200" ]; then
    log_success "Home Assistant authentication successful!"
    
    # Test entity access
    log_info "Testing entity access: $HA_ENTITY"
    ENTITY_RESPONSE=$(curl -s \
        -H "Authorization: Bearer $HA_TOKEN" \
        -H "Content-Type: application/json" \
        "$HA_URL/api/states/$HA_ENTITY")
    
    if echo "$ENTITY_RESPONSE" | grep -q "entity_id"; then
        log_success "Entity '$HA_ENTITY' is accessible"
        CURRENT_STATE=$(echo "$ENTITY_RESPONSE" | grep -o '"state":"[^"]*"' | cut -d'"' -f4)
        log_info "Current value: $CURRENT_STATE"
    else
        log_warn "Entity '$HA_ENTITY' not found. Please verify the entity ID."
    fi
else
    log_error "Home Assistant authentication failed (HTTP $HTTP_CODE)"
    log_warn "Please verify your URL and token."
    log_warn "Continuing installation, but data collection will fail until corrected."
fi

# =============================================================================
# STEP 9: Create config.json
# =============================================================================

echo ""
log_info "=== STEP 9: Creating config.json ==="

# Generate a random admin password hash (simplified for Alpine)
ADMIN_PASS=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 12 | head -n 1)
ADMIN_HASH="changeme_$(echo -n "$ADMIN_PASS" | md5sum | cut -d' ' -f1)"

log_info "Generating configuration file..."
cat > /opt/power-monitor/config.json << CONFIG_EOF
{
  "homeassistant": {
    "url": "$HA_URL",
    "token": "$HA_TOKEN",
    "entity_id": "$HA_ENTITY"
  },
  "github": {
    "token": "$GITHUB_TOKEN",
    "repo": "$GITHUB_REPO",
    "branch": "$GITHUB_BRANCH"
  },
  "data": {
    "retention_days": 7,
    "collection_interval_minutes": 10
  },
  "admin": {
    "username": "admin",
    "password_hash": "$ADMIN_HASH",
    "note": "Change this password hash! Current temp password: $ADMIN_PASS"
  },
  "paths": {
    "state_file": "/etc/monitor.conf",
    "web_root": "/var/www/html",
    "data_dir": "/var/www/html"
  },
  "comments": {
    "info": "Power monitoring system maintains 4 JSON files",
    "daily": "daily.json - Last 24 hours (stored locally)",
    "weekly": "weekly.json - Last 7 days (stored locally)",
    "monthly": "monthly.json - Last 30 days (synced to GitHub)",
    "yearly": "yearly.json - Last 365 days (synced to GitHub)"
  }
}
CONFIG_EOF

chmod 600 /opt/power-monitor/config.json
log_success "Configuration file created at /opt/power-monitor/config.json"

# Create root-level config.json symlink for easy access
ln -sf /opt/power-monitor/config.json /root/config.json
log_info "Symlink created at /root/config.json for easy editing"

# Initialize state file
echo "maintenance_mode=false" > /etc/monitor.conf

# =============================================================================
# STEP 10: Start Services and Run Initial Collection
# =============================================================================

echo ""
log_info "=== STEP 10: Starting Services ==="

# Start lighttpd
log_info "Starting lighttpd web server..."
rc-service lighttpd start
log_success "lighttpd started"

# Run initial data collection
echo ""
log_info "Running initial data collection (this may take a moment)..."
if /usr/bin/python3 /opt/power-monitor/collector.py; then
    log_success "Initial data collection completed"
else
    log_warn "Initial collection had issues. Check logs for details."
fi

# Run initial publish
log_info "Publishing initial dashboard..."
if /usr/bin/python3 /opt/power-monitor/publisher.py; then
    log_success "Dashboard published"
else
    log_warn "Initial publish had issues. Check logs for details."
fi

# =============================================================================
# Installation Complete
# =============================================================================

echo ""
echo ""
cat << 'EOF'
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║            Installation Complete! 🎉                      ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF

echo ""
log_success "Power Monitoring System is now installed and running!"

# Get device IP
DEVICE_IP=$(ip route get 1.1.1.1 2>/dev/null | grep -oP 'src \K\S+' || echo "localhost")

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Access Information"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Dashboard:      http://$DEVICE_IP/"
echo "  Admin Panel:    http://$DEVICE_IP/admin.cgi"
echo ""
echo "  Admin Username: admin"
echo "  Admin Password: $ADMIN_PASS"
echo "  ${RED}⚠️  CHANGE THIS PASSWORD IMMEDIATELY!${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Config File:    /opt/power-monitor/config.json"
echo "  Quick Edit:     vi /root/config.json"
echo ""
echo "  To edit configuration:"
echo "    1. Edit the file: vi /opt/power-monitor/config.json"
echo "    2. Update any settings (HA entities, GitHub repo, etc.)"
echo "    3. No restart needed - changes take effect on next run"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Log Files"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Collector:      /var/log/power-monitor-collector.log"
echo "  Publisher:      /var/log/power-monitor-publisher.log"
echo "  Web Server:     /var/log/lighttpd/access.log"
echo ""
echo "  View logs:      tail -f /var/log/power-monitor-collector.log"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  System Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Web Server:     $(rc-service lighttpd status | grep -q 'started' && echo '✓ Running' || echo '✗ Stopped')"
echo "  Data Collection: Runs every 10 minutes via cron"
echo "  Auto-start:     ✓ Enabled (survives reboots)"
echo ""
echo "  Manual commands:"
echo "    Collect data:   python3 /opt/power-monitor/collector.py"
echo "    Publish dashboard: python3 /opt/power-monitor/publisher.py"
echo "    Restart web:    rc-service lighttpd restart"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Next Steps"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  1. ${YELLOW}Access the dashboard at http://$DEVICE_IP/${NC}"
echo "  2. ${YELLOW}Change the admin password in the admin panel${NC}"
echo "  3. ${GREEN}Review and customize config.json if needed${NC}"
echo "  4. ${GREEN}Monitor logs to ensure data collection works${NC}"
echo "  5. ${GREEN}Data will sync to GitHub automatically${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

log_info "Installation script completed successfully!"
echo ""
