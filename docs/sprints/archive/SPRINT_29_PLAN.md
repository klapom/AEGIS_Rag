# Sprint 29 Plan: Interactive Graph Visualization Frontend

**Sprint Goal:** Implement comprehensive graph visualization frontend for end users and admins
**Duration:** 7-9 days (estimated)
**Story Points:** 36 SP
**Priority:** HIGH (User-Requested Feature)
**Start Date:** TBD (After Sprint 28 CI fixes)
**Branch:** `sprint-29-graph-viz-frontend`

---

## Executive Summary

Sprint 29 delivers **interactive graph visualization** for AegisRAG's knowledge graph, enabling end users to explore query results visually and admins to analyze the entire knowledge graph with community detection.

**Key Deliverables:**
1. Interactive Graph Viewer with pan/zoom/search
2. Query Result Graph (end user feature)
3. Admin Graph Analytics Dashboard
4. Knowledge Graph Explorer with filters
5. Embedding-based document discovery from graph nodes
6. Community-to-Document browser
7. Graph statistics and health metrics

**User-Requested Use Cases:**
1. ✅ End user sees query result relationships visually
2. ✅ Admin views entire graph with communities
3. ✅ Knowledge Graph Dashboard (statistics, top communities)
4. ✅ Graph Explorer (search, filter, navigate)
5. ✅ Pan, Zoom, Node-Search, Community-Highlighting
6. ✅ Embedding search from graph node → related documents
7. ✅ Documents belonging to specific communities

---

## Technical Architecture

### Frontend Stack Decision

**Recommended Library:** `react-force-graph` (3D/2D)

**Comparison:**

| Library | Pros | Cons | Verdict |
|---------|------|------|---------|
| **react-force-graph** | ✅ Physics-based layout (beautiful)<br>✅ 3D/2D modes<br>✅ Excellent performance (WebGL)<br>✅ Active maintenance | ❌ Learning curve for 3D controls | **RECOMMENDED** |
| cytoscape.js | ✅ Mature ecosystem<br>✅ Multiple layouts (force, hierarchical, circular)<br>✅ Good documentation | ❌ More complex API<br>❌ 2D only | Good alternative |
| vis.js | ✅ Simple API<br>✅ Good physics | ❌ Archived (no maintenance)<br>❌ Performance issues | ❌ NOT recommended |
| react-graph-vis | ✅ React wrapper for vis.js | ❌ Based on archived library | ❌ NOT recommended |

**Decision:** Use `react-force-graph` (2D mode) with fallback to cytoscape.js if physics becomes problematic.

**Installation:**
```bash
cd frontend
npm install react-force-graph
npm install @types/react-force-graph --save-dev
```

---

### Component Architecture

```
frontend/src/
├── pages/
│   ├── GraphVisualizationPage.tsx        # Main graph page (Feature 29.2 + 29.5)
│   └── admin/
│       └── GraphAnalyticsPage.tsx        # Admin-only (Feature 29.3)
├── components/
│   ├── graph/
│   │   ├── GraphViewer.tsx               # Core 3D/2D graph (Feature 29.1)
│   │   ├── GraphControls.tsx             # Pan/Zoom/Reset controls
│   │   ├── GraphSearch.tsx               # Node search (Feature 29.5)
│   │   ├── CommunityHighlight.tsx        # Community highlighting (Feature 29.5)
│   │   ├── NodeDetailsPanel.tsx          # Selected node info + docs (Feature 29.6)
│   │   ├── CommunityDocuments.tsx        # Community → Documents (Feature 29.7)
│   │   ├── GraphFilters.tsx              # Entity type, min degree filters
│   │   └── GraphExportButton.tsx         # Export JSON/GraphML
│   ├── dashboard/
│   │   ├── KnowledgeGraphDashboard.tsx   # Statistics dashboard (Feature 29.4)
│   │   ├── GraphStatistics.tsx           # Node/Edge/Community counts
│   │   └── TopCommunities.tsx            # Top 10 communities by size
│   └── layout/
│       └── GraphLayout.tsx               # Layout wrapper with sidebar
├── api/
│   └── graphViz.ts                       # API client for /api/v1/graph/viz/*
├── hooks/
│   ├── useGraphData.ts                   # Fetch graph data
│   ├── useGraphSearch.ts                 # Node search logic
│   └── useDocumentsByNode.ts             # Embedding-based doc search
└── types/
    └── graph.ts                          # Graph data types
```

---

## Features Overview

| ID | Feature | SP | Priority | Dependencies | Status |
|----|---------|----|---------| -------------|--------|
| 29.1 | Interactive Graph Viewer (Base) | 5 | 🔴 CRITICAL | None | 📋 TODO |
| 29.2 | Query Result Graph (End User) | 3 | 🔴 HIGH | 29.1 | 📋 TODO |
| 29.3 | Admin Graph Analytics View | 5 | 🟠 MEDIUM | 29.1 | 📋 TODO |
| 29.4 | Knowledge Graph Dashboard | 5 | 🟠 MEDIUM | 29.1 | 📋 TODO |
| 29.5 | Graph Explorer with Search | 5 | 🟠 MEDIUM | 29.1 | 📋 TODO |
| 29.6 | Embedding Document Search | 8 | 🟡 LOW | 29.1, 29.5 | 📋 TODO |
| 29.7 | Community Document Browser | 5 | 🟡 LOW | 29.1, 29.4 | 📋 TODO |
| **TOTAL** | | **36** | | | |

