# Graphiti Reference Documentation

**Status:** Reference Material for Future Implementation Review
**Created:** Sprint 13 (2025-10-22)
**Purpose:** Detailed Graphiti API documentation for implementation validation and enhancement

---

## Overview

This document contains the official Graphiti documentation for episodic memory implementation. It serves as a reference to validate our current GraphitiWrapper implementation and guide future enhancements.

**Current Implementation Status (Sprint 13):**
- ✅ Basic Graphiti initialization with Ollama + BGE-M3
- ✅ Constructor updated for Graphiti 0.3.21+ API
- ⏸️ Episode management (to be implemented)
- ⏸️ Custom entity types (to be implemented)
- ⏸️ Communities (to be implemented)
- ⏸️ Graph namespacing (to be implemented)

---

## 1. Adding Episodes

Episodes represent a single data ingestion event. An `episode` is itself a node, and any nodes identified while ingesting the episode are related to the episode via `MENTIONS` edges.

Episodes enable querying for information at a point in time and understanding the provenance of nodes and their edge relationships.

**Supported episode types:**
- `text`: Unstructured text data
- `message`: Conversational messages of the format `speaker: message...`
- `json`: Structured data, processed distinctly from the other types

### 1.1 Adding a `text` or `message` Episode

Using the `EpisodeType.text` type:

```python
await graphiti.add_episode(
    name="tech_innovation_article",
    episode_body=(
        "MIT researchers have unveiled 'ClimateNet', an AI system capable of predicting "
        "climate patterns with unprecedented accuracy. Early tests show it can forecast "
        "major weather events up to three weeks in advance, potentially revolutionizing "
        "disaster preparedness and agricultural planning."
    ),
    source=EpisodeType.text,
    # A description of the source (e.g., "podcast", "news article")
    source_description="Technology magazine article",
    # The timestamp for when this episode occurred or was created
    reference_time=datetime(2023, 11, 15, 9, 30),
)
```

Using the `EpisodeType.message` type supports passing in multi-turn conversations in the `episode_body`.

The text should be structured in `{role/name}: {message}` pairs.

```python
await graphiti.add_episode(
    name="Customer_Support_Interaction_1",
    episode_body=(
        "Customer: Hi, I'm having trouble with my Allbirds shoes. "
        "The sole is coming off after only 2 months of use.\n"
        "Support: I'm sorry to hear that. Can you please provide your order number?"
    ),
    source=EpisodeType.message,
    source_description="Customer support chat",
    reference_time=datetime(2024, 3, 15, 14, 45),
)
```

### 1.2 Adding an Episode using structured data in JSON format

JSON documents can be arbitrarily nested. However, it's advisable to keep documents compact, as they must fit within your LLM's context window.

> **Note:** For large data imports, consider using the `add_episode_bulk` API to efficiently add multiple episodes at once.

```python
product_data = {
    "id": "PROD001",
    "name": "Men's SuperLight Wool Runners",
    "color": "Dark Grey",
    "sole_color": "Medium Grey",
    "material": "Wool",
    "technology": "SuperLight Foam",
    "price": 125.00,
    "in_stock": True,
    "last_updated": "2024-03-15T10:30:00Z"
}

# Add the episode to the graph
await graphiti.add_episode(
    name="Product Update - PROD001",
    episode_body=product_data,  # Pass the Python dictionary directly
    source=EpisodeType.json,
    source_description="Allbirds product catalog update",
    reference_time=datetime.now(),
)
```

### 1.3 Loading Episodes in Bulk

Graphiti offers `add_episode_bulk` for efficient batch ingestion of episodes, significantly outperforming `add_episode` for large datasets. This method is highly recommended for bulk loading.

> **Warning:** Use `add_episode_bulk` only for populating empty graphs or when edge invalidation is not required. The bulk ingestion pipeline does not perform edge invalidation operations.

