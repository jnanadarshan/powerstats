#!/usr/bin/env sh
# Safe git sync helper for local environment
# Usage: cd /path/to/repo && sh deployment/git_sync.sh

set -e

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_BRANCH="backup-local-$TIMESTAMP"
CURBR=$(git rev-parse --abbrev-ref HEAD)

echo "[git_sync] Current branch: $CURBR"
echo "[git_sync] Creating backup branch: $BACKUP_BRANCH"

# Commit local changes (if any)
if [ -n "$(git status --porcelain)" ]; then
  echo "[git_sync] Found local changes — committing as WIP"
  git add -A
  git commit -m "WIP: save local changes before sync ($TIMESTAMP)" || echo "[git_sync] nothing to commit"
else
  echo "[git_sync] No uncommitted changes"
fi

# Force-create backup branch at HEAD and push
git branch -f "$BACKUP_BRANCH"
echo "[git_sync] Pushing backup branch to origin/$BACKUP_BRANCH"
git push -u origin "$BACKUP_BRANCH" || echo "[git_sync] warning: failed to push backup branch"

# Fetch remote and try to replace daily.json with remote copy
echo "[git_sync] Fetching origin"
git fetch origin --quiet

if git show origin/main:daily.json >/dev/null 2>&1; then
  echo "[git_sync] Remote daily.json found — replacing local copy from origin/main"
  git checkout origin/main -- daily.json || git show origin/main:daily.json > daily.json
  echo "[git_sync] Replaced local daily.json with remote copy"
else
  echo "[git_sync] No daily.json present in origin/main — skipping replace"
fi

# Stop tracking daily.json (keep local file)
if git ls-files --error-unmatch daily.json >/dev/null 2>&1; then
  echo "[git_sync] daily.json is tracked — removing from index (keeps local file)"
  git rm --cached daily.json || true
else
  echo "[git_sync] daily.json not currently tracked"
fi

# Ensure .gitignore has daily.json
if ! grep -qx "daily.json" .gitignore 2>/dev/null; then
  echo "[git_sync] Adding daily.json to .gitignore"
  printf '\n# Root dashboard data that changes frequently; keep local copy but do not track\ndaily.json\n' >> .gitignore
  git add .gitignore
fi

# Commit cleanup changes and push
if [ -n "$(git status --porcelain)" ]; then
  echo "[git_sync] Committing untrack/.gitignore changes"
  git add -A
  git commit -m "chore: untrack daily.json and sync remote copy ($TIMESTAMP)" || echo "[git_sync] nothing to commit"
  echo "[git_sync] Pushing changes to origin/main"
  if git push origin "$CURBR":main; then
    echo "[git_sync] Pushed changes to origin/main"
  else
    echo "[git_sync] Push to origin/main failed — pushing current branch to remote"
    git push -u origin "$CURBR"
  fi
else
  echo "[git_sync] No repository changes to commit"
fi

echo "[git_sync] Done. If you want this automated, run this script from the repo root."