---

## Feature Specifications

### Feature 29.1: Interactive Graph Viewer (Base Component) - 5 SP

**Priority:** 🔴 CRITICAL (Foundation for all other features)

**Description:**
Base React component for rendering knowledge graphs with pan, zoom, and basic interactions using `react-force-graph`.

**Technical Details:**
- **Library:** `react-force-graph` (2D mode)
- **API Integration:** `GET /api/v1/graph/viz/export` (JSON format)
- **Node Styling:** Color by entity type, size by degree
- **Edge Styling:** Arrow heads, thickness by relationship weight
- **Physics:** Force-directed layout with configurable parameters

**Implementation:**

```typescript
// frontend/src/components/graph/GraphViewer.tsx
import ForceGraph2D from 'react-force-graph-2d';
import { useGraphData } from '@/hooks/useGraphData';

interface GraphViewerProps {
  maxNodes?: number;
  entityTypes?: string[];
  highlightCommunities?: string[];
}

export const GraphViewer: React.FC<GraphViewerProps> = ({
  maxNodes = 100,
  entityTypes,
  highlightCommunities
}) => {
  const { data, loading } = useGraphData({ maxNodes, entityTypes });

  if (loading) return <GraphSkeleton />;

  return (
    <ForceGraph2D
      graphData={data}
      nodeLabel="label"
      nodeColor={(node) => getColorByType(node.type)}
      nodeVal={(node) => node.degree || 1}
      linkDirectionalArrowLength={3.5}
      linkDirectionalArrowRelPos={1}
      onNodeClick={handleNodeClick}
      onBackgroundClick={handleBackgroundClick}
    />
  );
};
```

**API Integration:**

```typescript
// frontend/src/api/graphViz.ts
export async function fetchGraphData(params: GraphExportRequest): Promise<GraphData> {
  const response = await fetch('/api/v1/graph/viz/export', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      format: 'json',
      max_nodes: params.maxNodes || 100,
      entity_types: params.entityTypes,
      include_communities: true
    })
  });

  const data = await response.json();

  return {
    nodes: data.nodes.map(node => ({
      id: node.id,
      label: node.label,
      type: node.type,
      community: node.community,
      degree: 0 // Calculate from edges
    })),
    links: data.edges.map(edge => ({
      source: edge.source,
      target: edge.target,
      label: edge.type
    }))
  };
}
```

**Acceptance Criteria:**
- [ ] Graph renders with nodes and edges from API
- [ ] Pan: Click + drag background
- [ ] Zoom: Mouse wheel (zoom in/out)
- [ ] Node hover shows tooltip (entity name, type)
- [ ] Node click highlights node + connected edges
- [ ] Performance: 100+ nodes at 60 FPS

**Testing:**
```typescript
// frontend/src/components/graph/GraphViewer.test.tsx
describe('GraphViewer', () => {
  it('renders graph with nodes and edges', async () => {
    const mockData = {
      nodes: [{ id: '1', label: 'Entity 1', type: 'PERSON' }],
      links: [{ source: '1', target: '2', label: 'RELATED_TO' }]
    };

    render(<GraphViewer data={mockData} />);

    expect(screen.getByTestId('force-graph')).toBeInTheDocument();
  });

  it('highlights node on click', async () => {
    render(<GraphViewer />);

    const node = screen.getByTestId('node-1');
    fireEvent.click(node);

    expect(node).toHaveClass('highlighted');
  });
});
```

---

### Feature 29.2: Query Result Graph Visualization (End User) - 3 SP

**Priority:** 🔴 HIGH (Core end-user feature)

**Description:**
Integrate graph visualization with search results. When user submits a query, show a "View Graph" button that displays entities and relationships from the retrieved context.

**User Flow:**
1. User submits query: "How are transformers related to attention mechanisms?"
2. StreamingAnswer displays answer with citations
3. "View Graph" button appears below answer
4. Click → Modal/Sidebar opens with graph of entities mentioned in sources
5. Graph shows: Transformer → USES → Attention Mechanism (from LightRAG)

**Implementation:**

```typescript
// frontend/src/components/chat/StreamingAnswer.tsx (modify existing)
export const StreamingAnswer: React.FC<StreamingAnswerProps> = ({ answer, sources }) => {
  const [showGraph, setShowGraph] = useState(false);

  return (
    <div className="streaming-answer">
      <MarkdownRenderer content={answer} />
      <SourceCardsScroll sources={sources} />

      {/* NEW: Graph Visualization Button */}
      <button
        onClick={() => setShowGraph(true)}
        className="mt-4 flex items-center gap-2 text-teal-600 hover:text-teal-700"
      >
        <Network className="w-5 h-5" />
        View Knowledge Graph
      </button>

      {/* Graph Modal */}
      {showGraph && (
        <GraphModal
          onClose={() => setShowGraph(false)}
          entityNames={extractEntitiesFromSources(sources)}
        />
      )}
    </div>
  );
};
```

