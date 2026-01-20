# Grafana Dashboard Setup Guide

## Quick Start (Docker)

### 1. Verify Dashboard Files

All 5 dashboards must be present:
```bash
ls -lh config/grafana/dashboards/
```

Expected output:
```
1-executive-overview.json    (11K)
2-rag-pipeline.json          (12K)
3-llm-operations.json        (13K)
4-data-stores.json           (16K)
5-memory-system.json         (16K)
```

### 2. Validate Dashboard JSON

```bash
python3 scripts/validate_dashboards.py --verbose
```

All 5 dashboards should pass validation.

### 3. Update docker-compose.yml

Ensure Grafana service includes dashboard volumes:

```yaml
grafana:
  image: grafana/grafana:latest
  container_name: aegis-grafana
  ports:
    - "3000:3000"
  volumes:
    # Dashboards provisioning
    - ./config/grafana/dashboards.yml:/etc/grafana/provisioning/dashboards/dashboards.yml
    - ./config/grafana/dashboards:/etc/grafana/provisioning/dashboards/aegis

    # Data source provisioning (if using)
    - ./config/grafana/datasources.yml:/etc/grafana/provisioning/datasources/datasources.yml

    # Storage
    - grafana_data:/var/lib/grafana

  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
    - GF_SECURITY_ADMIN_USER=admin
    - GF_USERS_ALLOW_SIGN_UP=false
    - GF_PATHS_PROVISIONING=/etc/grafana/provisioning
    - GF_LOG_LEVEL=info

  depends_on:
    - prometheus

  networks:
    - aegis-network

volumes:
  grafana_data:
```

### 4. Start Grafana Container

```bash
# Start Grafana (and dependencies)
docker compose up -d grafana

# Verify startup
docker logs grafana -f
```

Expected output:
```
logger=provisioning.dashboard msg="Searching for dashboards"
logger=provisioning.dashboard msg="Found 5 dashboards"
logger=provisioning.dashboard msg="Starting dashboard provisioning"
```

### 5. Access Grafana UI

Open browser:
```
http://localhost:3000
```

**Default Credentials:**
- Username: `admin`
- Password: `admin`

### 6. Verify Dashboards Loaded

1. Click "Dashboards" in left sidebar
2. Navigate to "Browse"
3. Verify 5 dashboards appear:
   - Executive Overview - AegisRAG Business KPIs
   - RAG Pipeline Performance
   - LLM Operations & Cost Management
   - Data Stores Infrastructure
   - Memory System - Graphiti 3-Layer Architecture

---

## Prometheus Datasource Setup

### 1. Verify Prometheus is Running

```bash
curl http://localhost:9090/api/v1/query?query=up
```

### 2. Add Prometheus to Grafana

**Option A: Automatic (Recommended)**

Create `config/grafana/datasources.yml`:

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    orgId: 1
    uid: prometheus-uid
    url: http://prometheus:9090
    jsonData:
      timeInterval: 15s
    isDefault: true
    editable: true
```

Then mount in docker-compose:
```yaml
volumes:
  - ./config/grafana/datasources.yml:/etc/grafana/provisioning/datasources/datasources.yml
```

**Option B: Manual**

1. Go to Configuration → Data Sources
2. Click "Add data source"
3. Select "Prometheus"
4. Set URL: `http://prometheus:9090`
5. Click "Save & Test"

### 3. Verify Connection

In Grafana, go to any dashboard and check panel:
- If metrics appear → connection working ✓
- If "No data" → check Prometheus datasource

---

## Verify Metrics Collection

For each dashboard, verify corresponding metrics exist in Prometheus:

### Executive Overview
```bash
curl 'http://localhost:9090/api/v1/query?query=aegis_queries_total'
curl 'http://localhost:9090/api/v1/query?query=llm_cost_usd'
curl 'http://localhost:9090/api/v1/query?query=qdrant_points_total'
curl 'http://localhost:9090/api/v1/query?query=neo4j_entities_total'
```

### RAG Pipeline
```bash
curl 'http://localhost:9090/api/v1/query?query=aegis_query_latency_seconds_bucket'
curl 'http://localhost:9090/api/v1/query?query=ragas_context_recall'
```

### LLM Operations
```bash
curl 'http://localhost:9090/api/v1/query?query=llm_cost_usd'
curl 'http://localhost:9090/api/v1/query?query=llm_tokens_total'
```

### Data Stores
```bash
curl 'http://localhost:9090/api/v1/query?query=qdrant_connections_active'
curl 'http://localhost:9090/api/v1/query?query=neo4j_entities_total'
curl 'http://localhost:9090/api/v1/query?query=redis_memory_used_bytes'
```

### Memory System
```bash
curl 'http://localhost:9090/api/v1/query?query=graphiti_facts_total'
curl 'http://localhost:9090/api/v1/query?query=graphiti_read_latency_seconds_bucket'
```

**If metrics missing:** Add to Prometheus scrape config

---

## Prometheus Configuration

Update `config/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  # AegisRAG API
  - job_name: 'aegis-rag-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'

  # Qdrant Vector DB
  - job_name: 'qdrant'
    static_configs:
      - targets: ['qdrant:6333']
    metrics_path: '/metrics'

  # Neo4j Graph DB
  - job_name: 'neo4j'
    static_configs:
      - targets: ['neo4j:7474']

  # Redis Cache
  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
    metrics_path: '/metrics'
```