```python
product_data = [
    {
        "id": "PROD001",
        "name": "Men's SuperLight Wool Runners",
        "color": "Dark Grey",
        "sole_color": "Medium Grey",
        "material": "Wool",
        "technology": "SuperLight Foam",
        "price": 125.00,
        "in_stock": True,
        "last_updated": "2024-03-15T10:30:00Z"
    },
    # ...
    {
        "id": "PROD0100",
        "name": "Kids Wool Runner-up Mizzles",
        "color": "Natural Grey",
        "sole_color": "Orange",
        "material": "Wool",
        "technology": "Water-repellent",
        "price": 80.00,
        "in_stock": True,
        "last_updated": "2024-03-17T14:45:00Z"
    }
]

# Prepare the episodes for bulk loading
bulk_episodes = [
    RawEpisode(
        name=f"Product Update - {product['id']}",
        content=json.dumps(product),
        source=EpisodeType.json,
        source_description="Allbirds product catalog update",
        reference_time=datetime.now()
    )
    for product in product_data
]

await graphiti.add_episode_bulk(bulk_episodes)
```

---

## 2. Custom Entity and Edge Types

Graphiti allows you to define custom entity types and edge types to better represent your domain-specific knowledge. This enables more structured data extraction and richer semantic relationships in your knowledge graph.

### 2.1 Defining Custom Entity and Edge Types

Custom entity types and edge types are defined using Pydantic models. Each model represents a specific type with custom attributes.

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

# Custom Entity Types
class Person(BaseModel):
    """A person entity with biographical information."""
    age: Optional[int] = Field(None, description="Age of the person")
    occupation: Optional[str] = Field(None, description="Current occupation")
    location: Optional[str] = Field(None, description="Current location")
    birth_date: Optional[datetime] = Field(None, description="Date of birth")

class Company(BaseModel):
    """A business organization."""
    industry: Optional[str] = Field(None, description="Primary industry")
    founded_year: Optional[int] = Field(None, description="Year company was founded")
    headquarters: Optional[str] = Field(None, description="Location of headquarters")
    employee_count: Optional[int] = Field(None, description="Number of employees")

class Product(BaseModel):
    """A product or service."""
    category: Optional[str] = Field(None, description="Product category")
    price: Optional[float] = Field(None, description="Price in USD")
    release_date: Optional[datetime] = Field(None, description="Product release date")

# Custom Edge Types
class Employment(BaseModel):
    """Employment relationship between a person and company."""
    position: Optional[str] = Field(None, description="Job title or position")
    start_date: Optional[datetime] = Field(None, description="Employment start date")
    end_date: Optional[datetime] = Field(None, description="Employment end date")
    salary: Optional[float] = Field(None, description="Annual salary in USD")
    is_current: Optional[bool] = Field(None, description="Whether employment is current")

class Investment(BaseModel):
    """Investment relationship between entities."""
    amount: Optional[float] = Field(None, description="Investment amount in USD")
    investment_type: Optional[str] = Field(None, description="Type of investment (equity, debt, etc.)")
    stake_percentage: Optional[float] = Field(None, description="Percentage ownership")
    investment_date: Optional[datetime] = Field(None, description="Date of investment")

class Partnership(BaseModel):
    """Partnership relationship between companies."""
    partnership_type: Optional[str] = Field(None, description="Type of partnership")
    duration: Optional[str] = Field(None, description="Expected duration")
    deal_value: Optional[float] = Field(None, description="Financial value of partnership")
```

### 2.2 Using Custom Entity and Edge Types

Pass your custom entity types and edge types to the add_episode method:

```python
entity_types = {
    "Person": Person,
    "Company": Company,
    "Product": Product
}

edge_types = {
    "Employment": Employment,
    "Investment": Investment,
    "Partnership": Partnership
}

edge_type_map = {
    ("Person", "Company"): ["Employment"],
    ("Company", "Company"): ["Partnership", "Investment"],
    ("Person", "Person"): ["Partnership"],
    ("Entity", "Entity"): ["Investment"],  # Apply to any entity type
}