```typescript
// frontend/src/components/graph/GraphModal.tsx
interface GraphModalProps {
  entityNames: string[];
  onClose: () => void;
}

export const GraphModal: React.FC<GraphModalProps> = ({ entityNames, onClose }) => {
  const { data } = useGraphDataByEntities(entityNames);

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-6xl h-[80vh]">
        <DialogHeader>
          <DialogTitle>Knowledge Graph - Query Results</DialogTitle>
          <DialogDescription>
            Showing relationships between {entityNames.length} entities from your query
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 relative">
          <GraphViewer
            data={data}
            highlightNodes={entityNames}
          />
        </div>

        <DialogFooter>
          <GraphExportButton data={data} />
          <Button variant="outline" onClick={onClose}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
```

**API Endpoint (NEW - Backend):**
```python
# src/api/routers/graph_viz.py (add endpoint)
@router.post("/query-subgraph")
async def get_query_subgraph(entity_names: list[str]) -> dict[str, Any]:
    """Get subgraph for specific entities (query results).

    Args:
        entity_names: List of entity names from query results

    Returns:
        Subgraph containing entities and their 1-hop relationships
    """
    neo4j = get_neo4j_client()

    query = """
    MATCH (n:Entity)
    WHERE n.name IN $entity_names
    WITH n
    OPTIONAL MATCH (n)-[r]-(m:Entity)
    RETURN n, r, m
    """

    async with neo4j.get_driver().session() as session:
        result = await session.run(query, entity_names=entity_names)
        records = await result.data()

    return _export_json(records, include_communities=True)
```

**Acceptance Criteria:**
- [ ] "View Graph" button appears after query answer
- [ ] Button click opens modal with graph visualization
- [ ] Graph shows only entities from query sources (not entire graph)
- [ ] Entities from answer are highlighted (different color)
- [ ] Modal has "Export" and "Close" buttons
- [ ] Graph updates if user submits new query

---

### Feature 29.3: Admin Graph Analytics View - 5 SP

**Priority:** 🟠 MEDIUM (Admin-only feature)

**Description:**
Admin-only page at `/admin/graph` showing the entire knowledge graph with advanced filtering, community visualization, and analytics.

**Access Control:**
- Requires `admin` role (JWT token check)
- Redirects to `/login` if not authenticated

**UI Layout:**
```
┌────────────────────────────────────────────────────────────┐
│ Header: "Knowledge Graph Analytics" + User Menu           │
├──────────┬─────────────────────────────────────────────────┤
│          │                                                 │
│ Sidebar  │          Graph Viewer (Full Graph)             │
│          │                                                 │
│ Filters: │                                                 │
│ - Entity │                                                 │
│   Types  │                                                 │
│ - Min    │                                                 │
│   Degree │                                                 │
│ - Max    │                                                 │
│   Nodes  │                                                 │
│          │                                                 │
│ Stats:   │                                                 │
│ - Nodes  │                                                 │
│ - Edges  │                                                 │
│ - Comms  │                                                 │
│          │                                                 │
│ Actions: │                                                 │
│ - Export │                                                 │
│ - Reset  │                                                 │
│          │                                                 │
└──────────┴─────────────────────────────────────────────────┘
```

**Implementation:**

```typescript
// frontend/src/pages/admin/GraphAnalyticsPage.tsx
export const GraphAnalyticsPage: React.FC = () => {
  const [filters, setFilters] = useState<GraphFilters>({
    entityTypes: [],
    minDegree: 1,
    maxNodes: 100
  });

  const { data, loading } = useGraphData(filters);
  const { stats } = useGraphStatistics();

  return (
    <AdminLayout>
      <div className="flex h-screen">
        {/* Sidebar */}
        <aside className="w-80 bg-white border-r p-6 overflow-y-auto">
          <h2 className="text-2xl font-bold mb-6">Graph Analytics</h2>

          {/* Filters */}
          <GraphFilters
            value={filters}
            onChange={setFilters}
            stats={stats}
          />

          {/* Statistics */}
          <GraphStatistics stats={stats} className="mt-6" />

          {/* Actions */}
          <div className="mt-6 space-y-2">
            <GraphExportButton data={data} />
            <Button variant="outline" onClick={handleReset}>
              Reset View
            </Button>
          </div>
        </aside>

        {/* Main Graph */}
        <main className="flex-1 relative">
          {loading ? (
            <GraphSkeleton />
          ) : (
            <GraphViewer data={data} />
          )}
        </main>
      </div>
    </AdminLayout>
  );
};
```

**Filters Component:**

```typescript
// frontend/src/components/graph/GraphFilters.tsx
interface GraphFiltersProps {
  value: GraphFilters;
  onChange: (filters: GraphFilters) => void;
  stats: GraphStatistics;
}

export const GraphFilters: React.FC<GraphFiltersProps> = ({
  value,
  onChange,
  stats
}) => {
  return (
    <div className="space-y-4">
      <div>
        <Label>Entity Types</Label>
        <MultiSelect
          options={stats.entityTypes}
          value={value.entityTypes}
          onChange={(types) => onChange({ ...value, entityTypes: types })}
        />
      </div>

      <div>
        <Label>Minimum Degree</Label>
        <Slider
          min={1}
          max={20}
          value={value.minDegree}
          onChange={(degree) => onChange({ ...value, minDegree: degree })}
        />
        <span className="text-sm text-gray-500">{value.minDegree} connections</span>
      </div>

      <div>
        <Label>Max Nodes</Label>
        <Select
          value={value.maxNodes.toString()}
          onChange={(val) => onChange({ ...value, maxNodes: parseInt(val) })}
        >
          <option value="50">50 nodes</option>
          <option value="100">100 nodes</option>
          <option value="200">200 nodes</option>
          <option value="500">500 nodes</option>
        </Select>
      </div>
    </div>
  );
};
```

