# Operations Documentation

This directory contains operational guides and runbooks for running and maintaining AegisRAG in production and development environments.

## Guides

### Quick Start
- **[QUICK_START_GUIDE.md](./QUICK_START_GUIDE.md)** - Get AegisRAG running in 15 minutes with local development setup

### MCP (Model Context Protocol)
- **[MCP_AUTHENTICATION_GUIDE.md](./MCP_AUTHENTICATION_GUIDE.md)** - Complete guide to MCP authentication using JWT tokens
  - JWT token architecture and validation
  - Setup instructions and environment configuration
  - Token generation and management
  - Security best practices
  - Integration examples (Python, TypeScript, curl)
  - Troubleshooting guide

- **[MCP_CONFIG_EXAMPLES.md](./MCP_CONFIG_EXAMPLES.md)** - Example configurations for MCP servers
  - Docker Compose configurations with secrets management
  - Kubernetes manifests
  - Environment files for different deployment scenarios
  - Setup scripts for secret generation

- **[MCP_AUTHENTICATION_TEST.md](./MCP_AUTHENTICATION_TEST.md)** - Testing guide for MCP authentication
  - Quick test procedures
  - Comprehensive test suite
  - Performance benchmarks
  - Troubleshooting procedures

### Monitoring & Observability
- **[MONITORING_GUIDE.md](./MONITORING_GUIDE.md)** - Monitor AegisRAG health and performance
  - Health checks
  - Metrics and dashboards
  - Logging and alerting

### DGX Spark Deployment
- **[DGX_SPARK_DEPLOYMENT.md](./DGX_SPARK_DEPLOYMENT.md)** - Deploy on NVIDIA DGX Spark (SM121 GPU)
  - Hardware specifications
  - CUDA and PyTorch configuration
  - Service startup procedures

## Scripts

Token generation and validation scripts in `scripts/`:

- **`generate_mcp_token.py`** - Generate JWT tokens for MCP authentication
  ```bash
  python3 scripts/generate_mcp_token.py --user-id admin --role admin --expiry 1
  ```

- **`validate_mcp_token.py`** - Validate and inspect JWT tokens
  ```bash
  python3 scripts/validate_mcp_token.py --token "$TOKEN" --verbose
  ```

## Common Tasks

### Generate MCP Authentication Token

```bash
# Set JWT secret (from .env or secret management)
export MCP_JWT_SECRET=$(cat /path/to/secret)

# Generate token for 1 hour
python3 scripts/generate_mcp_token.py --user-id admin --role admin --expiry 1

# Generate long-lived token (90 days)
python3 scripts/generate_mcp_token.py --user-id ci-pipeline --role admin --expiry 2160
```

### Validate MCP Token

```bash
# Validate with signature verification
python3 scripts/validate_mcp_token.py --token "$TOKEN"

# Show detailed information
python3 scripts/validate_mcp_token.py --token "$TOKEN" --verbose

# Get JSON output
python3 scripts/validate_mcp_token.py --token "$TOKEN" --json
```

### Set Up MCP Authentication

1. **Generate JWT Secret**
   ```bash
   openssl rand -hex 32
   ```

2. **Configure Environment**
   ```bash
   export MCP_JWT_SECRET="your-secret-here"
   export MCP_JWT_EXPIRY_HOURS="1"
   ```

3. **Generate Tokens**
   ```bash
   python3 scripts/generate_mcp_token.py --user-id admin --role admin
   ```

4. **Use in Requests**
   ```bash
   curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/v1/mcp/servers
   ```

### Start Development Environment

```bash
# 1. Install dependencies
poetry install

# 2. Start databases (Docker)
docker-compose up -d

# 3. Start API server
poetry run uvicorn src.api.main:app --reload --port 8000

# 4. Generate token
export MCP_JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
TOKEN=$(python3 scripts/generate_mcp_token.py --user-id admin --role admin --expiry 24 2>&1 | grep "^eyJ" | head -1)

# 5. Test endpoints
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/mcp/servers
```

## Security Checklist

- [ ] JWT secret is strong (min 32 characters, random)
- [ ] JWT secret is not committed to git
- [ ] JWT secret is stored in secure location (environment variables, secret manager)
- [ ] Token expiry is configured appropriately (short for access, longer for refresh)
- [ ] Tokens are not logged in plain text
- [ ] HTTPS/TLS is used in production
- [ ] Rate limiting is enabled
- [ ] Audit logging is enabled
- [ ] Token rotation is scheduled (every 90 days)

## Troubleshooting

### MCP Authentication Issues

See [MCP_AUTHENTICATION_GUIDE.md - Troubleshooting](./MCP_AUTHENTICATION_GUIDE.md#troubleshooting)

### Health Check Failed

```bash
# Check API health
curl http://localhost:8000/health

# Check MCP health
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/mcp/health
```

### Database Connection Issues

```bash
# Check PostgreSQL
psql -U aegisrag -d aegisrag -h localhost

# Check Qdrant
curl http://localhost:6333/health

# Check Neo4j
curl -u neo4j:password http://localhost:7474/db/neo4j/summary

# Check Redis
redis-cli ping
```

## References

- [MCP Authentication Guide](./MCP_AUTHENTICATION_GUIDE.md)
- [MCP Configuration Examples](./MCP_CONFIG_EXAMPLES.md)
- [MCP Testing Guide](./MCP_AUTHENTICATION_TEST.md)
- [Quick Start Guide](./QUICK_START_GUIDE.md)
- [Monitoring Guide](./MONITORING_GUIDE.md)

## Feature Status

| Feature | Status | Version | Documentation |
|---------|--------|---------|-----------------|
| MCP Authentication (JWT) | Implemented | 1.0.0 | Feature 63.7 |
| Token Generation | Implemented | 1.0.0 | Scripts + Guide |
| Token Validation | Implemented | 1.0.0 | Scripts + Guide |
| Security Best Practices | Documented | 1.0.0 | Guide |
| Configuration Examples | Provided | 1.0.0 | Examples |

---

**Last Updated:** 2025-12-23
**Version:** Sprint 63
**Maintained By:** Documentation Agent
