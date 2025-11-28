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

Our system implements a sophisticated hybrid approach to Retrieval-Augmented Generation (RAG) that combines traditional vector similarity search with structured knowledge graph queries. This dual-path architecture enables both semantic understanding through embeddings and precise ontological reasoning through RDF triples, providing AI agents with comprehensive knowledge access capabilities.

## System Overview

### Core Philosophy
The architecture is designed around the concept of "living systems" - treating knowledge as a metabolic process where information flows, transforms, and evolves through various stages. This biomimetic approach aligns with Regen Network's regenerative principles, creating a knowledge ecosystem that grows and adapts organically.

### Key Innovation: Dual Knowledge Representation
Unlike traditional RAG systems that rely solely on vector embeddings, our architecture maintains knowledge in two complementary forms:
1. **Vector Embeddings** - For semantic similarity and contextual understanding
2. **RDF Knowledge Graph** - For structured relationships and ontological reasoning

## Architecture Components

### Data Ingestion Pipeline

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│ KOI Sensors │────▶│ Coordinator  │────▶│ Event Bridge │
│  (Various)  │     │  (Port 8200) │     │  (Port 8100) │
└─────────────┘     └──────────────┘     └──────────────┘
                                                 │
                                 ┌───────────────┴───────────────┐
                                 │                               │
                                 ▼                               ▼
                         ┌──────────────┐            ┌──────────────────┐
                         │  Embedding   │            │ Entity Extractor │
                         │   Server     │            │  (LLM + Ontology)│
                         │  (Port 8090) │            │                  │
                         └──────────────┘            └──────────────────┘
                                 │                               │
                                 ▼                               ▼
                         ┌──────────────┐            ┌──────────────────┐
                         │ PostgreSQL   │            │  Apache Jena     │
                         │  (pgvector)  │            │    Fuseki        │
                         │              │            │  (Port 3030)     │
                         └──────────────┘            └──────────────────┘
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

#### PostgreSQL Database (Port 5433)
Dual-table architecture for optimal performance:

**koi_memories Table:**
- Stores original documents with RIDs
- Maintains version history
- Tracks source sensors and metadata
- Ensures deduplication at document level

**memories Table:**
- Stores chunked content for RAG
- Links to agent access permissions
- Optimized for retrieval operations
- Contains 40,000+ searchable chunks

#### Apache Jena Fuseki (Port 3030)
SPARQL triplestore for knowledge graph:

**Features:**
- Stores 3,900+ RDF triples
- OWL ontology reasoning capabilities
- SPARQL 1.1 query support
- Persistent TDB2 storage
- RESTful HTTP interface

**Dataset Structure:**
```
/koi
  ├── ontologies/      # OWL ontology definitions
  ├── entities/        # Extracted entities
  ├── relationships/   # Inter-entity connections
  └── metadata/        # Provenance and timestamps
```

### 5. Query & Access Layer

#### Knowledge MCP Server
Provides unified access to both knowledge representations:

**Hybrid Query Capabilities:**
1. **Semantic Search** → Routes to PostgreSQL pgvector
2. **Ontological Query** → Routes to Apache Jena Fuseki
3. **Hybrid Query** → Combines results from both systems

**Query Examples:**
```javascript
// Semantic search
{
  "tool": "bge_search",
  "query": "regenerative agriculture practices",
  "top_k": 10
}

// SPARQL query
{
  "tool": "sparql_query",
  "query": "SELECT ?project WHERE { ?project regen:implements ?practice . ?practice rdf:type regen:RegenerativePractice }"
}

// Hybrid query (combines both)
{
  "tool": "hybrid_search",
  "semantic_query": "carbon sequestration",
  "ontological_filter": "?entity rdf:type regen:CarbonProject"
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
    └─► Entity Recognition
              │
              ▼
        Query Router
        ├─► Vector Search (if semantic)
        ├─► SPARQL Query (if structured)
        └─► Hybrid Query (if both)
              │
              ▼
        Result Fusion
        ├─► Rank by relevance
        ├─► Apply permissions
        └─► Format response
              │
              ▼
        Agent Response
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

**Scoring Algorithm:**
```python
def fusion_score(semantic_score, graph_score, query_type):
    if query_type == "factual":
        # Prioritize knowledge graph
        return 0.3 * semantic_score + 0.7 * graph_score
    elif query_type == "exploratory":
        # Prioritize semantic search
        return 0.7 * semantic_score + 0.3 * graph_score
    else:
        # Balanced approach
        return 0.5 * semantic_score + 0.5 * graph_score
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
    role: Vector storage & agent data

  mcp-knowledge-server:
    port: 8200
    role: Unified knowledge API
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