**Acceptance Criteria:**
- [ ] Page accessible at `/admin/graph` (admin only)
- [ ] Sidebar with filters (entity types, min degree, max nodes)
- [ ] Graph updates when filters change
- [ ] Statistics panel shows node/edge/community counts
- [ ] Export button downloads JSON/GraphML
- [ ] Performance: <2s load time for 100 nodes

---

### Feature 29.4: Knowledge Graph Dashboard - 5 SP

**Priority:** 🟠 MEDIUM

**Description:**
Dashboard showing high-level statistics and insights about the knowledge graph.

**Metrics to Display:**
1. **Graph Size**: Total nodes, edges, avg degree
2. **Entity Types**: Breakdown by type (pie chart)
3. **Top Communities**: Top 10 by size with topics
4. **Growth Over Time**: Nodes/edges added per day (line chart)
5. **Health Metrics**: Orphaned nodes, disconnected components
6. **Centrality Metrics**: Top 10 most connected entities

**Implementation:**

```typescript
// frontend/src/components/dashboard/KnowledgeGraphDashboard.tsx
export const KnowledgeGraphDashboard: React.FC = () => {
  const { stats, loading } = useGraphStatistics();
  const { communities } = useTopCommunities(10);

  if (loading) return <DashboardSkeleton />;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">Knowledge Graph Dashboard</h1>

      {/* Quick Stats */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="Total Nodes"
          value={stats.nodeCount}
          icon={<Circle />}
          trend={stats.nodeGrowth}
        />
        <StatCard
          title="Total Edges"
          value={stats.edgeCount}
          icon={<GitBranch />}
          trend={stats.edgeGrowth}
        />
        <StatCard
          title="Communities"
          value={stats.communityCount}
          icon={<Users />}
        />
        <StatCard
          title="Avg Degree"
          value={stats.avgDegree.toFixed(2)}
          icon={<Network />}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-2 gap-6">
        {/* Entity Type Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Entity Types</CardTitle>
          </CardHeader>
          <CardContent>
            <PieChart data={stats.entityTypeDistribution} />
          </CardContent>
        </Card>

        {/* Growth Over Time */}
        <Card>
          <CardHeader>
            <CardTitle>Graph Growth (Last 30 Days)</CardTitle>
          </CardHeader>
          <CardContent>
            <LineChart data={stats.growthTimeline} />
          </CardContent>
        </Card>
      </div>

      {/* Top Communities */}
      <Card>
        <CardHeader>
          <CardTitle>Top 10 Communities</CardTitle>
          <CardDescription>Largest communities by member count</CardDescription>
        </CardHeader>
        <CardContent>
          <TopCommunities communities={communities} />
        </CardContent>
      </Card>

      {/* Health Metrics */}
      <Card>
        <CardHeader>
          <CardTitle>Graph Health</CardTitle>
        </CardHeader>
        <CardContent>
          <HealthMetrics
            orphanedNodes={stats.orphanedNodes}
            disconnectedComponents={stats.disconnectedComponents}
            largestComponentSize={stats.largestComponentSize}
          />
        </CardContent>
      </Card>
    </div>
  );
};
```

**API Endpoint (NEW - Backend):**

```python
# src/api/routers/graph_viz.py
@router.get("/statistics")
async def get_graph_statistics() -> dict[str, Any]:
    """Get comprehensive graph statistics.

    Returns:
        Statistics including counts, distributions, and health metrics
    """
    neo4j = get_neo4j_client()

    async with neo4j.get_driver().session() as session:
        # Node count
        node_result = await session.run("MATCH (n:Entity) RETURN count(n) as count")
        node_count = (await node_result.single())["count"]

        # Edge count
        edge_result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
        edge_count = (await edge_result.single())["count"]

        # Community count
        comm_result = await session.run(
            "MATCH (n:Entity) WHERE n.community_id IS NOT NULL "
            "RETURN count(DISTINCT n.community_id) as count"
        )
        community_count = (await comm_result.single())["count"]

        # Entity type distribution
        type_result = await session.run(
            "MATCH (n:Entity) RETURN n.entity_type as type, count(*) as count"
        )
        entity_types = {record["type"]: record["count"]
                       for record in await type_result.data()}

        # Orphaned nodes (degree = 0)
        orphan_result = await session.run(
            "MATCH (n:Entity) WHERE NOT (n)--() RETURN count(n) as count"
        )
        orphaned_nodes = (await orphan_result.single())["count"]

    return {
        "node_count": node_count,
        "edge_count": edge_count,
        "community_count": community_count,
        "avg_degree": (edge_count * 2) / node_count if node_count > 0 else 0,
        "entity_type_distribution": entity_types,
        "orphaned_nodes": orphaned_nodes,
        "timestamp": datetime.utcnow().isoformat()
    }
```

**Acceptance Criteria:**
- [ ] Dashboard shows 4 quick stat cards
- [ ] Pie chart for entity type distribution
- [ ] Line chart for growth over time (last 30 days)
- [ ] Top 10 communities table with topics
- [ ] Health metrics (orphaned nodes, disconnected components)
- [ ] Auto-refresh every 30 seconds (optional)

---

### Feature 29.5: Graph Explorer with Search - 5 SP

