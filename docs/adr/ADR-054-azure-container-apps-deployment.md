# ADR-054: Azure Container Apps Deployment

## Status
**Proposed** - 2026-01-15 (Sprint 92)

## Context

AegisRAG currently runs on a dedicated NVIDIA DGX Spark server (192.168.178.10) with all services containerized via Docker Compose. For enterprise adoption, cloud deployment options are required. Microsoft Azure is a common choice in enterprise environments, especially for organizations already using Microsoft 365 or Azure AD.

### Current Architecture (DGX Spark)

```
┌─────────────────────────────────────────────────────────────┐
│                    DGX Spark (On-Premises)                  │
├─────────────────────────────────────────────────────────────┤
│  Frontend │ Backend │ Qdrant │ Neo4j │ Redis │ Ollama      │
│  (React)  │(FastAPI)│(Vector)│(Graph)│(Cache)│ (LLM)       │
│    :80    │  :8000  │ :6333  │ :7687 │ :6379 │ :11434      │
└─────────────────────────────────────────────────────────────┘
```

### Requirements for Azure Deployment

1. **Scalability**: Auto-scale based on query load
2. **Cost Efficiency**: Pay-per-use for variable workloads
3. **GPU Support**: Required for embeddings (BGE-M3) and document processing (Docling)
4. **Managed Services**: Reduce operational overhead where possible
5. **Security**: Azure AD integration, VNET isolation
6. **Minimal Code Changes**: Reuse existing Docker containers

## Decision

We will deploy AegisRAG to **Azure Container Apps** for the application layer, combined with Azure managed services for databases and AI capabilities.

### Target Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Azure Container Apps Environment                 │
│                              (Consumption Plan)                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │   aegis-frontend │  │   aegis-backend  │  │   aegis-embedding    │  │
│  │   (React/Vite)   │  │   (FastAPI)      │  │   (BGE-M3 + GPU)     │  │
│  │                  │  │                  │  │                      │  │
│  │   Scale: 0-3     │  │   Scale: 1-10    │  │   Scale: 1-3         │  │
│  │   CPU: 0.5       │  │   CPU: 2.0       │  │   GPU: T4 / A10      │  │
│  │   Memory: 1Gi    │  │   Memory: 4Gi    │  │   Memory: 16Gi       │  │
│  └────────┬─────────┘  └────────┬─────────┘  └──────────┬───────────┘  │
│           │                     │                        │              │
│           └──────────┬──────────┴────────────────────────┘              │
│                      │                                                   │
│              ┌───────▼───────┐                                          │
│              │  Dapr Sidecar │  (Service Discovery, Secrets)            │
│              └───────────────┘                                          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
           ┌────────────────────────┼────────────────────────┐
           │                        │                        │
           ▼                        ▼                        ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐
│ Azure Cache for  │  │ Azure Cosmos DB  │  │ Qdrant on Azure          │
│ Redis            │  │ (Neo4j API or    │  │ Container Apps           │
│                  │  │  Gremlin API)    │  │ (with Azure Files)       │
│ SKU: Standard    │  │                  │  │                          │
│ Size: C1 (1GB)   │  │ Serverless       │  │ Scale: 1-2               │
└──────────────────┘  └──────────────────┘  └──────────────────────────┘
           │                        │                        │
           └────────────────────────┴────────────────────────┘
                                    │
                                    ▼
                      ┌──────────────────────────┐
                      │     Azure OpenAI         │
                      │   (GPT-4o / GPT-4)       │
                      │                          │
                      │   Region: Sweden Central │
                      │   TPM: 80K               │
                      └──────────────────────────┘
```

### Component Mapping

| Current (DGX Spark) | Azure Target | Migration Effort | Notes |
|---------------------|--------------|------------------|-------|
| FastAPI Backend | Container Apps | Low | Same Docker image |
| React Frontend | Container Apps | Low | Same Docker image |
| Qdrant | Container Apps + Azure Files | Medium | Persistent storage needed |
| Neo4j | Azure Cosmos DB (Gremlin) | High | API differences |
| Neo4j | Neo4j AuraDB (Alternative) | Low | Managed Neo4j |
| Redis | Azure Cache for Redis | Low | Drop-in replacement |
| Ollama (LLM) | Azure OpenAI | Medium | Adapter in AegisLLMProxy |
| BGE-M3 Embeddings | Container Apps + GPU | Medium | GPU workload profile |
| Docling (OCR) | Container Apps + GPU | Medium | GPU workload profile |

### Deployment Variants

#### Variant A: Fully Managed (Recommended for Production)

```yaml
# Estimated Monthly Cost: €800-1200

Services:
  - Azure Container Apps (Consumption): €150-300
  - Azure OpenAI (GPT-4o, 80K TPM): €200-400
  - Azure Cache for Redis (C1): €45
  - Neo4j AuraDB (Professional): €200-300
  - Qdrant Cloud (Starter): €100-150
  - Azure Files (100GB): €20
  - GPU Workloads (A10, spot): €100-200
