# Hybrid RAG & Knowledge Graph Architecture

## Current Status (Oct 2025)

- Graph: 20,325 refined statements stored as reified `regx:Statement` with `regx:subject`, `regx:predicate`, `regx:object`, and `regx:canonicalPredicate` (≈101,903 total triples). Canonical categories include: `eco_credit`, `finance`, `funding`, `governance`, `water`, `creation`, `leadership`, `collaboration`, `location`, `general`.
- Predicate consolidation: threshold t=0.25 in use (final_consolidation_all_t0.25.json). 7,037 → 4,009 consolidated forms (preserves diversity; avoids over‑merge at t=0.30).
- Predicate communities: computed (19 communities) and loaded for community‑aware expansion.
- Hybrid search: true parallel SPARQL + vector with Reciprocal Rank Fusion (RRF). Implemented in MCP (`hybrid-client.ts`).
- NL→SPARQL: adaptive dual‑branch in MCP with canonical‑aware filtering and smart fallback. Canonical first for precision; automatic non‑canonical fallback for recall.
- Embeddings: 7,037 predicate embeddings pre‑computed (82.5 MB) with lightweight similarity API.
- Evaluation: 20‑query harness shows 100% query success, 0% noise (Lingui/i18n eliminated), ~1.5 s avg latency; cold start ~19 s.

## Recent Improvements

- Canonical‑aware NL→SPARQL filtering: maps keywords → canonical categories, prunes noise structurally.
- Smart fallback: if canonical filters return 0 results, automatically retry broad branch without category filter (maintains recall while keeping default precision high).
- Expanded canonical lexicon: better coverage for eco‑credit, finance, water, funding, governance, leadership.
- Consolidation cleanup: standardized t=0.25 “all” mapping and aligned client paths; reduced over‑merge risk spotted at t=0.30.
- Eval harness: now persists JSON metrics (focused/broad/union/overlap, latency, noise rate, thresholds) for regression tracking.

## Next Steps

- Multi‑category gating (precision without fallback): require primary canonical match and secondary token evidence (e.g., eco_credit + finance for “stablecoin retirements”).
- Provenance filters: inject `regx:sourceDomain` / `regx:sourceType` per statement in refiner and prefer/deny by source to structurally suppress library/dev noise.
- Warm‑up on MCP start: prime Jena and embedding service to remove cold‑start 19 s spike.
- Jena Text index: enable text:query over `regx:subject` / `regx:object` for faster topical broad branch.
- Canonical enrichment: expand `canonical_predicates.json` and heuristics to boost category recall (especially water/finance).
- Evaluation gates: set pass/fail thresholds and baseline comparisons (t=0.25 vs t=0.30, canonical on/off).

## Executive Summary

Our system implements a sophisticated hybrid approach to Retrieval-Augmented Generation (RAG) that combines three complementary knowledge representations: vector similarity search, structured knowledge graphs, and code entity graphs. This triple-path architecture enables semantic understanding through embeddings, ontological reasoning through RDF triples, and code-level navigation through AST-extracted entity graphs, providing AI agents with comprehensive knowledge access across documentation, community discussions, and source code.

## System Overview

### Core Philosophy
The architecture is designed around the concept of "living systems" - treating knowledge as a metabolic process where information flows, transforms, and evolves through various stages. This biomimetic approach aligns with Regen Network's regenerative principles, creating a knowledge ecosystem that grows and adapts organically.

### Key Innovation: Triple Knowledge Representation
Unlike traditional RAG systems that rely solely on vector embeddings, our architecture maintains knowledge in **three complementary forms**:

1. **Vector Embeddings (Layer 1)** - For semantic similarity and contextual understanding
   - 15,000+ documents from 12 platforms (GitHub, Discourse, Medium, Telegram, etc.)
   - OpenAI text-embedding-3-large (1024-dimensional vectors)
   - Stored in PostgreSQL with pgvector extension

2. **RDF Knowledge Graph (Layer 2)** - For structured relationships and ontological reasoning
   - 101,903 RDF triples with canonical categories
   - Apache Jena Fuseki triplestore with SPARQL queries
   - OWL ontology reasoning capabilities

3. **Code Entity Graph (Layer 3)** - For code navigation and impact analysis
   - 26,768 code entities extracted via tree-sitter AST parsing
   - 11,331 CALLS edges mapping function relationships
   - Apache AGE graph database with Cypher queries

## Architecture Components

### Data Ingestion Pipeline

**Three Knowledge Layers:** The system maintains knowledge in three complementary forms for comprehensive understanding.

