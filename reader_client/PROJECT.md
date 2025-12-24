# Orthodox Reader Client

A SvelteKit-based reader for the Orthodox Study Bible API. Built for ROCOR parish members with a Byzantine dark theme.

## Quick Start

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # Production build
npm run check    # TypeScript validation
```

Expects the API at `http://localhost:8000`. Override with `VITE_API_URL` environment variable.

---

## What We Built

### Core Features

| Feature | Status | Notes |
|---------|--------|-------|
| Chapter reading | ✅ | SSR, verse rendering with HTML markup |
| Book/chapter navigation | ✅ | Three-level picker (Testament → Book → Chapter) |
| Annotation markers | ✅ | Clickable † § ‡ markers by type |
| Unified side panel | ✅ | Tabbed: Notes + Chat in single panel |
| Cross-ref previews | ✅ | Click ref → preview in side panel without navigating |
| Favorites | ✅ | Passages (hover) + study notes, localStorage persistence |
| 3:2 desktop split | ✅ | Reader (60%) / Side Panel (40%) |
| Mobile layout | ✅ | Full-height reader, side panel as sheet |
| Chat UI | ✅ | Context badge, message history, placeholder responses |
| Reading position persistence | ✅ | localStorage, survives refresh |
| Navigation history | ✅ | Back button through cross-ref chains |
| Independent scroll regions | ✅ | Reader, side panel, chat messages all scroll separately |
| Byzantine theming | ✅ | Dark, burgundy/gold palette |

### Not Yet Implemented

| Feature | Priority | Notes |
|---------|----------|-------|
| LLM server integration | High | Chat sends placeholder; needs WebSocket/SSE |
| Swipe navigation | Medium | Touch gesture for chapter prev/next |
| Search | Medium | Full-text and reference search |
| Reading progress | Low | Visual indicator of position in chapter |
| Offline/PWA | Low | Service worker, cache API responses |
| Patristic content routes | Future | `/read/patristic/[source]/[section]` |

---

## Architecture Decisions

### Why SvelteKit?

1. **SSR for shareability** - `/read/genesis/1` renders immediately, good for sharing references
2. **File-based routing** - Clean URL structure maps directly to file structure
3. **Svelte 5 runes** - Cleaner reactivity than stores, better TypeScript inference
4. **Small bundle** - No virtual DOM overhead; reader is mostly static content

### Why No UI Framework (Tailwind, shadcn, etc.)?

The Byzantine aesthetic requires custom components. A utility framework would fight the design language more than help. We use:

- **CSS custom properties** for all tokens (colors, spacing, typography)
- **Scoped component styles** in each `.svelte` file
- **Utility classes** only for layout helpers (`.desktop-only`, `.mobile-only`)

This keeps the styling cohesive and easy to modify.

### State Management: Svelte 5 Runes

We use class-based stores with `$state` instead of traditional Svelte stores:

```typescript
// lib/stores/reader.svelte.ts
class ReaderStore {
  #position = $state<ReaderPosition | null>(null);

  navigate(pos: ReaderPosition) {
    this.#position = pos;
    // Persistence, history, etc.
  }
}

export const reader = new ReaderStore();
```

**Why this pattern:**
- Encapsulates related state and actions
- Private fields (`#position`) prevent external mutation
- Methods provide clear API surface
- Works with TypeScript better than `writable()`

### Unified Side Panel

The side panel uses a **discriminated union type** for content:

```typescript
// lib/stores/ui.svelte.ts
type SidePanelContent =
  | { type: 'study'; note: StudyNote }
  | { type: 'liturgical'; note: LiturgicalNote }
  | { type: 'variant'; note: VariantNote }
  | { type: 'article'; article: Article }
  | { type: 'passage'; passage: PassageWithAnnotations; title: string };

type SidePanelTab = 'notes' | 'chat';
```

**Content-pushing pattern:** Click handlers push content to the store rather than passing data through props. This decouples components from the display logic.

```typescript
// In Verse.svelte - when annotation marker clicked
ui.showStudyNote(note);  // Pushes to store, switches to notes tab
```

### CSS Architecture

```
src/styles/
├── tokens/           # Design tokens (edit these to change theme)
│   ├── _colors.css   # Byzantine palette
│   ├── _typography.css
│   └── _spacing.css
├── base/             # Reset, global styles
└── utilities/        # Helper classes
```

**Key principle:** Every visual value references a CSS variable. To change the gold accent across the entire app, edit one line in `_colors.css`.

### API Client Design

