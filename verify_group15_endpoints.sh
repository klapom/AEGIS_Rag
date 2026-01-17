#!/bin/bash
# Verification script for Group 15 Explainability endpoints
# Sprint 107 Feature 107.3

set -e

echo "=========================================="
echo "Group 15 Endpoint Verification"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# API base URL
BASE_URL="http://localhost:8000"

# Function to test endpoint
test_endpoint() {
    local endpoint=$1
    local expected_field=$2

    echo -e "${YELLOW}Testing: ${endpoint}${NC}"

    response=$(curl -s -w "\n%{http_code}" "${BASE_URL}${endpoint}")
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$status_code" -eq 200 ]; then
        echo -e "${GREEN}✓ HTTP 200 OK${NC}"

        # Check if expected field exists
        if echo "$body" | python3 -c "import sys, json; data = json.load(sys.stdin); sys.exit(0 if '$expected_field' in data else 1)" 2>/dev/null; then
            echo -e "${GREEN}✓ Response contains '${expected_field}'${NC}"

            # Pretty print response
            echo "Response preview:"
            echo "$body" | python3 -m json.tool | head -20
            echo ""
        else
            echo -e "${RED}✗ Response missing '${expected_field}'${NC}"
            echo "$body" | python3 -m json.tool
            return 1
        fi
    else
        echo -e "${RED}✗ HTTP ${status_code}${NC}"
        echo "$body"
        return 1
    fi
}

echo "1. Testing Certification Status Endpoint"
echo "------------------------------------------"
test_endpoint "/api/v1/certification/status" "certification_status"
echo ""

echo "2. Testing Model Info Endpoint"
echo "------------------------------------------"
test_endpoint "/api/v1/explainability/model-info" "model_name"
echo ""

echo "3. Testing Alternative Certification Path"
echo "------------------------------------------"
test_endpoint "/api/v1/explainability/certification/status" "certification_status"
echo ""

echo "=========================================="
echo -e "${GREEN}All Group 15 endpoints verified!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Run Group 15 E2E tests: npm run test:e2e -- group15-explainability.spec.ts"
echo "  2. Check OpenAPI docs: http://localhost:8000/docs"
echo "  3. Replace mock data with production implementation"
echo ""
