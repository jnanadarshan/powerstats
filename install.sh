#!/bin/sh
# =============================================================================
# Power Monitoring System - Installation Script
# For Luckfox Pico Max with Alpine Linux
# =============================================================================
#
# Prerequisites:
#   1. Clone this repository: git clone <repo-url>
#   2. Edit config.json with your credentials
#   3. Run: sudo sh install.sh
#
# This script will:
#   1. Validate config.json exists
#   2. Install minimal dependencies (Python, lighttpd)
#   3. Setup cron jobs for data collection
#   4. Install application files
#   5. Validate GitHub API access
#   6. Validate Home Assistant API access
#   7. Start web server
#   8. Display access information
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
log_info "\n${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
log_info "${BLUE}STEP 0: Pre-flight Checks${NC}"
log_info "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    log_error "This script must be run as root"
    echo "Please run: sudo sh install.sh"
    exit 1
fi

log_success "Running as root"

# Determine script location
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
log_info "Installation running from: $SCRIPT_DIR"

# Check if config.json exists
if [ ! -f "$SCRIPT_DIR/config.json" ]; then
    log_error "config.json not found in $SCRIPT_DIR"
    echo ""
    echo "Please create and configure config.json before running installation."
    echo "See config.json.example or documentation for required fields."
    exit 1
fi

log_success "config.json found"

# Validate config.json is valid JSON
if ! python3 -c "import json; json.load(open('$SCRIPT_DIR/config.json'))" 2>/dev/null; then
    log_error "config.json is not valid JSON"
    echo "Please check your config.json syntax"
    exit 1
fi

log_success "config.json is valid JSON"

# Check internet connectivity
log_info "Checking internet connectivity..."
if ! ping -c 1 -W 5 8.8.8.8 > /dev/null 2>&1; then
    log_error "No internet connection detected"
    exit 1
fi
log_success "Internet connectivity verified"

# =============================================================================
# STEP 1: Install Dependencies
# =============================================================================
log_info "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
log_info "${BLUE}STEP 1: Installing Dependencies${NC}"
log_info "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

log_info "Updating package repositories..."
apk update

log_info "Installing minimal system packages..."
# Install only essential packages - minimize storage footprint
apk add --no-cache \
    python3 \
    py3-requests \
    py3-jinja2 \
    lighttpd \
    curl \
    dcron \
    busybox-syslogd \
    logrotate

# Note: We use Alpine's py3-* packages instead of pip to avoid externally-managed-environment error
log_info "Package installation complete"
apk info -s python3 py3-requests py3-jinja2 lighttpd curl | grep 'size' || echo "Package info not available"

log_success "Dependencies installed"

# Enable and start cron and syslog so scheduled jobs will run out of the box
log_info "Enabling cron (dcron) and syslog (syslogd) services"
if rc-update add dcron default > /dev/null 2>&1; then
    log_info "dcron added to default runlevel"
else
    log_warn "Could not add dcron to default runlevel (rc-update may not be available)"
fi
if rc-service dcron start > /dev/null 2>&1; then
    log_success "dcron started"
else
    log_warn "Failed to start dcron (it may already be running or service not available)"
fi

if rc-update add syslogd default > /dev/null 2>&1; then
    log_info "syslogd added to default runlevel"
else
    log_warn "Could not add syslogd to default runlevel"
fi
if rc-service syslogd start > /dev/null 2>&1; then
    log_success "syslogd started"
else
    log_warn "Failed to start syslogd (it may already be running or service not available)"
fi

# Configure logrotate for power-monitor logs to prevent uncontrolled growth
LOGROTATE_CONF="/etc/logrotate.d/power-monitor"
cat > "$LOGROTATE_CONF" << 'LR'
/var/log/power-monitor-collector.log /var/log/power-monitor-publisher.log {
    weekly
    rotate 4
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
    sharedscripts
    postrotate
        # no-op; logs are plain files appended by cron jobs
    endscript
}
LR
chown root:root "$LOGROTATE_CONF" || true
chmod 644 "$LOGROTATE_CONF" || true

# Ensure logrotate runs daily (Alpine runs /etc/periodic/daily/* via run-parts)
LR_DAILY="/etc/periodic/daily/logrotate-power-monitor"
cat > "$LR_DAILY" << 'LRD'
#!/bin/sh
# Run logrotate for configured logs
/usr/sbin/logrotate /etc/logrotate.conf || true
LRD
chmod 755 "$LR_DAILY" || true