**Priority:** 🟠 MEDIUM

**Description:**
Search and filter capabilities for the graph viewer: find nodes by name, filter by type, highlight communities.

**Features:**
1. **Node Search**: Type entity name → graph centers on node
2. **Filter by Entity Type**: Show only PERSON, ORGANIZATION, etc.
3. **Community Highlighting**: Select community → highlight all members
4. **Degree Filter**: Show only highly connected nodes (min degree)

**Implementation:**

```typescript
// frontend/src/components/graph/GraphSearch.tsx
interface GraphSearchProps {
  data: GraphData;
  onNodeSelect: (nodeId: string) => void;
}

export const GraphSearch: React.FC<GraphSearchProps> = ({ data, onNodeSelect }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<GraphNode[]>([]);

  useEffect(() => {
    if (query.length < 2) {
      setResults([]);
      return;
    }

    const filtered = data.nodes.filter(node =>
      node.label.toLowerCase().includes(query.toLowerCase())
    );

    setResults(filtered.slice(0, 10)); // Max 10 results
  }, [query, data]);

  return (
    <div className="relative">
      <Input
        type="search"
        placeholder="Search entities..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="w-full"
      />

      {results.length > 0 && (
        <div className="absolute top-full mt-1 w-full bg-white border rounded-lg shadow-lg z-10 max-h-64 overflow-y-auto">
          {results.map(node => (
            <button
              key={node.id}
              onClick={() => {
                onNodeSelect(node.id);
                setQuery('');
              }}
              className="w-full px-4 py-2 text-left hover:bg-gray-100 flex items-center gap-2"
            >
              <span className="w-3 h-3 rounded-full" style={{ backgroundColor: getColorByType(node.type) }} />
              <span className="font-medium">{node.label}</span>
              <span className="text-sm text-gray-500 ml-auto">{node.type}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
```

**Community Highlighting:**

```typescript
// frontend/src/components/graph/CommunityHighlight.tsx
interface CommunityHighlightProps {
  communities: Community[];
  selectedCommunity: string | null;
  onCommunitySelect: (communityId: string | null) => void;
}

export const CommunityHighlight: React.FC<CommunityHighlightProps> = ({
  communities,
  selectedCommunity,
  onCommunitySelect
}) => {
  return (
    <div className="space-y-2">
      <Label>Highlight Community</Label>
      <Select
        value={selectedCommunity || ''}
        onChange={(e) => onCommunitySelect(e.target.value || null)}
      >
        <option value="">None (Show All)</option>
        {communities.map(comm => (
          <option key={comm.id} value={comm.id}>
            {comm.topic} ({comm.size} members)
          </option>
        ))}
      </Select>
    </div>
  );
};
```

**Integration with GraphViewer:**

```typescript
// frontend/src/components/graph/GraphViewer.tsx (enhanced)
export const GraphViewer: React.FC<GraphViewerProps> = ({
  data,
  selectedNode,
  highlightCommunity
}) => {
  const graphRef = useRef<ForceGraphMethods>();

  // Center on selected node
  useEffect(() => {
    if (selectedNode && graphRef.current) {
      const node = data.nodes.find(n => n.id === selectedNode);
      if (node) {
        graphRef.current.centerAt(node.x, node.y, 1000);
        graphRef.current.zoom(2, 1000);
      }
    }
  }, [selectedNode, data]);

  return (
    <div className="relative w-full h-full">
      {/* Search Bar (Overlay) */}
      <div className="absolute top-4 left-4 z-10 w-96">
        <GraphSearch
          data={data}
          onNodeSelect={setSelectedNode}
        />
      </div>

      {/* Graph */}
      <ForceGraph2D
        ref={graphRef}
        graphData={data}
        nodeColor={(node) => {
          if (highlightCommunity && node.community !== highlightCommunity) {
            return '#e0e0e0'; // Dim non-highlighted nodes
          }
          if (node.id === selectedNode) {
            return '#ff4500'; // Highlight selected node
          }
          return getColorByType(node.type);
        }}
        linkColor={(link) => {
          if (highlightCommunity) {
            const sourceNode = data.nodes.find(n => n.id === link.source);
            const targetNode = data.nodes.find(n => n.id === link.target);
            if (sourceNode?.community === highlightCommunity &&
                targetNode?.community === highlightCommunity) {
              return '#1e90ff'; // Highlight community edges
            }
            return '#e0e0e0'; // Dim other edges
          }
          return '#999';
        }}
      />
    </div>
  );
};
```

**Acceptance Criteria:**
- [ ] Search bar overlay on graph
- [ ] Type 2+ characters → show dropdown with matching nodes
- [ ] Click node in dropdown → graph centers on node with zoom
- [ ] Filter by entity type → graph updates (only shows selected types)
- [ ] Select community → graph highlights community members + edges
- [ ] "Clear Filters" button resets all filters

---

### Feature 29.6: Embedding-based Document Search from Graph - 8 SP

**Priority:** 🟡 LOW (Advanced feature)

**Description:**
Click a node in the graph → find related documents using vector similarity. Uses the entity name as query to Qdrant, retrieves top-k similar documents, displays in side panel.

**User Flow:**
1. User clicks node "Transformer" in graph
2. Side panel opens showing "Related Documents"
3. Backend: Query Qdrant with entity name as query
4. Display: Top 10 documents with similarity scores
5. Click document → opens document preview

