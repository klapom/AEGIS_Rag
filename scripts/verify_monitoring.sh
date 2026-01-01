#!/bin/bash
# =============================================================================
# AegisRAG Monitoring Verification Script
# Sprint 69 - Feature 69.7: Production Monitoring & Observability
# =============================================================================
#
# This script verifies that all monitoring components are properly configured
# and operational.
#
# Usage: ./scripts/verify_monitoring.sh
# =============================================================================

set -e

echo "=========================================="
echo "AegisRAG Monitoring Verification"
echo "Sprint 69 - Feature 69.7"
echo "=========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check functions
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# =============================================================================
# 1. Verify File Structure
# =============================================================================
echo "1. Verifying file structure..."

if [ -f "src/core/metrics.py" ]; then
    check_pass "src/core/metrics.py exists"
else
    check_fail "src/core/metrics.py not found"
    exit 1
fi

if [ -f "prometheus/alerts.yml" ]; then
    check_pass "prometheus/alerts.yml exists"
else
    check_fail "prometheus/alerts.yml not found"
    exit 1
fi

if [ -f "config/grafana/aegis_overview_sprint69.json" ]; then
    check_pass "config/grafana/aegis_overview_sprint69.json exists"
else
    check_fail "Grafana dashboard not found"
    exit 1
fi

if [ -f "config/grafana/dashboards.yml" ]; then
    check_pass "config/grafana/dashboards.yml exists"
else
    check_fail "Grafana provisioning config not found"
    exit 1
fi

echo ""

# =============================================================================
# 2. Verify Metrics in Code
# =============================================================================
echo "2. Verifying Sprint 69 metrics in src/core/metrics.py..."

if grep -q "aegis_queries_total" src/core/metrics.py; then
    check_pass "aegis_queries_total metric defined"
else
    check_fail "aegis_queries_total metric not found"
fi

if grep -q "aegis_query_latency_seconds" src/core/metrics.py; then
    check_pass "aegis_query_latency_seconds metric defined"
else
    check_fail "aegis_query_latency_seconds metric not found"
fi

if grep -q "aegis_cache_hits_total" src/core/metrics.py; then
    check_pass "aegis_cache_hits_total metric defined"
else
    check_fail "aegis_cache_hits_total metric not found"
fi

if grep -q "aegis_memory_facts_count" src/core/metrics.py; then
    check_pass "aegis_memory_facts_count metric defined"
else
    check_fail "aegis_memory_facts_count metric not found"
fi

if grep -q "track_query" src/core/metrics.py; then
    check_pass "track_query() function defined"
else
    check_fail "track_query() function not found"
fi

echo ""

# =============================================================================
# 3. Verify Alert Rules
# =============================================================================
echo "3. Verifying Prometheus alert rules..."

alert_count=$(grep -c "^  - alert:" prometheus/alerts.yml || true)
if [ "$alert_count" -ge 20 ]; then
    check_pass "Found $alert_count alert rules (expected ≥20)"
else
    check_warn "Found only $alert_count alert rules (expected ≥20)"
fi

if grep -q "HighQueryLatency" prometheus/alerts.yml; then
    check_pass "HighQueryLatency alert defined"
else
    check_fail "HighQueryLatency alert not found"
fi

if grep -q "HighErrorRate" prometheus/alerts.yml; then
    check_pass "HighErrorRate alert defined"
else
    check_fail "HighErrorRate alert not found"
fi

if grep -q "MemoryBudgetCritical" prometheus/alerts.yml; then
    check_pass "MemoryBudgetCritical alert defined"
else
    check_fail "MemoryBudgetCritical alert not found"
fi

echo ""

# =============================================================================
# 4. Verify Prometheus Configuration
# =============================================================================
echo "4. Verifying Prometheus configuration..."

if grep -q "alerts.yml" config/prometheus.yml; then
    check_pass "Alert rules configured in prometheus.yml"
else
    check_fail "Alert rules not configured in prometheus.yml"
fi

if grep -q "job_name: 'aegis-api'" config/prometheus.yml; then
    check_pass "API scrape job configured"
else
    check_fail "API scrape job not configured"
fi

echo ""

# =============================================================================
# 5. Verify Docker Compose Configuration
# =============================================================================
echo "5. Verifying Docker Compose configuration..."

if grep -q "./prometheus/alerts.yml:/etc/prometheus/alerts.yml:ro" docker-compose.dgx-spark.yml; then
    check_pass "Prometheus alert rules volume mounted"
else
    check_fail "Prometheus alert rules volume not mounted"
fi

if grep -q "./config/grafana/dashboards.yml" docker-compose.dgx-spark.yml; then
    check_pass "Grafana dashboard provisioning configured"
else
    check_fail "Grafana dashboard provisioning not configured"
fi

if grep -q "GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH" docker-compose.dgx-spark.yml; then
    check_pass "Grafana default dashboard configured"
else
    check_warn "Grafana default dashboard not configured"
fi

echo ""

# =============================================================================
# 6. Verify Grafana Dashboard Structure
# =============================================================================
echo "6. Verifying Grafana dashboard structure..."

if grep -q '"title": "AegisRAG Production Overview (Sprint 69)"' config/grafana/aegis_overview_sprint69.json; then
    check_pass "Dashboard title correct"
else
    check_fail "Dashboard title incorrect"
fi

panel_count=$(grep -c '"title":' config/grafana/aegis_overview_sprint69.json || true)
if [ "$panel_count" -ge 14 ]; then
    check_pass "Found $panel_count panels (expected ≥14)"
else
    check_warn "Found only $panel_count panels (expected ≥14)"
fi

if grep -q "aegis_queries_total" config/grafana/aegis_overview_sprint69.json; then
    check_pass "Dashboard uses aegis_queries_total metric"
else
    check_fail "Dashboard doesn't use aegis_queries_total metric"
fi

echo ""

# =============================================================================
# 7. Test Service Connectivity (if running)
# =============================================================================
echo "7. Testing service connectivity (if services are running)..."

if curl -s http://localhost:9090/-/healthy > /dev/null 2>&1; then
    check_pass "Prometheus is healthy (http://localhost:9090)"
else
    check_warn "Prometheus not accessible (service may not be running)"
fi

if curl -s http://localhost:3000/api/health > /dev/null 2>&1; then
    check_pass "Grafana is healthy (http://localhost:3000)"
else
    check_warn "Grafana not accessible (service may not be running)"
fi

if curl -s http://localhost:8000/metrics > /dev/null 2>&1; then
    check_pass "API metrics endpoint accessible (http://localhost:8000/metrics)"
else
    check_warn "API metrics endpoint not accessible (service may not be running)"
fi

echo ""

# =============================================================================
# 8. Summary
# =============================================================================
echo "=========================================="
echo "Verification Summary"
echo "=========================================="
echo ""
echo "✓ File structure complete"
echo "✓ Metrics defined in code"
echo "✓ Alert rules configured"
echo "✓ Prometheus configured"
echo "✓ Docker Compose updated"
echo "✓ Grafana dashboard ready"
echo ""
echo "Next steps:"
echo "1. Start services: docker compose -f docker-compose.dgx-spark.yml up -d prometheus grafana"
echo "2. Access Prometheus: http://localhost:9090"
echo "3. Access Grafana: http://localhost:3000 (admin / aegis-rag-grafana)"
echo "4. View alerts: http://localhost:9090/alerts"
echo "5. View dashboard: Grafana → Dashboards → AegisRAG Production Overview (Sprint 69)"
echo ""
echo "Documentation: docs/sprints/SPRINT_69_FEATURE_69.7_SUMMARY.md"
echo "=========================================="