log_info "Logrotate configured for power-monitor logs (weekly, 4 rotations)"

# =============================================================================
# STEP 2: Setup Cron
# =============================================================================
log_info "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
log_info "${BLUE}STEP 2: Setting Up Cron Jobs${NC}"
log_info "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Create cron directory structure (Alpine Linux requirement)
log_info "Creating cron directories..."
mkdir -p /var/spool/cron/crontabs
mkdir -p /var/log/cron

log_success "Cron directories created"

# Setup cron jobs (will be configured after app installation)
log_info "Cron jobs will be configured in next step..."

# =============================================================================
# STEP 3: Install Application
# =============================================================================
log_info "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
log_info "${BLUE}STEP 3: Installing Application${NC}"
log_info "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Create directory structure
log_info "Creating application directories..."
mkdir -p /opt/power-monitor/templates
mkdir -p /var/www/html
mkdir -p /var/log/lighttpd
mkdir -p /etc

log_success "Directories created"

# Copy application files from cloned repository
log_info "Copying application files..."
cp "$SCRIPT_DIR"/opt/power-monitor/*.py /opt/power-monitor/
cp "$SCRIPT_DIR"/opt/power-monitor/templates/dashboard.html /opt/power-monitor/templates/
cp "$SCRIPT_DIR"/var/www/html/index.html /var/www/html/
cp "$SCRIPT_DIR"/var/www/html/admin.cgi /var/www/html/

# Copy config.json to application directory
cp "$SCRIPT_DIR"/config.json /opt/power-monitor/config.json

# Set permissions
log_info "Setting permissions..."
chmod +x /opt/power-monitor/*.py
chmod +x /var/www/html/admin.cgi
chmod 755 /opt/power-monitor
chmod 755 /var/www/html
chmod 644 /opt/power-monitor/templates/dashboard.html
chmod 600 /opt/power-monitor/config.json

# Create symlink for easy config access
ln -sf /opt/power-monitor/config.json /root/config.json

log_success "Application files installed"

# Configure cron jobs now that app is installed
log_info "Configuring cron jobs for data collection..."

# Ensure log files exist and are writable by root
mkdir -p /var/log
: > /var/log/power-monitor-collector.log 2>/dev/null || true
: > /var/log/power-monitor-publisher.log 2>/dev/null || true
chown root:root /var/log/power-monitor-collector.log /var/log/power-monitor-publisher.log || true
chmod 644 /var/log/power-monitor-collector.log /var/log/power-monitor-publisher.log || true

# Preferred on Alpine: append to system crontab at /etc/crontabs/root (no user column)
CRONTAB_FILE="/etc/crontabs/root"
TS=$(date +%Y%m%d%H%M%S)
BACKUP="${CRONTAB_FILE}.bak.${TS}"
if [ -f "${CRONTAB_FILE}" ]; then
    cp "${CRONTAB_FILE}" "${BACKUP}"
    log_info "Backed up ${CRONTAB_FILE} -> ${BACKUP}"
else
    # create basic file if missing (preserve existing periodic entries if any expected)
    touch "${CRONTAB_FILE}"
    log_info "Created ${CRONTAB_FILE}"
fi

# Combined job runs collector then publisher every 2 minutes
JOB_LINE="*/2 * * * * /bin/sh -c '/usr/bin/python3 /opt/power-monitor/collector.py >> /var/log/power-monitor-collector.log 2>&1 && /usr/bin/python3 /opt/power-monitor/publisher.py >> /var/log/power-monitor-publisher.log 2>&1'"

# Append job if not present (use fixed-string match)
if ! grep -Fq "${JOB_LINE}" "${CRONTAB_FILE}"; then
    printf "\n# Power Monitor - combined job (every 2 minutes)\n" >> "${CRONTAB_FILE}"
    printf "%s\n" "${JOB_LINE}" >> "${CRONTAB_FILE}"
    log_success "Appended power-monitor job to ${CRONTAB_FILE}"
else
    log_info "Power-monitor job already present in ${CRONTAB_FILE}"
fi

