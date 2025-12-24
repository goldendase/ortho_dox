# Orthodox Study Bible API - Implementation Plan

## Overview

Create a FastAPI REST API to serve Orthodox Study Bible data from MongoDB, supporting:
1. **Reader Component** - Fast verse display with inline annotations, cross-reference following
2. **MCP Server** - Rich theological/semantic context, patristic citations, related passages

---

## Consumer Analysis

### Consumer 1: Reader Component
**Needs:**
- Fast sequential reading (chapter at a time)
- Inline annotations displayed alongside text
- Cross-reference following (click to navigate)
- Annotation markers positioned precisely in text
- Navigation (prev/next verse, chapter)

**Optimized Endpoints:**
- `GET /books/{book_id}/chapters/{chapter}/passages` - Full chapter with embedded annotations
- `GET /passages/{id}?expand=annotations` - Single verse with annotations

### Consumer 2: MCP Server
**Needs:**
- Rich context for LLM prompts (all related material for a passage)
- Patristic source exploration ("What did Basil say about X?")
- Cross-reference discovery (incoming AND outgoing)
- Semantic exploration (related passages via shared annotations)
- Raw HTML access for re-processing

**Optimized Endpoints:**
- `GET /context/{passage_id}` - Full context bundle
- `GET /patristic-sources/{id}/annotations` - All citations by a Church Father
- `GET /context/cross-refs/{passage_id}` - Bidirectional cross-refs

---

## Project Restructure

```
orthodox/
├── venv/                          # NEW: Top-level virtual environment
├── api/                           # NEW: FastAPI application
│   ├── __init__.py
│   ├── main.py                    # FastAPI app entry point
│   ├── config.py                  # Settings (MongoDB URI, etc.)
│   ├── dependencies.py            # Dependency injection
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── books.py               # /books endpoints
│   │   ├── passages.py            # /passages endpoints
│   │   ├── annotations.py         # /annotations endpoints
│   │   ├── patristic.py           # /patristic-sources endpoints
│   │   └── context.py             # /context endpoints (MCP-focused)
│   ├── models/                    # Pydantic response/request models
│   │   ├── __init__.py
│   │   ├── book.py
│   │   ├── passage.py
│   │   ├── annotation.py
│   │   └── common.py
│   └── services/                  # Database query logic
│       ├── __init__.py
│       ├── book_service.py
│       ├── passage_service.py
│       └── annotation_service.py
├── etl/                           # MOVED: ETL code (was parser/)
│   ├── __init__.py
│   ├── models.py
│   ├── epub_parser.py
│   └── mongo_loader.py
├── run_api.py                     # NEW: Convenience script
├── extract.py                     # Updated import path
├── requirements.txt               # Extended with FastAPI deps
├── API_PLAN.md                    # This file
└── PROJECT_ETL.md
```

---

## API Endpoints

### Books (Navigation)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/books` | List all 78 books (filterable by testament) |
| GET | `/books/{book_id}` | Book details with chapter list |
| GET | `/books/{book_id}/chapters/{chapter}` | Chapter metadata |

**Query Parameters for `/books`:**
- `testament`: Filter by "old" or "new"

**Response for `/books/{book_id}`:**
```json
{
  "id": "genesis",
  "name": "Genesis",
  "abbreviation": "Gen",
  "abbreviations": ["Gen"],
  "order": 1,
  "testament": "old",
  "chapter_count": 50,
  "passage_count": 1533,
  "chapters": [
    {"chapter": 1, "verse_count": 31},
    {"chapter": 2, "verse_count": 25}
  ]
}
```

### Passages (Core Reading)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/passages/{passage_id}` | Single verse with expand options |
| GET | `/passages` | Batch fetch by IDs or filter |
| GET | `/books/{book_id}/chapters/{chapter}/passages` | Full chapter for reader |

**Query Parameters:**
- `expand`: `none` | `annotations` | `full` (see Expand Modes below)
- `ids`: Comma-separated passage IDs for batch fetch
- `include_html`: boolean, include raw HTML from ortho_raw
- `verse_start`, `verse_end`: Filter verse range within chapter

**Expand Modes:**
| Mode | Purpose | Includes |
|------|---------|----------|
| `none` | Minimal, fast | passage + annotation IDs only |
| `annotations` | Reader display | + embedded annotation text grouped by type |
| `full` | MCP context | + resolved cross-refs, patristic names, navigation, HTML |

### Annotations (Deep Dive)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/annotations/{id}` | Single annotation detail |
| GET | `/annotations` | Query with filters |

**Query Parameters for `/annotations`:**
- `type`: `study` | `liturgical` | `variant` | `citation` | `article`
- `patristic_source`: Filter by Church Father ID (e.g., "BasilG")
- `book_id`: Filter to annotations in a specific book
- `limit`, `offset`: Pagination

