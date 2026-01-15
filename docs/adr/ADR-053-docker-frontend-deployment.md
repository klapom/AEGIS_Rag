# ADR-053: Docker Frontend Deployment

## Status
**Accepted** - 2026-01-14 (Sprint 92)

## Context

Prior to Sprint 92, the AegisRAG frontend was started manually using `npm run dev` on the DGX Spark server. This caused several issues:

1. **Manual Startup Required**: Frontend didn't auto-start when Docker services were brought up
2. **Port Accessibility**: Development port 5179 was hard to remember
3. **Service Coordination**: Frontend could start before backend was healthy
4. **Hot-Reload Issues**: Local development mode didn't persist across reboots

The backend API was already running in Docker (`aegis-api` container), but the frontend was the last remaining manually-managed service.

## Decision

We decided to **containerize the React/Vite frontend** and add it to `docker-compose.dgx-spark.yml` with the following configuration:

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DGX Spark (192.168.178.10)               │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Frontend   │    │   Backend    │    │   Ollama     │  │
│  │  (aegis-     │    │  (aegis-api) │    │  (aegis-     │  │
│  │  frontend)   │    │              │    │   ollama)    │  │
│  │   Port 80    │───►│   Port 8000  │───►│  Port 11434  │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                   │                   │          │
│         └───────────────────┴───────────────────┘          │
│                      aegis-network                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  User's Browser  │
                    │  (any machine)   │
                    └──────────────────┘
```

### Key Configuration

1. **Port 80**: Frontend exposed on standard HTTP port for easy access
2. **Debian Slim Image**: Used instead of Alpine for ARM64/canvas compatibility
3. **Health Dependencies**: Waits for `aegis-api` to be healthy before starting
4. **Volume Mounts**: Source code mounted for hot-reload in development
5. **External IP**: API URL configured with `DGX_SPARK_IP` environment variable

### Dockerfile Strategy

```dockerfile
# Base: Debian slim for ARM64 native module support
FROM node:20-slim AS base

# System deps for canvas (graph visualizations)
RUN apt-get install -y libcairo2-dev libpango1.0-dev ...

# Development target: Vite dev server with hot-reload
FROM base AS development
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5179"]

# Production target: nginx serving static files
FROM nginx:alpine AS production
COPY --from=build /app/dist /usr/share/nginx/html
```

### Browser-Docker Communication

A key insight was that the browser runs on the user's machine, not inside Docker. Therefore:
- The frontend container cannot use `http://api:8000` (Docker internal hostname)
- The API URL must be the external IP: `http://192.168.178.10:8000`
- This is configured via `VITE_API_BASE_URL` environment variable

### CORS Configuration

Since the browser on port 80 makes requests to the API on port 8000, this is a **cross-origin request**:

```yaml
# In docker-compose.dgx-spark.yml (api service)
environment:
  # pydantic-settings requires JSON array format for list[str] fields
  - CORS_ORIGINS=["http://localhost","http://localhost:80","http://192.168.178.10"]
```

The API's FastAPI middleware validates the `Origin` header and returns:
- `access-control-allow-origin: http://192.168.178.10`
- `access-control-allow-credentials: true`
- `access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS`

## Consequences

### Positive

1. **Auto-Start**: Frontend now starts automatically with `docker compose up -d`
2. **Easy Access**: Standard port 80 - just navigate to `http://192.168.178.10`
3. **Service Health**: Proper dependency chain ensures backend is ready
4. **Consistent Deployment**: All services managed the same way
5. **Hot-Reload Preserved**: Development experience unchanged with volume mounts

### Negative

1. **Larger Image**: Debian slim (~200MB) vs Alpine (~50MB)
2. **Build Time**: First build takes ~30s due to native module compilation
3. **Canvas Dependency**: Required system libraries for graph visualizations

### Neutral

1. **Port Change**: From 5179 to 80 (one-time update to bookmarks)
2. **Environment Variable**: Need to set `DGX_SPARK_IP` in `.env`

## Files Changed

| File | Change |
|------|--------|
| `docker/Dockerfile.frontend` | New file - multi-stage build |
| `docker-compose.dgx-spark.yml` | Added frontend service + CORS config |
| `src/core/config.py` | Added port 80 to default CORS origins |
| `.env` | Added `DGX_SPARK_IP` and `CORS_ORIGINS` |
| `CLAUDE.md` | Updated service documentation |

## Usage

```bash
# Start all services (including frontend)
docker compose -f docker-compose.dgx-spark.yml up -d

# Access the application
open http://192.168.178.10

# View frontend logs
docker logs -f aegis-frontend

# Rebuild frontend after changes
docker compose -f docker-compose.dgx-spark.yml build --no-cache frontend
```

## Related ADRs

- ADR-027: Docling CUDA Container
- ADR-033: AegisLLMProxy Multi-Cloud Routing
- ADR-041: Graph Entity Expansion

## References

- [Vite Docker Deployment](https://vitejs.dev/guide/static-deploy.html)
- [node-canvas ARM64 Support](https://github.com/Automattic/node-canvas/issues/1779)