```
┌─────────────────────────────────────────────────────────┐
│              KOI SENSORS (12 platforms)                 │
│  GitHub, GitLab, Medium, Discourse, Telegram, Discord,  │
│  Twitter, Podcast, Notion, Ledger, Websites             │
└──────────────────────┬──────────────────────────────────┘
                       ↓ KOI Events
┌─────────────────────────────────────────────────────────┐
│           COORDINATOR + EVENT BRIDGE v2                 │
│  Deduplication, versioning, chunking, CAT receipts      │
└──────────────────────┬──────────────────────────────────┘
                       ↓
        ┌──────────────┴──────────────┬──────────────┐
        │                             │              │
        ↓                             ↓              ↓
┌──────────────┐          ┌───────────────────┐  ┌────────────┐
│  OpenAI API  │          │  Entity Extractor │  │ Tree-sitter│
│  Embeddings  │          │  (LLM + Ontology) │  │ AST Parser │
│  (Port 8090) │          │                   │  │ (Go Code)  │
└──────┬───────┘          └─────────┬─────────┘  └─────┬──────┘
       │                            │                   │
       ↓                            ↓                   ↓
┌─────────────────────────────────────────────────────────────┐
│              POSTGRESQL (Port 5433)                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────┐      ┌───────────────────────┐   │
│  │ pgvector             │      │ Apache AGE            │   │
│  │ ─────────            │      │ ──────────            │   │
│  │ koi_memories         │      │ Graph: regen_graph_v2 │   │
│  │ koi_embeddings       │      │                       │   │
│  │                      │      │ 26,768 code entities  │   │
│  │ 15,000+ documents    │      │ 11,331 CALLS edges    │   │
│  │ OpenAI vectors       │      │                       │   │
│  │ 1024-dimensional     │      │ Cypher queries        │   │
│  └──────────────────────┘      └───────────────────────┘   │
│                                                             │
│  LAYER 1: Document Vectors     LAYER 3: Code Graph         │
│  (semantic search)             (code navigation)           │
└─────────────────────────────────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────────────────────┐
│        APACHE JENA FUSEKI (Port 3030)                   │
│  ─────────────────────────────────────                  │
│  101,903 RDF triples                                    │
│  SPARQL queries, canonical categories                   │
│  Semantic reasoning                                     │
│                                                         │
│  LAYER 2: RDF Knowledge Graph                           │
│  (ontological reasoning)                                │
└─────────────────────────────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────────────────────┐
│           MCP SERVER (regen-koi-mcp v1.1.0)             │
│  ─────────────────────────────────────────              │
│  Query Router → Apache AGE + Apache Jena + pgvector     │
│  RRF Fusion, Caching, Metrics                           │
│  9 MCP Tools for AI Agents                              │
└─────────────────────────────────────────────────────────┘
```

### 1. KOI Sensors Network
The system begins with a distributed network of sensors that monitor various content sources:

- **Website Monitor Sensors** - Track changes in web content
- **GitHub Sensors** - Monitor repository updates and documentation
- **Medium Sensors** - Collect blog posts and articles
- **Telegram Sensors** - Capture community discussions
- **Discord Sensors** - Monitor governance and technical discussions
- **Twitter/X Sensors** - Track social media mentions and threads

Each sensor:
- Assigns a unique Resource Identifier (RID) to content
- Generates Content Identifiers (CIDs) for deduplication
- Extracts basic metadata (title, author, timestamp, source)
- Packages content into standardized KOI event bundles

### 2. KOI Event Processing

#### Event Bridge v2 (Port 8100)
The central processing hub that:

**Deduplication & Versioning:**
- Uses RID-based tracking to prevent duplicate processing
- Maintains version history for updated content
- Handles NEW, UPDATE, and FORGET event types
- Creates CAT (Content Addressable Transformation) receipts for provenance

**Content Chunking:**
- Intelligently splits documents into processable chunks (1000 chars with 200 char overlap)
- Preserves context across chunk boundaries
- Maintains chunk-to-document relationships
- Optimizes for both embedding generation and LLM context windows

### 3. Dual Processing Paths

#### Path A: Embedding Generation (Semantic Understanding)

**BGE Embedding Server (Port 8090):**
- Uses BAAI/bge-large-en-v1.5 model (1024-dimensional vectors)
- Generates high-quality semantic embeddings for each chunk
- Model-agnostic API allows swapping to other embedding models
- Supports multiple embedding dimensions (768, 1024, 1536)

**Storage in PostgreSQL with pgvector:**
```sql
CREATE TABLE koi_embeddings (
    id SERIAL PRIMARY KEY,
    memory_id UUID REFERENCES koi_memories(id),
    dim_768 vector(768),   -- Alternative models
    dim_1024 vector(1024), -- BGE embeddings
    dim_1536 vector(1536), -- OpenAI embeddings
    created_at TIMESTAMP
);
```

**Semantic Search Capabilities:**
- Cosine similarity search across embeddings
- Fast k-nearest neighbor retrieval
- Filtering by agent permissions and metadata
- Relevance scoring and ranking

#### Path B: Entity & Relationship Extraction (Ontological Understanding)

**LLM-Based Extraction Pipeline:**
- Uses Mistral 7B or similar models via Ollama
- Guided by unified ontology (36 classes)
- Extracts entities, relationships, and properties
- Generates JSON-LD structured data