await graphiti.add_episode(
    name="Business Update",
    episode_body="Sarah joined TechCorp as CTO in January 2023 with a $200K salary. TechCorp partnered with DataCorp in a $5M deal.",
    source_description="Business news",
    reference_time=datetime.now(),
    entity_types=entity_types,
    edge_types=edge_types,
    edge_type_map=edge_type_map
)
```

### 2.3 Searching with Custom Types

You can filter search results to specific entity types or edge types using SearchFilters:

```python
from graphiti_core.search.search_filters import SearchFilters

# Search for only specific entity types
search_filter = SearchFilters(
    node_labels=["Person", "Company"]  # Only return Person and Company entities
)

results = await graphiti.search_(
    query="Who works at tech companies?",
    search_filter=search_filter
)

# Search for only specific edge types
search_filter = SearchFilters(
    edge_types=["Employment", "Partnership"]  # Only return Employment and Partnership edges
)

results = await graphiti.search_(
    query="Tell me about business relationships",
    search_filter=search_filter
)
```

### 2.4 Best Practices for Custom Types

#### Model Design

- **Clear Descriptions**: Always include detailed descriptions in docstrings and Field descriptions
- **Optional Fields**: Make custom attributes optional to handle cases where information isn't available
- **Appropriate Types**: Use specific types (datetime, int, float) rather than strings when possible
- **Validation**: Consider adding Pydantic validators for complex validation rules
- **Atomic Attributes**: Attributes should be broken down into their smallest meaningful units

```python
from pydantic import validator

class Person(BaseModel):
    """A person entity."""
    age: Optional[int] = Field(None, description="Age in years")

    @validator('age')
    def validate_age(cls, v):
        if v is not None and (v < 0 or v > 150):
            raise ValueError('Age must be between 0 and 150')
        return v
```

**Instead of compound information:**
```python
class Customer(BaseModel):
    contact_info: Optional[str] = Field(None, description="Name and email")  # Don't do this
```

**Use atomic attributes:**
```python
class Customer(BaseModel):
    name: Optional[str] = Field(None, description="Customer name")
    email: Optional[str] = Field(None, description="Customer email address")
```

#### Naming Conventions

- **Entity Types**: Use PascalCase (e.g., Person, TechCompany)
- **Edge Types**: Use PascalCase for custom types (e.g., Employment, Partnership)
- **Attributes**: Use snake_case (e.g., start_date, employee_count)
- **Descriptions**: Be specific and actionable for the LLM
- **Consistency**: Maintain consistent naming conventions across related entity types

#### Protected Attribute Names

Custom entity type attributes cannot use protected names that are already used by Graphiti's core EntityNode class:
- `uuid`, `name`, `group_id`, `labels`, `created_at`, `summary`, `attributes`, `name_embedding`

---

## 3. Communities

In Graphiti, communities (represented as `CommunityNode` objects) represent groups of related entity nodes. Communities can be generated using the `build_communities` method on the graphiti class.

```python
await graphiti.build_communities()
```

Communities are determined using the **Leiden algorithm**, which groups strongly connected nodes together. Communities contain a summary field that collates the summaries held on each of its member entities. This allows Graphiti to provide high-level synthesized information about what the graph contains in addition to the more granular facts stored on edges.

### 3.1 Updating Communities

Once communities are built, they can also be updated with new episodes by passing in `update_communities=True` to the `add_episode` method.

```python
await graphiti.add_episode(
    name="new_episode",
    episode_body="Some new information",
    source=EpisodeType.text,
    source_description="New data",
    reference_time=datetime.now(),
    update_communities=True  # Update communities with this episode
)
```

If a new node is added to the graph, we will determine which community it should be added to based on the most represented community of the new node's surrounding nodes. This updating methodology is inspired by the label propagation algorithm for determining communities.

### 3.2 Rebuilding Communities

We still recommend periodically rebuilding communities to ensure the most optimal grouping. Whenever the `build_communities` method is called it will remove any existing communities before creating new ones.

---

## 4. Graph Namespacing

Graphiti supports the concept of graph namespacing through the use of `group_id` parameters. This feature allows you to create isolated graph environments within the same Graphiti instance, enabling multiple distinct knowledge graphs to coexist without interference.

### 4.1 Use Cases for Namespacing

Graph namespacing is particularly useful for:

- **Multi-tenant applications**: Isolate data between different customers or organizations
- **Testing environments**: Maintain separate development, testing, and production graphs
- **Domain-specific knowledge**: Create specialized graphs for different domains or use cases
- **Team collaboration**: Allow different teams to work with their own graph spaces

### 4.2 Key Benefits

- **Data isolation**: Prevent data leakage between different namespaces
- **Simplified management**: Organize and manage related data together
- **Performance optimization**: Improve query performance by limiting the search space
- **Flexible architecture**: Support multiple use cases within a single Graphiti instance

### 4.3 Adding Episodes with group_id

When adding episodes to your graph, you can specify a `group_id` to namespace the episode and all its extracted entities:

```python
await graphiti.add_episode(
    name="customer_interaction",
    episode_body="Customer Jane mentioned she loves our new SuperLight Wool Runners in Dark Grey.",
    source=EpisodeType.text,
    source_description="Customer feedback",
    reference_time=datetime.now(),
    group_id="customer_team"  # This namespaces the episode and its entities
)
```

### 4.4 Adding Fact Triples with group_id

When manually adding fact triples, ensure both nodes and the edge share the same `group_id`:

```python
from graphiti_core.nodes import EntityNode
from graphiti_core.edges import EntityEdge
import uuid
from datetime import datetime

