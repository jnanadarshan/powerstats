#!/bin/sh
# backup_restore.sh
# Pull live config and data files from installed system into local repo folder.
# This prepares the repo for reinstallation with existing data.
#
# Usage: Run from inside the cloned powerstats repo folder
#   sh backup_restore.sh
#
# This will copy files FROM the device installation TO the local repo:
#   /opt/power-monitor/config.json       -> ./config.json
#   /var/www/html/thresholds.json        -> ./var/www/html/thresholds.json
#   /var/www/html/daily.json             -> ./var/www/html/daily.json
#   /var/www/html/weekly.json            -> ./var/www/html/weekly.json
#   /var/www/html/monthly.json           -> ./var/www/html/monthly.json
#   /var/www/html/yearly.json            -> ./var/www/html/yearly.json
#
# When you later run install.sh, these files will be copied to the device,
# automatically restoring your configuration and data.

set -eu

timestamp() {
  date +"%Y%m%d-%H%M%S"
}

confirm() {
  msg="$1"; shift
  printf "%s (y/N): " "$msg"
  read yn
  case "$yn" in
    [Yy]|[Yy][Ee][Ss]) return 0 ;;
    *) return 1 ;;
  esac
}

print_header() {
  echo "========================================"
  echo " Powerstats Backup from Device"
  echo "========================================"
}

# Map of installed files -> repo locations
declare -A FILE_MAP
FILE_MAP["/opt/power-monitor/config.json"]="config.json"
FILE_MAP["/var/www/html/thresholds.json"]="var/www/html/thresholds.json"
FILE_MAP["/var/www/html/daily.json"]="var/www/html/daily.json"
FILE_MAP["/var/www/html/weekly.json"]="var/www/html/weekly.json"
FILE_MAP["/var/www/html/monthly.json"]="var/www/html/monthly.json"
FILE_MAP["/var/www/html/yearly.json"]="var/www/html/yearly.json"

check_repo_folder() {
  # Verify we're in a powerstats repo folder
  if [ ! -f "install.sh" ] || [ ! -d "opt" ] || [ ! -d "var" ]; then
    echo "ERROR: This doesn't look like a powerstats repository folder."
    echo "Please run this script from inside your cloned powerstats folder."
    return 1
  fi
  return 0
}

check_installation() {
  # Check if powerstats is installed on the device
  if [ ! -d "/opt/power-monitor" ] || [ ! -f "/opt/power-monitor/config.json" ]; then
    echo "ERROR: Powerstats installation not found on this device."
    echo "Cannot find /opt/power-monitor/config.json"
    echo ""
    echo "This script pulls files FROM an installed system."
    echo "If you need to reinstall, just run: sh install.sh"
    return 1
  fi
  return 0
}

list_available_files() {
  echo ""
  echo "Checking installed files on device:"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  local found_count=0
  local missing_count=0
  
  for src_file in "${!FILE_MAP[@]}"; do
    if [ -f "$src_file" ]; then
      echo "  ✓ FOUND: $src_file"
      found_count=$((found_count + 1))
    else
      echo "  ✗ MISSING: $src_file"
      missing_count=$((missing_count + 1))
    fi
  done
  
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Found: $found_count | Missing: $missing_count"
  echo ""
  
  if [ "$found_count" -eq 0 ]; then
    echo "ERROR: No files found to backup."
    return 1
  fi
  return 0
}

perform_backup() {
  local repo_dir="$(pwd)"
  local ts=$(timestamp)
  local backup_manifest="${repo_dir}/backup-manifest-${ts}.txt"
  local copied_count=0
  local skipped_count=0
  
  echo ""
  echo "Backing up files from device to repo..."
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  
  # Create backup manifest
  echo "Backup performed: $(date)" > "$backup_manifest"
  echo "Repository: $repo_dir" >> "$backup_manifest"
  echo "" >> "$backup_manifest"
  echo "Files copied:" >> "$backup_manifest"
  
  for src_file in "${!FILE_MAP[@]}"; do
    local dest_file="${repo_dir}/${FILE_MAP[$src_file]}"
    
    if [ -f "$src_file" ]; then
      # Create destination directory if needed
      mkdir -p "$(dirname "$dest_file")"
      
      # Create backup of existing repo file if it exists
      if [ -f "$dest_file" ]; then
        cp -p "$dest_file" "${dest_file}.bak.${ts}" 2>/dev/null || true
        echo "  → Backed up existing: ${FILE_MAP[$src_file]}.bak.${ts}"
      fi
      
      # Copy from device to repo
      if cp -p "$src_file" "$dest_file" 2>/dev/null; then
        echo "  ✓ Copied: $src_file"
        echo "           → ${FILE_MAP[$src_file]}"
        echo "$src_file -> ${FILE_MAP[$src_file]}" >> "$backup_manifest"
        copied_count=$((copied_count + 1))
      else
        echo "  ✗ Failed: $src_file (permission denied?)"
        echo "FAILED: $src_file" >> "$backup_manifest"
        skipped_count=$((skipped_count + 1))
      fi
    else
      echo "  - Skipped: $src_file (not found)"
      echo "MISSING: $src_file" >> "$backup_manifest"
      skipped_count=$((skipped_count + 1))
    fi
  done
  
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Backup complete!"
  echo "  Copied: $copied_count files"
  echo "  Skipped: $skipped_count files"
  echo "  Manifest: backup-manifest-${ts}.txt"
  echo ""
  
  if [ "$copied_count" -gt 0 ]; then
    echo "✓ Your repo now contains the live config and data files."
    echo "✓ When you run 'sh install.sh', these files will be restored."
    echo ""
    return 0
  else
    echo "✗ No files were copied. Check permissions."
    return 1
  fi
}

# Main execution
main() {
  print_header
  echo ""
  echo "This script copies live config and data files from your"
  echo "installed Powerstats system into this repository folder."
  echo ""
  echo "After backup, when you run install.sh, your configuration"
  echo "and historical data will be automatically restored."
  echo ""
  
  # Check if we're in the right place
  if ! check_repo_folder; then
    exit 1
  fi
  
  echo "✓ Running from powerstats repository folder"
  
  # Check if installation exists
  if ! check_installation; then
    exit 1
  fi
  
  echo "✓ Found powerstats installation on device"
  
  # List available files
  if ! list_available_files; then
    exit 1
  fi
  
  # Confirm
  if ! confirm "Pull these files from device into repo folder?"; then
    echo "Backup cancelled."
    exit 0
  fi
  
  # Perform backup
  if perform_backup; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Next steps:"
    echo "  1. (Optional) Commit changes: git add . && git commit -m 'Backup data'"
    echo "  2. To reinstall: sh uninstall.sh && sh install.sh"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 0
  else
    echo "Backup failed."
    exit 1
  fi
}

# Run main function
main
