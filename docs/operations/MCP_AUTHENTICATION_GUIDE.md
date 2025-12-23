# MCP Authentication Guide

## Overview

The Model Context Protocol (MCP) authentication system secures communication between MCP clients and the AegisRAG server. This guide documents JWT token configuration, token generation, and security best practices for MCP authentication.

### What is MCP Authentication?

MCP authentication ensures that only authorized clients can:
- Connect to MCP servers
- List available tools
- Execute MCP tools
- Access sensitive operations

### Why MCP Authentication Matters

1. **Access Control**: Restrict tool execution to authorized users
2. **Audit Trail**: Track which users executed which tools
3. **Rate Limiting**: Prevent abuse through request throttling
4. **Token Expiration**: Limit the lifetime of credentials
5. **Secret Security**: Protect sensitive environment variables

---

## Architecture

### JWT Token Flow

```
┌─────────────────────────────────────────────────────────┐
│           MCP Authentication Flow                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. Client Requests Token                              │
│     └─→ POST /api/v1/auth/token                        │
│                                                         │
│  2. Server Validates Credentials                       │
│     └─→ Check username/password                        │
│                                                         │
│  3. Server Issues JWT Token                            │
│     └─→ Sign with MCP_JWT_SECRET                       │
│         Return token with expiry                       │
│                                                         │
│  4. Client Stores Token                                │
│     └─→ Save in secure storage                         │
│         Never log or expose                            │
│                                                         │
│  5. Client Includes Token in Requests                  │
│     └─→ Authorization: Bearer <token>                  │
│         Header on all MCP calls                        │
│                                                         │
│  6. Server Validates Token                             │
│     └─→ Verify signature                               │
│         Check expiration                               │
│         Validate claims                                │
│                                                         │
│  7. Server Executes Tool (if authorized)               │
│     └─→ Log execution                                  │
│         Return result                                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Token Structure

JWT tokens consist of three parts:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.
eyJ1c2VyX2lkIjoiYWRtaW4iLCJleHAiOjE2NzE0MjM2MDB9.
SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

**Header** (Base64 decoded):
```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

**Payload** (Base64 decoded):
```json
{
  "user_id": "admin",
  "username": "admin",
  "role": "admin",
  "token_type": "access",
  "exp": 1671423600,
  "iat": 1671420000
}
```

**Signature**:
```
HMACSHA256(
  base64UrlEncode(header) + "." + base64UrlEncode(payload),
  MCP_JWT_SECRET
)
```

### Token Validation

On each request, the server:

1. **Extract Token**: Read `Authorization: Bearer <token>` header
2. **Verify Signature**: Validate HMAC using `MCP_JWT_SECRET`
3. **Check Expiration**: Ensure `exp` > current time
4. **Validate Claims**: Verify token type and user role
5. **Return User**: Make authenticated user available to endpoint

---

## Setup Instructions

### Step 1: Generate JWT Secret

Generate a cryptographically secure 32-byte (256-bit) secret:

```bash
# Using OpenSSL (recommended)
openssl rand -hex 32

# Example output:
# 8f3e4c2b1a9d7f5e3c6b2a0d8e1f4a7c9e2d5b8f1a3c6e9d2f5a8b1e4c7a0d

# Using Python
python3 -c "import secrets; print(secrets.token_hex(32))"

# Using Go
go run -c "package main; import (\"fmt\"; \"crypto/rand\"; \"encoding/hex\"); func main() { b := make([]byte, 32); rand.Read(b); fmt.Println(hex.EncodeToString(b)) }"
```

Save this output for the next step.

### Step 2: Set Environment Variables

Update your `.env` file or set environment variables:

```bash
# JWT Configuration
export MCP_JWT_SECRET="your-secret-here"
export MCP_JWT_ALGORITHM="HS256"
export MCP_JWT_EXPIRY_HOURS="1"
export MCP_REFRESH_TOKEN_EXPIRY_DAYS="7"

# Optional: MCP Server Configuration
export MCP_AUTH_ENABLED="true"
export MCP_MAX_TOKEN_AGE="3600"
```

**Security Notes:**
- Never commit `.env` with actual secrets to git
- Use `.env.local` for local development (ignored by git)
- For Docker, use secrets management (Docker Secrets, HashiCorp Vault, etc.)
- Rotate secrets every 90 days in production

### Step 3: Configure .mcp/config.json

Create MCP server configuration with authentication:

```json
{
  "mcpServers": {
    "bash": {
      "command": "node",
      "args": ["./mcp-server-bash/index.js"],
      "env": {
        "MCP_AUTH_ENABLED": "true",
        "MCP_JWT_SECRET": "${MCP_JWT_SECRET}",
        "MCP_JWT_ALGORITHM": "HS256"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-filesystem", "/data"],
      "env": {
        "MCP_AUTH_ENABLED": "true",
        "MCP_JWT_SECRET": "${MCP_JWT_SECRET}"
      }
    },
    "postgres": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-postgres"],
      "env": {
        "MCP_AUTH_ENABLED": "true",
        "MCP_JWT_SECRET": "${MCP_JWT_SECRET}",
        "POSTGRES_URL": "${POSTGRES_URL}"
      }
    }
  }
}
```

### Step 4: Verify Setup

Test JWT token creation and validation:

```bash
# 1. Generate a token using the script (see below)
python scripts/generate_mcp_token.py --user-id admin --expiry 24

# 2. Test token validation
python scripts/validate_mcp_token.py --token "your-token-here"

# 3. Test MCP server connectivity with token
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/mcp/servers
```

---

## Token Generation

### Using Python Script

The `scripts/generate_mcp_token.py` script generates JWT tokens:

```bash
# Generate admin token (24 hour expiry)
python scripts/generate_mcp_token.py --user-id admin --expiry 24

# Generate user token (1 hour expiry)
python scripts/generate_mcp_token.py --user-id user123 --expiry 1

# Generate long-lived integration token (90 days)
python scripts/generate_mcp_token.py --user-id ci-pipeline --role admin --expiry 2160
```

**Output:**
```
MCP Authentication Token Generated
=====================================
User ID:    admin
Username:   admin
Role:       admin
Expires In: 24 hours
Expiry:     2025-12-24T22:30:45Z

Token:
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiYWRtaW4iLCJ1c2VybmFtZSI6ImFkbWluIiwicm9sZSI6ImFkbWluIiwicHJvdmlzaW9uIjoiYWRtaW4iLCJleHAiOjE3MDM0MjM2NDUsImlhdCI6MTcwMzMzNzI0NX0.xyz...

Save this token securely. Do not commit to git or share in logs.
```

### Programmatic Token Generation

Generate tokens from Python code:

```python
from src.core.auth import create_access_token
from src.core.config import settings

# Generate single access token
token = create_access_token(
    user_id="admin",
    username="admin",
    role="admin"
)

# Use in requests
import requests

headers = {"Authorization": f"Bearer {token}"}
response = requests.get(
    "http://localhost:8000/api/v1/mcp/servers",
    headers=headers
)

print(response.json())
```

### Programmatic Token Creation (Advanced)

For custom token generation with specific claims:

```python
from datetime import datetime, timedelta, UTC
import jwt
import os

def generate_custom_mcp_token(
    user_id: str,
    role: str = "user",
    expiry_hours: int = 1,
    custom_claims: dict = None
) -> str:
    """Generate JWT token with custom claims."""

    secret = os.getenv("MCP_JWT_SECRET")
    if not secret:
        raise ValueError("MCP_JWT_SECRET not set")

    payload = {
        "user_id": user_id,
        "username": user_id,  # Default: use user_id as username
        "role": role,
        "token_type": "access",
        "exp": datetime.now(UTC) + timedelta(hours=expiry_hours),
        "iat": datetime.now(UTC)
    }

    # Add custom claims
    if custom_claims:
        payload.update(custom_claims)

    token = jwt.encode(
        payload,
        secret,
        algorithm="HS256"
    )

    return token

# Example usage
token = generate_custom_mcp_token(
    user_id="ci-pipeline",
    role="admin",
    expiry_hours=720,  # 30 days
    custom_claims={
        "service": "ci-cd",
        "environment": "production"
    }
)

print(f"Generated token: {token}")
```

---

## Configuration

### Environment Variables Reference

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MCP_JWT_SECRET` | string | (required) | HMAC secret for token signing (min 32 chars) |
| `MCP_JWT_ALGORITHM` | string | `HS256` | JWT signing algorithm |
| `MCP_JWT_EXPIRY_HOURS` | int | `1` | Access token lifetime in hours |
| `MCP_REFRESH_TOKEN_EXPIRY_DAYS` | int | `7` | Refresh token lifetime in days |
| `MCP_AUTH_ENABLED` | bool | `true` | Enable authentication on MCP servers |
| `MCP_MAX_TOKEN_AGE` | int | `3600` | Maximum token age in seconds |

### .env Configuration Example

```bash
# Application
ENVIRONMENT=production
DEBUG=false