```

#### Variant B: Self-Managed Databases (Cost-Optimized)

```yaml
# Estimated Monthly Cost: €400-700

Services:
  - Azure Container Apps (Consumption): €150-300
  - Azure OpenAI (GPT-4o, 80K TPM): €200-400
  - Azure Cache for Redis (C0): €15
  - Neo4j in Container Apps: €50 (compute)
  - Qdrant in Container Apps: €50 (compute)
  - Azure Files (100GB): €20
  - GPU Workloads (T4, spot): €50-100
```

### Container Apps Configuration

#### Backend Service (aegis-backend)

```yaml
# container-apps/aegis-backend.yaml
properties:
  configuration:
    ingress:
      external: true
      targetPort: 8000
      transport: http
    secrets:
      - name: azure-openai-key
        keyVaultUrl: https://aegis-kv.vault.azure.net/secrets/openai-key
      - name: redis-connection
        keyVaultUrl: https://aegis-kv.vault.azure.net/secrets/redis-conn

  template:
    containers:
      - name: aegis-backend
        image: aegisrag.azurecr.io/aegis-backend:latest
        resources:
          cpu: 2.0
          memory: 4Gi
        env:
          - name: AZURE_OPENAI_ENDPOINT
            value: https://aegis-openai.openai.azure.com/
          - name: AZURE_OPENAI_API_KEY
            secretRef: azure-openai-key
          - name: REDIS_URL
            secretRef: redis-connection
          - name: QDRANT_HOST
            value: aegis-qdrant.internal.azurecontainerapps.io
          - name: NEO4J_URI
            value: neo4j+s://xxxx.databases.neo4j.io

    scale:
      minReplicas: 1
      maxReplicas: 10
      rules:
        - name: http-scaling
          http:
            metadata:
              concurrentRequests: 50
```

#### Embedding Service with GPU

```yaml
# container-apps/aegis-embedding.yaml
properties:
  workloadProfileName: gpu-t4  # GPU workload profile

  template:
    containers:
      - name: aegis-embedding
        image: aegisrag.azurecr.io/aegis-embedding:latest
        resources:
          cpu: 4.0
          memory: 16Gi
          gpu: 1
        env:
          - name: MODEL_NAME
            value: BAAI/bge-m3
          - name: DEVICE
            value: cuda

    scale:
      minReplicas: 1
      maxReplicas: 3
      rules:
        - name: queue-scaling
          azure-queue:
            queueName: embedding-requests
            queueLength: 10
```

### Infrastructure as Code (Bicep)

```bicep
// main.bicep
param location string = 'swedencentral'
param environmentName string = 'aegis-prod'

// Container Apps Environment
resource containerAppEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: '${environmentName}-env'
  location: location
  properties: {
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
      {
        name: 'gpu-t4'
        workloadProfileType: 'NC4as-T4-v3'
        minimumCount: 0
        maximumCount: 3
      }
    ]
  }
}

// Azure Cache for Redis
resource redis 'Microsoft.Cache/redis@2023-08-01' = {
  name: '${environmentName}-redis'
  location: location
  properties: {
    sku: {
      name: 'Standard'
      family: 'C'
      capacity: 1
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
  }
}

// Azure OpenAI
resource openai 'Microsoft.CognitiveServices/accounts@2023-10-01-preview' = {
  name: '${environmentName}-openai'
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: '${environmentName}-openai'
  }
}

// GPT-4o Deployment
resource gpt4o 'Microsoft.CognitiveServices/accounts/deployments@2023-10-01-preview' = {
  parent: openai
  name: 'gpt-4o'
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-08-06'
    }
  }
  sku: {
    name: 'Standard'
    capacity: 80  // 80K TPM
  }
}
```

### Code Changes Required

#### 1. AegisLLMProxy Azure OpenAI Adapter

```python
# src/components/llm/providers/azure_openai.py (NEW FILE)

from openai import AsyncAzureOpenAI
from src.components.llm.base import LLMProvider