# Ensure correct ownership/permissions for system crontab
chown root:root "${CRONTAB_FILE}" || true
chmod 644 "${CRONTAB_FILE}" || true

# Restart whichever cron service is present so changes take effect
if rc-service dcron restart > /dev/null 2>&1; then
    log_success "dcron restarted"
elif rc-service crond restart > /dev/null 2>&1; then
    log_success "crond restarted"
elif rc-service cronie restart > /dev/null 2>&1; then
    log_success "cronie restarted"
else
    log_warn "Could not restart cron service automatically; please restart (dcron/crond/cronie) to apply crontab changes"
fi

log_success "Cron jobs configured (system crontab updated)"

# Initialize state file
echo "maintenance_mode=false" > /etc/monitor.conf

log_success "Application installed successfully"

# =============================================================================
# STEP 4: Validate GitHub API
# =============================================================================
log_info "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
log_info "${BLUE}STEP 4: Validating GitHub API Access${NC}"
log_info "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Extract GitHub config from config.json
GITHUB_TOKEN=$(python3 -c "import json; print(json.load(open('/opt/power-monitor/config.json'))['github']['token'])")
GITHUB_REPO=$(python3 -c "import json; print(json.load(open('/opt/power-monitor/config.json'))['github']['repo'])")
GIT_USER=$(python3 -c "import json; print(json.load(open('/opt/power-monitor/config.json'))['github']['user']['name'])")
GIT_EMAIL=$(python3 -c "import json; print(json.load(open('/opt/power-monitor/config.json'))['github']['user']['email'])")

# Configure git user (needed for commits)
git config --global user.name "$GIT_USER"
git config --global user.email "$GIT_EMAIL"
log_success "Git configured: $GIT_USER <$GIT_EMAIL>"