# Authentication
JWT_SECRET_KEY=8f3e4c2b1a9d7f5e3c6b2a0d8e1f4a7c9e2d5b8f1a3c6e9d2f5a8b1e4c7a0d
MCP_JWT_SECRET=8f3e4c2b1a9d7f5e3c6b2a0d8e1f4a7c9e2d5b8f1a3c6e9d2f5a8b1e4c7a0d
MCP_JWT_ALGORITHM=HS256
MCP_JWT_EXPIRY_HOURS=1
MCP_REFRESH_TOKEN_EXPIRY_DAYS=7

# API
API_HOST=0.0.0.0
API_PORT=8000
API_AUTH_ENABLED=true

# MCP Servers
MCP_AUTH_ENABLED=true
MCP_MAX_TOKEN_AGE=3600

# Databases
QDRANT_HOST=localhost
QDRANT_PORT=6333
NEO4J_URI=bolt://localhost:7687
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Docker Secret Management

For production Docker deployments:

```yaml
# docker-compose.yml
version: '3.8'

secrets:
  mcp_jwt_secret:
    file: ./secrets/mcp_jwt_secret.txt

services:
  api:
    image: aegis-rag-api:latest
    secrets:
      - mcp_jwt_secret
    environment:
      MCP_JWT_SECRET_FILE: /run/secrets/mcp_jwt_secret
    volumes:
      - /run/secrets:/run/secrets:ro
```

### Kubernetes Secret Management

For Kubernetes deployments:

```bash
# Create secret from file
kubectl create secret generic mcp-jwt-secret \
  --from-literal=token=$(openssl rand -hex 32) \
  -n aegisrag

# Reference in deployment
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: aegis-rag-api
spec:
  containers:
  - name: api
    env:
    - name: MCP_JWT_SECRET
      valueFrom:
        secretKeyRef:
          name: mcp-jwt-secret
          key: token
EOF
```

---

## Troubleshooting

### Common Authentication Errors

#### 1. Invalid Token Signature

**Error:**
```json
{
  "detail": "Could not validate credentials",
  "status_code": 401
}
```

**Causes:**
- Wrong `MCP_JWT_SECRET` used to validate token
- Token was signed with different secret
- Secret was rotated but old token used

**Solutions:**
```bash
# 1. Verify secret is set correctly
echo $MCP_JWT_SECRET

# 2. Generate new token with current secret
python scripts/generate_mcp_token.py --user-id admin

# 3. Use new token in requests
```

#### 2. Token Expired

**Error:**
```json
{
  "detail": "Token has expired",
  "status_code": 401
}
```

**Causes:**
- Token lifetime exceeded expiration
- System clock skew (server/client time mismatch)
- Token age exceeds `MCP_MAX_TOKEN_AGE`

**Solutions:**
```bash
# 1. Generate new token
python scripts/generate_mcp_token.py --user-id admin

# 2. Check server time
date
date -u  # UTC time

# 3. Increase expiry for long-running operations
python scripts/generate_mcp_token.py --user-id admin --expiry 24

# 4. Verify system clock sync
timedatectl  # Linux
sudo ntpdate -s time.nist.gov  # Sync if needed
```

#### 3. Missing Authorization Header

**Error:**
```json
{
  "detail": "Not authenticated",
  "status_code": 401
}
```

**Causes:**
- No `Authorization` header in request
- Header format incorrect
- Token not passed correctly

**Solutions:**
```bash
# WRONG - Missing Authorization header
curl http://localhost:8000/api/v1/mcp/servers

# WRONG - Incorrect format
curl -H "Authorization: Token $TOKEN" http://localhost:8000/api/v1/mcp/servers
curl -H "Bearer: $TOKEN" http://localhost:8000/api/v1/mcp/servers

# CORRECT - Proper Bearer format
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/mcp/servers

# Python requests
headers = {"Authorization": f"Bearer {token}"}
response = requests.get("http://localhost:8000/api/v1/mcp/servers", headers=headers)
```

#### 4. User Not Authorized

**Error:**
```json
{
  "detail": "User does not have permission",
  "status_code": 403
}
```

**Causes:**
- User role insufficient for operation
- User account disabled
- User deleted from system