**Ontology-Driven Processing:**
```turtle
# Unified Ontology Structure
@prefix regen: <https://regen.network/ontology#> .

# Core Classes
regen:System           # Living systems
regen:MetabolicFlow    # Information flows
regen:Agent           # Actors in the system
regen:SemanticAsset   # Knowledge artifacts
regen:EcologicalAsset # Environmental data

# Relationships
regen:produces        # Agent produces asset
regen:derivesFrom     # Asset lineage
regen:alignsWith      # Conceptual alignment
```

**RDF Triple Generation:**
The system converts extracted entities into RDF triples:
```
<document:123> regen:discusses <concept:regenerative-agriculture> .
<concept:regenerative-agriculture> regen:alignsWith "soil-health" .
<project:xyz> regen:produces <outcome:carbon-credits> .
```

### 4. Storage Layer

The storage layer consists of **three knowledge representations** hosted across two database systems:

#### PostgreSQL Database (Port 5433)

**Layer 1: pgvector Extension (Document Vectors)**

Dual-table architecture for optimal performance:

**koi_memories Table:**
- Stores original documents with RIDs
- Maintains version history
- Tracks source sensors and metadata
- Ensures deduplication at document level
- 15,000+ documents from 12 platforms

**koi_embeddings Table:**
- OpenAI text-embedding-3-large vectors (1024-dimensional)
- Cosine similarity search for semantic retrieval
- Supports fast k-nearest neighbor queries
- Links to agent access permissions
- Contains 40,000+ searchable chunks

**Layer 3: Apache AGE Extension (Code Graph)**

Graph database for code understanding:

**regen_graph_v2 Graph:**
- 26,768 code entities (Functions, Structs, Interfaces, Methods, Imports)
- 11,331 CALLS edges mapping function call relationships
- 10 domain Concepts with EXPLAINS edges to code
- Tree-sitter AST extraction from Go source
- Cypher query language support
- Enables call graph traversal, impact analysis, orphan detection

**Code Entity Types:**
- Methods: 19,884
- Imports: 3,363
- Functions: 1,693
- Structs: 1,636
- Interfaces: 192
- Concepts: 10

#### Apache Jena Fuseki (Port 3030)

**Layer 2: RDF Triplestore (Knowledge Graph)**

SPARQL triplestore for ontological reasoning:

**Features:**
- Stores 101,903 RDF triples
- 20,325 refined statements with canonical categories
- OWL ontology reasoning capabilities
- SPARQL 1.1 query support
- Persistent TDB2 storage
- RESTful HTTP interface

**Canonical Categories:**
- eco_credit, finance, funding, governance
- water, creation, leadership, collaboration
- location, general

**Dataset Structure:**
```
/koi
  ├── ontologies/      # OWL ontology definitions
  ├── entities/        # Extracted entities
  ├── relationships/   # Inter-entity connections
  └── metadata/        # Provenance and timestamps
```

### 5. Query & Access Layer

#### Regen KOI MCP Server v1.1.0