# Test GitHub API access
log_info "Testing GitHub API access (timeout: 10 seconds)..."
HTTP_CODE=$(timeout 10 curl -s -o /dev/null -w "%{http_code}" \
    --connect-timeout 5 \
    --max-time 10 \
    -H "Authorization: token $GITHUB_TOKEN" \
    "https://api.github.com/repos/$GITHUB_REPO" 2>/dev/null || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
    log_success "GitHub API: ✓ Authentication successful"
    log_success "Repository: ✓ '$GITHUB_REPO' is accessible"
elif [ "$HTTP_CODE" = "404" ]; then
    log_warn "GitHub API: ✗ Repository not found"
    log_warn "Please verify repository name in config.json"
    log_warn "Continuing installation - fix config and restart collection manually"
elif [ "$HTTP_CODE" = "401" ]; then
    log_warn "GitHub API: ✗ Authentication failed"
    log_warn "Please verify your GitHub token in config.json"
    log_warn "Continuing installation - fix config and restart collection manually"
elif [ "$HTTP_CODE" = "000" ]; then
    log_warn "GitHub API: ✗ Connection timeout or unreachable"
    log_warn "The device may not have internet connectivity"
    log_warn "Continuing installation - verify network and restart collection manually"
else
    log_warn "GitHub API: ? Unexpected response (HTTP $HTTP_CODE)"
    log_warn "Continuing installation - verify settings if needed"
fi

# =============================================================================
# STEP 5: Validate Home Assistant API
# =============================================================================
log_info "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
log_info "${BLUE}STEP 5: Validating Home Assistant API Access${NC}"
log_info "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Extract HA config from config.json (use safe lookups to avoid KeyError)
HA_URL=$(python3 - <<'PY'
import json
cfg=json.load(open('/opt/power-monitor/config.json'))
ha=cfg.get('homeassistant',{})
print(ha.get('url',''))
PY
)
HA_TOKEN=$(python3 - <<'PY'
import json
cfg=json.load(open('/opt/power-monitor/config.json'))
ha=cfg.get('homeassistant',{})
print(ha.get('token',''))
PY
)
HA_POWER_ENTITY=$(python3 - <<'PY'
import json
cfg=json.load(open('/opt/power-monitor/config.json'))
ha=cfg.get('homeassistant',{})
ents=ha.get('entities',{})
print(ents.get('power_sensor',''))
PY
)
HA_SOLAR_ENTITY=$(python3 - <<'PY'
import json
cfg=json.load(open('/opt/power-monitor/config.json'))
ha=cfg.get('homeassistant',{})
ents=ha.get('entities',{})
print(ents.get('solar_sensor',''))
PY
)

# Warn if HA configuration appears incomplete
if [ -z "$HA_URL" ] || [ -z "$HA_TOKEN" ]; then
    log_warn "Home Assistant URL or token not set in /opt/power-monitor/config.json"
    log_warn "Please populate 'homeassistant.url' and 'homeassistant.token' in config.json"
fi
if [ -z "$HA_POWER_ENTITY" ] || [ -z "$HA_SOLAR_ENTITY" ]; then
    log_warn "Home Assistant entity names 'power_sensor' or 'solar_sensor' are missing in config.json -> homeassistant.entities"
    log_warn "Example: \"entities\": { \"power_sensor\": \"sensor.live_power\", \"solar_sensor\": \"sensor.solar_today\" }"
fi

log_info "Testing Home Assistant connection (timeout: 10 seconds)..."

# Test HA API with timeout - if it fails, continue anyway
HTTP_CODE=$(timeout 10 curl -s -o /dev/null -w "%{http_code}" \
    --connect-timeout 5 \
    --max-time 10 \
    -H "Authorization: Bearer $HA_TOKEN" \
    -H "Content-Type: application/json" \
    "$HA_URL/api/" 2>/dev/null || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
    log_success "Home Assistant API: ✓ Authentication successful"
    
    # Test power entity
    log_info "Testing entity: $HA_POWER_ENTITY"
    ENTITY_RESPONSE=$(timeout 5 curl -s \
        --connect-timeout 3 \
        --max-time 5 \
        -H "Authorization: Bearer $HA_TOKEN" \
        -H "Content-Type: application/json" \
        "$HA_URL/api/states/$HA_POWER_ENTITY" 2>/dev/null || echo "{}")
    
    if echo "$ENTITY_RESPONSE" | grep -q "entity_id"; then
        CURRENT_VALUE=$(echo "$ENTITY_RESPONSE" | grep -o '"state":"[^"]*"' | cut -d'"' -f4)
        log_success "Power Entity: ✓ '$HA_POWER_ENTITY' (current: $CURRENT_VALUE)"
    else
        log_warn "Power Entity: ✗ '$HA_POWER_ENTITY' not found or no response"
    fi
    
    # Test solar entity
    log_info "Testing entity: $HA_SOLAR_ENTITY"
    SOLAR_RESPONSE=$(timeout 5 curl -s \
        --connect-timeout 3 \
        --max-time 5 \
        -H "Authorization: Bearer $HA_TOKEN" \
        -H "Content-Type: application/json" \
        "$HA_URL/api/states/$HA_SOLAR_ENTITY" 2>/dev/null || echo "{}")
    
    if echo "$SOLAR_RESPONSE" | grep -q "entity_id"; then
        SOLAR_VALUE=$(echo "$SOLAR_RESPONSE" | grep -o '"state":"[^"]*"' | cut -d'"' -f4)
        log_success "Solar Entity: ✓ '$HA_SOLAR_ENTITY' (current: $SOLAR_VALUE)"
    else
        log_warn "Solar Entity: ✗ '$HA_SOLAR_ENTITY' not found or no response"
    fi
elif [ "$HTTP_CODE" = "000" ]; then
    log_warn "Home Assistant API: ✗ Connection timeout or unreachable"
    log_warn "The device may not have network access to Home Assistant"
    log_warn "Continuing installation - fix config and restart collection manually"
else
    log_warn "Home Assistant API: ✗ Authentication failed (HTTP $HTTP_CODE)"
    log_warn "Please verify URL and token in config.json"
    log_warn "Continuing installation - fix config and restart collection manually"
fi

# =============================================================================
# STEP 6: Configure and Start Web Server
# =============================================================================
log_info "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
log_info "${BLUE}STEP 6: Configuring and Starting Web Server${NC}"
log_info "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

log_info "Creating lighttpd configuration..."
cat > /etc/lighttpd/lighttpd.conf << 'LIGHTTPD_EOF'
server.document-root = "/var/www/html"
server.port = 80
server.username = "lighttpd"
server.groupname = "lighttpd"
server.pid-file = "/var/run/lighttpd.pid"

# Enable required modules
server.modules = (
    "mod_access",
    "mod_cgi",
    "mod_accesslog"
)

# CGI configuration for admin interface
cgi.assign = ( ".cgi" => "/usr/bin/python3" )

# Access log
accesslog.filename = "/var/log/lighttpd/access.log"

# Error log
server.errorlog = "/var/log/lighttpd/error.log"

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

# Upload directory required by Alpine lighttpd
server.upload-dirs = ( "/var/tmp" )

# Security
server.tag = "webserver"

# Connection settings
server.max-connections = 256
server.max-request-size = 4096
LIGHTTPD_EOF

# Ensure /var/tmp exists for lighttpd upload-dirs
mkdir -p /var/tmp

# Verify lighttpd config syntax
log_info "Validating lighttpd configuration..."
if /usr/sbin/lighttpd -t -f /etc/lighttpd/lighttpd.conf > /dev/null 2>&1; then
    log_success "lighttpd configuration is valid"
else
    log_warn "lighttpd configuration validation failed"
    log_warn "Attempting to continue anyway..."
    /usr/sbin/lighttpd -t -f /etc/lighttpd/lighttpd.conf || true
fi

# Create lighttpd log directory
mkdir -p /var/log/lighttpd
chown lighttpd:lighttpd /var/log/lighttpd

log_success "lighttpd configured"

# Enable lighttpd to start on boot
log_info "Enabling lighttpd auto-start on boot..."
rc-update add lighttpd default
log_success "Auto-start enabled"

# Stop any existing lighttpd processes
log_info "Stopping any existing lighttpd processes..."
killall lighttpd 2>/dev/null || true
sleep 1

# Start lighttpd web server
log_info "Starting lighttpd..."
if rc-service lighttpd start > /dev/null 2>&1; then
    sleep 2
    if rc-service lighttpd status > /dev/null 2>&1 && ! rc-service lighttpd status 2>&1 | grep -q 'crashed'; then
        log_success "Web server started successfully"
    else
        log_error "Web server failed to start"
        log_info "Checking error logs..."
        tail -n 20 /var/log/lighttpd/error.log 2>/dev/null || echo "No error log available"
        log_info "Attempting direct start..."
        /usr/sbin/lighttpd -f /etc/lighttpd/lighttpd.conf 2>&1 || log_warn "Direct start also failed"
    fi
else
    log_error "Failed to start web server via rc-service"
    log_info "Check logs: tail /var/log/lighttpd/error.log"
fi

# =============================================================================
# STEP 7: Run Initial Data Collection
# =============================================================================
log_info "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
log_info "${BLUE}STEP 7: Running Initial Data Collection${NC}"
log_info "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

log_info "Collecting initial data (this may take a moment)..."
if /usr/bin/python3 /opt/power-monitor/collector.py >> /var/log/power-monitor-collector.log 2>&1; then
    log_success "Initial data collection completed"
else
    COLLECTOR_EXIT=$?
    log_warn "Initial collection had issues (exit code: $COLLECTOR_EXIT)"
    log_info "Last 30 lines of collector log:"
    tail -n 30 /var/log/power-monitor-collector.log || true
fi

log_info "Publishing dashboard..."
if /usr/bin/python3 /opt/power-monitor/publisher.py >> /var/log/power-monitor-publisher.log 2>&1; then
    log_success "Dashboard published"
else
    PUBLISHER_EXIT=$?
    log_warn "Initial publish had issues (exit code: $PUBLISHER_EXIT)"
    log_info "Last 30 lines of publisher log:"
    tail -n 30 /var/log/power-monitor-publisher.log || true
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
echo "  ${GREEN}Dashboard:      http://$DEVICE_IP/${NC}"
echo "  ${GREEN}Admin Panel:    http://$DEVICE_IP/admin.cgi${NC}"
echo ""
echo "  Admin credentials configured in config.json"
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
echo "  1. ${GREEN}Access dashboard: http://$DEVICE_IP/${NC}"
echo "  2. ${GREEN}Monitor logs to verify data collection${NC}"
echo "  3. ${GREEN}Data will sync to GitHub automatically every 10 minutes${NC}"
echo "  4. ${YELLOW}Edit config: vi /root/config.json (if changes needed)${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

log_info "Installation script completed successfully!"
echo ""
