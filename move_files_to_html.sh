#!/bin/bash
# Script to move JSON and HTML files from repo root to var/www/html folder in GitHub
# This corrects the publisher location issue where files were published to root instead of var/www/html

set -e

echo "Moving files from root to var/www/html in GitHub repository..."
echo "This script uses the GitHub API to move files in the remote repository."
echo ""

# Read GitHub config from config.json
CONFIG_FILE="config.json"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: config.json not found"
    exit 1
fi

# Extract GitHub config using Python
GITHUB_INFO=$(python3 - <<'PY'
import json
import sys

try:
    with open('config.json') as f:
        cfg = json.load(f)
    
    gh = cfg.get('github', {})
    token = gh.get('token', '')
    repo = gh.get('repo', '')
    branch = gh.get('branch', 'main')
    
    if not token or not repo:
        print("ERROR: GitHub token or repo not configured", file=sys.stderr)
        sys.exit(1)
    
    # Split repo into owner/name
    parts = repo.split('/')
    if len(parts) != 2:
        print("ERROR: Invalid repo format. Expected: owner/repo", file=sys.stderr)
        sys.exit(1)
    
    print(f"{token}|{parts[0]}|{parts[1]}|{branch}")
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
PY
)

if [ $? -ne 0 ]; then
    echo "Failed to read GitHub configuration"
    exit 1
fi

IFS='|' read -r GH_TOKEN GH_OWNER GH_REPO GH_BRANCH <<< "$GITHUB_INFO"

echo "Repository: $GH_OWNER/$GH_REPO"
echo "Branch: $GH_BRANCH"
echo ""

# Files to move
FILES_TO_MOVE="daily.json weekly.json monthly.json yearly.json index.html"

# GitHub API base URL
API_BASE="https://api.github.com/repos/$GH_OWNER/$GH_REPO"

# Function to move a file in GitHub
move_file() {
    local file=$1
    local src_path="$file"
    local dest_path="var/www/html/$file"
    
    echo "Moving $src_path -> $dest_path..."
    
    # Get the file content and SHA from root
    RESPONSE=$(curl -s -H "Authorization: token $GH_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        "$API_BASE/contents/$src_path?ref=$GH_BRANCH")
    
    # Check if file exists in root
    if echo "$RESPONSE" | grep -q '"message": "Not Found"'; then
        echo "  ⚠️  $src_path not found in root (may already be moved or doesn't exist)"
        return 0
    fi
    
    # Extract content and SHA
    CONTENT=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('content',''))")
    SHA=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('sha',''))")
    
    if [ -z "$CONTENT" ] || [ -z "$SHA" ]; then
        echo "  ⚠️  Could not read $src_path (empty or invalid response)"
        return 0
    fi
    
    # Check if destination already exists and get its SHA if it does
    DEST_RESPONSE=$(curl -s -H "Authorization: token $GH_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        "$API_BASE/contents/$dest_path?ref=$GH_BRANCH")
    
    DEST_SHA=""
    if ! echo "$DEST_RESPONSE" | grep -q '"message": "Not Found"'; then
        DEST_SHA=$(echo "$DEST_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('sha',''))")
        echo "  ℹ️  Destination exists, will update"
    fi
    
    # Create/update file in destination
    PAYLOAD=$(python3 - <<PY
import json
import sys

payload = {
    "message": f"Move $file to var/www/html",
    "content": "$CONTENT",
    "branch": "$GH_BRANCH"
}

if "$DEST_SHA":
    payload["sha"] = "$DEST_SHA"

print(json.dumps(payload))
PY
    )
    
    PUT_RESPONSE=$(curl -s -X PUT \
        -H "Authorization: token $GH_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD" \
        "$API_BASE/contents/$dest_path")
    
    if echo "$PUT_RESPONSE" | grep -q '"sha"'; then
        echo "  ✓ Created/updated $dest_path"
        
        # Delete from root
        DELETE_PAYLOAD=$(python3 - <<PY
import json
print(json.dumps({
    "message": f"Remove $file from root (moved to var/www/html)",
    "sha": "$SHA",
    "branch": "$GH_BRANCH"
}))
PY
        )
        
        DELETE_RESPONSE=$(curl -s -X DELETE \
            -H "Authorization: token $GH_TOKEN" \
            -H "Accept: application/vnd.github.v3+json" \
            -H "Content-Type: application/json" \
            -d "$DELETE_PAYLOAD" \
            "$API_BASE/contents/$src_path")
        
        if echo "$DELETE_RESPONSE" | grep -q '"sha"'; then
            echo "  ✓ Deleted $src_path from root"
        else
            echo "  ⚠️  Could not delete $src_path from root (may have been modified)"
        fi
    else
        echo "  ✗ Failed to create $dest_path"
        echo "$PUT_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('message','Unknown error'))"
    fi
    
    echo ""
}

# Move each file
for file in $FILES_TO_MOVE; do
    move_file "$file"
done

echo "Done! Files have been moved to var/www/html in the GitHub repository."
echo "The publisher script has been updated to use the correct paths going forward."
