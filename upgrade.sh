#!/bin/sh
# Selective GitHub upgrade script for Powerstats
#
# Usage: sudo sh upgrade.sh
#
# Features:
#  - Downloads selective files from GitHub (UI, backend, or full app)
#  - Always preserves config.json and data files (daily.json, etc.)
#  - Interactive prompts for GitHub repo and upgrade scope
#
# This script must run as root on the target device.

set -e

TIMESTAMP() {
  date +%Y%m%d_%H%M%S
}

ensure_root() {
  if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: This script must be run as root. Use: sudo sh upgrade.sh"
    exit 1
  fi
}

confirm() {
  # $1 = prompt
  while true; do
    printf "%s [y/n]: " "$1"
    read yn
    case "$yn" in
      [Yy]*) return 0 ;;
      [Nn]*) return 1 ;;
      *) echo "Please answer y or n." ;;
    esac
  done
}

backup_config() {
  # Backup config.json before any file operations
  CONFIG_SRC="/opt/power-monitor/config.json"
  BACKUP_DIR="/root/powerstats-backup-$(TIMESTAMP)"
  
  if [ -f "$CONFIG_SRC" ]; then
    echo "==> Backing up config.json to $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
    cp -a "$CONFIG_SRC" "$BACKUP_DIR/config.json.bak"
    echo "    Backup saved: $BACKUP_DIR/config.json.bak"
  else
    echo "==> No existing config.json found at $CONFIG_SRC (first install?)"
  fi
}

restore_config() {
  # Restore config.json after upgrade
  CONFIG_DST="/opt/power-monitor/config.json"
  BACKUP_DIR="/root/powerstats-backup-$(TIMESTAMP)"
  BACKUP_FILE="$BACKUP_DIR/config.json.bak"
  
  if [ -f "$BACKUP_FILE" ]; then
    echo "==> Restoring config.json from backup"
    cp -a "$BACKUP_FILE" "$CONFIG_DST"
    chmod 640 "$CONFIG_DST"
    chown root:root "$CONFIG_DST"
    echo "    Config restored: $CONFIG_DST"
  fi
}

prompt_github_info() {
  echo ""
  echo "==> GitHub Repository Information"
  printf "Enter GitHub username: "
  read GH_USER
  if [ -z "$GH_USER" ]; then
    echo "ERROR: Username cannot be empty"
    exit 1
  fi
  
  printf "Enter repository name: "
  read GH_REPO
  if [ -z "$GH_REPO" ]; then
    echo "ERROR: Repository name cannot be empty"
    exit 1
  fi
  
  printf "Enter branch name (default: main): "
  read GH_BRANCH
  if [ -z "$GH_BRANCH" ]; then
    GH_BRANCH="main"
  fi
  
  # Build GitHub raw content base URL
  GH_BASE_URL="https://raw.githubusercontent.com/${GH_USER}/${GH_REPO}/${GH_BRANCH}"
  
  echo ""
  echo "GitHub URL base: $GH_BASE_URL"
  echo ""
}

download_file() {
  # $1 = relative path in repo (e.g., "opt/power-monitor/collector.py")
  # $2 = destination absolute path (e.g., "/opt/power-monitor/collector.py")
  SRC_URL="${GH_BASE_URL}/${1}"
  DST_PATH="$2"
  
  echo "  Downloading: $1"
  
  # Create parent directory if needed
  DST_DIR=$(dirname "$DST_PATH")
  mkdir -p "$DST_DIR"
  
  # Download with curl (follow redirects, fail on error)
  if curl -fsSL "$SRC_URL" -o "$DST_PATH"; then
    echo "    -> $DST_PATH [OK]"
    return 0
  else
    echo "    -> $DST_PATH [FAILED]"
    return 1
  fi
}

