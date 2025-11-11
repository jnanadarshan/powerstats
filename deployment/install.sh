#!/bin/sh
# Installation script for Luckfox Pico Max (Alpine Linux)
# Run this script as root

set -e

echo "================================================"
echo "Power Monitoring System Installation"
echo "================================================"
echo ""

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "Error: This script must be run as root"
    exit 1
fi

# Update package repositories
echo "Updating package repositories..."
apk update

# Install required packages
echo "Installing required packages..."
apk add lighttpd python3 py3-pip

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install --no-cache-dir requests jinja2

# Create directory structure
echo "Creating directory structure..."
mkdir -p /opt/power-monitor/templates
mkdir -p /var/www/html
mkdir -p /var/log
mkdir -p /etc

# Copy files (assumes script is run from deployment directory)
echo "Copying application files..."

# Copy main scripts
cp ../opt/power-monitor/collector.py /opt/power-monitor/
cp ../opt/power-monitor/publisher.py /opt/power-monitor/
cp ../opt/power-monitor/config_manager.py /opt/power-monitor/
cp ../opt/power-monitor/config.example.json /opt/power-monitor/

# Copy templates
cp ../opt/power-monitor/templates/dashboard.html /opt/power-monitor/templates/

# Copy web files
cp ../var/www/html/admin.cgi /var/www/html/
chmod +x /var/www/html/admin.cgi

# Set permissions
echo "Setting permissions..."
chmod +x /opt/power-monitor/collector.py
chmod +x /opt/power-monitor/publisher.py
chmod 755 /opt/power-monitor
chmod 755 /var/www/html
chmod 644 /opt/power-monitor/templates/dashboard.html

# Configure lighttpd
echo "Configuring lighttpd..."
cat > /etc/lighttpd/lighttpd.conf << 'EOF'
server.document-root = "/var/www/html"
server.port = 80
server.username = "lighttpd"
server.groupname = "lighttpd"

# Enable CGI for admin interface
server.modules = (
    "mod_access",
    "mod_cgi",
    "mod_accesslog"
)

# CGI configuration
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
    ".gif" => "image/gif"
)

# Index files
index-file.names = ( "index.html" )
EOF

# Create log directory for lighttpd
mkdir -p /var/log/lighttpd
chown lighttpd:lighttpd /var/log/lighttpd

# Initialize state file
echo "Initializing state file..."
echo "maintenance_mode=false" > /etc/monitor.conf

# Create config file if it doesn't exist
if [ ! -f /opt/power-monitor/config.json ]; then
    echo ""
    echo "================================================"
    echo "IMPORTANT: Configuration Required"
    echo "================================================"
    echo "Please create /opt/power-monitor/config.json"
    echo "based on config.example.json with your settings:"
    echo ""
    echo "1. Home Assistant URL and token"
    echo "2. GitHub repository details and token"
    echo "3. Admin credentials"
    echo ""
    echo "Example:"
    echo "  vi /opt/power-monitor/config.json"
    echo ""
fi

# Setup cron job
echo "Setting up cron job..."
(crontab -l 2>/dev/null || true; echo "*/10 * * * * /usr/bin/python3 /opt/power-monitor/collector.py && /usr/bin/python3 /opt/power-monitor/publisher.py") | crontab -

# Enable and start lighttpd
echo "Starting lighttpd..."
rc-update add lighttpd default
rc-service lighttpd start

echo ""
echo "================================================"
echo "Installation Complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Create /opt/power-monitor/config.json (see config.example.json)"
echo "2. Test collector: /usr/bin/python3 /opt/power-monitor/collector.py"
echo "3. Test publisher: /usr/bin/python3 /opt/power-monitor/publisher.py"
echo "4. Access dashboard: http://$(hostname -i)/"
echo "5. Access admin panel: http://$(hostname -i)/admin.cgi"
echo ""
echo "Logs:"
echo "  - Collector: /var/log/power-monitor-collector.log"
echo "  - Publisher: /var/log/power-monitor-publisher.log"
echo "  - Web server: /var/log/lighttpd/access.log"
echo ""