Typed wrappers around fetch with function overloads for expand modes:

```typescript
// Returns PassageWithAnnotations when expand='annotations'
const passage = await passages.get('Gen_vchap1-1', 'annotations');

// Returns PassageFull when expand='full'
const full = await passages.get('Gen_vchap1-1', 'full');
```

TypeScript knows the return type based on the expand parameter.

---

## Gotchas & Quirks

### API Data Quirks (from API_SPEC.md)

| Quirk | What to Do |
|-------|------------|
| **LXX Psalm numbering** | Psalm 22 = "The Lord is my shepherd". Don't "correct" to 23. |
| **HTML in text** | Verse text contains `<i>` and `<b>` tags. Render as HTML, not escaped. |
| **Articles before verses** | Check `article_ids`, render article content BEFORE the verse. |
| **Shared annotations** | One study note can span verses 1-5; all five list it. Deduplicate at render time. |
| **Poetry newlines** | Some verses have `\n` for poetic structure. Use `white-space: pre-wrap`. |
| **Opaque passage IDs** | Don't regex-parse `Gen_vchap1-1`. Use the `book_id`, `chapter`, `verse` fields. |

### Svelte 5 Gotchas

1. **`$state` for bind:this** - Element references from `bind:this` must be declared with `$state()`:
   ```typescript
   let inputEl = $state<HTMLTextAreaElement | undefined>(undefined);
   ```

2. **Snippets vs slots** - We use `{@render children()}` (Svelte 5 snippets), not `<slot>`. The `children` prop is typed as `Snippet`.

3. **`$effect` dependency loops** - If an effect reads and writes the same state, use `untrack()`:
   ```typescript
   $effect(() => {
     const { book, chapter } = $page.params;
     untrack(() => reader.navigate({ book, chapter }));
   });
   ```

4. **`$derived` for computed values** - Use `$derived()` not `const` for reactive computations:
   ```typescript
   const iconSize = $derived(size === 'sm' ? 14 : 18);
   ```

### CSS Gotchas

1. **Flexbox `min-height: 0`** - Critical for nested scrolling. Flex items default to `min-height: auto`, preventing children from shrinking below content size. This breaks `overflow-y: auto` on nested elements:
   ```css
   .flex-child-with-scroll-inside {
     flex: 1;
     min-height: 0;  /* REQUIRED for nested scroll to work */
     overflow: hidden;
   }
   ```

2. **Fixed viewport height** - Use `height: 100dvh` not `min-height: 100dvh` when you need to constrain content. `min-height` allows growth, breaking scroll containment.

3. **`dvh` units** - We use `100dvh` (dynamic viewport height) for mobile to account for browser chrome. Falls back gracefully.

4. **`env(safe-area-inset-bottom)`** - Used for iPhone home indicator safe area.

5. **CSS nesting not used** - For maximum compatibility, we don't use native CSS nesting. Each selector is flat.

### TypeScript Gotchas

1. **Patristic citations type** - Can be `string[]` or `PatristicCitation[]` depending on expand mode. Handle both cases.

2. **Navigation URLs** - The API returns URLs like `/books/genesis/chapters/2/passages`. We parse these to construct client routes (`/read/genesis/2`).

---

## File Reference

### Key Files

| File | Purpose |
|------|---------|
| `src/routes/+layout.svelte` | App shell with 3:2 split, fixed viewport |
| `src/routes/read/[book]/[chapter]/+page.svelte` | Reader page |
| `src/lib/stores/reader.svelte.ts` | Reading position, history |
| `src/lib/stores/ui.svelte.ts` | UI state (tabs, panels, content) |
| `src/lib/stores/chat.svelte.ts` | Chat messages, streaming state |
| `src/lib/stores/favorites.svelte.ts` | Favorites with localStorage |
| `src/lib/components/SidePanel.svelte` | Unified tabbed panel (Notes + Chat) |
| `src/lib/api/types.ts` | All TypeScript interfaces |
| `src/styles/tokens/_colors.css` | Color palette |
| `src/styles/tokens/_typography.css` | Font sizes (reduced ~10% from original) |

### Component Hierarchy