class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI provider for AegisLLMProxy."""

    def __init__(self):
        self.client = AsyncAzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-08-01-preview",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        )

    async def generate(
        self,
        prompt: str,
        model: str = "gpt-4o",
        **kwargs
    ) -> str:
        response = await self.client.chat.completions.create(
            model=model,  # deployment name
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        return response.choices[0].message.content
```

#### 2. Environment Configuration

```python
# src/core/config.py - Add Azure settings

class Settings(BaseSettings):
    # Existing settings...

    # Azure-specific settings
    azure_openai_endpoint: str | None = Field(
        default=None,
        description="Azure OpenAI endpoint URL"
    )
    azure_openai_api_key: SecretStr | None = Field(
        default=None,
        description="Azure OpenAI API key"
    )
    azure_openai_deployment: str = Field(
        default="gpt-4o",
        description="Azure OpenAI deployment name"
    )

    # Cloud provider selection
    cloud_provider: Literal["local", "azure", "aws", "gcp"] = Field(
        default="local",
        description="Cloud provider for managed services"
    )
```

### Migration Steps

#### Phase 1: Infrastructure Setup (Week 1)

1. Create Azure Resource Group
2. Deploy Container Apps Environment with GPU workload profile
3. Create Azure Container Registry (ACR)
4. Set up Azure Key Vault for secrets
5. Configure Azure Cache for Redis
6. Set up Neo4j AuraDB or Cosmos DB

#### Phase 2: Container Migration (Week 2)

1. Push Docker images to ACR
2. Deploy Qdrant to Container Apps with Azure Files
3. Deploy embedding service with GPU
4. Deploy backend service
5. Deploy frontend service
6. Configure Dapr for service discovery

#### Phase 3: Integration & Testing (Week 3)

1. Implement Azure OpenAI adapter
2. Update environment configuration
3. Test all retrieval modes (Vector, Graph, Hybrid)
4. Load testing with Azure Load Testing
5. Configure auto-scaling rules

#### Phase 4: Production Readiness (Week 4)

1. Set up Azure Monitor and Application Insights
2. Configure alerts and dashboards
3. Implement backup strategy for Qdrant/Neo4j
4. Document runbooks and procedures
5. Security audit and penetration testing

### Monitoring & Observability

```yaml
# Application Insights integration
APPLICATIONINSIGHTS_CONNECTION_STRING: <from-key-vault>

# Custom metrics to track
metrics:
  - aegis.query.latency_ms
  - aegis.retrieval.vector_results
  - aegis.retrieval.graph_results
  - aegis.embedding.requests_per_minute
  - aegis.llm.tokens_consumed
```

### Security Considerations

1. **Network Isolation**: Use VNET integration for Container Apps
2. **Secrets Management**: All secrets in Azure Key Vault
3. **Identity**: Managed Identity for service-to-service auth
4. **Data Encryption**: TLS 1.3 in transit, Azure-managed keys at rest
5. **RBAC**: Azure AD integration for user authentication

### Cost Optimization Strategies

1. **Spot Instances**: Use spot GPUs for embedding service (70% savings)
2. **Scale to Zero**: Frontend can scale to 0 during off-hours
3. **Reserved Capacity**: 1-year reservation for Redis/Neo4j (40% savings)
4. **Regional Selection**: Sweden Central for EU data residency + good pricing

## Consequences

### Positive

1. **Enterprise Ready**: Azure AD SSO, compliance certifications
2. **Auto-Scaling**: Handle traffic spikes without manual intervention
3. **Reduced Ops**: Managed services reduce maintenance burden
4. **Global Reach**: Easy to deploy to multiple regions
5. **Cost Visibility**: Detailed cost breakdown per service

### Negative

1. **Vendor Lock-in**: Some Azure-specific configurations
2. **Migration Effort**: ~3-4 weeks for full migration
3. **Cost Variability**: GPU costs can spike with high usage
4. **Latency**: Slightly higher than on-prem for embedding/LLM calls

### Risks

1. **Neo4j Migration**: Cosmos DB Gremlin API has different query syntax
   - Mitigation: Use Neo4j AuraDB instead (fully compatible)

2. **GPU Availability**: T4/A10 GPUs may be limited in some regions
   - Mitigation: Use multiple regions, implement queue-based processing

3. **Cold Starts**: Container Apps can have cold start latency
   - Mitigation: Keep minReplicas=1 for critical services

## Alternatives Considered

### Azure Kubernetes Service (AKS)

- **Pros**: More control, existing Helm charts work
- **Cons**: Higher operational complexity, manual scaling configuration
- **Decision**: Rejected for initial deployment, consider for large scale

### Azure App Service

- **Pros**: Simpler deployment model
- **Cons**: No GPU support, less flexible scaling
- **Decision**: Rejected due to GPU requirement

### AWS/GCP

- **Pros**: Potentially lower costs for some services
- **Cons**: Customer requires Azure
- **Decision**: Out of scope for this ADR

## References

- [Azure Container Apps Documentation](https://learn.microsoft.com/azure/container-apps/)
- [Azure OpenAI Service](https://learn.microsoft.com/azure/ai-services/openai/)
- [Neo4j AuraDB on Azure](https://neo4j.com/cloud/platform/aura-graph-database/)
- [Qdrant Cloud](https://qdrant.tech/documentation/cloud/)
- [ADR-033: AegisLLMProxy Multi-Cloud Routing](./ADR-033-mozilla-any-llm-framework.md)
- [ADR-053: Docker Frontend Deployment](./ADR-053-docker-frontend-deployment.md)
