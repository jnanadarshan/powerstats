#!/bin/sh
# UI upgrade helper
#
# Usage: sudo sh deployment/ui-upgrade.sh
#
# Steps:
# 1) Ask for GitHub username (repo assumed to be <username>/powerstats)
# 2) Clone only UI paths from that repo into a temporary dir (sparse checkout)
# 3) Remove current UI files inside this local powerstats repo (./var/www/html and HELP_CONSOLIDATED.md)
# 4) Remove UI files from the deployed device web root (from config or default /var/www/html)
# 5) Copy the new UI files from the local powerstats folder to the device web root

set -eu

TIMESTAMP() { date +%Y%m%d%H%M%S; }

ensure_root() {
  if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root. Use: sudo sh deployment/ui-upgrade.sh"
    exit 1
  fi
}

read_input() {
  # $1 prompt, $2 default
  if [ -n "${2:-}" ]; then
    printf "%s (default: %s): " "$1" "$2"
  else
    printf "%s: " "$1"
  fi
  read ans
  if [ -z "$ans" ]; then
    echo "$2"
  else
    echo "$ans"
  fi
}

get_web_root() {
  # Try to read /opt/power-monitor/config.json paths.web_root; fall back to /var/www/html
  if [ -f "/opt/power-monitor/config.json" ]; then
    if command -v python3 >/dev/null 2>&1; then
      python3 - <<PY
import json
try:
    cfg=json.load(open('/opt/power-monitor/config.json'))
    p=cfg.get('paths',{}).get('web_root','/var/www/html')
    print(p)
except Exception:
    print('/var/www/html')
PY
      return 0
    fi
  fi
  printf '/var/www/html\n'
}

cleanup() {
  if [ -n "${TMPDIR:-}" ] && [ -d "$TMPDIR" ]; then
    rm -rf "$TMPDIR"
  fi
}

main() {
  ensure_root

  echo "Powerstats UI upgrade helper"

  USERNAME=$(read_input "Enter GitHub username that owns the 'powerstats' repo" "")
  if [ -z "$USERNAME" ]; then
    echo "No username provided. Aborting."; exit 1
  fi

  REPO_URL="https://github.com/${USERNAME}/powerstats.git"
  echo "Will fetch UI files from: $REPO_URL"

  if ! command -v git >/dev/null 2>&1; then
    echo "git is required but not installed. Please install git and re-run."; exit 1
  fi

  TMPDIR="/tmp/powerstats-ui-${TIMESTAMP()}"
  mkdir -p "$TMPDIR"

  echo "Cloning sparse copy into $TMPDIR (this will be shallow)..."
  if ! git clone --depth=1 --filter=blob:none --sparse "$REPO_URL" "$TMPDIR"; then
    echo "Failed to clone $REPO_URL"; cleanup; exit 1
  fi

  cd "$TMPDIR"
  # fetch only UI paths: var/www/html and HELP_CONSOLIDATED.md (if present)
  git sparse-checkout init --cone >/dev/null 2>&1 || true
  git sparse-checkout set var/www/html HELP_CONSOLIDATED.md >/dev/null 2>&1 || true

  echo "Sparse checkout complete. Available paths:"
  ls -la var/www/html 2>/dev/null || true
  [ -f HELP_CONSOLIDATED.md ] && echo "HELP_CONSOLIDATED.md available"

  # Remove current UI files inside this local powerstats repo (the repo where this script is run from)
  REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  echo "Repository root detected at: $REPO_ROOT"

  LOCAL_UI_DIR="$REPO_ROOT/var/www/html"
  LOCAL_HELP="$REPO_ROOT/HELP_CONSOLIDATED.md"

  printf "About to remove current UI files inside the repository at %s\n" "$LOCAL_UI_DIR"
  if [ -d "$LOCAL_UI_DIR" ]; then
    if read -r -p "Confirm removal of files under $LOCAL_UI_DIR ? [y/N]: " yn && echo "$yn" | grep -iq "^y"; then
      rm -rf "$LOCAL_UI_DIR"/* || true
      echo "Removed contents of $LOCAL_UI_DIR"
    else
      echo "Skipping removal of local UI files.";
    fi
  else
    echo "Local UI dir not found: $LOCAL_UI_DIR — creating it."; mkdir -p "$LOCAL_UI_DIR"
  fi

  if [ -f "$LOCAL_HELP" ]; then
    if read -r -p "Remove local $LOCAL_HELP ? [y/N]: " yn && echo "$yn" | grep -iq "^y"; then
      rm -f "$LOCAL_HELP"; echo "Removed $LOCAL_HELP";
    fi
  fi

  # Copy new UI files from the freshly cloned repo into the local repository
  echo "Copying new UI files into local repository..."
  if [ -d "$TMPDIR/var/www/html" ]; then
    mkdir -p "$LOCAL_UI_DIR"
    rsync -a --delete "$TMPDIR/var/www/html/" "$LOCAL_UI_DIR/"
    echo "Copied var/www/html -> $LOCAL_UI_DIR"
  else
    echo "No var/www/html in upstream repo. Nothing to copy.";
  fi
  if [ -f "$TMPDIR/HELP_CONSOLIDATED.md" ]; then
    cp -a "$TMPDIR/HELP_CONSOLIDATED.md" "$LOCAL_HELP"
    echo "Copied HELP_CONSOLIDATED.md -> $LOCAL_HELP"
  fi

  # Determine deployed web root on device (use config or fallback)
  TARGET_WEB_ROOT=$(get_web_root)
  echo "Target web root determined as: $TARGET_WEB_ROOT"

  if [ ! -d "$TARGET_WEB_ROOT" ]; then
    echo "Target web root does not exist. Creating: $TARGET_WEB_ROOT"; mkdir -p "$TARGET_WEB_ROOT"
  fi

  # Confirm removal of deployed UI files
  if read -r -p "Remove existing UI files from device web root $TARGET_WEB_ROOT ? [y/N]: " yn && echo "$yn" | grep -iq "^y"; then
    rm -rf "$TARGET_WEB_ROOT"/* || true
    echo "Removed deployed UI files from $TARGET_WEB_ROOT"
  else
    echo "Skipping removal of deployed UI files. Aborting deploy step.";
    cleanup
    exit 0
  fi

  # Copy new UI files from local repo to device target
  echo "Copying updated UI files to device web root..."
  rsync -a --delete "$LOCAL_UI_DIR/" "$TARGET_WEB_ROOT/"
  # copy HELP file if present
  [ -f "$LOCAL_HELP" ] && cp -a "$LOCAL_HELP" "$TARGET_WEB_ROOT/HELP_CONSOLIDATED.md"

  echo "UI files deployed to $TARGET_WEB_ROOT"

  cleanup
  echo "Temporary files removed. Upgrade complete."
}

main "$@"