**Architecture:**

```
GraphViewer (Node Click)
   ↓
NodeDetailsPanel (Opens)
   ↓
useDocumentsByNode (Hook)
   ↓
API: POST /api/v1/graph/viz/node-documents
   ↓
Backend: Embed entity name (BGE-M3) → Qdrant search
   ↓
Return: Top 10 documents with scores
   ↓
Display: Document list with previews
```

**Implementation:**

```typescript
// frontend/src/components/graph/NodeDetailsPanel.tsx
interface NodeDetailsPanelProps {
  node: GraphNode | null;
  onClose: () => void;
}

export const NodeDetailsPanel: React.FC<NodeDetailsPanelProps> = ({ node, onClose }) => {
  const { documents, loading } = useDocumentsByNode(node?.label);

  if (!node) return null;

  return (
    <div className="absolute right-0 top-0 w-96 h-full bg-white border-l shadow-lg overflow-y-auto">
      {/* Header */}
      <div className="sticky top-0 bg-white border-b p-4 flex items-center justify-between">
        <div>
          <h3 className="font-bold text-lg">{node.label}</h3>
          <p className="text-sm text-gray-500">{node.type}</p>
        </div>
        <Button variant="ghost" size="sm" onClick={onClose}>
          <X className="w-4 h-4" />
        </Button>
      </div>

      {/* Node Info */}
      <div className="p-4 border-b space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-gray-500">Connections:</span>
          <span className="font-medium">{node.degree}</span>
        </div>
        {node.community && (
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Community:</span>
            <span className="font-medium">{node.community}</span>
          </div>
        )}
      </div>

      {/* Related Documents */}
      <div className="p-4">
        <h4 className="font-semibold mb-3 flex items-center gap-2">
          <FileText className="w-4 h-4" />
          Related Documents
        </h4>

        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map(i => <DocumentCardSkeleton key={i} />)}
          </div>
        ) : documents.length === 0 ? (
          <p className="text-sm text-gray-500">No related documents found</p>
        ) : (
          <div className="space-y-3">
            {documents.map(doc => (
              <DocumentCard
                key={doc.id}
                document={doc}
                onPreview={() => handlePreview(doc)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
```

**Document Card:**

```typescript
// frontend/src/components/graph/DocumentCard.tsx
interface DocumentCardProps {
  document: RelatedDocument;
  onPreview: () => void;
}

export const DocumentCard: React.FC<DocumentCardProps> = ({ document, onPreview }) => {
  return (
    <div className="border rounded-lg p-3 hover:border-teal-500 cursor-pointer" onClick={onPreview}>
      <div className="flex items-start justify-between mb-2">
        <h5 className="font-medium text-sm line-clamp-1">{document.title}</h5>
        <span className="text-xs text-gray-500 ml-2">
          {(document.similarity * 100).toFixed(0)}%
        </span>
      </div>

      <p className="text-xs text-gray-600 line-clamp-2 mb-2">
        {document.excerpt}
      </p>

      <div className="flex items-center gap-2 text-xs text-gray-500">
        <FileText className="w-3 h-3" />
        <span>{document.source}</span>
        <span>•</span>
        <span>{document.chunk_id}</span>
      </div>
    </div>
  );
};
```

**Backend API Endpoint (NEW):**

```python
# src/api/routers/graph_viz.py
from src.components.shared.embedding_service import UnifiedEmbeddingService
from src.components.vector_search.qdrant_client import QdrantClientWrapper

@router.post("/node-documents")
async def get_documents_by_node(entity_name: str, top_k: int = 10) -> dict[str, Any]:
    """Get related documents for an entity using vector similarity.

    Args:
        entity_name: Entity name to search for (e.g., "Transformer")
        top_k: Number of top documents to return

    Returns:
        List of documents with similarity scores
    """
    try:
        # 1. Generate embedding for entity name
        embedding_service = UnifiedEmbeddingService()
        query_vector = await embedding_service.embed(entity_name)

        # 2. Search Qdrant
        qdrant = QdrantClientWrapper()
        results = await qdrant.search(
            collection_name="aegis-rag-documents",
            query_vector=query_vector,
            limit=top_k
        )

        # 3. Format response
        documents = []
        for result in results:
            documents.append({
                "id": result.id,
                "title": result.payload.get("source", "Unknown"),
                "excerpt": result.payload.get("text", "")[:200],
                "source": result.payload.get("source"),
                "chunk_id": result.payload.get("chunk_id"),
                "similarity": result.score,
                "metadata": result.payload.get("metadata", {})
            })

        return {
            "entity_name": entity_name,
            "documents": documents,
            "total": len(documents)
        }

    except Exception as e:
        logger.error("node_documents_failed", error=str(e), entity=entity_name)
        raise HTTPException(status_code=500, detail=f"Document search failed: {e}") from e
```

**Acceptance Criteria:**
- [ ] Click node → side panel opens
- [ ] Panel shows node info (name, type, degree, community)
- [ ] "Related Documents" section shows top 10 documents
- [ ] Documents sorted by similarity (highest first)
- [ ] Click document → opens preview modal
- [ ] Loading state while fetching documents
- [ ] Error handling if no documents found

---

### Feature 29.7: Community Document Browser - 5 SP

**Priority:** 🟡 LOW

**Description:**
Browse all documents that belong to a specific community. Useful for understanding what topics a community covers.

