# Orthodox Reader Client Architecture

**Framework:** SvelteKit
**Target:** ROCOR parish members
**Theme:** Byzantine Orthodox (dark, burgundy/gold)

---

## 1. Core Principles

### 1.1 Content-Agnostic Reading Engine
The reader is designed around a **generic content model** that currently serves Scripture but will extend to patristic commentaries, homilies, and theological texts. The abstraction:

```
ContentSource → ContentUnit → Annotation
     ↓              ↓             ↓
   Bible        Chapter       Study Note
  Homilies      Section       Citation
  Patristics    Passage       Cross-ref
```

### 1.2 Mobile-First, Touch-Optimized
- Bottom navigation bar (thumb-reachable)
- Swipe gestures for chapter navigation
- Collapsible annotation panel (slide-up sheet on mobile)
- Minimum 44px touch targets

### 1.3 Reading State Persistence
- Current position survives refresh (localStorage + URL)
- Reading history for "back" navigation through cross-refs
- Annotation collapse states remembered per-session

---

## 2. Project Structure

```
src/
├── lib/
│   ├── api/                    # API client layer
│   │   ├── client.ts           # Base HTTP client with error handling
│   │   ├── books.ts            # Books/chapters endpoints
│   │   ├── passages.ts         # Passages/batch fetch
│   │   ├── annotations.ts      # Annotation queries
│   │   ├── context.ts          # MCP context endpoints (for chat)
│   │   └── types.ts            # TypeScript interfaces matching API
│   │
│   ├── stores/                 # Svelte 5 runes-based state
│   │   ├── reader.svelte.ts    # Position, history, scroll state
│   │   ├── annotations.svelte.ts # Visibility, active annotation
│   │   ├── chat.svelte.ts      # Session ID, messages, context
│   │   └── preferences.svelte.ts # Theme, font size, etc.
│   │
│   ├── components/
│   │   ├── reader/
│   │   │   ├── Chapter.svelte       # Main chapter renderer
│   │   │   ├── Verse.svelte         # Single verse with markers
│   │   │   ├── VerseText.svelte     # HTML-aware text renderer
│   │   │   ├── AnnotationMarker.svelte # Clickable [†] markers
│   │   │   └── Article.svelte       # Study articles (before verse)
│   │   │
│   │   ├── annotations/
│   │   │   ├── Panel.svelte         # Sidebar/sheet container
│   │   │   ├── StudyNote.svelte     # Patristic study notes
│   │   │   ├── CrossRef.svelte      # Cross-reference with preview
│   │   │   ├── Variant.svelte       # Manuscript variants
│   │   │   └── Liturgical.svelte    # Liturgical references
│   │   │
│   │   ├── navigation/
│   │   │   ├── BookPicker.svelte    # Testament → Book → Chapter
│   │   │   ├── ChapterNav.svelte    # Prev/Next chapter controls
│   │   │   ├── BottomBar.svelte     # Mobile nav bar
│   │   │   └── Breadcrumb.svelte    # Genesis > Chapter 1 > v.15
│   │   │
│   │   ├── chat/
│   │   │   ├── ChatWindow.svelte    # Message list + input
│   │   │   ├── Message.svelte       # Single message bubble
│   │   │   ├── ContextBadge.svelte  # Shows current passage context
│   │   │   └── PassageReference.svelte # Clickable refs in chat
│   │   │
│   │   └── ui/                      # Design system primitives
│   │       ├── Button.svelte
│   │       ├── Modal.svelte
│   │       ├── Sheet.svelte         # Bottom sheet (mobile)
│   │       ├── Icon.svelte
│   │       └── Skeleton.svelte      # Loading states
│   │
│   └── utils/
│       ├── html.ts             # Safe HTML rendering helpers
│       ├── dedup.ts            # Annotation deduplication
│       ├── format.ts           # Verse display formatting
│       └── gestures.ts         # Swipe detection
│
├── routes/
│   ├── +layout.svelte          # App shell, theme provider
│   ├── +layout.server.ts       # Load books list for nav
│   ├── +page.svelte            # Landing → redirect to last position
│   │
│   ├── read/
│   │   ├── +layout.svelte      # Reader layout with nav
│   │   └── [book]/
│   │       └── [chapter]/
│   │           ├── +page.svelte
│   │           └── +page.server.ts  # SSR chapter load
│   │
│   ├── chat/
│   │   ├── +page.svelte        # Chat interface
│   │   └── +page.server.ts     # SSR chat init
│   │
│   └── api/                    # Optional: proxy endpoints
│       └── chat/
│           └── +server.ts      # WebSocket or SSE for streaming
│
├── app.css                     # Global styles, CSS variables
├── app.html                    # HTML template
└── hooks.server.ts             # Request hooks (auth future)
```