```
+layout.svelte (height: 100dvh, grid)
├── Header
│   └── BookPicker (in Sheet)
├── app-main (grid: 3fr 2fr)
│   ├── reader-pane (overflow-y: auto)
│   │   └── read/[book]/[chapter]/+page.svelte
│   │       ├── Chapter
│   │       │   ├── Article (before verse if present)
│   │       │   └── Verse
│   │       │       ├── AnnotationMarker
│   │       │       └── FavoriteButton (on hover)
│   │       └── ChapterNav
│   └── sidebar-pane (desktop only)
│       └── SidePanel
│           ├── Tab Bar (Notes | Chat)
│           ├── Notes Tab
│           │   ├── panel-header (title + favorite)
│           │   └── panel-content (scrollable)
│           └── Chat Tab
│               ├── context-badge
│               ├── messages (scrollable)
│               └── input-form
└── Sheet (mobile side panel)
    └── SidePanel
```

### Removed Components

These were consolidated into `SidePanel.svelte`:
- `MobileNav.svelte` - Bottom navigation removed entirely
- `ChatPanel.svelte` - Now a tab in SidePanel
- `AnnotationPanel.svelte` - Now the Notes tab
- `ReferencePanel.svelte` - Merged into Notes tab
- `StudyNoteView.svelte` - Inline in SidePanel

---

## Extending for Future Content

The architecture anticipates patristic commentaries, homilies, and other content. The abstraction:

```
ContentSource → ContentUnit → Annotation
     ↓              ↓             ↓
   Bible        Chapter       Study Note
  Homilies      Section       Citation
  Patristics    Passage       Cross-ref
```

When new content types arrive:

1. Add routes: `/read/patristic/[source]/[section]`
2. Create loader that calls appropriate API endpoints
3. Reuse existing components (Chapter, Verse, SidePanel work with any content matching the shape)

The current `/read/[book]/[chapter]` could become `/read/bible/[book]/[chapter]` with a redirect alias.

---

## Chat Integration Notes

The chat feature is UI-complete but not connected to an LLM server. Current behavior:

1. User types message
2. `chat.send()` captures current reader position as context
3. Placeholder response is shown after 500ms

To integrate with actual LLM server:

```typescript
// lib/stores/chat.svelte.ts - send() method

async send(content: string): Promise<void> {
  const context = this.currentContext; // { book, chapter, verse? }

  // Send to your LLM server
  const response = await fetch('/api/chat', {
    method: 'POST',
    body: JSON.stringify({ message: content, context })
  });

  // Handle streaming response (SSE or WebSocket)
  // Update messages as chunks arrive
}
```

The LLM server should use the `/context/{passage_id}` endpoint to fetch full passage data - don't send the payload from the client.

---

## Favorites System

Favorites are stored in localStorage with two types:

```typescript
interface FavoritePassage {
  id: string;           // "genesis-1-5" format
  book: string;
  bookName: string;
  chapter: number;
  verse: number;
  preview: string;      // First ~100 chars of verse text
  addedAt: number;
}

interface FavoriteNote {
  id: string;           // Annotation ID
  type: 'study' | 'liturgical' | 'variant';
  verseDisplay: string; // "Genesis 1:1"
  preview: string;      // First ~100 chars
  addedAt: number;
}
```

**Usage:**
- Passage favorites appear on verse hover
- Note favorites appear in side panel header when viewing a study note
- Both stored in `localStorage` under `favorites-passages` and `favorites-notes` keys

---

## Development Notes

### Adding a New Annotation Type

1. Add type to `AnnotationType` in `lib/api/types.ts`
2. Add marker symbol to `AnnotationMarker.svelte`
3. Add color variable to `_colors.css` (`--color-annotation-newtype`)
4. Add content type to `SidePanelContent` union in `ui.svelte.ts`
5. Add rendering case to `SidePanel.svelte` Notes tab

### Changing the Color Theme

Edit `src/styles/tokens/_colors.css`. Key variables:

```css
--color-bg-base: #0d0b0a;        /* Page background */
--color-gold: #c9a227;           /* Primary accent */
--color-burgundy: #722f37;       /* Secondary accent */
--color-text-primary: #ece5db;   /* Body text */
```

All components reference these variables.

### Testing with Mock Data

The API client expects a running server. For offline development, you could:

1. Create `src/lib/api/mock.ts` with static responses
2. Conditionally import mock vs real client based on env var
3. Or use MSW (Mock Service Worker) for request interception

---

## Known Issues

1. **Cross-ref ID parsing** - Cross-reference click handler parses passage IDs with regex. This is fragile; the API recommends using fields not parsing IDs. Currently works but could break with edge cases.

2. **No error boundaries** - API errors will currently crash the page. Add `+error.svelte` files for graceful error handling.

3. **Chat not connected** - Returns placeholder responses. Needs LLM server integration.

---

*Glory to God for all things.*