upgrade_ui_files() {
  echo ""
  echo "==> Upgrading UI files from GitHub"
  
  # UI files in var/www/html (exclude JSON data files and config-related files)
  UI_FILES="
    var/www/html/index.html
    var/www/html/theme.css
    var/www/html/admin.cgi
    var/www/html/health.cgi
    var/www/html/debug.html
    var/www/html/test_health.html
    var/www/html/HELP_CONSOLIDATED.md
  "
  
  FAILED=0
  for file in $UI_FILES; do
    # Extract filename for destination (keep relative path structure)
    DST="/${file}"
    download_file "$file" "$DST" || FAILED=$((FAILED + 1))
  done
  
  if [ $FAILED -gt 0 ]; then
    echo "WARNING: $FAILED file(s) failed to download"
  else
    echo "==> UI files upgraded successfully"
  fi
  
  # Set permissions
  echo "==> Setting permissions on web files"
  chmod 755 /var/www/html/*.cgi 2>/dev/null || true
  chmod 644 /var/www/html/*.html /var/www/html/*.css /var/www/html/*.md 2>/dev/null || true
}

upgrade_backend_files() {
  echo ""
  echo "==> Upgrading backend Python files from GitHub"
  
  # Backend files in /opt/power-monitor (exclude config.json)
  BACKEND_FILES="
    opt/power-monitor/collector.py
    opt/power-monitor/publisher.py
    opt/power-monitor/aggregator.py
    opt/power-monitor/scheduler.py
    opt/power-monitor/health.py
    opt/power-monitor/github_sync.py
    opt/power-monitor/config_manager.py
    opt/power-monitor/utils.py
  "
  
  FAILED=0
  for file in $BACKEND_FILES; do
    DST="/${file}"
    download_file "$file" "$DST" || FAILED=$((FAILED + 1))
  done
  
  if [ $FAILED -gt 0 ]; then
    echo "WARNING: $FAILED file(s) failed to download"
  else
    echo "==> Backend files upgraded successfully"
  fi
  
  # Set permissions
  echo "==> Setting permissions on backend files"
  chmod 755 /opt/power-monitor/*.py 2>/dev/null || true
}

upgrade_app_full() {
  echo ""
  echo "==> Performing FULL APP upgrade (UI + Backend)"
  echo "    Note: config.json and data files will be preserved"
  
  backup_config
  upgrade_ui_files
  upgrade_backend_files
  restore_config
  
  echo ""
  echo "==> Full app upgrade completed"
  echo "    - UI files updated"
  echo "    - Backend files updated"
  echo "    - config.json preserved"
  echo "    - Data files (*.json) preserved"
}

show_upgrade_menu() {
  echo ""
  echo "=========================================="
  echo "  Powerstats GitHub Upgrade Tool"
  echo "=========================================="
  echo ""
  echo "Select upgrade scope:"
  echo "  1) Upgrade App (Full: UI + Backend)"
  echo "  2) Upgrade UI only"
  echo "  3) Upgrade Backend only"
  echo "  4) Exit (no changes)"
  echo ""
  printf "Choice [1-4]: "
  read choice
  
  case "$choice" in
    1)
      if confirm "Proceed with FULL upgrade (UI + Backend)?"; then
        upgrade_app_full
      else
        echo "Upgrade cancelled"
      fi
      ;;
    2)
      if confirm "Proceed with UI-only upgrade?"; then
        backup_config
        upgrade_ui_files
        restore_config
      else
        echo "Upgrade cancelled"
      fi
      ;;
    3)
      if confirm "Proceed with Backend-only upgrade?"; then
        backup_config
        upgrade_backend_files
        restore_config
      else
        echo "Upgrade cancelled"
      fi
      ;;
    4)
      echo "Exiting. No changes made."
      exit 0
      ;;
    *)
      echo "Invalid choice. Exiting."
      exit 1
      ;;
  esac
}

restart_services() {
  echo ""
  if confirm "Restart power-monitor services now?"; then
    echo "==> Restarting services..."
    
    # Stop services gracefully
    pkill -f "python.*collector.py" 2>/dev/null || true
    pkill -f "python.*publisher.py" 2>/dev/null || true
    sleep 2
    
    # Restart via cron (cron will re-launch on next scheduled interval)
    # Or manually restart if using systemd:
    if command -v systemctl >/dev/null 2>&1; then
      systemctl restart power-monitor-scheduler 2>/dev/null || echo "  (systemd service not found, will restart via cron)"
    fi
    
    echo "==> Services restart initiated"
    echo "    Note: Collector/publisher will restart at next cron interval"
  fi
}

main() {
  ensure_root
  
  echo ""
  echo "=========================================="
  echo "  Powerstats Selective GitHub Upgrade"
  echo "=========================================="
  echo ""
  echo "This script will:"
  echo "  - Download files from your GitHub repository"
  echo "  - PRESERVE config.json (automatic backup/restore)"
  echo "  - PRESERVE all data files (*.json)"
  echo "  - Allow selective upgrade (full/UI/backend)"
  echo ""
  
  if ! confirm "Continue?"; then
    echo "Upgrade cancelled"
    exit 0
  fi
  
  # Get GitHub repo info
  prompt_github_info
  
  # Show upgrade options
  show_upgrade_menu
  
  # Optionally restart services
  restart_services
  
  echo ""
  echo "=========================================="
  echo "  Upgrade Complete!"
  echo "=========================================="
  echo ""
  echo "Next steps:"
  echo "  1. Verify config: cat /opt/power-monitor/config.json"
  echo "  2. Check web UI: http://$(hostname -I | awk '{print $1}')/"
  echo "  3. Monitor logs: tail -f /var/log/syslog | grep power"
  echo ""
}

main "$@"
