#!/bin/sh
# Test Home Assistant API connectivity and entity state
# Usage: sh test_homeassistant_api.sh <HA_URL> <HA_TOKEN> <ENTITY_ID>

if [ "$#" -ne 3 ]; then
    echo "Usage: sh test_homeassistant_api.sh <HA_URL> <HA_TOKEN> <ENTITY_ID>"
    exit 1
fi

HA_URL="$1"
HA_TOKEN="$2"
ENTITY_ID="$3"

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

printf "${BLUE}Testing Home Assistant API...${NC}\n"

# Test API root
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $HA_TOKEN" \
    -H "Content-Type: application/json" \
    "$HA_URL/api/" 2>/dev/null)

if [ "$HTTP_CODE" = "200" ]; then
    printf "${GREEN}✓ API root reachable${NC}\n"
else
    printf "${RED}✗ API root unreachable (HTTP $HTTP_CODE)${NC}\n"
    exit 2
fi

# Test entity state
printf "${BLUE}Testing entity: $ENTITY_ID...${NC}\n"
ENTITY_RESPONSE=$(curl -s \
    -H "Authorization: Bearer $HA_TOKEN" \
    -H "Content-Type: application/json" \
    "$HA_URL/api/states/$ENTITY_ID" 2>/dev/null)

if echo "$ENTITY_RESPONSE" | grep -q '"entity_id"'; then
    STATE=$(echo "$ENTITY_RESPONSE" | grep -o '"state":"[^"]*"' | cut -d'"' -f4)
    printf "${GREEN}✓ Entity found. Current state: $STATE${NC}\n"
else
    printf "${YELLOW}⚠ Entity not found or no response${NC}\n"
    echo "$ENTITY_RESPONSE"
    exit 3
fi

printf "${GREEN}Home Assistant API test complete.${NC}\n"
