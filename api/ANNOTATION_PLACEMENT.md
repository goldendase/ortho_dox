# Annotation Placement Guide

## The Problem

When rendering passages with `expand=annotations`, study notes for later verses may appear in the response for earlier verses. This is by design, but requires frontend logic to place annotations correctly.

## Why This Happens

In the Orthodox Study Bible, study notes often cover a **range** of verses. For example, the Prologue of John (1:1-5) has four study notes that all relate to this theological unit. The data model links **all notes to all verses in the range** so that:

1. A reader on any verse can access all relevant commentary
2. Cross-verse theological connections are preserved

However, this means the `study_note_ids` array tells you which notes are **relevant** to a verse, not where they should be **displayed**.

## Example: John 1:1-5

### API Response (truncated)

```
GET /books/john/chapters/1/passages?expand=annotations
```

```json
{
  "passages": [
    {
      "id": "John_vchap1-1",
      "verse": 1,
      "text": "In the beginning was the Word...",
      "study_note_ids": ["f4706", "f4707", "f4708", "f4709"],
      "annotations": {
        "study_notes": [
          {"id": "f4706", "verse_display": "1:1", "text": "..."},
          {"id": "f4707", "verse_display": "1:3", "text": "..."},
          {"id": "f4708", "verse_display": "1:4", "text": "..."},
          {"id": "f4709", "verse_display": "1:5", "text": "..."}
        ]
      }
    },
    {
      "id": "John_vchap1-2",
      "verse": 2,
      "text": "He was in the beginning with God.",
      "study_note_ids": ["f4706", "f4707", "f4708", "f4709"],
      "annotations": {
        "study_notes": [
          {"id": "f4706", "verse_display": "1:1", "text": "..."},
          {"id": "f4707", "verse_display": "1:3", "text": "..."},
          {"id": "f4708", "verse_display": "1:4", "text": "..."},
          {"id": "f4709", "verse_display": "1:5", "text": "..."}
        ]
      }
    }
  ]
}
```

Notice:
- Verse 1 contains notes with `verse_display` of "1:1", "1:3", "1:4", "1:5"
- Verse 2 contains the same four notes
- All five verses (1-5) will contain all four notes

## How to Determine Placement

Use the `verse_display` field to determine where each annotation should be rendered.

| Field | Purpose |
|-------|---------|
| `study_note_ids` | Which notes are **relevant** to this verse (for cross-reference, search, etc.) |
| `verse_display` | Which verse the note should be **displayed** on |

### Placement Logic

For each passage, filter annotations where `verse_display` matches the current verse:

| Current Verse | Show annotations where `verse_display` equals |
|---------------|---------------------------------------------|
| 1:1 | "1:1" |
| 1:2 | "1:2" |
| 1:3 | "1:3" |
| ... | ... |

### Verse Display Format

The `verse_display` field uses these formats:

| Format | Example | Meaning |
|--------|---------|---------|
| `chapter:verse` | "1:3" | Single verse |
| `chapter:verse-verse` | "1:9-11" | Verse range (display on first verse of range) |
| `chapter:verseLetter` | "1:5a" | Sub-verse reference (display on that verse) |

For range formats like "1:9-11", display the annotation on the **first verse** of the range (verse 9).

## Summary

1. `study_note_ids` = relevance (which notes relate to this verse)
2. `verse_display` = placement (where to render the note)
3. Filter annotations by matching `verse_display` to current `chapter:verse`
