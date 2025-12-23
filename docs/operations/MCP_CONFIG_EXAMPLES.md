# MCP Configuration Examples

This document provides example configuration files and setup scripts for MCP authentication.

## .mcp/config.json Examples

### Basic Configuration with Authentication

```json
{
  "mcpServers": {
    "bash": {
      "command": "node",
      "args": ["./mcp-server-bash/index.js"],
      "description": "Execute shell commands",
      "env": {
        "MCP_AUTH_ENABLED": "true",
        "MCP_JWT_SECRET": "${MCP_JWT_SECRET}",
        "MCP_JWT_ALGORITHM": "HS256",
        "LOG_LEVEL": "INFO"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-filesystem", "/data"],
      "description": "Access files in /data directory",
      "env": {
        "MCP_AUTH_ENABLED": "true",
        "MCP_JWT_SECRET": "${MCP_JWT_SECRET}",
        "MCP_PATH_RESTRICTIONS": "true",
        "MCP_ALLOWED_PATHS": "/data,/var/log"
      }
    },
    "postgres": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-postgres"],
      "description": "PostgreSQL database access",
      "env": {
        "MCP_AUTH_ENABLED": "true",
        "MCP_JWT_SECRET": "${MCP_JWT_SECRET}",
        "POSTGRES_URL": "${POSTGRES_URL}",
        "DATABASE_POOL_SIZE": "10"
      }
    }
  }
}
```