---

## Troubleshooting

### Dashboards Not Appearing

1. **Check Grafana logs:**
   ```bash
   docker logs aegis-grafana | grep dashboard
   ```

2. **Verify volume mounts:**
   ```bash
   docker inspect aegis-grafana | grep -A 20 Mounts
   ```

3. **Test provisioning file:**
   ```bash
   python3 -m json.tool config/grafana/dashboards.yml
   ```

4. **Restart Grafana:**
   ```bash
   docker restart aegis-grafana
   ```

### Metrics Not Showing

1. **Check Prometheus scrape targets:**
   ```
   http://localhost:9090/targets
   ```

2. **Query metric directly:**
   ```bash
   curl 'http://localhost:9090/api/v1/query?query=aegis_queries_total'
   ```

3. **Check scrape logs:**
   ```bash
   docker logs aegis-prometheus | tail -50
   ```

### No Data in Panels

1. **Verify time range:** Adjust dashboard time picker
2. **Check metric labels:** Ensure labels match in PromQL queries
3. **Verify query syntax:** Click panel → Edit → check PromQL

### High Memory Usage

1. Reduce refresh rate:
   - Change dashboard `refresh` from `10s` to `30s`
   - Edit JSON file or UI

2. Reduce time range:
   - Dashboard default: 1-24h
   - For long-term analysis: 7-30 days

3. Enable Prometheus downsampling:
   ```yaml
   storage:
     tsdb:
       retention:
         size: 50GB
   ```

---

## Performance Tuning

### Optimize Query Performance

1. **Add metric filters:**
   ```promql
   # Before (slow)
   histogram_quantile(0.95, rate(aegis_query_latency_seconds_bucket[5m]))

   # After (optimized)
   histogram_quantile(0.95, sum(rate(aegis_query_latency_seconds_bucket[5m])) by (le))
   ```

2. **Use recording rules** in Prometheus:
   ```yaml
   groups:
     - name: aegis_rag
       interval: 30s
       rules:
         - record: aegis:qps
           expr: sum(rate(aegis_queries_total[5m]))
   ```

3. **Increase scrape interval** (if 15s too frequent):
   ```yaml
   global:
     scrape_interval: 30s  # increased from 15s
   ```

### Panel Optimization

- **Timeseries:** Max 100 series per panel
- **Stat:** Use for single metrics only
- **Gauge:** Use for percentage/threshold metrics
- **Piechart:** Max 20 segments

---

## Backup & Restore

### Export Dashboard

1. Dashboard → ... menu → Export → Export for sharing
2. Save JSON file (for version control)

### Backup Grafana

```bash
# Backup data volume
docker run --rm \
  -v aegis_grafana_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/grafana_data.tar.gz -C /data .

# Backup dashboards
cp -r config/grafana/dashboards config/grafana/dashboards.backup
```

### Restore Dashboard

1. Upload JSON via UI: Create → Import → Paste JSON
2. Or: Copy JSON to `config/grafana/dashboards/` and restart container

---

## Advanced: Custom Dashboards

### Create New Dashboard

1. UI: Click "Create" → "Dashboard"
2. Add panels with queries
3. Save as JSON
4. Place in `config/grafana/dashboards/`
5. Restart Grafana

### Dashboard Template Variables

Add to JSON `templating` section:

```json
"templating": {
  "list": [
    {
      "name": "namespace",
      "type": "query",
      "datasource": "Prometheus",
      "query": "label_values(aegis_queries_total, namespace)",
      "sort": 1
    }
  ]
}
```

Then use in queries:
```promql
sum(rate(aegis_queries_total{namespace="$namespace"}[5m]))
```

---

## Security Considerations

### Restrict Dashboard Access

**Option 1: Anonymous Dashboards**
```yaml
environment:
  - GF_AUTH_ANONYMOUS_ENABLED=true
  - GF_AUTH_ANONYMOUS_ORG_ROLE=Viewer
```

**Option 2: API Token Authentication**
```bash
# Create API token in Grafana UI
# Admin → API tokens → New API token

# Use in scripts
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:3000/api/dashboards
```

### Secure Sensitive Data

- **Cost dashboards:** Restrict to Finance team
- **LLM keys:** Use Grafana secrets (not shown in JSON)
- **Database credentials:** Store in Grafana secrets

---

## Monitoring the Dashboards Themselves

Enable Grafana metrics export:

```yaml
environment:
  - GF_USERS_METRICS_ENABLED=true
```

Then monitor:
```promql
grafana_dashboard_provisioning_duration_seconds
grafana_http_request_duration_seconds
```

---

## Maintenance Schedule

| Task | Frequency | Owner |
|------|-----------|-------|
| Validate dashboard JSON | Weekly | DevOps |
| Check metric availability | Daily | Monitoring |
| Review alert thresholds | Monthly | Operations |
| Archive old dashboards | Quarterly | DevOps |
| Upgrade Grafana | Quarterly | DevOps |
| Backup Grafana data | Weekly | DevOps |

---

## Support

For issues:
1. Check Grafana logs: `docker logs aegis-grafana`
2. Check Prometheus health: http://localhost:9090/-/healthy
3. Validate dashboard: `python3 scripts/validate_dashboards.py --verbose`
4. Review DASHBOARDS_README.md for dashboard-specific issues