---

## 3. API Client Design

### 3.1 Base Client

```typescript
// lib/api/client.ts
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(detail);
  }
}

async function request<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(path, API_BASE);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined) url.searchParams.set(k, v);
    });
  }

  const res = await fetch(url);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(res.status, body.detail);
  }
  return res.json();
}

export const api = { request };
```

### 3.2 Domain Clients

```typescript
// lib/api/books.ts
export const books = {
  list: (testament?: 'old' | 'new') =>
    api.request<BooksResponse>('/books', { testament }),

  get: (bookId: string) =>
    api.request<BookDetail>(`/books/${bookId}`),

  getChapterPassages: (bookId: string, chapter: number, expand: ExpandMode = 'annotations') =>
    api.request<ChapterPassages>(`/books/${bookId}/chapters/${chapter}/passages`, { expand }),
};

// lib/api/passages.ts
export const passages = {
  get: (id: string, expand: ExpandMode = 'annotations') =>
    api.request<Passage>(`/passages/${id}`, { expand }),

  batch: (ids: string[], expand: ExpandMode = 'none') =>
    api.request<BatchPassages>('/passages', { ids: ids.join(','), expand }),
};
```

---

## 4. State Management

Using Svelte 5 runes for reactive state:

### 4.1 Reader State

```typescript
// lib/stores/reader.svelte.ts
import { browser } from '$app/environment';

interface ReaderPosition {
  book: string;
  chapter: number;
  verse?: number;      // Optional scroll target
  annotation?: string; // Active annotation ID
}

class ReaderState {
  position = $state<ReaderPosition | null>(null);
  history = $state<ReaderPosition[]>([]);

  constructor() {
    if (browser) {
      const saved = localStorage.getItem('reader_position');
      if (saved) this.position = JSON.parse(saved);
    }
  }

  navigate(pos: ReaderPosition, pushHistory = true) {
    if (pushHistory && this.position) {
      this.history = [...this.history.slice(-49), this.position];
    }
    this.position = pos;
    if (browser) {
      localStorage.setItem('reader_position', JSON.stringify(pos));
    }
  }

  back() {
    const prev = this.history.pop();
    if (prev) {
      this.position = prev;
      this.history = [...this.history];
    }
  }

  get canGoBack() {
    return this.history.length > 0;
  }
}

export const reader = new ReaderState();
```

### 4.2 Chat State

```typescript
// lib/stores/chat.svelte.ts
interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  passageContext?: ReaderPosition; // What the user was reading
  timestamp: Date;
}

class ChatState {
  messages = $state<ChatMessage[]>([]);
  isStreaming = $state(false);
  error = $state<string | null>(null);

  // The passage context to send with next message
  // Synced from reader.position
  currentContext = $state<ReaderPosition | null>(null);

  async send(content: string) {
    // Implementation: POST to LLM server with currentContext
  }
}

export const chat = new ChatState();
```

---

## 5. Routing & Data Loading

### 5.1 Reader Route

```typescript
// routes/read/[book]/[chapter]/+page.server.ts
import type { PageServerLoad } from './$types';
import { books } from '$lib/api/books';
import { error } from '@sveltejs/kit';

export const load: PageServerLoad = async ({ params }) => {
  const { book, chapter } = params;
  const chapterNum = parseInt(chapter, 10);

  if (isNaN(chapterNum)) throw error(400, 'Invalid chapter');

  try {
    const data = await books.getChapterPassages(book, chapterNum, 'annotations');
    return { chapter: data };
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) {
      throw error(404, `${book} chapter ${chapter} not found`);
    }
    throw e;
  }
};
```

### 5.2 URL Scheme

```
/read/genesis/1           → Genesis Chapter 1
/read/genesis/1#v15       → Genesis 1:15 (scroll to verse)
/read/matthew/5?note=f12  → Matthew 5 with annotation f12 open
/chat                     → Chat interface
/chat?ref=Gen_vchap1-1    → Chat with initial context
```

---

## 6. Component Design

### 6.1 Chapter Renderer

The Chapter component handles:
1. **Article insertion** - Articles render BEFORE their associated verse
2. **Annotation deduplication** - Track shown annotation IDs
3. **Scroll restoration** - Jump to verse from URL hash
4. **Lazy annotation loading** - Expand details on demand