# Define a namespace for this data
namespace = "product_catalog"

# Create source and target nodes with the namespace
source_node = EntityNode(
    uuid=str(uuid.uuid4()),
    name="SuperLight Wool Runners",
    group_id=namespace  # Apply namespace to source node
)

target_node = EntityNode(
    uuid=str(uuid.uuid4()),
    name="Sustainable Footwear",
    group_id=namespace  # Apply namespace to target node
)

# Create an edge with the same namespace
edge = EntityEdge(
    group_id=namespace,  # Apply namespace to edge
    source_node_uuid=source_node.uuid,
    target_node_uuid=target_node.uuid,
    created_at=datetime.now(),
    name="is_category_of",
    fact="SuperLight Wool Runners is a product in the Sustainable Footwear category"
)

# Add the triplet to the graph
await graphiti.add_triplet(source_node, edge, target_node)
```

### 4.5 Querying Within a Namespace

When querying the graph, specify the `group_id` to limit results to a particular namespace:

```python
# Search within a specific namespace
search_results = await graphiti.search(
    query="Wool Runners",
    group_id="product_catalog"  # Only search within this namespace
)

# For more advanced node-specific searches, use the _search method with a recipe
from graphiti_core.search.search_config_recipes import NODE_HYBRID_SEARCH_RRF

# Create a search config for nodes only
node_search_config = NODE_HYBRID_SEARCH_RRF.model_copy(deep=True)
node_search_config.limit = 5  # Limit to 5 results

# Execute the node search within a specific namespace
node_search_results = await graphiti._search(
    query="SuperLight Wool Runners",
    group_id="product_catalog",  # Only search within this namespace
    config=node_search_config
)
```

### 4.6 Best Practices for Graph Namespacing

1. **Consistent naming**: Use a consistent naming convention for your `group_id` values
2. **Documentation**: Maintain documentation of your namespace structure and purpose
3. **Granularity**: Choose an appropriate level of granularity for your namespaces
   - Too many namespaces can lead to fragmented data
   - Too few namespaces may not provide sufficient isolation
4. **Cross-namespace queries**: When necessary, perform multiple queries across namespaces and combine results in your application logic

### 4.7 Example: Multi-tenant Application

Here's an example of using namespacing in a multi-tenant application:

```python
async def add_customer_data(tenant_id, customer_data):
    """Add customer data to a tenant-specific namespace"""

    # Use the tenant_id as the namespace
    namespace = f"tenant_{tenant_id}"

    # Create an episode for this customer data
    await graphiti.add_episode(
        name=f"customer_data_{customer_data['id']}",
        episode_body=customer_data,
        source=EpisodeType.json,
        source_description="Customer profile update",
        reference_time=datetime.now(),
        group_id=namespace  # Namespace by tenant
    )