This hybrid RAG and knowledge graph architecture represents a significant advancement in AI knowledge systems. By combining the semantic understanding of vector embeddings with the structured reasoning of knowledge graphs, we create a system that can handle both exploratory questions requiring contextual understanding and precise queries demanding factual accuracy.

The biomimetic design philosophy, treating knowledge as a living system with metabolic flows and transformations, aligns perfectly with Regen Network's mission of regenerative systems. This architecture not only serves current needs but is designed to evolve and adapt, growing more capable and comprehensive over time.

Through careful integration of cutting-edge technologies - from distributed sensors to advanced embedding models, from RDF reasoning to hybrid query processing - we've built a knowledge infrastructure that empowers AI agents to engage meaningfully with complex regenerative concepts and support the transition to a more sustainable future.
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

### Updated Architecture Diagram

**Complete Hybrid RAG + Code Graph:**

```
┌─────────────────────────────────────────────────────────┐
│                    SENSORS (12 platforms)               │
│  GitHub, GitLab, Medium, Discourse, Telegram, Discord,  │
│  Twitter, Podcast, Notion, Ledger, Websites             │
└──────────────────────┬──────────────────────────────────┘
                       ↓ KOI Events
┌─────────────────────────────────────────────────────────┐
│              COORDINATOR + EVENT BRIDGE v2              │
│  Deduplication, versioning, chunking, CAT receipts      │
└──────────────────────┬──────────────────────────────────┘
                       ↓
            ┌──────────┴──────────┐
            ↓                     ↓
    ┌───────────────┐     ┌───────────────┐
    │  BGE Server   │     │  Tree-sitter  │
    │  (8090)       │     │  Code Parser  │
    │  OpenAI API   │     │               │
    └───────┬───────┘     └───────┬───────┘
            │                     │
            ↓                     ↓
┌─────────────────────────────────────────────────────────┐
│           POSTGRESQL (Port 5433)                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────┐    ┌──────────────────┐         │
│  │ koi_memories +   │    │ Apache AGE       │         │
│  │ koi_embeddings   │    │ Graph            │         │
│  │                  │    │                  │         │
│  │ 15,000+ docs     │    │ regen_graph_v2   │         │
│  │ OpenAI vectors   │    │ 26,768 entities  │         │
│  │ 1024-dim         │    │ 11,331 edges     │         │
│  └──────────────────┘    └──────────────────┘         │
│                                                         │
└─────────────────────────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────┐
│        APACHE JENA FUSEKI (Port 3030)                   │
│  - 101,903 RDF triples                                  │
│  - SPARQL queries, canonical categories                 │
└─────────────────────────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────┐
│           MCP SERVER (regen-koi-mcp v1.1.0)             │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Query Router                                    │   │
│  │  ├─ Apache AGE (Cypher) ──→ Code entities      │   │
│  │  ├─ Apache Jena (SPARQL) ──→ RDF triples       │   │
│  │  └─ pgvector (Cosine) ──→ Document vectors     │   │
│  └───────────────────┬─────────────────────────────┘   │
│                      ↓                                  │
│           RRF Fusion + Caching + Metrics                │
│                      ↓                                  │
│                  9 MCP Tools                            │
└─────────────────────┬───────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│              AI AGENTS (Claude, ElizaOS)                │
│  - Comprehensive knowledge access                       │
│  - Code + Docs + Community content                      │
└─────────────────────────────────────────────────────────┘
```

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