```svelte
<!-- lib/components/reader/Chapter.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import Verse from './Verse.svelte';
  import Article from './Article.svelte';

  let { passages, navigation } = $props();

  // Deduplication: track which annotations we've shown
  let shownAnnotations = new Set<string>();

  function getUniqueAnnotations(passage: Passage) {
    const unique = passage.annotations.study_notes.filter(
      note => !shownAnnotations.has(note.id)
    );
    unique.forEach(n => shownAnnotations.add(n.id));
    return unique;
  }
</script>

{#each passages as passage (passage.id)}
  {#if passage.annotations?.articles?.length}
    {#each passage.annotations.articles as article}
      <Article {article} />
    {/each}
  {/if}

  <Verse
    {passage}
    annotations={getUniqueAnnotations(passage)}
  />
{/each}
```

### 6.2 Verse with HTML Rendering

```svelte
<!-- lib/components/reader/Verse.svelte -->
<script lang="ts">
  let { passage, annotations } = $props();

  // The API returns text with intentional <i> and <b> markup
  // We render it as HTML but sanitize first
</script>

<div class="verse" id="v{passage.verse}">
  <span class="verse-num">{passage.verse}</span>
  <span class="verse-text">
    {@html sanitizeHtml(passage.text)}
  </span>

  {#if passage.annotation_markers.length}
    <span class="markers">
      {#each passage.annotation_markers as marker}
        <AnnotationMarker {marker} />
      {/each}
    </span>
  {/if}
</div>

<style>
  .verse {
    margin-bottom: var(--space-2);
    line-height: var(--line-height-relaxed);
  }

  .verse-num {
    font-size: var(--font-xs);
    color: var(--color-gold);
    vertical-align: super;
    margin-right: 0.25em;
  }

  /* Preserve poetry line breaks */
  .verse-text {
    white-space: pre-wrap;
  }
</style>
```

---

## 7. CSS Architecture

### 7.1 File Organization

```
src/
├── styles/
│   ├── tokens/
│   │   ├── _colors.css      # Color palette
│   │   ├── _typography.css  # Font stacks, sizes, line heights
│   │   ├── _spacing.css     # Spacing scale
│   │   └── _index.css       # Barrel import
│   │
│   ├── base/
│   │   ├── _reset.css       # Minimal reset
│   │   ├── _global.css      # html, body, root styles
│   │   └── _index.css
│   │
│   ├── utilities/
│   │   ├── _layout.css      # .desktop-only, .mobile-only, etc.
│   │   ├── _text.css        # .text-muted, .text-gold, etc.
│   │   └── _index.css
│   │
│   └── app.css              # Imports all above
│
├── lib/components/
│   └── ComponentName.svelte  # Component-scoped <style> only
```

**Principles:**
- **Tokens in CSS files, not inline** - All colors, spacing, fonts are CSS custom properties
- **Component styles are scoped** - Each `.svelte` file has `<style>` for its own styles
- **No inline styles** - Ever. Use utility classes or component styles
- **Easy to find and change** - Token file names match what they contain

### 7.2 Token Files

```css
/* src/styles/tokens/_colors.css */
:root {
  /* Byzantine Dark Theme */
  --color-bg-base: #12100f;
  --color-bg-surface: #1e1a18;
  --color-bg-elevated: #2a2422;

  --color-text-primary: #e8e0d5;
  --color-text-secondary: #a89f94;
  --color-text-muted: #6b6259;

  --color-gold: #c9a227;
  --color-gold-dim: #8a7019;
  --color-burgundy: #722f37;
  --color-burgundy-light: #934048;
  --color-navy: #1a2744;

  --color-accent: var(--color-gold);
  --color-accent-hover: var(--color-gold-dim);

  /* Semantic tokens */
  --color-study-note: var(--color-gold);
  --color-cross-ref: #5b8a72;
  --color-variant: #7a6b8a;
  --color-liturgical: var(--color-burgundy-light);

  /* Typography */
  --font-body: 'Spectral', Georgia, serif;
  --font-ui: 'Inter', system-ui, sans-serif;

  --font-base: clamp(16px, 4vw, 18px);
  --font-sm: 0.875rem;
  --font-xs: 0.75rem;
  --font-lg: 1.125rem;

  --line-height-tight: 1.3;
  --line-height-normal: 1.5;
  --line-height-relaxed: 1.75;

  /* Spacing */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-6: 1.5rem;
  --space-8: 2rem;

  /* Layout */
  --content-max-width: 42rem;
  --sidebar-width: 20rem;
  --bottom-nav-height: 4rem;

  /* Touch targets */
  --touch-min: 44px;
}

/* Typography base */
body {
  font-family: var(--font-body);
  font-size: var(--font-base);
  line-height: var(--line-height-normal);
  color: var(--color-text-primary);
  background: var(--color-bg-base);
  -webkit-font-smoothing: antialiased;
}

/* Reader text styling */
.reader-text :global(i) {
  font-style: italic;
  color: var(--color-text-secondary);
}

.reader-text :global(b) {
  font-weight: 600;
  color: var(--color-text-primary);
}
```