async def search_tenant_data(tenant_id, query):
    """Search within a tenant's namespace"""

    namespace = f"tenant_{tenant_id}"

    # Only search within this tenant's namespace
    return await graphiti.search(
        query=query,
        group_id=namespace
    )
```

---

## 5. Implementation Gaps & Future Work

### Current AEGIS RAG Implementation (Sprint 13)

Our current `GraphitiWrapper` implementation (`src/components/memory/graphiti_wrapper.py`) covers:

✅ **Basic Initialization**
- Graphiti client setup with Ollama
- BGE-M3 embedder configuration (1024-dim)
- OpenAI-compatible LLM client
- Cross-encoder reranker

✅ **Episode Management (Basic)**
- `add_episode()` method implemented
- Supports text-based episodes
- Session ID for episode grouping

✅ **Search Functionality**
- `search_episodes()` method implemented
- SearchConfig support

⚠️ **Partially Implemented**
- Edge management (add_edge exists but not fully utilized)
- Metadata support (partially implemented)

### Missing Features (To Be Implemented)

❌ **Episode Types**
- Message type episodes (multi-turn conversations)
- JSON type episodes (structured data)
- Bulk episode loading (`add_episode_bulk`)

❌ **Custom Entity & Edge Types**
- Pydantic model definitions
- Entity type extraction
- Edge type mapping
- SearchFilters for type-specific queries

❌ **Communities**
- `build_communities()` implementation
- Community updates on episode addition
- Community-based search

❌ **Graph Namespacing**
- `group_id` parameter support in all methods
- Multi-tenant isolation
- Namespace-specific queries

❌ **Advanced Features**
- Entity type exclusion
- Protected attribute validation
- Schema evolution support

### Recommended Implementation Order

**Post-Sprint 13 Priorities:**

1. **Sprint 14-15: Enhanced Episode Management**
   - Add support for message and JSON episode types
   - Implement bulk episode loading
   - Add episode metadata enrichment

2. **Sprint 16-17: Custom Entity Types**
   - Define AEGIS RAG domain entities (User, Query, Document, etc.)
   - Implement entity type extraction
   - Add entity-specific search filters

3. **Sprint 18-19: Communities & Graph Analysis**
   - Implement community detection
   - Add community-based retrieval
   - Create visualization tools

4. **Sprint 20+: Multi-tenancy Support**
   - Implement graph namespacing
   - Add tenant isolation
   - Create namespace management tools

---

## 6. Searching the Graph

Graphiti provides powerful search capabilities to retrieve information from your knowledge graph. Two main approaches are available:

### 6.1 Hybrid Search

Combines semantic similarity and BM25 retrieval, reranked using Reciprocal Rank Fusion:

```python
results = await graphiti.search(query)
```

**Example:** Broad retrieval of facts related to a query.

### 6.2 Node Distance Reranking

Extends Hybrid Search by prioritizing results based on proximity to a specified node in the graph:

```python
results = await graphiti.search(query, focal_node_uuid)
```

**Example:** Entity-specific queries, providing more contextually relevant results.

Node Distance Reranking weights facts by their closeness to the focal node, emphasizing information directly related to the entity of interest.

### 6.3 Search Example

```python
query = "Can Jane wear Allbirds Wool Runners?"
jane_node_uuid = "123e4567-e89b-12d3-a456-426614174000"

def print_facts(edges):
    print("\n".join([edge.fact for edge in edges]))

# Hybrid Search
results = await graphiti.search(query)
print_facts(results)
# Output:
# > The Allbirds Wool Runners are sold by Allbirds.
# > Men's SuperLight Wool Runners - Dark Grey (Medium Grey Sole) has a runner silhouette.
# > Jane purchased SuperLight Wool Runners.