**Solutions:**
```bash
# 1. Check user role
python scripts/validate_mcp_token.py --token "$TOKEN"

# 2. Verify user exists and is active
# Use admin endpoint to check user status

# 3. Generate token with correct role
python scripts/generate_mcp_token.py --user-id admin --role admin
```

### Debug Token Validation

Use the token validation script to debug:

```bash
# Validate token
python scripts/validate_mcp_token.py --token "your-token" --verbose

# Output:
# Token Validation Report
# =======================
# Valid:           ✓
# Token Type:      access
# User ID:         admin
# Username:        admin
# Role:            admin
# Issued At:       2025-12-23T22:00:00Z
# Expires At:      2025-12-24T22:00:00Z
# Time Until Exp:  23h 59m 30s
# Current Time:    2025-12-23T22:00:30Z
```

### Enable Debug Logging

For detailed authentication debugging:

```bash
# Set debug log level
export LOG_LEVEL=DEBUG

# Run application
uvicorn src.api.main:app --reload --log-level debug

# Check logs for authentication details
# Look for: "token_decoded", "token_invalid", "mcp_*" entries
```

---

## Security Best Practices

### 1. Secret Management

#### Do:
- Use cryptographically secure random generation (OpenSSL, secrets module)
- Store secrets in environment variables or secret managers
- Rotate secrets every 90 days
- Use different secrets per environment
- Use strong secrets (min 32 chars, random)

#### Don't:
- Hardcode secrets in code
- Commit secrets to version control
- Share secrets in chat or email
- Use weak secrets (predictable, short)
- Reuse secrets across environments

### 2. Token Expiration

#### Do:
- Use short-lived access tokens (1 hour)
- Use longer-lived refresh tokens (7 days)
- Refresh tokens before expiration
- Clear expired tokens from memory
- Implement token rotation

#### Don't:
- Never-expiring tokens
- Very long token lifetimes
- Store tokens in localStorage (XSS risk)
- Pass tokens in URL parameters
- Log tokens

### 3. Token Storage

#### Client-Side Storage:
```javascript
// DO: Use secure storage
// Browser: httpOnly cookie
response.headers['Set-Cookie'] =
  `authToken=${token}; httpOnly; Secure; SameSite=Strict`;

// DO: Use sessionStorage for short-lived tokens
sessionStorage.setItem('mcp_token', token);

// DON'T: Use localStorage for sensitive tokens
// localStorage.setItem('token', token);  // XSS vulnerable

// DON'T: Pass in URL
// window.location = `/page?token=${token}`;  // Logged in history
```

#### Server-Side Storage:
```python
# DO: Hash tokens in database
import hashlib

token_hash = hashlib.sha256(token.encode()).hexdigest()
# Store token_hash in database

# DO: Store with metadata
token_metadata = {
    "token_hash": token_hash,
    "user_id": "admin",
    "issued_at": datetime.now(UTC),
    "expires_at": datetime.now(UTC) + timedelta(hours=1),
    "ip_address": "192.168.1.100",
    "user_agent": "curl/7.68.0"
}

# DON'T: Store plain tokens
# db.save(token)  # Insecure!
```

### 4. Token Transmission

#### Do:
```bash
# HTTPS/TLS for all requests
curl -H "Authorization: Bearer $TOKEN" https://api.example.com/...

# Set secure cookie flags
Set-Cookie: token=...; Secure; HttpOnly; SameSite=Strict

# Include in request header
Authorization: Bearer eyJhbGc...
```

#### Don't:
```bash
# HTTP (unencrypted)
curl -H "Authorization: Bearer $TOKEN" http://api.example.com/...  # NO!

# URL parameter
curl https://api.example.com/endpoint?token=TOKEN  # NO!

# Request body (unless TLS)
POST /endpoint
Authorization: Bearer TOKEN  # Only with TLS!

# Cookies without flags
Set-Cookie: token=...  # Missing Secure, HttpOnly, SameSite
```

### 5. Rate Limiting

Protect against brute force and DoS:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/mcp/tools/{tool_name}/execute")
@limiter.limit("10/minute")  # 10 requests per minute
async def execute_tool(
    tool_name: str,
    request: ToolExecuteRequest,
    current_user: User = Depends(get_current_user),
):
    # Tool execution logic
    pass
```

### 6. Audit Logging

Log all authentication events:

```python
import structlog

logger = structlog.get_logger(__name__)

# Log successful token creation
logger.info(
    "mcp_token_generated",
    user_id=user_id,
    role=role,
    expiry_hours=expiry_hours,
    timestamp=datetime.now(UTC).isoformat()
)