**User Flow:**
1. User selects community from dropdown (Feature 29.5)
2. "View Community Documents" button appears
3. Click → Opens document browser modal
4. Shows all documents where entities from this community are mentioned

**Implementation:**

```typescript
// frontend/src/components/graph/CommunityDocuments.tsx
interface CommunityDocumentsProps {
  communityId: string;
  onClose: () => void;
}

export const CommunityDocuments: React.FC<CommunityDocumentsProps> = ({
  communityId,
  onClose
}) => {
  const { documents, loading, community } = useCommunityDocuments(communityId);

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle>Documents - {community?.topic}</DialogTitle>
          <DialogDescription>
            {documents.length} documents mention entities from this community
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="grid grid-cols-2 gap-4">
              {[1, 2, 3, 4].map(i => <DocumentCardSkeleton key={i} />)}
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              {documents.map(doc => (
                <DocumentCard
                  key={doc.id}
                  document={doc}
                  onPreview={() => handlePreview(doc)}
                  entities={doc.entities} // Entities from community mentioned in doc
                />
              ))}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
```

**Backend API Endpoint (NEW):**

```python
# src/api/routers/graph_viz.py
@router.get("/communities/{community_id}/documents")
async def get_community_documents(
    community_id: str,
    limit: int = 50
) -> dict[str, Any]:
    """Get all documents mentioning entities from a community.

    Args:
        community_id: Community ID
        limit: Max documents to return

    Returns:
        Documents with entity mentions from community
    """
    try:
        neo4j = get_neo4j_client()

        # 1. Get entities in community
        async with neo4j.get_driver().session() as session:
            entity_result = await session.run(
                "MATCH (n:Entity {community_id: $community_id}) "
                "RETURN collect(n.name) as entity_names",
                community_id=community_id
            )
            entity_names = (await entity_result.single())["entity_names"]

        # 2. Find documents mentioning these entities
        # This requires a Document → Entity relationship in Neo4j
        # Alternatively, search Qdrant for chunks mentioning entities

        qdrant = QdrantClientWrapper()
        documents = []

        for entity_name in entity_names[:10]:  # Sample 10 entities
            results = await qdrant.search(
                collection_name="aegis-rag-documents",
                query_filter={
                    "must": [
                        {
                            "key": "text",
                            "match": {"text": entity_name}
                        }
                    ]
                },
                limit=limit
            )

            for result in results:
                doc_id = result.payload.get("source")
                if doc_id not in [d["id"] for d in documents]:
                    documents.append({
                        "id": doc_id,
                        "title": result.payload.get("source"),
                        "excerpt": result.payload.get("text")[:200],
                        "entities": [entity_name],  # Entities mentioned
                        "chunk_id": result.payload.get("chunk_id")
                    })

        return {
            "community_id": community_id,
            "documents": documents[:limit],
            "total": len(documents)
        }

    except Exception as e:
        logger.error("community_documents_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e
```

**Acceptance Criteria:**
- [ ] "View Documents" button in community selector
- [ ] Modal shows all documents from community
- [ ] Documents grouped/sorted by relevance
- [ ] Each document card shows mentioned entities (highlighted)
- [ ] Click document → opens preview
- [ ] Pagination if >50 documents

---

## Testing Strategy

### Unit Tests

```typescript
// frontend/src/components/graph/GraphViewer.test.tsx
describe('GraphViewer', () => {
  it('renders graph with correct number of nodes', () => {
    const data = {
      nodes: [{ id: '1', label: 'Node 1' }],
      links: []
    };
    render(<GraphViewer data={data} />);
    expect(screen.getAllByTestId('graph-node')).toHaveLength(1);
  });

  it('highlights node on click', () => {
    render(<GraphViewer />);
    const node = screen.getByTestId('node-1');
    fireEvent.click(node);
    expect(node).toHaveClass('highlighted');
  });

  it('zooms in on double click', () => {
    const { container } = render(<GraphViewer />);
    const svg = container.querySelector('svg');
    fireEvent.doubleClick(svg);
    // Assert zoom level increased
  });
});
```

### Integration Tests

```python
# tests/integration/test_graph_viz_api.py
async def test_export_graph_json():
    """Test graph export in JSON format."""
    response = await client.post("/api/v1/graph/viz/export", json={
        "format": "json",
        "max_nodes": 10
    })

    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) <= 10

async def test_node_documents_search():
    """Test document search by entity name."""
    response = await client.post("/api/v1/graph/viz/node-documents", json={
        "entity_name": "Transformer",
        "top_k": 5
    })

    assert response.status_code == 200
    data = response.json()
    assert data["entity_name"] == "Transformer"
    assert len(data["documents"]) <= 5
    assert all("similarity" in doc for doc in data["documents"])
```

### E2E Tests

```typescript
// frontend/e2e/graph-visualization.spec.ts
test('end user views query result graph', async ({ page }) => {
  // 1. Submit query
  await page.goto('/');
  await page.fill('input[type="search"]', 'How are transformers related to attention?');
  await page.click('button[type="submit"]');

  // 2. Wait for answer
  await page.waitForSelector('.streaming-answer');

  // 3. Click "View Graph" button
  await page.click('text=View Knowledge Graph');

  // 4. Assert graph modal opens
  await expect(page.locator('.graph-modal')).toBeVisible();

  // 5. Assert graph has nodes
  const nodes = page.locator('.graph-node');
  await expect(nodes).toHaveCount(2); // At least 2 nodes

  // 6. Click node
  await nodes.first().click();

  // 7. Assert side panel opens
  await expect(page.locator('.node-details-panel')).toBeVisible();
});
```

