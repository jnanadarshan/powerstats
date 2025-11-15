#!/usr/bin/env zsh
# backup_restore.sh
# Interactive helper to backup and restore Powerstats config and JSON data files.
# Places: repo root `config.json` and data files under `var/www/html` (daily.json, weekly.json, monthly.json, yearly.json)

set -euo pipefail

timestamp() {
  date +"%Y%m%d-%H%M%S"
}

read_answer() {
  # prompt with default
  local prompt="$1"; shift
  local default="$1"; shift
  local ans
  echo -n "$prompt [$default]: "
  read ans
  if [[ -z "$ans" ]]; then
    echo "$default"
  else
    echo "$ans"
  fi
}

confirm() {
  local msg="$1"; shift
  echo -n "$msg (y/N): "
  read yn
  case "$yn" in
    [Yy]|[Yy][Ee][Ss]) return 0 ;;
    *) return 1 ;;
  esac
}

# default file list (relative to repo root / source dir)
FILES=(
  "config.json"
  "var/www/html/daily.json"
  "var/www/html/weekly.json"
  "var/www/html/monthly.json"
  "var/www/html/yearly.json"
)

print_header() {
  echo "========================================"
  echo " Powerstats Backup & Restore"
  echo "========================================"
}

list_files_found() {
  local src_dir="$1"
  for f in "${FILES[@]}"; do
    if [[ -f "$src_dir/$f" ]]; then
      echo "FOUND: $f"
    else
      echo "MISSING: $f"
    fi
  done
}

perform_backup() {
  local src_dir dest_dir dest_sub ts
  src_dir="$1"
  dest_dir="$2"
  ts=$(timestamp)
  dest_sub="$dest_dir/powerstats-backup-$ts"
  echo "Creating backup folder: $dest_sub"
  mkdir -p -- "$dest_sub"
  echo "Backing up files from: $src_dir"
  local any=0
  local manifest="$dest_sub/manifest.txt"
  echo "Backup created: $ts" > "$manifest"
  echo "Source: $src_dir" >> "$manifest"
  echo "Files:" >> "$manifest"
  for f in "${FILES[@]}"; do
    if [[ -f "$src_dir/$f" ]]; then
      mkdir -p -- "$(dirname "$dest_sub/$f")"
      cp -a -- "$src_dir/$f" "$dest_sub/$f"
      echo "$f -> $dest_sub/$f" >> "$manifest"
      echo " - copied: $f"
      any=1
    else
      echo " - missing: $f (skipped)"
      echo "MISSING: $f" >> "$manifest"
    fi
  done
  if [[ $any -eq 0 ]]; then
    echo "No files were copied. Removing empty backup folder."
    rm -rf -- "$dest_sub"
    return 1
  fi
  echo "Backup complete. Manifest at: $manifest"
  return 0
}

choose_backup_folder() {
  local base
  base=$(read_answer "Enter destination folder for backups (absolute path)" "$HOME")
  mkdir -p -- "$base"
  echo "$base"
}

list_available_backups() {
  local base="$1"
  if [[ ! -d "$base" ]]; then
    echo "No such folder: $base"
    return 1
  fi
  echo "Available backups in $base:"
  ls -1d "$base"/powerstats-backup-* 2>/dev/null || echo " (none)"
}

perform_restore() {
  local backup_dir target_dir
  backup_dir="$1"
  target_dir="$2"
  if [[ ! -d "$backup_dir" ]]; then
    echo "Backup folder not found: $backup_dir"
    return 1
  fi
  echo "Restoring from $backup_dir to $target_dir"
  # for safety, list files present in backup
  local available_files
  available_files=($(find "$backup_dir" -type f -maxdepth 4 -printf "%P\n" 2>/dev/null))
  if [[ ${#available_files[@]} -eq 0 ]]; then
    echo "No files found in backup to restore."
    return 1
  fi
  echo "Files in backup:"
  for f in "${available_files[@]}"; do
    echo " - $f"
  done

  if ! confirm "Proceed to restore all files (will overwrite target files)?"; then
    echo "Restore aborted by user."
    return 2
  fi

  # copy files (preserve attributes)
  for f in "${available_files[@]}"; do
    local src="$backup_dir/$f"
    # avoid restoring manifest
    if [[ "$f" == "manifest.txt" ]]; then continue; fi
    local dest="$target_dir/$f"
    mkdir -p -- "$(dirname "$dest")"
    cp -a -- "$src" "$dest"
    echo "Restored: $dest"
  done
  echo "Restore complete."
  return 0
}

main_menu() {
  while true; do
    print_header
    echo "Choose an option:"
    echo "  1) Backup config and data files"
    echo "  2) Restore from a backup"
    echo "  3) List backups in a folder"
    echo "  4) Exit"
    echo -n "Select [1-4]: "
    read opt
    case "$opt" in
      1)
        echo "Backup selected."
        src=$(read_answer "Enter the Powerstats repo folder (source)" "$(pwd)")
        echo "Checking for files in: $src"
        list_files_found "$src"
        dest=$(choose_backup_folder)
        if confirm "Start backup now to $dest?"; then
          if perform_backup "$src" "$dest"; then
            echo "Backup saved to $dest"
          else
            echo "Backup failed or nothing copied."
          fi
        else
          echo "Backup cancelled."
        fi
        read -p "Press Enter to continue..."
        ;;
      2)
        echo "Restore selected."
        base=$(read_answer "Enter folder where backups are located" "$HOME")
        list_available_backups "$base"
        bdir=$(read_answer "Enter the exact backup directory to restore (full path)" "")
        if [[ -z "$bdir" ]]; then
          echo "No backup chosen; aborting."
        else
          tgt=$(read_answer "Enter target folder to restore into (your Powerstats repo folder)" "$(pwd)")
          if confirm "Restore from $bdir into $tgt ?"; then
            perform_restore "$bdir" "$tgt"
          else
            echo "Restore cancelled."
          fi
        fi
        read -p "Press Enter to continue..."
        ;;
      3)
        base=$(read_answer "Enter folder where backups are located" "$HOME")
        list_available_backups "$base"
        read -p "Press Enter to continue..."
        ;;
      4)
        echo "Goodbye."
        exit 0
        ;;
      *) echo "Invalid choice";;
    esac
  done
}

# If script is run directly, start menu. If sourced, export functions for reuse.
if [[ "$0" == "$BASH_SOURCE" || "$0" == "$0" ]]; then
  main_menu
fi