# Log failed validation
logger.warning(
    "mcp_authentication_failed",
    reason="Invalid signature",
    ip_address=request.client.host,
    timestamp=datetime.now(UTC).isoformat()
)

# Log tool execution
logger.info(
    "mcp_tool_executed",
    user_id=user_id,
    tool_name=tool_name,
    success=True,
    execution_time=0.45,
    timestamp=datetime.now(UTC).isoformat()
)
```

### 7. Token Revocation

Implement token blacklist for logout and security:

```python
import redis
from datetime import datetime, timedelta, UTC

redis_client = redis.Redis(host='localhost', port=6379)

def revoke_token(token: str, expiry_seconds: int):
    """Add token to blacklist until expiry."""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    redis_client.setex(
        f"token_blacklist:{token_hash}",
        expiry_seconds,
        "revoked"
    )
    logger.info("token_revoked", token_hash=token_hash)

def is_token_revoked(token: str) -> bool:
    """Check if token is revoked."""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return redis_client.exists(f"token_blacklist:{token_hash}") > 0

# Check revocation on every request
def verify_access_token(token: str):
    if is_token_revoked(token):
        raise HTTPException(
            status_code=401,
            detail="Token has been revoked"
        )
    # Continue with token validation
```

---

## Integration Examples

### Python Client Example

```python
#!/usr/bin/env python3
"""MCP authentication client example."""

import asyncio
import httpx
from datetime import datetime, timedelta, UTC
import jwt
import os