**Location:** [regen-koi-mcp](https://github.com/gaiaaiagent/regen-koi-mcp)
**NPM Package:** `regen-koi-mcp@1.1.0`
**Status:** Phase 7 Production Ready (November 2025)

Provides unified access to all three knowledge representations:

**9 MCP Tools:**
1. **query_code_graph** - Apache AGE Cypher queries (15+ query types)
2. **hybrid_search** - Intelligent routing between vector and graph
3. **search_knowledge** - Semantic search with date filters
4. **search_github_docs** - Documentation across 4 repositories
5. **get_repo_overview** - Repository structure and key files
6. **get_tech_stack** - Technology stack breakdown
7. **get_stats** - Knowledge base statistics
8. **generate_weekly_digest** - Weekly activity summaries
9. **get_mcp_metrics** - Production metrics and health

**Hybrid Query Capabilities:**
1. **Semantic Search** → Routes to PostgreSQL pgvector (Layer 1)
2. **Code Graph Query** → Routes to PostgreSQL Apache AGE (Layer 3)
3. **Ontological Query** → Routes to Apache Jena Fuseki (Layer 2)
4. **Hybrid Query** → Combines results from all three systems via RRF fusion

**Phase 7 Production Features:**
- Exponential backoff retry (3 attempts)
- Circuit breaker pattern
- 4-tier LRU caching (static/semi-static/dynamic/volatile)
- Zod schema validation
- Structured logging (pino)
- Metrics tracking (p50/p95/p99 latencies)
- Cache hit/miss rates
- SQL/Cypher injection detection

**Query Examples:**
```javascript
// Code graph query (Apache AGE)
{
  "tool": "query_code_graph",
  "query_type": "search_entities",
  "entity_name": "MsgCreateBatch",
  "repo_name": "regen-ledger"
}

// Semantic document search (pgvector)
{
  "tool": "search_knowledge",
  "query": "regenerative agriculture practices",
  "limit": 10
}

// Intelligent hybrid search (auto-routing)
{
  "tool": "hybrid_search",
  "query": "How does credit retirement work?",
  "limit": 10
}
// → Routes to code graph for "retirement" code entities
// → Also searches documentation and RDF triples
// → Combines via RRF fusion

// Call graph traversal (Apache AGE)
{
  "tool": "query_code_graph",
  "query_type": "find_callers",
  "entity_name": "Retire"
}
```

### 6. Agent Integration

#### ElizaOS Agents
Five AI agents with specialized roles:
- **RegenAI** - Development orchestrator
- **Advocate** - Community engagement
- **Voice of Nature** - Philosophical perspective
- **Governor** - Governance expertise
- **Narrator** - Storytelling and synthesis

**Access Patterns:**
1. Direct PostgreSQL queries for agent state
2. MCP tools for knowledge retrieval
3. Plugin-based architecture for extensibility

## Hybrid RAG Implementation

### Query Processing Flow

```
User Query
    │
    ▼
Query Analysis
    ├─► Semantic Intent Extraction
    ├─► Entity Recognition
    └─► Query Type Classification
              │
              ▼
    MCP Server Query Router
        ├─► Vector Search (Layer 1: Documents)
        ├─► SPARQL Query (Layer 2: RDF Graph)
        ├─► Cypher Query (Layer 3: Code Graph)
        └─► Hybrid Query (All 3 layers)
              │
              ▼
    Result Fusion (RRF)
        ├─► Rank by relevance
        ├─► Deduplicate results
        ├─► Apply permissions
        └─► Format response
              │
              ▼
        Agent Response
        (Comprehensive: Code + Docs + Community)
```

### Semantic Search Pipeline

1. **Query Embedding Generation**
   - Convert user query to BGE embedding
   - Apply query expansion techniques

2. **Vector Similarity Search**
   ```sql
   SELECT content, 1 - (embedding <=> query_vector) as similarity
   FROM koi_embeddings
   WHERE similarity > threshold
   ORDER BY similarity DESC
   LIMIT k;
   ```

3. **Context Retrieval**
   - Fetch surrounding chunks
   - Retrieve document metadata
   - Apply agent-specific filters

### Knowledge Graph Query Pipeline

1. **Natural Language to SPARQL**
   - LLM converts questions to SPARQL
   - Ontology guides query construction
   - Validation against schema

2. **SPARQL Execution**
   ```sparql
   PREFIX regen: <https://regen.network/ontology#>

   SELECT ?doc ?title ?concept WHERE {
     ?doc regen:discusses ?concept .
     ?doc regen:title ?title .
     ?concept rdf:type regen:RegenerativeConcept .
     FILTER(REGEX(?title, "carbon", "i"))
   }
   ```

3. **Graph Traversal**
   - Follow relationship paths
   - Aggregate connected entities
   - Apply reasoning rules

### Result Fusion Strategy

**Reciprocal Rank Fusion (RRF):**

The MCP server uses RRF to combine results from all three knowledge layers:

```python
def reciprocal_rank_fusion(results_by_layer, k=60):
    """
    Combine results from 3 layers using RRF.

    Args:
        results_by_layer: {
            'vector': [(doc_id, score), ...],    # Layer 1
            'rdf': [(doc_id, score), ...],       # Layer 2
            'code': [(entity_id, score), ...]    # Layer 3
        }
        k: RRF constant (default 60)

    Returns:
        Combined ranking with RRF scores
    """
    combined_scores = {}

    for layer, results in results_by_layer.items():
        for rank, (item_id, _) in enumerate(results, 1):
            score = 1.0 / (k + rank)
            combined_scores[item_id] = combined_scores.get(item_id, 0) + score

    return sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
```

**Query Type Routing:**

```python
def route_query(query, query_type):
    """Intelligent routing based on query characteristics"""
    if "function" in query or "code" in query:
        # Code-focused: prioritize Layer 3 (Code Graph)
        return query_code_graph(query)
    elif "governance" in query or "proposal" in query:
        # Ontological: prioritize Layer 2 (RDF Graph)
        return query_rdf_graph(query)
    elif is_semantic_question(query):
        # Exploratory: prioritize Layer 1 (Vector Search)
        return query_vector_search(query)
    else:
        # Comprehensive: query all 3 layers with RRF fusion
        return hybrid_search(query)
```

## Ontology Design

### Unified Metabolic Ontology
Based on living systems theory with 36 core classes:

**Core Metaphors:**
- **System** - Self-organizing wholes
- **Organ** - Functional components
- **MetabolicFlow** - Information/resource flows
- **Transformation** - State changes
- **FeedbackLoop** - Regulatory mechanisms

**Domain-Specific Extensions:**
- **DiscourseElement** - Communication artifacts
- **ScientificProcess** - Research activities
- **GovernanceAct** - Decision-making events
- **EcologicalAsset** - Environmental resources

### Source-Specific Ontologies
Specialized ontologies for each content source:

**GitHub Ontology:**
- Repository, Commit, Issue, PullRequest
- Contributor, Branch, Release

**Twitter Ontology:**
- Tweet, Thread, Mention, Hashtag
- User, Retweet, Like

**Discourse Ontology:**
- Topic, Post, Category, Tag
- Member, Vote, Solution

## Performance Characteristics

### Throughput Metrics
- **Sensor ingestion**: 1,500+ documents/day
- **Embedding generation**: ~100ms per document
- **Entity extraction**: 2-3 seconds per document
- **End-to-end latency**: 3-5 seconds from sensor to availability

### Storage Efficiency
- **Document deduplication**: 90% reduction in redundant processing
- **Chunk optimization**: 40,000+ chunks from 26 unique documents
- **Embedding storage**: 1024-dimensional vectors with compression
- **Triple storage**: 3,900+ RDF triples with full reasoning

### Query Performance
- **Semantic search**: <200ms average response
- **SPARQL queries**: <500ms for complex traversals
- **Hybrid queries**: <1 second total latency
- **Cache hit rate**: 70%+ for common queries

## Production Deployment

### Service Architecture
```yaml
Services:
  koi-coordinator:
    port: 8200
    role: Sensor event routing

  koi-event-bridge:
    port: 8100
    role: Event processing & deduplication

  bge-embedding-server:
    port: 8090
    role: Vector embedding generation

  apache-jena-fuseki:
    port: 3030
    role: RDF triplestore & SPARQL

  postgresql:
    port: 5433
    role: Vector storage (pgvector) + Code graph (Apache AGE)

  mcp-server:
    package: regen-koi-mcp@1.1.0
    role: Unified knowledge API (9 MCP tools)
```

### Monitoring & Observability
- Real-time dashboard at port 8400
- Pipeline statistics and throughput metrics
- Agent processing status tracking
- Content source breakdown visualization

## Future Enhancements

### Planned Improvements

1. **Advanced Reasoning**
   - OWL-DL inference rules
   - Temporal reasoning capabilities
   - Causal relationship extraction

2. **Federated Queries**
   - Cross-organization knowledge sharing
   - Distributed SPARQL endpoints
   - Privacy-preserving aggregation

3. **Adaptive Learning**
   - Reinforcement learning from query feedback
   - Ontology evolution through usage patterns
   - Dynamic embedding model selection

4. **Enhanced Extraction**
   - Multi-modal content processing (images, audio)
   - Scientific paper parsing with equation extraction
   - Code repository semantic analysis

## Conclusion

This triple-layer hybrid RAG architecture represents a significant advancement in AI knowledge systems. By combining **three complementary knowledge representations** - semantic vector embeddings, structured RDF knowledge graphs, and code entity graphs - we create a system that can handle exploratory questions, precise ontological queries, and code-level navigation simultaneously.

**The Three Layers:**
1. **Layer 1 (pgvector)**: Semantic understanding across 15,000+ documents from 12 platforms
2. **Layer 2 (Apache Jena)**: Ontological reasoning with 101,903 RDF triples
3. **Layer 3 (Apache AGE)**: Code navigation with 26,768 entities and 11,331 call edges

The biomimetic design philosophy, treating knowledge as a living system with metabolic flows and transformations, aligns perfectly with Regen Network's mission of regenerative systems. This architecture not only serves current needs but is designed to evolve and adapt, growing more capable and comprehensive over time.

Through careful integration of cutting-edge technologies - from distributed sensors to OpenAI embeddings, from RDF reasoning to tree-sitter AST parsing, from SPARQL to Cypher queries - we've built a knowledge infrastructure that empowers AI agents to engage meaningfully with complex regenerative concepts at every level: community discussions, ontological relationships, and source code implementation.

**Access via MCP Server v1.1.0**: All three knowledge layers are unified behind a production-ready Model Context Protocol server with 9 tools, RRF fusion, and Phase 7 hardening (retry logic, circuit breakers, caching, validation). Available as `regen-koi-mcp@1.1.0` on npm.
---

## Implementation Updates (September 30, 2025)

### BM25 Keyword Search Enhancement

**Motivation:** Pure semantic search (BGE embeddings) showed limitations with entity names and exact keyword matching. Integrated PostgreSQL full-text search for hybrid retrieval.

**Architecture Update:**

```
Query Input
    ↓
┌───────────────────────────┐
│  Query Router             │
├───────────┬───────────────┤
│ Semantic  │  Keyword      │
│ (BGE)     │  (BM25/FTS)   │
└─────┬─────┴──────┬────────┘
      │            │
      ↓            ↓
┌─────────┐  ┌──────────┐
│ Vector  │  │   FTS    │
│ Search  │  │  Search  │
│ (Top-K) │  │ (Top-K)  │
└────┬────┘  └─────┬────┘
     │             │
     └──────┬──────┘
            ↓
    ┌───────────────┐
    │ RRF Fusion    │
    └───────┬───────┘
            ↓
    Ranked Results
```

**Implementation Details:**

**Database Layer:**
```sql
-- FTS infrastructure
ALTER TABLE koi_memories ADD COLUMN content_tsv tsvector;
CREATE INDEX koi_memories_content_tsv_idx ON koi_memories USING GIN (content_tsv);

-- Auto-update trigger with weighted search
CREATE FUNCTION koi_memories_content_tsv_trigger() RETURNS trigger AS $$
BEGIN
  NEW.content_tsv := 
    setweight(to_tsvector('english', COALESCE(NEW.content->>'text', ''), 'A') ||
    setweight(to_tsvector('english', COALESCE(NEW.metadata->>'title', ''), 'B') ||
    setweight(to_tsvector('english', COALESCE(NEW.metadata->>'description', ''), 'C');
  RETURN NEW;
END
$$ LANGUAGE plpgsql;
```

**Query API Layer:**
- `performSemanticSearch()` - BGE embeddings via cosine distance
- `performKeywordSearch()` - ts_rank_cd() for BM25-like ranking  
- `reciprocalRankFusion()` - Combines results with position-based scoring
- `calculateConfidence()` - Multi-factor confidence from fused results

**Benefits:**
- **Better entity recall:** Names, organizations, technical terms
- **Exact phrase matching:** Citations, specific terminology
- **Complementary strengths:** Semantic understanding + keyword precision
- **Seamless integration:** RRF fusion maintains unified ranking

**Performance:**
- Semantic search: ~100ms
- Keyword search: ~50ms
- RRF fusion: ~10ms overhead
- **Total: ~160ms** (20% faster than semantic-only due to better caching)

---

### Provenance Traceability System

**Context:** Full provenance chain required for compliance, citations, and verifiability.

**Architecture:**

```
Search Result
    ↓
┌─────────────────────────┐
│ Chunk RID               │
│ orn:web.page:domain/    │
│   hash#chunk3           │
└───────┬─────────────────┘
        │
        ↓ metadata->>url
┌─────────────────────────┐
│ Source URL              │
│ https://domain.com/     │
│   page-title            │
└───────┬─────────────────┘
        │
        ↓ CAT Receipts
┌─────────────────────────┐
│ Transformation Chain    │
│ • Sensor Collection     │
│ • Text Chunking         │
│ • Embedding Generation  │
│ • Graph Triple Creation │
└─────────────────────────┘
```

**Implementation Fixes:**

1. **Backend API** (`pipeline_metadata_api.py`):
   - Fixed `fetch_source_url()` to use `WHERE rid = $1`
   - Properly extracts URL from chunk metadata
   - Returns full provenance timeline with URLs

2. **Frontend UI** (`ProvenanceTimeline.tsx`):
   - Added `source_url` field to document interface
   - Displays clickable links to original sources
   - Shows full CAT receipt chain

**Data Quality:**
- **100% URL coverage** across all 4,160+ records
- All sensors validated (GitHub, GitLab, Website, Discourse, Podcast)
- Website sensor refreshed with verified URLs
- Provenance API tested and confirmed working

**Impact:**
- Complete traceability for all knowledge
- Supports academic citation requirements
- Enables user verification of facts
- Foundation for feedback attribution

---

### Updated Performance Metrics

**Storage Statistics:**
- **Documents:** 4,160+ with embeddings
- **Chunks:** 40,000+ text segments
- **FTS Index:** 4,031 records (97% coverage)
- **URL Coverage:** 100% across all sources

**Query Performance:**
```
Semantic Search:     ~100ms
Keyword Search:      ~50ms
RRF Fusion:          ~10ms
Total Hybrid:        ~160ms
Provenance Lookup:   ~20ms
──────────────────────────
End-to-End:         ~180ms
```

**Data Sources:**
| Source | Records | Embeddings | URLs |
|--------|---------|------------|------|
| GitHub | 1,747 | 100% | 100% |
| Website | 792 | 100% | 100% |
| Discourse | 905 | 100% | 100% |
| GitLab | 600 | 100% | 100% |
| Podcast | 116 | 100% | 100% |

---

### Architecture Diagram Update

**Hybrid RAG Query Flow:**

```
┌─────────────────┐
│  User Query     │
│  "biochar for   │
│   soil carbon"  │
└────────┬────────┘
         │
         ↓
┌────────────────────────────┐
│  Query API (8301)          │
│  - Parse query             │
│  - Route to search methods │
└───────┬────────────────────┘
        │
        ├──────────────────┬──────────────────┐
        ↓                  ↓                  ↓
┌───────────────┐  ┌───────────────┐  ┌──────────────┐
│ BGE Semantic  │  │ BM25 Keyword  │  │ SPARQL Graph │
│ (vectors)     │  │ (FTS)         │  │ (optional)   │
└───────┬───────┘  └───────┬───────┘  └──────┬───────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           ↓
                  ┌────────────────┐
                  │  RRF Fusion    │
                  │  (rank merge)  │
                  └────────┬───────┘
                           ↓
                  ┌────────────────┐
                  │  Confidence    │
                  │  Calculation   │
                  └────────┬───────┘
                           ↓
         ┌─────────────────┴─────────────────┐
         ↓                                    ↓
┌────────────────┐                  ┌──────────────────┐
│ Return Results │                  │ Adaptive Extract │
│ + Provenance   │                  │ (if low conf)    │
│ URLs           │                  └──────────────────┘
└────────────────┘
```


---

## Major Update: OpenAI Embeddings Migration (October 2025)

### Migration Complete ✅

**Status:** Production deployment successful - all objectives met

**Key Changes:**

1. **Embedding Model Migration**
   - **From:** BAAI/bge-large-en-v1.5 (MTEB 54.25)
   - **To:** OpenAI text-embedding-3-large (MTEB 64.59)
   - **Improvement:** +10 MTEB points, 12x faster query times

2. **Fusion Method Upgrade**
   - **From:** Reciprocal Rank Fusion (k=60)
   - **To:** Weighted Average Fusion (0.7 vector + 0.3 keyword)
   - **Result:** Eliminated score compression, excellent ranking discrimination

3. **Complete Re-Embedding**
   - Re-embedded all 6,174 memories with OpenAI embeddings
   - 100% coverage maintained
   - One-time cost: $0.78
   - Completion time: 36 minutes

**Performance Improvements:**

| Metric | Before (BGE) | After (OpenAI) | Improvement |
|--------|--------------|----------------|-------------|
| Query embedding | 4s | 341ms | 12x faster |
| End-to-end search | 6s | 105ms | 57x faster |
| Score discrimination | 0.016-0.016 | 0.36-0.26 | ∞ better |
| Search quality | Poor | Excellent | Major |

**Architecture Impact:**

```
Updated Query Flow:

Query Input
    ↓
┌────────────────────────────┐
│  Query API (8301)          │
│  - OpenAI embedding gen    │  ← CHANGED: Using OpenAI API
│  - Route to search methods │
└───────┬────────────────────┘
        │
        ├──────────────────┬──────────────────┐
        ↓                  ↓                  ↓
┌───────────────┐  ┌───────────────┐  ┌──────────────┐
│ OpenAI Vector │  │ BM25 Keyword  │  │ SPARQL Graph │
│ (1024 dim)    │  │ (FTS)         │  │ (optional)   │
└───────┬───────┘  └───────┬───────┘  └──────┬───────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           ↓
                  ┌──────────────────┐
                  │ Weighted Average │  ← CHANGED: From RRF k=60
                  │ Fusion (0.7/0.3) │
                  └────────┬───────────┘
                           ↓
                  Ranked Results (0.36-0.26 score range)
```

**Data Quality Status:**

- ✅ 100% embedding coverage (6,174/6,174)
- ✅ 100% URL coverage across all sources
- ✅ Complete provenance tracking (29,714 CAT receipts)
- ✅ Synthetic receipts for historical data gaps

**Cost Structure:**

- One-time: $0.78 (re-embedding)
- Ongoing: ~$0.02/month (query embeddings @ 100/day)
- **ROI:** Massive performance gains for negligible cost

**No Breaking Changes:**

- API endpoints unchanged
- Database schema unchanged (just data replacement)
- Frontend integration unchanged
- MCP tools unchanged

See `/opt/projects/koi-processor/docs/SEARCH_QUALITY_FIX_PLAN.md` for complete migration details.

**Last Updated:** October 1, 2025

---

## Major Update: Code Graph Integration with Apache AGE (November 2025)

### Architecture Evolution: Three Knowledge Layers

The system has evolved to include a **third knowledge layer** specifically for code understanding:

```
┌─────────────────────────────────────────────────────────┐
│                   KOI Knowledge System                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Layer 1: DOCUMENT VECTORS (pgvector)                  │
│  - 15,000+ documents from 12 platforms                 │
│  - OpenAI embeddings (1024-dim)                        │
│  - Semantic search                                     │
│                                                         │
│  Layer 2: RDF KNOWLEDGE GRAPH (Apache Jena Fuseki)     │
│  - 101,903 RDF triples                                 │
│  - SPARQL queries, canonical categories                │
│  - Semantic reasoning                                  │
│                                                         │
│  Layer 3: CODE GRAPH (Apache AGE) ← NEW!               │
│  - 26,768 code entities (Functions, Structs, etc.)    │
│  - 11,331 CALLS edges                                  │
│  - Cypher graph queries                                │
│  - Tree-sitter AST extraction                          │
│                                                         │
└─────────────────────────────────────────────────────────┘
                         │
                         ↓
              ┌──────────────────────┐
              │  MCP Server v1.1.0   │
              │  (regen-koi-mcp)     │
              │  - 9 Tools           │
              │  - RRF Fusion        │
              │  - Phase 7 Hardening │
              └──────────────────────┘
```

### Code Graph (Apache AGE)

**Purpose:** Enable code-level understanding and navigation for AI agents.

**Storage:** PostgreSQL with Apache AGE extension (same PostgreSQL instance as pgvector)

**Graph Name:** `regen_graph_v2`

**Content:**
- **26,768 entities** extracted via tree-sitter AST parsing
  - Methods: 19,884
  - Imports: 3,363
  - Functions: 1,693
  - Structs: 1,636
  - Interfaces: 192
  - Concepts: 10 (domain abstractions)

- **11,331 CALLS edges** mapping function call relationships
  - Enables "what calls this?" queries
  - Enables "what does this call?" queries
  - Call graph traversal
  - Orphan code detection

**Extraction Pipeline:**
```
Go Source Code
      ↓
Tree-sitter Parser (AST)
      ↓
Entity Extractor
  - Function signatures
  - Struct definitions
  - Interface declarations
  - Method implementations
      ↓
Relationship Analyzer
  - CALLS edges (function → function)
  - CONTAINS edges (module → entity)
  - EXPLAINS edges (concept → code)
      ↓
Apache AGE Graph (Cypher)
```

**Query Capabilities:**
- `find_callers(function_name)` - Who calls this function?
- `find_callees(function_name)` - What does this function call?
- `find_call_graph(function_name)` - Complete call tree
- `find_orphaned_code()` - Functions never called
- `trace_call_chain(from, to)` - Path between functions
- `search_entities(name)` - Find by name pattern
- `find_by_type(entity_type)` - List all Structs, Functions, etc.
- `list_modules()` - Show module hierarchy
- `module_entities(module_name)` - Code in specific module

**Integration with Existing Layers:**

```
User Query: "How does credit retirement work?"

MCP Server Routes to All 3 Layers:

1. Apache AGE (Code Graph)
   └─ Cypher: MATCH (e:Entity {name: 'MsgRetire'})
   └─ Returns: MsgRetire struct, Retire function, retirement handlers

2. Apache Jena (RDF Graph)
   └─ SPARQL: Find triples about retirement
   └─ Returns: Semantic relationships, canonical categories

3. pgvector (Document Search)
   └─ Vector: Semantic search for "retirement"
   └─ Returns: Documentation, forum posts, guides

RRF Fusion → Combined Results
```

### MCP Server v1.1.0 (Phase 7 Production Ready)

**Location:** [github.com/gaiaaiagent/regen-koi-mcp](https://github.com/gaiaaiagent/regen-koi-mcp)

**NPM Package:** `regen-koi-mcp@1.1.0`

**Deployment:** `npx -y regen-koi-mcp@latest` (auto-updates)

**9 MCP Tools:**

1. **query_code_graph** - 15+ graph query types over Apache AGE
2. **hybrid_search** - Intelligent routing (graph vs vector)
3. **search_knowledge** - Semantic search with date filters
4. **search_github_docs** - Documentation across 4 repos
5. **get_repo_overview** - Repository structure
6. **get_tech_stack** - Technology breakdown
7. **get_stats** - Knowledge base statistics
8. **generate_weekly_digest** - Activity summaries
9. **get_mcp_metrics** - Production metrics

**Phase 7 Production Features:**

**Resilience:**
- Exponential backoff retry (3 attempts: 1s → 2s → 4s)
- Circuit breaker pattern (prevents cascading failures)
- Timeout enforcement (30s default)
- Graceful degradation

**Observability:**
- Structured logging (pino → stderr, MCP-safe)
- Latency tracking (p50/p95/p99 percentiles)
- Cache hit/miss rates
- Error tracking by tool
- Circuit breaker state monitoring

**Performance:**
- 4-tier LRU caching:
  - Static: 1 hour TTL (repository lists)
  - Semi-static: 10 min TTL (entity types)
  - Dynamic: 5 min TTL (search results)
  - Volatile: 1 min TTL (metrics)
- Query result caching reduces API load

**Security:**
- Zod schema validation on all inputs
- SQL/Cypher injection detection
- Path traversal prevention
- Sensitive data redaction in logs

**Production Metrics (Current):**
- Query latency: p95 < 500ms, p99 < 1000ms
- Cache hit rate: Target > 50%
- Success rate: 100%
- Circuit breaker trips: 0 (healthy)

### Performance Impact

**Query Performance with Code Graph:**

| Query Type | Latency (p95) | Cache Hit Rate |
|------------|---------------|----------------|
| Code entity search | 753ms | 45% |
| Call graph traversal | 1,155ms | 30% |
| Hybrid search (all 3) | 2,781ms | 25% |
| Document search only | 341ms | 60% |

**Storage:**
- Apache AGE: ~50MB (26,768 entities + 11,331 edges)
- pgvector: ~200MB (15,000+ documents × 1024-dim)
- Apache Jena: ~100MB (101,903 triples)
- **Total:** ~350MB in-memory, efficient indexes

### Use Cases Enabled

**Code Navigation:**
- "What functions call CreateBatch?"
- "Show me the call graph for MsgRetire"
- "Find all orphaned code that's never called"
- "What Structs exist in the ecocredit module?"

**Cross-Layer Queries:**
- "How does credit retirement work?" → Code + Docs + RDF
- "Show me the MsgCreateBatch implementation and documentation"
- "Explain the Keeper pattern with code examples"

**Impact Analysis:**
- "If I change this function, what will break?"
- "What depends on the BasketKeeper?"
- "Trace the call path from API to database"

### Technology Stack Update

**Added:**
- Apache AGE (PostgreSQL extension for graph)
- Tree-sitter (AST parser for Go)
- Cypher query language
- pino (structured logging)
- lru-cache (multi-tier caching)
- Zod (validation schemas)

**Updated:**
- MCP Server: v1.0.6 → v1.1.0
- PostgreSQL: Now hosts both pgvector AND Apache AGE
- Query fusion: Now merges 3 sources (was 2)

**Last Updated:** November 27, 2025
