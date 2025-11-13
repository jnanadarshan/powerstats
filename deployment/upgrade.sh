#!/bin/sh
# Interactive upgrade/backup/restore helper for Powerstats
#
# Usage: sudo sh deployment/upgrade.sh
#
# Features:
#  - Backup: copy /opt/power-monitor/config.json and selected JSON data files from web root to a timestamped backup directory
#  - Restore: restore config.json and/or JSON data files from a chosen backup directory
#
# This script is designed to run on-device during upgrade/maintenance.

set -e

TIMESTAMP() {
  date +%Y%m%d%H%M%S
}

ensure_root() {
  if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root. Use sudo sh upgrade.sh"
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

prompt_dir() {
  # $1 = prompt
  printf "%s (default: %s): " "$1" "$DEFAULT_BACKUP_DIR"
  read answer
  if [ -z "$answer" ]; then
    echo "$DEFAULT_BACKUP_DIR"
  else
    echo "$answer"
  fi
}

backup_config() {
  SRC_CONFIG="/opt/power-monitor/config.json"
  if [ ! -f "$SRC_CONFIG" ]; then
    echo "No config found at $SRC_CONFIG"
    return 1
  fi
  echo "Copying config: $SRC_CONFIG -> $DEST_DIR/"
  cp -a "$SRC_CONFIG" "$DEST_DIR/" || return 1
  echo "Config backed up as $DEST_DIR/config.json"
}

backup_data_files() {
  WEB_ROOT="/var/www/html"
  # data files are JSONs: daily.json, weekly.json, monthly.json, yearly.json (but take any .json in web root)
  echo "Copying JSON data files from $WEB_ROOT to $DEST_DIR/"
  if [ ! -d "$WEB_ROOT" ]; then
    echo "Web root $WEB_ROOT not found"
    return 1
  fi
  rsync -a --include='*.json' --exclude='*' "$WEB_ROOT/" "$DEST_DIR/" || return 1
  echo "Data files copied to $DEST_DIR/"
}

list_backups() {
  ls -1d /root/powerstats-backup-* 2>/dev/null || true
}

choose_backup_dir() {
  echo "Available backups:"; list_backups
  printf "Enter backup directory to restore from (full path): "
  read BD
  if [ -z "$BD" ]; then
    echo "No directory specified. Aborting."; return 1
  fi
  if [ ! -d "$BD" ]; then
    echo "Directory $BD does not exist."; return 1
  fi
  RESTORE_DIR="$BD"
  return 0
}

restore_config() {
  SRC="$RESTORE_DIR/config.json"
  DST="/opt/power-monitor/config.json"
  if [ ! -f "$SRC" ]; then
    echo "No config.json in $RESTORE_DIR"
    return 1
  fi
  echo "Removing existing $DST (if present) and restoring $SRC -> $DST"
  rm -f "$DST" || true
  cp -a "$SRC" "$DST" || return 1
  chown root:root "$DST" || true
  chmod 640 "$DST" || true
  echo "Restored config.json"
}

restore_data_files() {
  WEB_ROOT="/var/www/html"
  if [ ! -d "$RESTORE_DIR" ]; then
    echo "Restore dir $RESTORE_DIR not found"
    return 1
  fi
  echo "Copying JSON files from $RESTORE_DIR -> $WEB_ROOT"
  mkdir -p "$WEB_ROOT"
  rsync -a --include='*.json' --exclude='*' "$RESTORE_DIR/" "$WEB_ROOT/" || return 1
  echo "Data files restored to $WEB_ROOT"
}

main() {
  ensure_root

  echo "Powerstats Upgrade Helper"
  echo "Select an action:"
  echo "  1) Backup"
  echo "  2) Restore"
  echo "  3) Exit"
  printf "Choice: "
  read choice
  case "$choice" in
    1)
      # Backup flow
      DEFAULT_BACKUP_DIR="/root/powerstats-backup-$(TIMESTAMP)"
      DEST_DIR=$(prompt_dir "Enter backup destination directory")
      mkdir -p "$DEST_DIR" || { echo "Failed to create $DEST_DIR"; exit 1; }
      echo "Backup destination: $DEST_DIR"

      if confirm "Backup config.json (from /opt/power-monitor/config.json) to $DEST_DIR?"; then
        backup_config || echo "config backup failed"
      fi

      if confirm "Backup JSON data files from /var/www/html to $DEST_DIR?"; then
        backup_data_files || echo "data files backup failed"
      fi

      echo "Backup completed: $DEST_DIR"
      ;;
    2)
      # Restore flow
      if ! choose_backup_dir; then exit 1; fi

      if confirm "Restore config.json from $RESTORE_DIR/config.json? This will overwrite /opt/power-monitor/config.json"; then
        restore_config || echo "config restore failed"
      fi

      if confirm "Restore JSON data files from $RESTORE_DIR to /var/www/html (this will overwrite existing files)?"; then
        restore_data_files || echo "data files restore failed"
      fi

      echo "Restore completed from: $RESTORE_DIR"
      ;;
    *)
      echo "Exiting. No action taken."; exit 0 ;;
  esac
}

main "$@"
