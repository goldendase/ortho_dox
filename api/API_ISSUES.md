# API Issues & Technical Debt

Tracking known issues, limitations, and planned improvements.

---

## Fixed

### #3 - N+1 Query Problem for Cross-Refs (FIXED)
**Problem**: In `get_chapter_passages` and `get_passages_by_ids`, cross-ref resolution was inside the loop, causing N queries for N passages with cross-refs.

**Fix**: Batch all cross-ref targets first, resolve once.

### #4 - No Chapter Navigation (FIXED)
**Problem**: `ChapterPassagesResponse` lacked prev/next chapter links. Reader at Genesis 50 couldn't know to go to Exodus 1.

**Fix**: Added `prev_chapter` and `next_chapter` to response.

### #8 - No Cross-Book Navigation (FIXED)
**Problem**: `NavigationLinks.next` was `null` at end of book. Continuous reading required manual book-order lookup.

**Fix**: Navigation now crosses book boundaries using canonical order.

### #7 - Scripture Refs in Annotations Are Opaque (FIXED)
**Problem**: `AnnotationEmbed.scripture_refs` contained IDs like `"P2et_vchap2-6"`. Reader couldn't display "2 Peter 2:6" without parsing.

**Fix**: Changed `scripture_refs` from `list[str]` to `list[ScriptureRefDisplay]` where each item has:
- `id`: The passage ID (for navigation)
- `display`: Human-readable string like "2 Peter 2:6"

---

## Open Issues

### #1 - Cross-Reference Targets Opaque in Minimal Mode
**Status**: Won't fix (for now)
**Severity**: Medium

`PassageMinimal.cross_ref_targets` returns opaque IDs. Reader can't display "Isaiah 7:14" without `expand=full`.

**Rationale**: `PassageMinimal` likely won't be used much - readers will use `expand=annotations` for display.

### #2 - Annotation Markers Missing from Minimal Mode
**Status**: Won't fix (for now)
**Severity**: Low

Annotation markers (position data for †) only in `PassageWithAnnotations`, not `PassageMinimal`.

**Rationale**: Lazy-load pattern unlikely given small annotation payloads.

### #5 - Article Placement Non-Obvious
**Status**: Open - needs documentation
**Severity**: Medium

Articles in `article_ids` and `annotations.articles` should render **before** the verse they're linked to, not after. This matches how they appear in the source EPUB (articles precede the following verse).

**Workaround**: Reader must know to render articles before verse text.

**Potential fix**: Add `placement: "before" | "after"` to annotation type metadata.

### #6 - Format Field Unreliable for Poetry
**Status**: Open - documentation issue
**Severity**: Low

`format: "poetry"` reflects HTML element structure, not literary genre. Psalms shows only 2% "poetry" because most verses use `<sup>` inside `<p>` rather than `<ol>` structures.

**Workaround**: Check for `\n` characters in text to detect poetic line breaks.

**Note**: This is a data quirk from the ETL, not an API issue.

### #9 - Shared Annotations Show Repeatedly
**Status**: Open - future enhancement
**Severity**: Low

Annotation `f1` covers verses 1:1-1:5. When loading a chapter, all 5 verses list `f1` in their `study_note_ids`. Reader might display the same note 5 times.

**Potential fixes**:
1. Add `anchor_verse` to annotations indicating where it should primarily display
2. Add `is_anchor: bool` to embedded annotations
3. Leave to reader to deduplicate (track "already shown" IDs)

---

## Not Planned

### Search Functionality
Full-text search not in current scope. Would require:
- Text index on passages.text
- Handling of LXX Psalm numbering in queries
- Possibly Elasticsearch for advanced features

### Reading Progress / Bookmarks
User-specific features not in scope for this API.