### Advanced Configuration with Rate Limiting

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-filesystem", "/data"],
      "description": "Restricted filesystem access",
      "env": {
        "MCP_AUTH_ENABLED": "true",
        "MCP_JWT_SECRET": "${MCP_JWT_SECRET}",
        "MCP_JWT_ALGORITHM": "HS256",
        "MCP_RATE_LIMIT_ENABLED": "true",
        "MCP_RATE_LIMIT_REQUESTS": "100",
        "MCP_RATE_LIMIT_WINDOW_SECS": "60",
        "MCP_PATH_RESTRICTIONS": "true",
        "MCP_ALLOWED_PATHS": "/data/documents,/data/uploads",
        "MCP_FORBIDDEN_PATHS": "/data/sensitive,/etc,/root",
        "MCP_LOG_LEVEL": "DEBUG"
      }
    },
    "bash": {
      "command": "node",
      "args": ["./mcp-server-bash/index.js"],
      "description": "Shell command execution",
      "env": {
        "MCP_AUTH_ENABLED": "true",
        "MCP_JWT_SECRET": "${MCP_JWT_SECRET}",
        "MCP_REQUIRE_ADMIN_ROLE": "true",
        "MCP_RATE_LIMIT_ENABLED": "true",
        "MCP_RATE_LIMIT_REQUESTS": "10",
        "MCP_RATE_LIMIT_WINDOW_SECS": "60",
        "MCP_LOG_ALL_COMMANDS": "true",
        "MCP_AUDIT_LOG_PATH": "/var/log/mcp-audit.log"
      }
    }
  }
}
```

### Production Configuration with Security Hardening

```json
{
  "mcpServers": {
    "bash": {
      "command": "node",
      "args": ["./mcp-server-bash/index.js"],
      "description": "Restricted shell access",
      "env": {
        "MCP_AUTH_ENABLED": "true",
        "MCP_JWT_SECRET_FILE": "/run/secrets/mcp_jwt_secret",
        "MCP_JWT_ALGORITHM": "HS256",
        "MCP_JWT_VERIFY_EXPIRY": "true",
        "MCP_JWT_MAX_AGE_SECS": "3600",
        "MCP_REQUIRE_ADMIN_ROLE": "true",
        "MCP_RATE_LIMIT_ENABLED": "true",
        "MCP_RATE_LIMIT_REQUESTS": "5",
        "MCP_RATE_LIMIT_WINDOW_SECS": "60",
        "MCP_AUDIT_ENABLED": "true",
        "MCP_AUDIT_LOG_PATH": "/var/log/mcp/audit.log",
        "MCP_AUDIT_LOG_RETENTION_DAYS": "90",
        "MCP_TLS_ENABLED": "true",
        "MCP_TLS_CERT": "/etc/mcp/certs/server.crt",
        "MCP_TLS_KEY": "/etc/mcp/certs/server.key",
        "NODE_ENV": "production",
        "LOG_LEVEL": "WARN"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-filesystem", "/data/documents"],
      "description": "Restricted document access",
      "env": {
        "MCP_AUTH_ENABLED": "true",
        "MCP_JWT_SECRET_FILE": "/run/secrets/mcp_jwt_secret",
        "MCP_PATH_RESTRICTIONS": "true",
        "MCP_ALLOWED_PATHS": "/data/documents/incoming,/data/documents/processed",
        "MCP_FORBIDDEN_PATHS": "/data/secrets,/data/private,/root",
        "MCP_SYMLINK_RESOLUTION": "false",
        "MCP_RATE_LIMIT_ENABLED": "true",
        "MCP_RATE_LIMIT_REQUESTS": "50",
        "MCP_RATE_LIMIT_WINDOW_SECS": "60",
        "MCP_AUDIT_ENABLED": "true",
        "MCP_AUDIT_LOG_PATH": "/var/log/mcp/filesystem.log"
      }
    },
    "postgres": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-postgres"],
      "description": "Production database access",
      "env": {
        "MCP_AUTH_ENABLED": "true",
        "MCP_JWT_SECRET_FILE": "/run/secrets/mcp_jwt_secret",
        "POSTGRES_URL_FILE": "/run/secrets/postgres_url",
        "DATABASE_POOL_SIZE": "20",
        "DATABASE_CONNECTION_TIMEOUT": "5000",
        "DATABASE_IDLE_TIMEOUT": "30000",
        "MCP_QUERY_TIMEOUT_SECS": "30",
        "MCP_MAX_RESULT_ROWS": "10000",
        "MCP_AUDIT_ENABLED": "true",
        "MCP_AUDIT_LOG_PATH": "/var/log/mcp/database.log",
        "MCP_SSL_ENABLED": "true",
        "MCP_SSL_VERIFY": "true"
      }
    }
  }
}
```

### Development Configuration (No Security)

```json
{
  "mcpServers": {
    "bash": {
      "command": "node",
      "args": ["./mcp-server-bash/index.js"],
      "env": {
        "MCP_AUTH_ENABLED": "false",
        "LOG_LEVEL": "DEBUG"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-filesystem", "."],
      "env": {
        "MCP_AUTH_ENABLED": "false",
        "MCP_PATH_RESTRICTIONS": "false"
      }
    }
  }
}
```

## Docker Compose Configuration

### Docker Compose with Secret Management

```yaml
version: '3.8'

secrets:
  mcp_jwt_secret:
    file: ./secrets/mcp_jwt_secret.txt
  postgres_password:
    file: ./secrets/postgres_password.txt

services:
  api:
    image: aegis-rag-api:latest
    ports:
      - "8000:8000"
    secrets:
      - mcp_jwt_secret
      - postgres_password
    environment:
      # Load secret from file
      MCP_JWT_SECRET_FILE: /run/secrets/mcp_jwt_secret
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password

      # Configuration
      ENVIRONMENT: production
      DEBUG: "false"
      LOG_LEVEL: INFO

      # Database
      POSTGRES_HOST: postgres
      POSTGRES_PORT: 5432
      POSTGRES_USER: aegisrag

      # MCP
      MCP_AUTH_ENABLED: "true"
      MCP_JWT_ALGORITHM: HS256
      MCP_JWT_EXPIRY_HOURS: "1"
      MCP_RATE_LIMIT_ENABLED: "true"
      MCP_RATE_LIMIT_REQUESTS: "100"
      MCP_RATE_LIMIT_WINDOW_SECS: "60"
    depends_on:
      - postgres
      - redis
      - qdrant
    volumes:
      - /run/secrets:/run/secrets:ro
    networks:
      - aegisrag

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: aegisrag
      POSTGRES_USER: aegisrag
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
    secrets:
      - postgres_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - aegisrag

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - aegisrag

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    networks:
      - aegisrag

volumes:
  postgres_data:
  redis_data:
  qdrant_data:

networks:
  aegisrag:
    driver: bridge
```

### Docker Compose with Environment Files

```yaml
version: '3.8'

services:
  api:
    image: aegis-rag-api:latest
    ports:
      - "8000:8000"
    env_file:
      - .env
      - .env.local  # Override with local settings
    environment:
      # Override specific values
      ENVIRONMENT: ${ENVIRONMENT:-development}
      DEBUG: ${DEBUG:-false}
    depends_on:
      - postgres
      - redis
    networks:
      - aegisrag

  postgres:
    image: postgres:15-alpine
    env_file:
      - .env.postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - aegisrag

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - aegisrag

volumes:
  postgres_data:
  redis_data:

networks:
  aegisrag:
```

## Environment Files

### .env.production

```bash
# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
JSON_LOGS=true

# API
API_HOST=0.0.0.0
API_PORT=8000
API_AUTH_ENABLED=true
API_WORKERS=4
API_RELOAD=false

# JWT/MCP
JWT_ALGORITHM=HS256
JWT_SECRET_KEY_FILE=/run/secrets/jwt_secret
MCP_JWT_SECRET_FILE=/run/secrets/mcp_jwt_secret
MCP_JWT_ALGORITHM=HS256
MCP_JWT_EXPIRY_HOURS=1
MCP_REFRESH_TOKEN_EXPIRY_DAYS=7
MCP_AUTH_ENABLED=true
MCP_RATE_LIMIT_ENABLED=true
MCP_RATE_LIMIT_REQUESTS=100
MCP_RATE_LIMIT_WINDOW_SECS=60
MCP_MAX_TOKEN_AGE=3600

# Databases
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=aegisrag
POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password
POSTGRES_DB=aegisrag

REDIS_HOST=redis
REDIS_PORT=6379

QDRANT_HOST=qdrant
QDRANT_PORT=6333

NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD_FILE=/run/secrets/neo4j_password
NEO4J_DATABASE=neo4j

# LLM
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL_GENERATION=llama3.2:8b

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090
JAEGER_ENABLED=true
JAEGER_ENDPOINT=http://jaeger:14268/api/traces
```

### .env.development

```bash
# Application
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
JSON_LOGS=false

# API
API_HOST=0.0.0.0
API_PORT=8000
API_AUTH_ENABLED=true
API_WORKERS=1
API_RELOAD=true

# JWT/MCP
JWT_ALGORITHM=HS256
JWT_SECRET_KEY=dev-secret-key-change-in-production
MCP_JWT_SECRET=dev-mcp-secret-key-change-in-production
MCP_JWT_ALGORITHM=HS256
MCP_JWT_EXPIRY_HOURS=24
MCP_REFRESH_TOKEN_EXPIRY_DAYS=30
MCP_AUTH_ENABLED=true
MCP_RATE_LIMIT_ENABLED=false

# Databases
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=aegisrag
POSTGRES_PASSWORD=aegisrag
POSTGRES_DB=aegisrag

REDIS_HOST=localhost
REDIS_PORT=6379

QDRANT_HOST=localhost
QDRANT_PORT=6333

NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j

# LLM
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_GENERATION=llama3.2:8b
```

## Kubernetes Configuration

### Secret Definitions

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: mcp-secrets
  namespace: aegisrag
type: Opaque
data:
  jwt-secret: $(echo -n 'your-secret-here' | base64)
  postgres-password: $(echo -n 'postgres-password' | base64)
  neo4j-password: $(echo -n 'neo4j-password' | base64)
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-config
  namespace: aegisrag
data:
  config.json: |
    {
      "mcpServers": {
        "bash": {
          "command": "node",
          "args": ["./mcp-server-bash/index.js"],
          "env": {
            "MCP_AUTH_ENABLED": "true",
            "MCP_JWT_SECRET": "${MCP_JWT_SECRET}"
          }
        }
      }
    }
```

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aegis-rag-api
  namespace: aegisrag
spec:
  replicas: 3
  selector:
    matchLabels:
      app: aegis-rag-api
  template:
    metadata:
      labels:
        app: aegis-rag-api
    spec:
      serviceAccountName: aegis-rag-api
      containers:
      - name: api
        image: aegis-rag-api:latest
        ports:
        - name: http
          containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: production
        - name: MCP_JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: mcp-secrets
              key: jwt-secret
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mcp-secrets
              key: postgres-password
        - name: NEO4J_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mcp-secrets
              key: neo4j-password
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        volumeMounts:
        - name: mcp-config
          mountPath: /app/.mcp
      volumes:
      - name: mcp-config
        configMap:
          name: mcp-config
```

## Setup Scripts

### setup_mcp_secrets.sh

```bash
#!/bin/bash
# Setup MCP secrets for production deployment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_DIR="${SCRIPT_DIR}/secrets"

echo "Setting up MCP secrets..."

# Create secrets directory
mkdir -p "$SECRETS_DIR"
chmod 700 "$SECRETS_DIR"

# Generate JWT secret
echo "Generating JWT secret..."
JWT_SECRET=$(openssl rand -hex 32)
echo "$JWT_SECRET" > "$SECRETS_DIR/mcp_jwt_secret.txt"
chmod 600 "$SECRETS_DIR/mcp_jwt_secret.txt"

# Generate other secrets
echo "Generating database passwords..."
POSTGRES_PASSWORD=$(openssl rand -base64 32)
echo "$POSTGRES_PASSWORD" > "$SECRETS_DIR/postgres_password.txt"
chmod 600 "$SECRETS_DIR/postgres_password.txt"

NEO4J_PASSWORD=$(openssl rand -base64 32)
echo "$NEO4J_PASSWORD" > "$SECRETS_DIR/neo4j_password.txt"
chmod 600 "$SECRETS_DIR/neo4j_password.txt"

# Display summary
echo ""
echo "Secrets generated successfully!"
echo ""
echo "JWT Secret:      $(cat "$SECRETS_DIR/mcp_jwt_secret.txt" | cut -c1-16)..."
echo "Postgres Pass:   $(cat "$SECRETS_DIR/postgres_password.txt" | cut -c1-16)..."
echo "Neo4j Pass:      $(cat "$SECRETS_DIR/neo4j_password.txt" | cut -c1-16)..."
echo ""
echo "Location: $SECRETS_DIR"
echo "Permissions: 600 (readable by owner only)"
echo ""
echo "IMPORTANT: Backup these secrets to a secure location!"
echo "Add to .gitignore: $SECRETS_DIR"
```

### generate_mcp_tokens.sh

```bash
#!/bin/bash
# Generate multiple MCP tokens for different purposes

set -e

# Source environment
export $(grep -v '^#' .env | xargs)

echo "Generating MCP tokens..."
echo ""

# Generate tokens
ADMIN_TOKEN=$(python scripts/generate_mcp_token.py --user-id admin --role admin --expiry 1 2>&1 | grep "^eyJ" | head -1)
USER_TOKEN=$(python scripts/generate_mcp_token.py --user-id user --role user --expiry 1 2>&1 | grep "^eyJ" | head -1)
PIPELINE_TOKEN=$(python scripts/generate_mcp_token.py --user-id ci-pipeline --role admin --expiry 2160 2>&1 | grep "^eyJ" | head -1)

# Save to file
cat > .mcp_tokens.env <<EOF
# MCP Authentication Tokens
# Generated: $(date)
# WARNING: Do not commit to git!

# Admin token (1 hour)
ADMIN_TOKEN="$ADMIN_TOKEN"

# User token (1 hour)
USER_TOKEN="$USER_TOKEN"

# CI/CD Pipeline token (90 days)
PIPELINE_TOKEN="$PIPELINE_TOKEN"
EOF

chmod 600 .mcp_tokens.env

echo "Tokens generated and saved to .mcp_tokens.env"
echo ""
echo "Usage:"
echo "  source .mcp_tokens.env"
echo "  curl -H \"Authorization: Bearer \$ADMIN_TOKEN\" http://localhost:8000/api/v1/mcp/servers"
echo ""
```

---

## See Also

- [MCP Authentication Guide](./MCP_AUTHENTICATION_GUIDE.md)
- [Quick Start Guide](./QUICK_START_GUIDE.md)
- [Monitoring Guide](./MONITORING_GUIDE.md)

---

**Document Version:** 1.0.0
**Last Updated:** 2025-12-23
**Status:** Feature 63.7 - MCP Configuration Examples