### Patristic Sources
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/patristic-sources` | List all 53 Church Fathers |
| GET | `/patristic-sources/{id}` | Single source details |
| GET | `/patristic-sources/{id}/annotations` | All citations by a source |

**Response for `/patristic-sources`:**
```json
{
  "sources": [
    {"id": "BasilG", "name": "Basil the Great", "citation_count": 127},
    {"id": "JohnChr", "name": "John Chrysostom", "citation_count": 312}
  ],
  "total": 53
}
```

### Context (MCP-Focused)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/context/{passage_id}` | Full context bundle for MCP |
| GET | `/context/cross-refs/{passage_id}` | Incoming + outgoing cross-refs |

**Response for `/context/{passage_id}`:**
```json
{
  "passage": { /* full passage with expand=full */ },
  "cross_references": {
    "outgoing": [ /* passages this verse references */ ],
    "incoming": [ /* passages that reference this verse */ ]
  },
  "patristic_sources": [
    {"id": "BasilG", "name": "Basil the Great"}
  ],
  "related_articles": [ /* topical articles mentioning this passage */ ]
}
```

---

## Key Pydantic Models

### Common Types
```python
from enum import Enum

class Testament(str, Enum):
    OLD = "old"
    NEW = "new"

class Format(str, Enum):
    PROSE = "prose"
    POETRY = "poetry"

class AnnotationType(str, Enum):
    STUDY = "study"
    LITURGICAL = "liturgical"
    VARIANT = "variant"
    CITATION = "citation"
    ARTICLE = "article"

class ExpandMode(str, Enum):
    NONE = "none"
    ANNOTATIONS = "annotations"
    FULL = "full"
```

### Passage Models
```python
class AnnotationMarker(BaseModel):
    id: str                    # "f1", "fx1", "fvar1", etc.
    type: AnnotationType
    preceding: str             # ~40 chars before marker for positioning

class PassageMinimal(BaseModel):
    """expand=none"""
    id: str                    # "Gen_vchap1-1"
    book_id: str
    chapter: int
    verse: int
    text: str                  # Preserves <i>/<b> semantic markup
    format: Format
    study_note_ids: list[str]
    liturgical_ids: list[str]
    variant_ids: list[str]
    citation_ids: list[str]
    article_ids: list[str]
    cross_ref_targets: list[str]

class AnnotationEmbed(BaseModel):
    """Embedded in passage response"""
    id: str
    type: AnnotationType
    verse_display: str
    text: str
    patristic_citations: list[str]  # IDs only for annotations mode
    scripture_refs: list[str]

class AnnotationsGroup(BaseModel):
    study_notes: list[AnnotationEmbed]
    liturgical: list[AnnotationEmbed]
    variants: list[AnnotationEmbed]
    citations: list[AnnotationEmbed]
    articles: list[AnnotationEmbed]

class PassageWithAnnotations(BaseModel):
    """expand=annotations"""
    # ... all PassageMinimal fields ...
    annotations: AnnotationsGroup
    annotation_markers: list[AnnotationMarker]

class PassageRef(BaseModel):
    """For cross-reference targets"""
    id: str
    book_id: str
    book_name: str
    chapter: int
    verse: int
    preview: str               # First ~100 chars

class PatristicCitationExpanded(BaseModel):
    id: str
    name: str

class CrossReferenceData(BaseModel):
    text: str | None           # Full cross-ref text from passage
    targets: list[PassageRef]

class NavigationLinks(BaseModel):
    prev: str | None
    next: str | None

class PassageFull(BaseModel):
    """expand=full"""
    # ... all PassageWithAnnotations fields ...
    book_name: str
    html: str | None
    cross_references: CrossReferenceData
    navigation: NavigationLinks
    # annotations have PatristicCitationExpanded instead of IDs
```

---

## Database Layer

### Connection Management
```python
# api/db/mongodb.py
from motor.motor_asyncio import AsyncIOMotorClient

class MongoDB:
    client: AsyncIOMotorClient | None = None
    db_dox: AsyncIOMotorDatabase | None = None
    db_raw: AsyncIOMotorDatabase | None = None

    @classmethod
    async def connect(cls, uri: str):
        cls.client = AsyncIOMotorClient(uri)
        cls.db_dox = cls.client["ortho_dox"]
        cls.db_raw = cls.client["ortho_raw"]

    @classmethod
    async def close(cls):
        if cls.client:
            cls.client.close()
```

### Existing Indexes (from ETL)
These indexes already exist and should be leveraged:

```javascript
// Passages
db.passages.createIndex("book_id")                           // List by book
db.passages.createIndex({book_id: 1, chapter: 1})           // Chapter queries
db.passages.createIndex({book_id: 1, chapter: 1, verse: 1}) // Navigation
db.passages.createIndex("cross_ref_targets")                 // Find incoming refs
db.passages.createIndex("study_note_ids")                    // Has study notes
db.passages.createIndex("liturgical_ids")
db.passages.createIndex("variant_ids")
db.passages.createIndex("citation_ids")
db.passages.createIndex("article_ids")
db.passages.createIndex("annotation_markers.id")

// Annotations
db.annotations.createIndex("type")                           // Filter by type
db.annotations.createIndex("passage_ids")                    // Reverse lookup
db.annotations.createIndex("patristic_citations")            // By Church Father
```