### 7.2 Color Palette Rationale

The color scheme draws from:
- **Deep burgundy (#722f37)** - Liturgical vestments, icon backgrounds
- **Byzantine gold (#c9a227)** - Halos, iconostasis gilding
- **Near-black (#12100f)** - Reading comfort, icon backgrounds
- **Navy (#1a2744)** - Secondary accent, Marian references

---

## 8. Mobile Patterns

### 8.1 Bottom Navigation

```svelte
<!-- lib/components/navigation/BottomBar.svelte -->
<nav class="bottom-bar">
  <button onclick={() => openBookPicker()}>
    <Icon name="book" />
    <span>Books</span>
  </button>

  <button onclick={() => goto('/chat')}>
    <Icon name="message" />
    <span>Chat</span>
  </button>

  <button onclick={() => openAnnotations()}>
    <Icon name="note" />
    <span>Notes</span>
  </button>
</nav>

<style>
  .bottom-bar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: var(--bottom-nav-height);
    background: var(--color-bg-elevated);
    border-top: 1px solid var(--color-bg-surface);
    display: flex;
    justify-content: space-around;
    align-items: center;
    padding-bottom: env(safe-area-inset-bottom);
  }

  button {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-1);
    min-width: var(--touch-min);
    min-height: var(--touch-min);
    color: var(--color-text-secondary);
  }
</style>
```

### 8.2 Annotation Sheet (Mobile)

On mobile, annotations appear in a bottom sheet rather than sidebar:

```svelte
<!-- lib/components/ui/Sheet.svelte -->
<script lang="ts">
  let { open = $bindable(false), children } = $props();
  let sheetEl: HTMLElement;
  let startY = 0;
  let currentY = 0;

  function handleTouchStart(e: TouchEvent) {
    startY = e.touches[0].clientY;
  }

  function handleTouchMove(e: TouchEvent) {
    currentY = e.touches[0].clientY;
    const delta = currentY - startY;
    if (delta > 0) {
      sheetEl.style.transform = `translateY(${delta}px)`;
    }
  }

  function handleTouchEnd() {
    const delta = currentY - startY;
    if (delta > 100) {
      open = false;
    }
    sheetEl.style.transform = '';
  }
</script>

{#if open}
  <div class="overlay" onclick={() => open = false}></div>
  <div
    class="sheet"
    bind:this={sheetEl}
    ontouchstart={handleTouchStart}
    ontouchmove={handleTouchMove}
    ontouchend={handleTouchEnd}
  >
    <div class="handle"></div>
    {@render children()}
  </div>
{/if}
```

### 8.3 Swipe Navigation

```typescript
// lib/utils/gestures.ts
export function createSwipeHandler(
  onSwipeLeft: () => void,
  onSwipeRight: () => void,
  threshold = 75
) {
  let startX = 0;
  let startY = 0;

  return {
    touchstart(e: TouchEvent) {
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
    },
    touchend(e: TouchEvent) {
      const deltaX = e.changedTouches[0].clientX - startX;
      const deltaY = e.changedTouches[0].clientY - startY;

      // Only horizontal swipes (not scrolling)
      if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > threshold) {
        if (deltaX > 0) onSwipeRight();
        else onSwipeLeft();
      }
    }
  };
}
```

---

## 9. Layout Architecture

### 9.1 Split View (Desktop)

Desktop uses a 3:2 split between reader and chat:

```
┌─────────────────────────────────────────────────────────┐
│  Header (breadcrumb, book picker)                       │
├────────────────────────────────┬────────────────────────┤
│                                │                        │
│         READER (60%)           │      CHAT (40%)        │
│                                │                        │
│   Genesis 1                    │  ┌────────────────┐   │
│                                │  │ Context: Gen 1 │   │
│   ¹In the beginning God made   │  └────────────────┘   │
│   heaven and earth...          │                        │
│                                │  Messages...           │
│                                │                        │
│                                │  ┌────────────────┐   │
│                                │  │ Type message   │   │
│                                │  └────────────────┘   │
├────────────────────────────────┴────────────────────────┤
│  (no footer on desktop)                                 │
└─────────────────────────────────────────────────────────┘
```

### 9.2 Mobile Layout

Mobile: full-screen reader with bottom nav. Chat slides up as a sheet:

```
┌─────────────────────┐     ┌─────────────────────┐
│ Genesis 1        ≡  │     │ Genesis 1        ≡  │
├─────────────────────┤     ├─────────────────────┤
│                     │     │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│
│ ¹In the beginning   │     │                     │
│ God made heaven...  │  →  │   CHAT SHEET        │
│                     │     │   (covers 85%)      │
│                     │     │                     │
│                     │     │                     │
├─────────────────────┤     │  ┌───────────────┐  │
│ [Books] [Chat] [☰]  │     │  │ Type message  │  │
└─────────────────────┘     └──┴───────────────┴──┘
```

### 9.3 Layout Implementation

```svelte
<!-- routes/+layout.svelte -->
<script lang="ts">
  import { page } from '$app/stores';
  import ChatPanel from '$lib/components/chat/ChatPanel.svelte';
  import MobileNav from '$lib/components/navigation/MobileNav.svelte';
  import { chatOpen } from '$lib/stores/ui.svelte';
</script>

<div class="app-layout">
  <header class="app-header">
    <slot name="header" />
  </header>

  <main class="app-main">
    <div class="reader-pane">
      <slot />
    </div>

    <aside class="chat-pane desktop-only">
      <ChatPanel />
    </aside>
  </main>

  <MobileNav class="mobile-only" />

  {#if chatOpen}
    <div class="chat-sheet mobile-only">
      <ChatPanel />
    </div>
  {/if}
</div>

<style>
  .app-layout {
    display: grid;
    grid-template-rows: auto 1fr auto;
    min-height: 100dvh;
  }

  .app-main {
    display: grid;
    grid-template-columns: 3fr 2fr;
    overflow: hidden;
  }

  @media (max-width: 768px) {
    .app-main {
      grid-template-columns: 1fr;
    }
  }
</style>
```

### 9.4 Chat Context Passing

Chat syncs from reader position automatically:

```typescript
// Message to LLM server
{
  message: "What does St. Basil say about this passage?",
  context: {
    book: "genesis",
    chapter: 1,
    verse: 1  // Optional
  }
}
```

The LLM server constructs `Gen_vchap1-1` and calls the API itself.

---

## 10. Future Extensibility

### 10.1 Content Source Abstraction

When patristic texts arrive, the same components work:

```typescript
interface ContentSource {
  type: 'bible' | 'patristic' | 'homily';
  id: string;
  name: string;
}

interface ContentUnit {
  id: string;
  source: ContentSource;
  position: { section: number; paragraph?: number };
  text: string;
  annotations: Annotation[];
}
```

### 10.2 Route Structure Ready for Extension

```
/read/bible/genesis/1        → Bible
/read/patristic/philokalia/1 → Patristic (future)
/read/homily/pascha-2024     → Homilies (future)
```

Current `/read/[book]/[chapter]` becomes `/read/bible/[book]/[chapter]` with an alias.

---

## 11. Implementation Order

**Phase 1: Core Reader**
1. Project scaffolding (SvelteKit, TypeScript, CSS)
2. API client with full types
3. Basic reader route + Chapter component
4. Book/chapter navigation
5. Theming foundation

**Phase 2: Annotations**
1. Annotation panel component
2. Marker interaction
3. Cross-reference modal
4. Deduplication logic

**Phase 3: Mobile Polish**
1. Bottom navigation
2. Sheet component
3. Swipe gestures
4. PWA setup

**Phase 4: Chat**
1. Chat UI components
2. Context passing
3. LLM server integration
4. Reference linking in responses

---

## 12. Dependencies

```json
{
  "devDependencies": {
    "@sveltejs/kit": "^2.0.0",
    "svelte": "^5.0.0",
    "typescript": "^5.0.0",
    "vite": "^5.0.0"
  },
  "dependencies": {
    "dompurify": "^3.0.0"  // HTML sanitization
  }
}
```

Intentionally minimal. No UI framework - custom Byzantine components.

---

*In the name of the Father, and of the Son, and of the Holy Spirit. Amen.*