# Hybrid Search with Node Distance Reranking
results = await graphiti.search(query, jane_node_uuid)
print_facts(results)
# Output:
# > Jane purchased SuperLight Wool Runners.
# > Jane is allergic to wool.
# > The Allbirds Wool Runners are sold by Allbirds.
```

### 6.4 Configurable Search Strategies

Graphiti provides a low-level search method `graphiti._search()` with configurable `SearchConfig` parameters:

```python
from graphiti_core.search.search_config_recipes import NODE_HYBRID_SEARCH_RRF

# Create a search config for nodes only
node_search_config = NODE_HYBRID_SEARCH_RRF.model_copy(deep=True)
node_search_config.limit = 5

# Execute the node search
node_search_results = await graphiti._search(
    query="SuperLight Wool Runners",
    group_id="product_catalog",
    config=node_search_config
)
```

### 6.5 Search Config Recipes

Graphiti provides 15 pre-built `SearchConfig` recipes for common use cases:

| Search Type | Description |
|-------------|-------------|
| **COMBINED_HYBRID_SEARCH_RRF** | Hybrid search with RRF reranking over edges, nodes, and communities |
| **COMBINED_HYBRID_SEARCH_MMR** | Hybrid search with MMR reranking over edges, nodes, and communities |
| **COMBINED_HYBRID_SEARCH_CROSS_ENCODER** | Full-text + similarity + BFS with cross_encoder reranking |
| **EDGE_HYBRID_SEARCH_RRF** | Hybrid search over edges with RRF reranking |
| **EDGE_HYBRID_SEARCH_MMR** | Hybrid search over edges with MMR reranking |
| **EDGE_HYBRID_SEARCH_NODE_DISTANCE** | Hybrid search over edges with node distance reranking |
| **EDGE_HYBRID_SEARCH_EPISODE_MENTIONS** | Hybrid search over edges with episode mention reranking |
| **EDGE_HYBRID_SEARCH_CROSS_ENCODER** | Hybrid search over edges with cross encoder reranking |
| **NODE_HYBRID_SEARCH_RRF** | Hybrid search over nodes with RRF reranking |
| **NODE_HYBRID_SEARCH_MMR** | Hybrid search over nodes with MMR reranking |
| **NODE_HYBRID_SEARCH_NODE_DISTANCE** | Hybrid search over nodes with node distance reranking |
| **NODE_HYBRID_SEARCH_EPISODE_MENTIONS** | Hybrid search over nodes with episode mentions reranking |
| **NODE_HYBRID_SEARCH_CROSS_ENCODER** | Hybrid search over nodes with cross encoder reranking |
| **COMMUNITY_HYBRID_SEARCH_RRF** | Hybrid search over communities with RRF reranking |
| **COMMUNITY_HYBRID_SEARCH_MMR** | Hybrid search over communities with MMR reranking |
| **COMMUNITY_HYBRID_SEARCH_CROSS_ENCODER** | Hybrid search over communities with cross encoder reranking |

### 6.6 Supported Reranking Approaches

#### Reciprocal Rank Fusion (RRF)
Combines results from different algorithms (BM25, semantic search) by converting ranks to reciprocal scores (1/rank) and summing them. The aggregated score determines the final ranking, leveraging the strengths of each method.

#### Maximal Marginal Relevance (MMR)
Balances relevance and diversity in results. Selects results that are both relevant to the query and diverse from already chosen ones, reducing redundancy and covering different query aspects.

#### Cross-Encoder
Jointly encodes query and result, scoring their relevance by considering their combined context. More accurate than methods that encode separately.

**Supported Cross Encoders:**
- `OpenAIRerankerClient` (default) - Uses OpenAI model with `logprobs` for reranking
- `GeminiRerankerClient` - Uses Google Gemini for cost-effective, low-latency reranking
- `BGERerankerClient` - Uses `BAAI/bge-reranker-v2-m3` (requires `sentence_transformers`)

---

## 7. CRUD Operations

Graphiti uses 8 core classes for data management:

**Base Classes:**
- `Node` (abstract)
- `Edge` (abstract)

**Concrete Classes:**
- `EpisodicNode`
- `EntityNode`
- `EpisodicEdge`
- `EntityEdge`
- `CommunityNode`
- `CommunityEdge`

Each concrete class has fully supported CRUD operations.

### 7.1 Save (Create/Update)

The `save()` method performs find-or-create based on UUID and updates data:

```python
async def save(self, driver: AsyncDriver):
    result = await driver.execute_query(
        """
        MERGE (n:Entity {uuid: $uuid})
        SET n = {
            uuid: $uuid,
            name: $name,
            name_embedding: $name_embedding,
            summary: $summary,
            created_at: $created_at
        }
        RETURN n.uuid AS uuid
        """,
        uuid=self.uuid,
        name=self.name,
        summary=self.summary,
        name_embedding=self.name_embedding,
        created_at=self.created_at,
    )
    logger.info(f'Saved Node to neo4j: {self.uuid}')
    return result