---

## Implementation Phases

### Phase 1: Project Setup
1. Create `api/` directory structure
2. Move `parser/` → `etl/`, update `extract.py` imports
3. Create top-level venv: `python -m venv venv`
4. Install deps: `pip install fastapi uvicorn[standard] motor pydantic-settings`
5. Set up `api/main.py` with lifespan events
6. Create `run_api.py` convenience script
7. Add `api/config.py` with environment variable support

### Phase 2: Core Models & Books
1. Create `api/models/common.py` with enums and shared types
2. Create `api/models/book.py` with Book schemas
3. Implement `api/services/book_service.py`
4. Create `api/routers/books.py`
5. Wire up in `main.py`

### Phase 3: Passages (Reader Priority)
1. Create `api/models/passage.py` with all expand variants
2. Implement `api/services/passage_service.py` with expand logic
3. Create `api/routers/passages.py`
4. Add chapter passages endpoint
5. Implement batch fetch for efficiency

### Phase 4: Annotations & Patristic
1. Create `api/models/annotation.py`
2. Implement `api/services/annotation_service.py`
3. Create `api/routers/annotations.py`
4. Create `api/routers/patristic.py`

### Phase 5: Context (MCP Priority)
1. Create `api/routers/context.py`
2. Implement cross-reference discovery
3. Add related passages by shared annotations
4. Bundle everything for MCP consumption

### Phase 6: Polish
1. Custom exception handlers (404s, validation errors)
2. OpenAPI documentation (descriptions, examples)
3. CORS middleware if needed for browser access

---

## Dependencies to Add

```
# requirements.txt additions
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
motor>=3.6.0
pydantic>=2.10.0
pydantic-settings>=2.6.0
```

---

## Files to Modify

| File | Action |
|------|--------|
| `parser/` → `etl/` | Rename directory |
| `extract.py` | Update import: `from etl.epub_parser import OSBParser` |
| `requirements.txt` | Add FastAPI dependencies |

## Files to Create

| File | Purpose |
|------|---------|
| `run_api.py` | Convenience script: `uvicorn api.main:app --reload` |
| `api/__init__.py` | Package marker |
| `api/main.py` | FastAPI app with lifespan events |
| `api/config.py` | Settings from env vars (OSB_MONGODB_URI, etc.) |
| `api/dependencies.py` | DB dependency injection |
| `api/routers/__init__.py` | Package marker |
| `api/routers/books.py` | /books endpoints |
| `api/routers/passages.py` | /passages endpoints |
| `api/routers/annotations.py` | /annotations endpoints |
| `api/routers/patristic.py` | /patristic-sources endpoints |
| `api/routers/context.py` | /context endpoints |
| `api/models/__init__.py` | Package marker + re-exports |
| `api/models/common.py` | Enums, pagination, errors |
| `api/models/book.py` | Book schemas |
| `api/models/passage.py` | Passage schemas (all expand variants) |
| `api/models/annotation.py` | Annotation schemas |
| `api/services/__init__.py` | Package marker |
| `api/services/book_service.py` | Book queries |
| `api/services/passage_service.py` | Passage queries with expand logic |
| `api/services/annotation_service.py` | Annotation queries |

---

## Notes to Self / Important Reminders

### Data Quirks to Handle
1. **Passage IDs are opaque** - Don't regex-parse `Gen_vchap1-1`. The chapter/verse fields come from the DB.
2. **LXX Psalm numbering** - Psalm 22 = "The Lord is my shepherd" (not 23)
3. **Semantic markup preserved** - `<i>` and `<b>` in text field are intentional
4. **Poetry newlines** - Some passages have `\n` for poetic structure
5. **Multi-text books** - Daniel has `abbreviations: ["Sus", "Dan", "Bel"]`
6. **Unbalanced quotes** - Multi-verse speeches have quotes spanning verses

### Performance Considerations
1. **Batch annotation fetching** - When expanding passages, collect all annotation IDs first, then batch fetch
2. **Use projections** - Don't fetch full documents when only IDs needed
3. **Leverage indexes** - All the filters map to existing indexes
4. **Pagination** - Default limit 100, max 500 for list endpoints

### Expand Mode Implementation
The `expand` parameter is the key abstraction:
- `none`: Return raw MongoDB document (minimal transformation)
- `annotations`: Fetch linked annotations, group by type, embed in response
- `full`: Additionally resolve cross-refs to PassageRef, resolve patristic_citations to names, add navigation links

### Error Handling
- 404 for non-existent passages, books, annotations
- 400 for invalid query params (bad testament, unknown expand mode)
- Return helpful error messages with the invalid value

### Future Extensibility
- Additional data sources (patristic commentaries, homilies) → new routers
- The `/context` pattern can aggregate across multiple databases
- URL versioning (`/v1/`) when breaking changes needed
- Auth can be added later via FastAPI middleware

---

## User Decisions (Recorded)

- **Auth**: No authentication (internal/localhost only)
- **Rename**: Yes, rename `parser/` → `etl/`
- **Server**: Add `run_api.py` convenience script