---

## Implementation Plan

### Week 1: Foundation (Days 1-3, 13 SP)
- **Day 1:** Feature 29.1 (GraphViewer component) - 5 SP
- **Day 2:** Feature 29.2 (Query Result Graph) + Feature 29.5 (Search) - 8 SP

### Week 2: Admin & Advanced (Days 4-7, 23 SP)
- **Day 3-4:** Feature 29.3 (Admin Analytics) + Feature 29.4 (Dashboard) - 10 SP
- **Day 5-6:** Feature 29.6 (Embedding Document Search) - 8 SP
- **Day 7:** Feature 29.7 (Community Documents) - 5 SP

### Testing & Polish (Day 8-9)
- Unit tests for all components
- Integration tests for API endpoints
- E2E tests for user flows
- Performance optimization (60 FPS with 100+ nodes)
- Documentation updates

---

## Success Metrics

### Performance Targets
- **Graph Rendering:** <1s for 100 nodes, <3s for 500 nodes
- **Search Latency:** <200ms for node search
- **Document Lookup:** <500ms for embedding-based search
- **Frame Rate:** 60 FPS with pan/zoom

### User Experience
- **Discoverability:** 80%+ users find "View Graph" button within first query
- **Navigation:** Users can find specific nodes in <10 seconds
- **Clarity:** 90%+ users understand graph relationships (survey)

### Technical
- **Test Coverage:** >80% for graph components
- **Accessibility:** WCAG 2.1 AA compliant
- **Browser Support:** Chrome, Firefox, Safari (latest 2 versions)

---

## Risks & Mitigation

### Risk 1: Performance with Large Graphs (500+ nodes)
**Impact:** HIGH
**Mitigation:**
- Use WebGL rendering (react-force-graph)
- Implement node clustering for large graphs
- Add pagination/lazy loading
- Server-side graph sampling (max 500 nodes default)

### Risk 2: Library Learning Curve (react-force-graph)
**Impact:** MEDIUM
**Mitigation:**
- Start with 2D mode (simpler than 3D)
- Reference official examples and demos
- Fallback to cytoscape.js if issues arise
- Allocate 1 day for spike/exploration

### Risk 3: Document-to-Entity Relationships Missing
**Impact:** MEDIUM (affects Feature 29.6, 29.7)
**Mitigation:**
- Use Qdrant text search as fallback
- Add Document → Entity relationship in future sprint
- Embed entity names as queries (good enough for MVP)

---

## Dependencies

### External Libraries
```json
{
  "react-force-graph": "^1.43.0",
  "@types/react-force-graph": "^1.43.0",
  "lucide-react": "^0.294.0" // Icons
}
```

### Backend APIs (Existing)
- ✅ `POST /api/v1/graph/viz/export` (Sprint 12)
- ✅ `GET /api/v1/graph/viz/export/formats` (Sprint 12)
- ✅ `POST /api/v1/graph/viz/filter` (Sprint 12)
- ✅ `POST /api/v1/graph/viz/communities/highlight` (Sprint 12)

### Backend APIs (NEW - Sprint 29)
- ❌ `POST /api/v1/graph/viz/query-subgraph` (Feature 29.2)
- ❌ `GET /api/v1/graph/viz/statistics` (Feature 29.4)
- ❌ `POST /api/v1/graph/viz/node-documents` (Feature 29.6)
- ❌ `GET /api/v1/graph/viz/communities/{id}/documents` (Feature 29.7)

---

## Rollout Plan

### Phase 1: Internal Testing (Day 8)
- Deploy to staging environment
- Test with internal team (admin users)
- Collect feedback on UX and performance

### Phase 2: Beta Release (Day 9)
- Enable for selected end users
- Monitor performance metrics
- Gather user feedback

### Phase 3: General Availability (Sprint 30)
- Full rollout to all users
- Update documentation
- Create user guide video

---

## Documentation Updates

### Files to Update
1. `docs/COMPONENT_INTERACTION_MAP.md` - Add Graph Viz Frontend section
2. `docs/api/ENDPOINTS.md` - Document new API endpoints
3. `frontend/README.md` - Add graph visualization setup
4. `docs/USER_GUIDE.md` - Create user guide for graph features

### User Guide Topics
- How to view query result graphs
- Navigating the knowledge graph (pan, zoom, search)
- Understanding entity relationships
- Finding related documents from graph nodes
- Admin: Analyzing communities and graph health

---

## Sprint 29 Completion Criteria

- [ ] All 7 features implemented and tested
- [ ] GraphViewer component renders 100+ nodes at 60 FPS
- [ ] End users can view query result graphs
- [ ] Admins can explore entire knowledge graph
- [ ] Document search from graph nodes works
- [ ] Community document browser functional
- [ ] Unit test coverage >80%
- [ ] E2E tests pass for all user flows
- [ ] Documentation updated (API docs, user guide)
- [ ] Performance benchmarks met (see Success Metrics)

---

**Next Steps:**
1. Review Sprint 29 Plan with team
2. Approve library choice (react-force-graph)
3. Create Sprint 29 branch
4. Start Feature 29.1 (GraphViewer component)
