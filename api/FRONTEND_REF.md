# Chat Agent Reference Annotations

The chat agent (Michael) returns inline annotations in its responses that should be parsed and rendered as clickable links. This document specifies the annotation formats and their resolution.

---

## Annotation Format

All annotations follow the pattern: `[TYPE[value]]`

The agent returns plain text with embedded annotations like:

```
In [SCRIPTURE[genesis:1:1]], God created heaven and earth. The study note
[study[f1]] explains that the Hebrew word *Elohim* is plural, pointing to
the Trinity. See also [SCRIPTURE[john:1:1-3]] for the New Testament parallel.
```

---

## Reference Types

### 1. Scripture References

**Pattern:** `[SCRIPTURE[book_id:chapter:verse]]`

| Variant | Example | Meaning |
|---------|---------|---------|
| Single verse | `[SCRIPTURE[genesis:1:1]]` | Genesis 1:1 |
| Verse range | `[SCRIPTURE[matthew:5:3-12]]` | Matthew 5:3-12 |
| Whole chapter | `[SCRIPTURE[psalms:22]]` | Psalm 22 |

**Resolution:**

1. Parse `book_id`, `chapter`, and optional `verse`/`verse_range`
2. Look up book to get abbreviation: `GET /books/{book_id}`
3. Construct passage ID: `{abbreviation}_vchap{chapter}-{verse}`
4. Link to passage: `GET /passages/{passage_id}?expand=annotations`

**Example resolution:**
```
[SCRIPTURE[genesis:1:1]]
  → GET /books/genesis → abbreviation: "Gen"
  → passage_id: "Gen_vchap1-1"
  → Link: /passages/Gen_vchap1-1?expand=annotations
```

**For verse ranges**, either:
- Link to the chapter with verse highlighting: `/books/{book_id}/chapters/{chapter}/passages?verse_start={start}&verse_end={end}`
- Or fetch each passage individually

**Display text:** Render the human-readable form (e.g., "Genesis 1:1", "Matthew 5:3-12")

---

### 2. Study Notes

**Pattern:** `[study[id]]`

**Example:** `[study[f1]]`, `[study[f2534]]`

**Resolution:**
```
GET /annotations/{id}
```

**UI behavior:** Open annotation panel/modal showing the study note content.

---

### 3. Liturgical Notes

**Pattern:** `[liturgical[id]]`

**Example:** `[liturgical[fx1]]`, `[liturgical[fx234]]`

**Resolution:**
```
GET /annotations/{id}
```

**UI behavior:** Open annotation panel showing liturgical usage.

---

### 4. Textual Variants

**Pattern:** `[variant[id]]`

**Example:** `[variant[fvar1]]`, `[variant[fvar456]]`

**Resolution:**
```
GET /annotations/{id}
```

**UI behavior:** Open annotation panel showing NU-Text/M-Text variant information.

---

### 5. Citation Cross-References

**Pattern:** `[citation[id]]`

**Example:** `[citation[fcit1]]`, `[citation[fcit89]]`

**Resolution:**
```
GET /annotations/{id}
```

The annotation's `scripture_refs` field contains the target passage(s).

**UI behavior:** Navigate to the referenced passage or show a preview modal.

---

### 6. Topical Articles

**Pattern:** `[article[slug]]`

**Example:** `[article[creation]]`, `[article[theosis]]`, `[article[trinity]]`

**Resolution:**
```
GET /annotations/{slug}
```

**UI behavior:** Open article panel/modal or navigate to article view.

---

### 7. Book References

**Pattern:** `[book[book_id]]`

**Example:** `[book[genesis]]`, `[book[sirach]]`

**Resolution:**
```
GET /books/{book_id}
```

**UI behavior:** Navigate to book overview or first chapter.

---

## Parsing Implementation

### Regex Pattern

```javascript
const ANNOTATION_REGEX = /\[(SCRIPTURE|study|liturgical|variant|citation|article|book)\[([^\]]+)\]\]/g;
```

### Parser Example

```javascript
function parseAnnotations(text) {
  const annotations = [];
  let match;

  while ((match = ANNOTATION_REGEX.exec(text)) !== null) {
    const [fullMatch, type, value] = match;

    annotations.push({
      fullMatch,
      type: type.toLowerCase(),
      value,
      start: match.index,
      end: match.index + fullMatch.length,
    });
  }

  return annotations;
}

function parseScriptureRef(value) {
  // value: "genesis:1:1" or "matthew:5:3-12" or "psalms:22"
  const parts = value.split(':');
  const bookId = parts[0];
  const chapter = parseInt(parts[1], 10);

  if (parts.length === 2) {
    // Chapter only
    return { bookId, chapter, verseStart: null, verseEnd: null };
  }

  const versePart = parts[2];
  if (versePart.includes('-')) {
    const [start, end] = versePart.split('-').map(v => parseInt(v, 10));
    return { bookId, chapter, verseStart: start, verseEnd: end };
  }

  const verse = parseInt(versePart, 10);
  return { bookId, chapter, verseStart: verse, verseEnd: verse };
}
```

### Rendering Example

```javascript
function renderWithAnnotations(text) {
  const annotations = parseAnnotations(text);

  // Sort by position descending to replace from end to start
  annotations.sort((a, b) => b.start - a.start);

  let result = text;

  for (const ann of annotations) {
    const link = createLink(ann);
    result = result.slice(0, ann.start) + link + result.slice(ann.end);
  }

  return result;
}

function createLink(annotation) {
  switch (annotation.type) {
    case 'scripture': {
      const ref = parseScriptureRef(annotation.value);
      const displayText = formatScriptureDisplay(ref);
      return `<a href="#" data-scripture="${annotation.value}" class="scripture-ref">${displayText}</a>`;
    }
    case 'study':
    case 'liturgical':
    case 'variant':
    case 'citation':
    case 'article':
      return `<a href="#" data-annotation="${annotation.value}" data-type="${annotation.type}" class="annotation-ref">${annotation.value}</a>`;
    case 'book':
      return `<a href="#" data-book="${annotation.value}" class="book-ref">${formatBookName(annotation.value)}</a>`;
    default:
      return annotation.fullMatch;
  }
}
```

---

## Book ID Reference

Common book IDs (lowercase, no spaces):

| Book | ID | Book | ID |
|------|-----|------|-----|
| Genesis | `genesis` | Matthew | `matthew` |
| Exodus | `exodus` | Mark | `mark` |
| Psalms | `psalms` | Luke | `luke` |
| Isaiah | `isaiah` | John | `john` |
| Wisdom of Solomon | `wisdomofsolomon` | Romans | `romans` |
| Sirach | `sirach` | 1 Corinthians | `1corinthians` |
| 1 Samuel | `1samuel` | Revelation | `revelation` |

For the full list: `GET /books`

---

## Notes

1. **LXX Psalm numbering**: The OSB uses Septuagint numbering. Psalm 22 in this system is "The Lord is my shepherd" (Protestant Psalm 23).

2. **Caching**: Book abbreviation lookups can be cached client-side since they don't change.

3. **Error handling**: If a referenced passage or annotation doesn't exist, degrade gracefully to plain text.

4. **Accessibility**: Ensure links have appropriate ARIA labels describing the reference type.