```

### 7.2 Delete

Hard delete nodes and edges:

```python
async def delete(self, driver: AsyncDriver):
    result = await driver.execute_query(
        """
        MATCH (n:Entity {uuid: $uuid})
        DETACH DELETE n
        """,
        uuid=self.uuid,
    )
    logger.info(f'Deleted Node: {self.uuid}')
    return result
```

### 7.3 Get by UUID

Class method to retrieve nodes/edges:

```python
@classmethod
async def get_by_uuid(cls, driver: AsyncDriver, uuid: str):
    records, _, _ = await driver.execute_query(
        """
        MATCH (n:Entity {uuid: $uuid})
        RETURN
            n.uuid As uuid,
            n.name AS name,
            n.created_at AS created_at,
            n.summary AS summary
        """,
        uuid=uuid,
    )

    nodes: list[EntityNode] = []
    for record in records:
        nodes.append(
            EntityNode(
                uuid=record['uuid'],
                name=record['name'],
                labels=['Entity'],
                created_at=record['created_at'].to_native(),
                summary=record['summary'],
            )
        )
    logger.info(f'Found Node: {uuid}')
    return nodes[0]
```

---

## 8. Adding Fact Triples

A "fact triple" consists of two nodes and an edge between them, where the edge typically contains some fact.

### 8.1 Manual Fact Triple Creation

```python
from graphiti_core.nodes import EpisodeType, EntityNode
from graphiti_core.edges import EntityEdge
import uuid
from datetime import datetime

source_name = "Bob"
target_name = "bananas"
source_uuid = "some existing UUID"  # Existing node UUID from Neo4j
target_uuid = str(uuid.uuid4())     # New node, create new UUID
edge_name = "LIKES"
edge_fact = "Bob likes bananas"

source_node = EntityNode(
    uuid=source_uuid,
    name=source_name,
    group_id=""
)

target_node = EntityNode(
    uuid=target_uuid,
    name=target_name,
    group_id=""
)

edge = EntityEdge(
    group_id="",
    source_node_uuid=source_uuid,
    target_node_uuid=target_uuid,
    created_at=datetime.now(),
    name=edge_name,
    fact=edge_fact
)

await graphiti.add_triplet(source_node, edge, target_node)
```

### 8.2 Deduplication

When you add a fact triple, Graphiti will attempt to deduplicate your passed-in nodes and edge with existing nodes and edges in the graph. If there are no duplicates, it will add them as new nodes and edges.

### 8.3 Using Search Results

You can avoid constructing `EntityEdge` or `EntityNode` objects manually by using the results of a Graphiti search.

---

## 9. LangGraph Integration

Example of building an agent using LangGraph with Graphiti for personalized responses.

### 9.1 Key Features

- **Memory Persistence**: New chat turns persisted to Graphiti
- **Contextual Recall**: Relevant facts retrieved using most recent message
- **Tool Integration**: Query Graphiti for domain-specific information
- **State Management**: In-memory `MemorySaver` for agent state

### 9.2 Basic Setup

```python
from graphiti_core import Graphiti
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

# Initialize Graphiti
client = Graphiti(
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j",
    neo4j_password="password",
)

# Initialize LLM
llm = ChatOpenAI(model='gpt-4o-mini', temperature=0)
```

### 9.3 Tool Creation

```python
from langchain_core.tools import tool