class MCPAuthClient:
    """MCP client with JWT authentication."""

    def __init__(self, base_url: str, user_id: str, token: str = None):
        self.base_url = base_url
        self.user_id = user_id
        self.token = token
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=30.0
        )

    async def list_servers(self) -> list:
        """List all MCP servers."""
        headers = {"Authorization": f"Bearer {self.token}"}
        response = await self.client.get(
            "/api/v1/mcp/servers",
            headers=headers
        )
        response.raise_for_status()
        return response.json()

    async def list_tools(self, server_name: str = None) -> list:
        """List available tools."""
        headers = {"Authorization": f"Bearer {self.token}"}
        params = {"server_name": server_name} if server_name else {}
        response = await self.client.get(
            "/api/v1/mcp/tools",
            headers=headers,
            params=params
        )
        response.raise_for_status()
        return response.json()

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict,
        timeout: int = 60
    ) -> dict:
        """Execute an MCP tool."""
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {
            "arguments": arguments,
            "timeout": timeout
        }
        response = await self.client.post(
            f"/api/v1/mcp/tools/{tool_name}/execute",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

# Usage example
async def main():
    # Load token from environment
    token = os.getenv("MCP_TOKEN")
    if not token:
        raise ValueError("MCP_TOKEN not set")

    # Create client
    client = MCPAuthClient(
        base_url="http://localhost:8000",
        user_id="admin",
        token=token
    )

    try:
        # List servers
        servers = await client.list_servers()
        print(f"Available servers: {len(servers)}")
        for server in servers:
            print(f"  - {server['name']}: {server['status']}")

        # List tools
        tools = await client.list_tools()
        print(f"\nAvailable tools: {len(tools)}")
        for tool in tools[:5]:
            print(f"  - {tool['name']}: {tool['description'][:50]}...")

        # Execute tool
        result = await client.execute_tool(
            tool_name="read_file",
            arguments={"path": "/data/example.txt"}
        )
        print(f"\nTool execution result: {result['success']}")
        if result['success']:
            print(f"Output: {result['result'][:100]}...")

    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### TypeScript/Node.js Client Example

```typescript
// mcp-client.ts - MCP authentication client

import axios, { AxiosInstance } from 'axios';

interface MCPToken {
  access_token: string;
  token_type: string;
  expires_in: number;
}

interface ToolResult {
  success: boolean;
  tool_name: string;
  result: any;
  error?: string;
  execution_time: number;
}

class MCPClient {
  private client: AxiosInstance;
  private token: string;

  constructor(baseURL: string, token: string) {
    this.token = token;
    this.client = axios.create({
      baseURL,
      timeout: 30000,
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
  }

  async listServers() {
    const response = await this.client.get('/api/v1/mcp/servers');
    return response.data;
  }

  async listTools(serverName?: string) {
    const params = serverName ? { server_name: serverName } : {};
    const response = await this.client.get('/api/v1/mcp/tools', { params });
    return response.data;
  }

  async executeTool(
    toolName: string,
    arguments: Record<string, any>,
    timeout: number = 60
  ): Promise<ToolResult> {
    const response = await this.client.post(
      `/api/v1/mcp/tools/${toolName}/execute`,
      {
        arguments,
        timeout
      }
    );
    return response.data as ToolResult;
  }

  async getToolDetails(toolName: string) {
    const response = await this.client.get(`/api/v1/mcp/tools/${toolName}`);
    return response.data;
  }

  async connectServer(
    serverName: string,
    transport: 'stdio' | 'http',
    endpoint: string,
    description?: string
  ) {
    const response = await this.client.post(
      `/api/v1/mcp/servers/${serverName}/connect`,
      {
        transport,
        endpoint,
        description
      }
    );
    return response.data;
  }
}

// Usage example
async function main() {
  const token = process.env.MCP_TOKEN;
  if (!token) {
    throw new Error('MCP_TOKEN environment variable not set');
  }

  const client = new MCPClient('http://localhost:8000', token);

  try {
    // List servers
    const servers = await client.listServers();
    console.log(`Available servers: ${servers.length}`);
    servers.forEach((server: any) => {
      console.log(`  - ${server.name}: ${server.status}`);
    });

    // List tools
    const tools = await client.listTools();
    console.log(`\nAvailable tools: ${tools.length}`);
    tools.slice(0, 5).forEach((tool: any) => {
      console.log(`  - ${tool.name}: ${tool.description.substring(0, 50)}...`);
    });

    // Execute tool
    const result = await client.executeTool(
      'read_file',
      { path: '/data/example.txt' }
    );
    console.log(`\nTool execution: ${result.success ? 'success' : 'failed'}`);
    if (result.success) {
      console.log(`Result: ${JSON.stringify(result.result, null, 2)}`);
    }
  } catch (error) {
    console.error('Error:', error);
  }
}

main();
```

### curl Examples

```bash
# 1. Generate token
TOKEN=$(python scripts/generate_mcp_token.py --user-id admin --expiry 1 | grep "^eyJ" | head -1)
echo "Token: $TOKEN"

# 2. List MCP servers
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/mcp/servers

# 3. List all tools
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/mcp/tools

# 4. Get specific tool details
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/mcp/tools/read_file

# 5. Execute tool
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"path": "/data/example.txt"}, "timeout": 30}' \
  http://localhost:8000/api/v1/mcp/tools/read_file/execute

# 6. Connect to new server
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "transport": "stdio",
    "endpoint": "npx @modelcontextprotocol/server-filesystem /data",
    "description": "Filesystem access"
  }' \
  http://localhost:8000/api/v1/mcp/servers/fs/connect

# 7. Disconnect from server
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/mcp/servers/fs/disconnect

# 8. Check MCP health
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/mcp/health

# 9. Test with invalid token (should fail)
curl -H "Authorization: Bearer invalid.token.here" \
  http://localhost:8000/api/v1/mcp/servers
# Response: 401 Unauthorized

# 10. Test without token (should fail)
curl http://localhost:8000/api/v1/mcp/servers
# Response: 401 Unauthorized
```

---

## References

### Related Documentation
- [MCP Tool Framework](./TOOL_FRAMEWORK_USER_JOURNEY.md)
- [Quick Start Guide](./QUICK_START_GUIDE.md)
- [Monitoring Guide](./MONITORING_GUIDE.md)

### External Resources
- [JWT Introduction](https://jwt.io/introduction)
- [OWASP JWT Security](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)
- [PyJWT Documentation](https://pyjwt.readthedocs.io/)
- [Model Context Protocol](https://modelcontextprotocol.io/)

### Implementation Details
- Token generation: `src/core/auth.py`
- MCP endpoints: `src/api/v1/mcp.py`
- Configuration: `src/core/config.py`
- Token scripts: `scripts/generate_mcp_token.py`, `scripts/validate_mcp_token.py`

---

## Support

For authentication issues:

1. Check [Troubleshooting](#troubleshooting) section
2. Enable debug logging: `export LOG_LEVEL=DEBUG`
3. Validate token: `python scripts/validate_mcp_token.py --token "$TOKEN" --verbose`
4. Review logs: `docker logs aegis-rag-api` (Docker) or check application logs
5. Check security best practices compliance

---

**Document Version:** 1.0.0
**Last Updated:** 2025-12-23
**Status:** Feature 63.7 - MCP Authentication Guide
**Sprint:** Sprint 63
