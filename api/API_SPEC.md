# Orthodox Study Bible API Specification

Client implementation guide for the Reader UI and MCP Server.

**Base URL:** `http://localhost:8000` (dev) | Configure for production
**Content-Type:** `application/json`
**Interactive Docs:** `/docs` (Swagger) | `/redoc` (ReDoc)

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Core Concepts](#core-concepts)
3. [Endpoints](#endpoints)
   - [Books](#books)
   - [Passages](#passages)
   - [Annotations](#annotations)
   - [Patristic Sources](#patristic-sources)
   - [Context (MCP)](#context-mcp)
   - [Chat](#chat)
4. [Data Quirks](#data-quirks)
5. [Error Handling](#error-handling)
6. [Client Recipes](#client-recipes)

---

## Quick Start

### Reader App: Load a Chapter
```http
GET /books/genesis/chapters/1/passages?expand=annotations
```

### MCP Server: Get Full Context
```http
GET /context/Isa_vchap7-14
```

### Lookup a Book
```http
GET /books/matthew
```

---

## Core Concepts

### Passage IDs

Passage IDs are **opaque strings**. Do not parse them.

| Example | Book | Chapter | Verse |
|---------|------|---------|-------|
| `Gen_vchap1-1` | Genesis | 1 | 1 |
| `Ps_vchap22-1` | Psalms | 22 | 1 |
| `Matt_vchap5-12` | Matthew | 5 | 12 |
| `P2et_vchap2-6` | 2 Peter | 2 | 6 |

The API returns `book_id`, `chapter`, and `verse` fields—use those, not the ID string.

### Book IDs

Lowercase, no spaces: `genesis`, `matthew`, `songofsolomon`, `1corinthians`

### Expand Modes

Control response detail level for passage endpoints:

| Mode | Use Case | Includes |
|------|----------|----------|
| `none` | Fast scanning, ID lists | Passage text + annotation IDs only |
| `annotations` | **Reader display** | + Embedded annotations grouped by type |
| `full` | **MCP context** | + Resolved cross-refs, patristic names, navigation, HTML |

```http
GET /passages/Gen_vchap1-1?expand=annotations
GET /books/genesis/chapters/1/passages?expand=full
```

### Annotation Types

| Type | ID Pattern | Description |
|------|------------|-------------|
| `study` | `f{n}` | Patristic commentary and theological notes |
| `liturgical` | `fx{n}` | Liturgical usage references |
| `variant` | `fvar{n}` | NT manuscript variants (NU-Text vs M-Text) |
| `citation` | `fcit{n}` | "See note at X" cross-references |
| `article` | slug | Topical study articles (e.g., `creation`, `trinity`) |
| `cross_ref` | — | Cross-reference markers (in annotation_markers only) |

---

## Endpoints

### Books

#### List All Books
```http
GET /books
GET /books?testament=old
GET /books?testament=new
```

**Response:**
```json
{
  "books": [
    {
      "id": "genesis",
      "name": "Genesis",
      "abbreviation": "Gen",
      "abbreviations": ["Gen"],
      "order": 1,
      "testament": "old",
      "chapter_count": 50,
      "passage_count": 1533
    }
  ],
  "total": 78
}
```

#### Get Book Details
```http
GET /books/{book_id}
```

**Response:**
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

#### Get Chapter Metadata
```http
GET /books/{book_id}/chapters/{chapter}
```

**Response:**
```json
{
  "book_id": "genesis",
  "book_name": "Genesis",
  "chapter": 1,
  "verse_count": 31,
  "first_verse_id": "Gen_vchap1-1",
  "last_verse_id": "Gen_vchap1-31"
}
```

#### Get Chapter Passages (Primary Reader Endpoint)
```http
GET /books/{book_id}/chapters/{chapter}/passages
GET /books/{book_id}/chapters/{chapter}/passages?expand=annotations
GET /books/{book_id}/chapters/{chapter}/passages?expand=full
GET /books/{book_id}/chapters/{chapter}/passages?verse_start=1&verse_end=10
```

**Response:**
```json
{
  "book_id": "genesis",
  "book_name": "Genesis",
  "chapter": 1,
  "passages": [
    {
      "id": "Gen_vchap1-1",
      "book_id": "genesis",
      "chapter": 1,
      "verse": 1,
      "text": "In the beginning God made heaven and earth.",
      "format": "prose",
      "study_note_ids": ["f1", "f2"],
      "liturgical_ids": ["fx1"],
      "variant_ids": [],
      "citation_ids": [],
      "article_ids": ["creation"],
      "cross_ref_targets": []
    }
  ],
  "total": 31,
  "navigation": {
    "prev_chapter": null,
    "next_chapter": "/books/genesis/chapters/2/passages"
  }
}
```

**Navigation crosses book boundaries:** Genesis 50 → Exodus 1

---

### Passages

#### Get Single Passage
```http
GET /passages/{passage_id}
GET /passages/{passage_id}?expand=annotations
GET /passages/{passage_id}?expand=full
GET /passages/{passage_id}?expand=full&include_html=true
```

**Response (expand=annotations):**
```json
{
  "id": "Gen_vchap1-1",
  "book_id": "genesis",
  "chapter": 1,
  "verse": 1,
  "text": "In the beginning God made heaven and earth.",
  "format": "prose",
  "study_note_ids": ["f1"],
  "annotations": {
    "study_notes": [
      {
        "id": "f1",
        "type": "study",
        "verse_display": "1:1",
        "text": "<b>1:1</b> God the Father made heaven and earth...",
        "patristic_citations": ["Creed"],
        "scripture_refs": [
          {"id": "Ps_vchap103-30", "display": "Psalms 103:30"}
        ]
      }
    ],
    "liturgical": [],
    "variants": [],
    "citations": [],
    "articles": []
  },
  "annotation_markers": [
    {"id": "f1", "type": "study", "preceding": "made heaven and earth."}
  ]
}
```

**Response (expand=full) adds:**
```json
{
  "book_name": "Genesis",
  "html": "<span class=\"chbeg\" id=\"Gen_vchap1-1\">...",
  "cross_references": {
    "text": "1:23a Isaiah 7:14...",
    "targets": [
      {
        "id": "Isa_vchap7-14",
        "book_id": "isaiah",
        "book_name": "Isaiah",
        "chapter": 7,
        "verse": 14,
        "preview": "Therefore the Lord Himself will give you a sign..."
      }
    ]
  },
  "navigation": {
    "prev": "Gen_vchap1-1",
    "next": "Gen_vchap1-2"
  }
}
```

**Patristic citations expand to names in `full` mode:**
```json
"patristic_citations": [
  {"id": "BasilG", "name": "Basil the Great"},
  {"id": "JohnChr", "name": "John Chrysostom"}
]
```

#### Batch Fetch Passages
```http
GET /passages?ids=Gen_vchap1-1,Gen_vchap1-2,Gen_vchap1-3
GET /passages?ids=Gen_vchap1-1,Gen_vchap1-2&expand=annotations
```

**Limits:** Maximum 500 passages per request.

---

### Annotations

#### Query Annotations
```http
GET /annotations
GET /annotations?type=study
GET /annotations?type=variant
GET /annotations?patristic_source=BasilG
GET /annotations?book_id=genesis
GET /annotations?type=study&patristic_source=JohnChr&limit=50&offset=0
```

**Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `type` | enum | `study`, `liturgical`, `variant`, `citation`, `article` |
| `patristic_source` | string | Church Father ID (e.g., `BasilG`) |
| `book_id` | string | Filter to annotations in a book |
| `limit` | int | 1-500, default 100 |
| `offset` | int | Pagination offset |

**Response:**
```json
{
  "annotations": [
    {
      "id": "f1",
      "type": "study",
      "passage_ids": ["Gen_vchap1-1"],
      "verse_display": "1:1",
      "text": "<b>1:1</b> God the Father made heaven and earth...",
      "patristic_citations": ["Creed"],
      "scripture_refs": ["Ps_vchap103-30"]
    }
  ],
  "total": 6290,
  "limit": 100,
  "offset": 0
}
```

#### Get Single Annotation
```http
GET /annotations/{annotation_id}
```

---

### Patristic Sources

#### List All Church Fathers
```http
GET /patristic-sources
```

**Response:** Sorted by citation count descending.
```json
{
  "sources": [
    {"id": "JohnChr", "name": "John Chrysostom", "citation_count": 312},
    {"id": "BasilG", "name": "Basil the Great", "citation_count": 127}
  ],
  "total": 53
}
```

#### Get Single Source
```http
GET /patristic-sources/{source_id}
```

#### Get Source's Annotations
```http
GET /patristic-sources/{source_id}/annotations
GET /patristic-sources/BasilG/annotations?limit=50&offset=0
```

Returns all annotations citing this Church Father.

---

### Context (MCP)

Optimized for LLM consumption with rich context bundles.

#### Full Context Bundle
```http
GET /context/{passage_id}
```

**Response:**
```json
{
  "passage": {
    /* Full passage with expand=full */
  },
  "cross_references": {
    "outgoing": [
      {"id": "Isa_vchap7-14", "book_name": "Isaiah", "chapter": 7, "verse": 14, "preview": "..."}
    ],
    "incoming": [
      {"id": "Matt_vchap1-23", "book_name": "Matthew", "chapter": 1, "verse": 23, "preview": "..."}
    ]
  },
  "patristic_sources": [
    {"id": "JohnChr", "name": "John Chrysostom"},
    {"id": "Jerome", "name": "Jerome"}
  ],
  "related_articles": [
    {"id": "creation", "type": "article", "text": "CREATION\n\n..."}
  ]
}
```

#### Cross-References Only
```http
GET /context/cross-refs/{passage_id}
```

**Response:**
```json
{
  "passage_id": "Isa_vchap7-14",
  "outgoing": [],
  "incoming": [
    {"id": "Matt_vchap1-23", "book_name": "Matthew", "chapter": 1, "verse": 23, "preview": "..."}
  ]
}
```

**Key Feature:** Bidirectional cross-refs. Isaiah 7:14 shows Matthew 1:23 as incoming because Matthew quotes Isaiah.

---

### Chat

Conversational interface with the OSB study assistant (Michael). The agent has tool access to query passages, annotations, cross-references, and patristic sources.

#### Send Chat Message
```http
POST /chat
```

**Request Body:**
```json
{
  "messages": [
    {"role": "user", "content": "What does Genesis 1:1 teach about the Trinity?"}
  ],
  "context": {
    "passage_id": "Gen_vchap1-1"
  }
}
```

**Context Options:**

| Field | Description |
|-------|-------------|
| `passage_id` | Specific verse user is viewing (e.g., `Gen_vchap1-1`) |
| `book_id` + `chapter` | Chapter user is reading, no specific verse selected |

```json
// Viewing a specific verse
{"context": {"passage_id": "John_vchap3-16"}}

// Reading a chapter (no verse selected)
{"context": {"book_id": "genesis", "chapter": 1}}

// No context (general question)
{"context": null}
```

**Response:**
```json
{
  "message": {
    "role": "assistant",
    "content": "Genesis 1:1 reveals the Trinity through the Hebrew word *Elohim*..."
  },
  "tool_calls": [
    {
      "name": "get_passage",
      "arguments": {"passage_id": "Gen_vchap1-1"},
      "result": { /* passage data */ }
    }
  ],
  "error": null
}
```

**Message Roles:**

| Role | Description |
|------|-------------|
| `user` | User message |
| `assistant` | Assistant response |
| `system` | System instruction (rarely used by client) |

**Agent Tools:**

The assistant can call these tools to access OSB data:

| Tool | Description |
|------|-------------|
| `get_passage` | Retrieve a passage by ID with full study notes |
| `get_chapter_passages` | Get all verses in a chapter |
| `get_passage_context` | Cross-refs, patristic sources, related articles |
| `search_annotations` | Search by type or Church Father |
| `get_patristic_sources` | List all 53 Church Fathers with citation counts |
| `get_book_info` | Book details (chapters, verses, testament) |
| `list_books` | List all 78 canonical books |

**Error Handling:**

The agent retries up to 3 times on empty responses or API errors. If all retries fail:

```json
{
  "message": {
    "role": "assistant",
    "content": "I apologize, but I'm having trouble connecting right now. Please try again."
  },
  "tool_calls": [],
  "error": "HTTP error: 503"
}
```

**Conversation History:**

The frontend manages conversation history. Send the full message list with each request:

```json
{
  "messages": [
    {"role": "user", "content": "What is theosis?"},
    {"role": "assistant", "content": "Theosis, or deification, is..."},
    {"role": "user", "content": "Which Church Fathers wrote about this?"}
  ]
}
```

---

## Data Quirks

### Must-Know for Client Implementation

| Quirk | Details | Client Action |
|-------|---------|---------------|
| **LXX Psalm Numbering** | Psalm 22 = "The Lord is my shepherd" (not 23) | Display as-is; don't "correct" |
| **Semantic Markup** | Text contains `<i>` and `<b>` tags intentionally | Render as HTML, not plain text |
| **Article Placement** | Articles in `article_ids` render **before** the verse | Check `article_ids`, display before verse text |
| **Shared Annotations** | One annotation may cover verses 1-5; all 5 list it | Deduplicate when displaying (track shown IDs) |
| **Poetry Newlines** | Some verses contain `\n` for poetic structure | Preserve line breaks in display |
| **Multi-Abbreviation Books** | Daniel has `["Sus", "Dan", "Bel"]` | Use `abbreviation` (primary) for display |
| **Opaque IDs** | Don't regex-parse `Gen_vchap1-1` | Use `chapter` and `verse` fields instead |

### Format Field Caveat

The `format` field (`prose`/`poetry`) reflects HTML structure, not literary genre. Psalms shows mostly `prose` because verses use `<p>` with inline `<sup>` markers.

**Workaround:** Check for `\n` in text to detect actual poetic line breaks.

### Missing Data

| Item | Notes |
|------|-------|
| Esther 4:6 | Missing in source EPUB—not an API bug |
| 16 orphan annotations | Esther Greek additions, edge cases—documented |

---

## Error Handling

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (e.g., empty IDs list) |
| 404 | Resource not found |
| 422 | Validation error (bad enum value, etc.) |
| 500 | Internal server error |

### Error Response Format

**404:**
```json
{"detail": "Passage not found: Gen_vchap999-1"}
```

**422 (Validation):**
```json
{
  "detail": "Validation error",
  "errors": [
    {"field": "query -> expand", "message": "Input should be 'none', 'annotations' or 'full'"}
  ]
}
```

**500:**
```json
{"detail": "Internal server error"}
```

---

## Client Recipes

### Reader App: Initial Chapter Load

```javascript
// 1. Get chapter with annotations
const response = await fetch('/books/genesis/chapters/1/passages?expand=annotations');
const data = await response.json();

// 2. Render passages
for (const passage of data.passages) {
  // Check for articles (render BEFORE verse)
  if (passage.article_ids.length > 0) {
    renderArticles(passage.annotations.articles);
  }

  // Render verse (text contains <i>/<b> markup)
  renderVerse(passage.verse, passage.text);

  // Render annotation markers inline using annotation_markers[].preceding
  // Render annotation panel from passage.annotations.study_notes, etc.
}

// 3. Navigation
if (data.navigation.next_chapter) {
  enableNextButton(data.navigation.next_chapter);
}
```

### Reader App: Cross-Reference Click

```javascript
async function onCrossRefClick(targetId) {
  // targetId is e.g., "Isa_vchap7-14"
  const response = await fetch(`/passages/${targetId}?expand=annotations`);
  const passage = await response.json();
  showPassageModal(passage);
}
```

### MCP Server: Build Context Prompt

```python
async def get_passage_context_for_llm(passage_id: str) -> str:
    response = await client.get(f"/context/{passage_id}")
    data = response.json()

    # Build prompt context
    lines = [
        f"## {data['passage']['book_name']} {data['passage']['chapter']}:{data['passage']['verse']}",
        f"\n{data['passage']['text']}\n",
    ]

    # Add study notes
    for note in data['passage']['annotations']['study_notes']:
        lines.append(f"### Study Note ({note['verse_display']})")
        lines.append(note['text'])
        if note['patristic_citations']:
            names = [p['name'] for p in note['patristic_citations']]
            lines.append(f"*Sources: {', '.join(names)}*")

    # Add cross-references
    if data['cross_references']['incoming']:
        lines.append("\n### Referenced By:")
        for ref in data['cross_references']['incoming']:
            lines.append(f"- {ref['book_name']} {ref['chapter']}:{ref['verse']}: {ref['preview']}")

    return "\n".join(lines)
```

### MCP Server: "What did Basil say?"

```python
async def get_basil_quotes(book_id: str = None) -> list:
    url = "/patristic-sources/BasilG/annotations"
    if book_id:
        url = f"/annotations?patristic_source=BasilG&book_id={book_id}"

    response = await client.get(url)
    return response.json()['annotations']
```

### Reader App: Chat Interface

```javascript
// Chat state managed by frontend
let conversationHistory = [];

async function sendMessage(userMessage, currentContext) {
  // Add user message to history
  conversationHistory.push({
    role: 'user',
    content: userMessage
  });

  // Build request
  const request = {
    messages: conversationHistory,
    context: currentContext  // { passage_id } or { book_id, chapter } or null
  };

  const response = await fetch('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  });

  const data = await response.json();

  // Add assistant response to history
  conversationHistory.push(data.message);

  // Check for errors
  if (data.error) {
    console.warn('Chat error:', data.error);
  }

  // Optionally show tool calls for transparency
  if (data.tool_calls.length > 0) {
    console.log('Tools used:', data.tool_calls.map(t => t.name));
  }

  return data.message.content;
}

// Usage examples:

// User viewing Genesis 1:1
await sendMessage(
  "What do the Fathers say about this verse?",
  { passage_id: "Gen_vchap1-1" }
);

// User reading Psalm 22 (no specific verse)
await sendMessage(
  "Is this a Messianic psalm?",
  { book_id: "psalms", chapter: 22 }
);

// General question (no context)
await sendMessage(
  "What is the Orthodox view of salvation?",
  null
);

// Clear conversation
function newConversation() {
  conversationHistory = [];
}
```

---

## Health Check

```http
GET /health
```

**Response:**
```json
{"status": "healthy"}
```

---

## CORS

CORS is enabled for all origins by default (`*`). Configure `OSB_CORS_ORIGINS` environment variable for production:

```bash
OSB_CORS_ORIGINS=https://reader.example.com,https://admin.example.com
```