@tool
async def get_shoe_data(query: str) -> str:
    """Search the graphiti graph for information about shoes"""
    edge_results = await client.search(
        query,
        center_node_uuid=manybirds_node_uuid,
        num_results=10,
    )
    return edges_to_facts_string(edge_results)
```

### 9.4 Chatbot Function

```python
from langchain_core.messages import SystemMessage

async def chatbot(state: State):
    # Retrieve context from Graphiti
    if len(state['messages']) > 0:
        last_message = state['messages'][-1]
        graphiti_query = f'{state["user_name"]}: {last_message.content}'

        # Search centered on user node
        edge_results = await client.search(
            graphiti_query,
            center_node_uuid=state['user_node_uuid'],
            num_results=5
        )
        facts_string = edges_to_facts_string(edge_results)

    # Create system message with facts
    system_message = SystemMessage(
        content=f"""You are a helpful assistant. Use the following facts:
        {facts_string or 'No facts available'}"""
    )

    messages = [system_message] + state['messages']
    response = await llm.ainvoke(messages)

    # Persist conversation to Graphiti (async)
    asyncio.create_task(
        client.add_episode(
            name='Chatbot Response',
            episode_body=f"{state['user_name']}: {state['messages'][-1]}\nBot: {response.content}",
            source=EpisodeType.message,
            reference_time=datetime.now(),
        )
    )

    return {'messages': [response]}
```

### 9.5 Graph Construction

```python
graph_builder = StateGraph(State)
memory = MemorySaver()

graph_builder.add_node('agent', chatbot)
graph_builder.add_node('tools', tool_node)

graph_builder.add_edge(START, 'agent')
graph_builder.add_conditional_edges(
    'agent',
    should_continue,
    {'continue': 'tools', 'end': END}
)
graph_builder.add_edge('tools', 'agent')

graph = graph_builder.compile(checkpointer=memory)
```

### 9.6 Running the Agent

```python
await graph.ainvoke(
    {
        'messages': [
            {'role': 'user', 'content': 'What shoes do you recommend?'}
        ],
        'user_name': 'jess',
        'user_node_uuid': user_node_uuid,
    },
    config={'configurable': {'thread_id': uuid.uuid4().hex}},
)
```

---

## 10. Telemetry

Graphiti collects anonymous usage statistics to improve the framework.

### 10.1 What is Collected

- Anonymous UUID (stored in `~/.cache/graphiti/telemetry_anon_id`)
- System information (OS, Python version, architecture)
- Graphiti version
- Configuration choices (LLM provider, database backend, embedder)

### 10.2 What is NOT Collected

- Personal information or identifiers
- API keys or credentials
- Data, queries, or graph content
- IP addresses or hostnames
- File paths or system information
- Episode, node, or edge content

### 10.3 How to Disable

**Option 1: Environment Variable**
```bash
export GRAPHITI_TELEMETRY_ENABLED=false
```

**Option 2: Shell Profile**
```bash
# For bash
echo 'export GRAPHITI_TELEMETRY_ENABLED=false' >> ~/.bashrc

# For zsh
echo 'export GRAPHITI_TELEMETRY_ENABLED=false' >> ~/.zshrc
```

**Option 3: Python Session**
```python
import os
os.environ['GRAPHITI_TELEMETRY_ENABLED'] = 'false'
```

Telemetry is automatically disabled during test runs (when `pytest` is detected).

---

## 11. References

- **Graphiti Documentation**: https://help.getzep.com/graphiti/
- **Graphiti GitHub**: https://github.com/getzep/graphiti
- **Graphiti PyPI**: https://pypi.org/project/graphiti-core/
- **AEGIS RAG Implementation**: `src/components/memory/graphiti_wrapper.py`
- **Sprint 13 ADR-016**: BGE-M3 Embedding Model Decision

---

**Document Status:** Reference Material
**Last Updated:** Sprint 13 (2025-10-22)
**Next Review:** Sprint 14 Planning

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
