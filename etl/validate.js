#!/usr/bin/env mongosh
// ============================================================
// ORTHODOX STUDY BIBLE DATA VALIDATION
// St. Nestor the Chronicler, pray for us
// ============================================================
//
// Usage: mongosh ortho_dox validate.js
//
// This script performs comprehensive validation of the extracted
// OSB data to ensure integrity before use as a source of truth.
//
// Checks performed:
//   1. Null/empty field validation
//   2. Sequential integrity (missing verses/chapters, duplicates)
//   3. Referential integrity (all foreign keys resolve)
//   4. Bidirectional consistency (passage<->annotation links)
//   5. Text quality (HTML leakage, markers, length anomalies)
//   6. Patristic citation validation
//   7. Cross-database consistency (ortho_dox vs ortho_raw)
//   8. Book structure validation
//   9. Statistical analysis
//
// ============================================================

print("=".repeat(70));
print("ORTHODOX STUDY BIBLE DATA VALIDATION");
print("=".repeat(70));

let issues = [];
let warnings = [];

function logIssue(category, msg, samples) {
    issues.push({category, msg, samples: samples || []});
}

function logWarning(category, msg, samples) {
    warnings.push({category, msg, samples: samples || []});
}

// ============================================================
// 1. NULL/EMPTY FIELD VALIDATION
// ============================================================
print("\n[1] CHECKING NULL/EMPTY FIELDS...");

// Passages with empty text
let emptyTextPassages = db.passages.find({
    $or: [
        {text: null},
        {text: ""},
        {text: {$exists: false}}
    ]
}).toArray();
if (emptyTextPassages.length > 0) {
    logIssue("NULL_FIELDS", emptyTextPassages.length + " passages with null/empty text",
        emptyTextPassages.slice(0, 5).map(p => p._id));
}

// Passages with empty book_id
let emptyBookId = db.passages.find({
    $or: [{book_id: null}, {book_id: ""}, {book_id: {$exists: false}}]
}).toArray();
if (emptyBookId.length > 0) {
    logIssue("NULL_FIELDS", emptyBookId.length + " passages with null/empty book_id",
        emptyBookId.slice(0, 5).map(p => p._id));
}

// Annotations with empty text
let emptyAnnText = db.annotations.find({
    $or: [{text: null}, {text: ""}, {text: {$exists: false}}]
}).toArray();
if (emptyAnnText.length > 0) {
    logIssue("NULL_FIELDS", emptyAnnText.length + " annotations with null/empty text",
        emptyAnnText.slice(0, 5).map(a => a._id));
}

// Annotations with invalid type
let invalidType = db.annotations.find({
    type: {$nin: ["study", "liturgical", "variant", "citation", "article"]}
}).toArray();
if (invalidType.length > 0) {
    logIssue("NULL_FIELDS", invalidType.length + " annotations with invalid type",
        invalidType.slice(0, 5).map(a => a._id + ":" + a.type));
}

// Books with empty abbreviations
let emptyAbbrev = db.books.find({
    $or: [
        {abbreviations: {$size: 0}},
        {abbreviations: null},
        {abbreviations: {$exists: false}}
    ]
}).toArray();
if (emptyAbbrev.length > 0) {
    logIssue("NULL_FIELDS", emptyAbbrev.length + " books with no abbreviations",
        emptyAbbrev.map(b => b._id));
}

print("  Checked: passages.text, passages.book_id, annotations.text, annotations.type, books.abbreviations");

// ============================================================
// 2. SEQUENTIAL INTEGRITY - Missing verses/chapters
// ============================================================
print("\n[2] CHECKING SEQUENTIAL INTEGRITY...");

let missingVerses = [];
let missingChapters = [];
let duplicateVerses = [];

let books = db.books.find({}).toArray();
for (let book of books) {
    let passages = db.passages.find({book_id: book._id}).sort({chapter: 1, verse: 1}).toArray();

    if (passages.length === 0) {
        logWarning("SEQUENCE", "Book '" + book._id + "' has no passages");
        continue;
    }

    // Group by chapter
    let chapters = {};
    for (let p of passages) {
        if (!chapters[p.chapter]) chapters[p.chapter] = [];
        chapters[p.chapter].push(p.verse);
    }

    // Check for chapter gaps
    let chapterNums = Object.keys(chapters).map(Number).sort((a,b) => a-b);
    for (let i = 1; i < chapterNums.length; i++) {
        let gap = chapterNums[i] - chapterNums[i-1];
        if (gap > 1) {
            for (let missing = chapterNums[i-1] + 1; missing < chapterNums[i]; missing++) {
                missingChapters.push(book._id + " ch" + missing);
            }
        }
    }

    // Check for verse gaps within each chapter
    for (let chap in chapters) {
        let verses = chapters[chap];
        verses.sort((a,b) => a-b);

        // Check for duplicates
        let seen = {};
        for (let v of verses) {
            if (seen[v]) {
                duplicateVerses.push(book._id + " " + chap + ":" + v);
            }
            seen[v] = true;
        }

        // Check for gaps (only flag if more than 1 verse in chapter)
        if (verses.length > 1) {
            for (let i = 1; i < verses.length; i++) {
                let gap = verses[i] - verses[i-1];
                if (gap > 1) {
                    for (let missing = verses[i-1] + 1; missing < verses[i]; missing++) {
                        missingVerses.push(book._id + " " + chap + ":" + missing);
                    }
                }
            }
        }
    }
}

if (missingChapters.length > 0) {
    logWarning("SEQUENCE", missingChapters.length + " potentially missing chapters",
        missingChapters.slice(0, 10));
}
if (missingVerses.length > 0) {
    logWarning("SEQUENCE", missingVerses.length + " potentially missing verses",
        missingVerses.slice(0, 15));
}
if (duplicateVerses.length > 0) {
    logIssue("SEQUENCE", duplicateVerses.length + " duplicate verse IDs",
        duplicateVerses.slice(0, 10));
}

// Check for verse 0 or chapter 0
let zeroVerse = db.passages.find({verse: 0}).toArray();
let zeroChapter = db.passages.find({chapter: 0}).toArray();
if (zeroVerse.length > 0) {
    logWarning("SEQUENCE", zeroVerse.length + " passages with verse=0",
        zeroVerse.slice(0, 5).map(p => p._id));
}
if (zeroChapter.length > 0) {
    logWarning("SEQUENCE", zeroChapter.length + " passages with chapter=0",
        zeroChapter.slice(0, 5).map(p => p._id));
}

print("  Checked: chapter gaps, verse gaps, duplicates, zero values");

// ============================================================
// 3. REFERENTIAL INTEGRITY
// ============================================================
print("\n[3] CHECKING REFERENTIAL INTEGRITY...");

// All passage.book_id should exist in books
let bookIds = {};
db.books.find({}).forEach(b => { bookIds[b._id] = true; });
let orphanedPassages = db.passages.find({}).toArray().filter(p => !bookIds[p.book_id]);
if (orphanedPassages.length > 0) {
    logIssue("REF_INTEGRITY", orphanedPassages.length + " passages with non-existent book_id",
        orphanedPassages.slice(0, 5).map(p => p._id + " -> " + p.book_id));
}

// All cross_ref_targets should exist as passages
let passageIds = {};
db.passages.find({}).forEach(p => { passageIds[p._id] = true; });
let brokenCrossRefs = [];
db.passages.find({cross_ref_targets: {$exists: true, $not: {$size: 0}}}).forEach(p => {
    for (let target of p.cross_ref_targets) {
        if (!passageIds[target]) {
            brokenCrossRefs.push(p._id + " -> " + target);
        }
    }
});
if (brokenCrossRefs.length > 0) {
    logIssue("REF_INTEGRITY", brokenCrossRefs.length + " broken cross-ref targets",
        brokenCrossRefs.slice(0, 10));
}

// All annotation.passage_ids should exist as passages
let brokenAnnRefs = [];
db.annotations.find({passage_ids: {$exists: true, $not: {$size: 0}}}).forEach(a => {
    for (let pid of a.passage_ids) {
        if (!passageIds[pid]) {
            brokenAnnRefs.push(a._id + " -> " + pid);
        }
    }
});
if (brokenAnnRefs.length > 0) {
    logIssue("REF_INTEGRITY", brokenAnnRefs.length + " annotations pointing to non-existent passages",
        brokenAnnRefs.slice(0, 10));
}

// Orphan annotations (no linked passages)
let orphanAnnotations = db.annotations.find({
    $or: [{passage_ids: {$size: 0}}, {passage_ids: null}, {passage_ids: {$exists: false}}]
}).toArray();
if (orphanAnnotations.length > 0) {
    logWarning("REF_INTEGRITY", orphanAnnotations.length + " orphan annotations (no linked passages)",
        orphanAnnotations.slice(0, 5).map(a => a._id + " - " + a.verse_display));
}

// All study_note_ids on passages should exist as annotations
let annotationIds = {};
db.annotations.find({}).forEach(a => { annotationIds[a._id] = true; });
let brokenStudyRefs = [];
db.passages.find({study_note_ids: {$exists: true, $not: {$size: 0}}}).forEach(p => {
    for (let sid of p.study_note_ids) {
        if (!annotationIds[sid]) {
            brokenStudyRefs.push(p._id + " -> " + sid);
        }
    }
});
if (brokenStudyRefs.length > 0) {
    logIssue("REF_INTEGRITY", brokenStudyRefs.length + " passages with non-existent study_note_ids",
        brokenStudyRefs.slice(0, 10));
}

// Same for liturgical_ids
let brokenLitRefs = [];
db.passages.find({liturgical_ids: {$exists: true, $not: {$size: 0}}}).forEach(p => {
    for (let lid of p.liturgical_ids) {
        if (!annotationIds[lid]) {
            brokenLitRefs.push(p._id + " -> " + lid);
        }
    }
});
if (brokenLitRefs.length > 0) {
    logIssue("REF_INTEGRITY", brokenLitRefs.length + " passages with non-existent liturgical_ids",
        brokenLitRefs.slice(0, 10));
}

print("  Checked: book_id refs, cross_ref targets, annotation refs, study/liturgical refs");

// ============================================================
// 4. BIDIRECTIONAL CONSISTENCY
// ============================================================
print("\n[4] CHECKING BIDIRECTIONAL CONSISTENCY...");

// If passage has study_note_id X, annotation X should have passage in passage_ids
let bidirectionalMismatches = [];
db.passages.find({study_note_ids: {$exists: true, $not: {$size: 0}}}).forEach(p => {
    for (let sid of p.study_note_ids) {
        let ann = db.annotations.findOne({_id: sid});
        if (ann && ann.passage_ids.indexOf(p._id) === -1) {
            bidirectionalMismatches.push("passage " + p._id + " has " + sid + ", but annotation lacks passage ref");
        }
    }
});

// And vice versa - check all annotation types
db.annotations.find({passage_ids: {$exists: true, $not: {$size: 0}}}).forEach(a => {
    for (let pid of a.passage_ids) {
        let p = db.passages.findOne({_id: pid});
        if (p) {
            let hasRef = (p.study_note_ids && p.study_note_ids.indexOf(a._id) !== -1) ||
                        (p.liturgical_ids && p.liturgical_ids.indexOf(a._id) !== -1) ||
                        (p.variant_ids && p.variant_ids.indexOf(a._id) !== -1) ||
                        (p.citation_ids && p.citation_ids.indexOf(a._id) !== -1) ||
                        (p.article_ids && p.article_ids.indexOf(a._id) !== -1);
            if (!hasRef) {
                bidirectionalMismatches.push("annotation " + a._id + " has " + pid + ", but passage lacks ref back");
            }
        }
    }
});

if (bidirectionalMismatches.length > 0) {
    logWarning("BIDIRECTIONAL", bidirectionalMismatches.length + " bidirectional mismatches",
        bidirectionalMismatches.slice(0, 10));
}

print("  Checked: passage<->annotation bidirectional refs");

// ============================================================
// 5. TEXT QUALITY CHECKS
// ============================================================
print("\n[5] CHECKING TEXT QUALITY...");

// Very short verses (< 5 chars)
let shortVerses = [];
db.passages.find({}).forEach(p => {
    if (p.text && p.text.trim().length < 5) {
        shortVerses.push(p._id + ': "' + p.text + '"');
    }
});
if (shortVerses.length > 0) {
    logWarning("TEXT_QUALITY", shortVerses.length + " very short verses (<5 chars)",
        shortVerses.slice(0, 10));
}

// Very long verses (> 2000 chars) - might include article content
let longVerses = [];
db.passages.find({}).forEach(p => {
    if (p.text && p.text.length > 2000) {
        longVerses.push(p._id + ": " + p.text.length + " chars");
    }
});
if (longVerses.length > 0) {
    logWarning("TEXT_QUALITY", longVerses.length + " very long verses (>2000 chars)",
        longVerses);
}

// Verses containing HTML tags (except <i> and <b> which are intentionally preserved)
// <i> = italics for OT quotes, psalm superscriptions, translator additions, theological terms
// <b> = bold for scripture quotations in study notes
let htmlInText = db.passages.find({
    text: {$regex: /<(?!\/?(i|b)>)[a-z]+[^>]*>/i}
}).toArray();
if (htmlInText.length > 0) {
    logIssue("TEXT_QUALITY", htmlInText.length + " passages with unexpected HTML tags in text (not <i>/<b>)",
        htmlInText.slice(0, 5).map(p => p._id));
}

// Verses containing annotation markers (dagger, double-dagger, omega)
let markersInText = db.passages.find({
    text: {$regex: /[†‡ω]/}
}).toArray();
if (markersInText.length > 0) {
    logIssue("TEXT_QUALITY", markersInText.length + " passages with annotation markers in text",
        markersInText.slice(0, 5).map(p => p._id));
}

// Verses starting with numbers (verse number leaked into text)
let startsWithNum = db.passages.find({
    text: {$regex: /^\d+\s/}
}).toArray();
if (startsWithNum.length > 0) {
    logWarning("TEXT_QUALITY", startsWithNum.length + " passages starting with numbers",
        startsWithNum.slice(0, 5).map(p => p._id + ': "' + p.text.substring(0, 30) + '..."'));
}

// Whitespace-only text
let whitespaceOnly = [];
db.passages.find({}).forEach(p => {
    if (p.text && p.text.trim() === "") {
        whitespaceOnly.push(p._id);
    }
});
if (whitespaceOnly.length > 0) {
    logIssue("TEXT_QUALITY", whitespaceOnly.length + " passages with whitespace-only text",
        whitespaceOnly.slice(0, 5));
}

print("  Checked: short verses, long verses, HTML tags, markers, leading numbers, whitespace");

// ============================================================
// 6. PATRISTIC CITATION VALIDATION
// ============================================================
print("\n[6] CHECKING PATRISTIC CITATIONS...");

let sourceIds = {};
db.patristic_sources.find({}).forEach(s => { sourceIds[s._id] = true; });
let unknownCitations = [];
db.annotations.find({patristic_citations: {$exists: true, $not: {$size: 0}}}).forEach(a => {
    for (let cit of a.patristic_citations) {
        if (!sourceIds[cit]) {
            unknownCitations.push(a._id + ": " + cit);
        }
    }
});
if (unknownCitations.length > 0) {
    logWarning("PATRISTIC", unknownCitations.length + " citations to unknown patristic sources",
        unknownCitations.slice(0, 10));
}

print("  Checked: patristic citation references");

// ============================================================
// 7. CROSS-DATABASE CONSISTENCY (ortho_dox vs ortho_raw)
// ============================================================
print("\n[7] CHECKING CROSS-DATABASE CONSISTENCY...");

let rawDb = db.getSiblingDB("ortho_raw");

let rawPassageIds = {};
rawDb.passages.find({}).forEach(p => { rawPassageIds[p._id] = true; });
let doxPassageIds = {};
db.passages.find({}).forEach(p => { doxPassageIds[p._id] = true; });

// Passages in dox but not in raw
let doxOnlyPassages = [];
for (let id in doxPassageIds) {
    if (!rawPassageIds[id]) doxOnlyPassages.push(id);
}
if (doxOnlyPassages.length > 0) {
    logIssue("CROSS_DB", doxOnlyPassages.length + " passages in ortho_dox but not in ortho_raw",
        doxOnlyPassages.slice(0, 5));
}

// Passages in raw but not in dox
let rawOnlyPassages = [];
for (let id in rawPassageIds) {
    if (!doxPassageIds[id]) rawOnlyPassages.push(id);
}
if (rawOnlyPassages.length > 0) {
    logIssue("CROSS_DB", rawOnlyPassages.length + " passages in ortho_raw but not in ortho_dox",
        rawOnlyPassages.slice(0, 5));
}

// Same for annotations
let rawAnnIds = {};
rawDb.annotations.find({}).forEach(a => { rawAnnIds[a._id] = true; });
let doxAnnIds = {};
db.annotations.find({}).forEach(a => { doxAnnIds[a._id] = true; });

let doxOnlyAnns = [];
for (let id in doxAnnIds) {
    if (!rawAnnIds[id]) doxOnlyAnns.push(id);
}
if (doxOnlyAnns.length > 0) {
    logIssue("CROSS_DB", doxOnlyAnns.length + " annotations in ortho_dox but not in ortho_raw",
        doxOnlyAnns.slice(0, 5));
}

let rawOnlyAnns = [];
for (let id in rawAnnIds) {
    if (!doxAnnIds[id]) rawOnlyAnns.push(id);
}
if (rawOnlyAnns.length > 0) {
    logIssue("CROSS_DB", rawOnlyAnns.length + " annotations in ortho_raw but not in ortho_dox",
        rawOnlyAnns.slice(0, 5));
}

print("  Checked: ortho_dox <-> ortho_raw passage/annotation alignment");

// ============================================================
// 8. BOOK STRUCTURE VALIDATION
// ============================================================
print("\n[8] CHECKING BOOK STRUCTURE...");

// Books with no passages
let booksWithNoPassages = [];
for (let book of books) {
    let count = db.passages.countDocuments({book_id: book._id});
    if (count === 0) {
        booksWithNoPassages.push(book._id);
    }
}
if (booksWithNoPassages.length > 0) {
    logIssue("BOOK_STRUCT", booksWithNoPassages.length + " books with no passages",
        booksWithNoPassages);
}

// Check testament assignment
let otBooks = db.books.find({testament: "old"}).toArray();
let ntBooks = db.books.find({testament: "new"}).toArray();
print("  Old Testament books: " + otBooks.length);
print("  New Testament books: " + ntBooks.length);

print("  Checked: books with passages, testament assignment");

// ============================================================
// 9. ID FORMAT VALIDATION
// ============================================================
print("\n[9] CHECKING ID FORMAT INTEGRITY...");

// Passage IDs should match pattern: {Abbr}_vchap{Chapter}-{Verse}
let malformedPassageIds = db.passages.find({
    _id: {$not: /^[A-Za-z0-9]+_vchap\d+-\d+$/}
}).toArray();
if (malformedPassageIds.length > 0) {
    logIssue("ID_FORMAT", malformedPassageIds.length + " passages with malformed IDs",
        malformedPassageIds.slice(0, 5).map(p => p._id));
}

// Study annotation IDs should match: f{number}
let malformedStudyIds = db.annotations.find({
    type: "study",
    _id: {$not: /^f\d+$/}
}).toArray();
if (malformedStudyIds.length > 0) {
    logIssue("ID_FORMAT", malformedStudyIds.length + " study annotations with malformed IDs",
        malformedStudyIds.slice(0, 5).map(a => a._id));
}

// Liturgical annotation IDs should match: fx{number}
let malformedLiturgicalIds = db.annotations.find({
    type: "liturgical",
    _id: {$not: /^fx\d+$/}
}).toArray();
if (malformedLiturgicalIds.length > 0) {
    logIssue("ID_FORMAT", malformedLiturgicalIds.length + " liturgical annotations with malformed IDs",
        malformedLiturgicalIds.slice(0, 5).map(a => a._id));
}

// Book IDs should be lowercase, no special chars except allowed
let malformedBookIds = db.books.find({
    _id: {$not: /^[a-z0-9]+$/}
}).toArray();
if (malformedBookIds.length > 0) {
    logIssue("ID_FORMAT", malformedBookIds.length + " books with malformed IDs",
        malformedBookIds.map(b => b._id));
}

print("  Checked: passage ID format, annotation ID format, book ID format");

// ============================================================
// 10. ID-TO-FIELD CONSISTENCY
// ============================================================
print("\n[10] CHECKING ID-TO-FIELD CONSISTENCY...");

// Verify chapter/verse fields match what the ID says
let idFieldMismatches = [];
db.passages.find({}).forEach(p => {
    let match = p._id.match(/_vchap(\d+)-(\d+)$/);
    if (match) {
        let idChapter = parseInt(match[1]);
        let idVerse = parseInt(match[2]);
        if (p.chapter !== idChapter) {
            idFieldMismatches.push(p._id + ": ID says ch" + idChapter + ", field says ch" + p.chapter);
        }
        if (p.verse !== idVerse) {
            idFieldMismatches.push(p._id + ": ID says v" + idVerse + ", field says v" + p.verse);
        }
    }
});
if (idFieldMismatches.length > 0) {
    logIssue("ID_FIELD", idFieldMismatches.length + " passages where ID doesn't match chapter/verse fields",
        idFieldMismatches.slice(0, 10));
}

// Verify book abbreviation in ID matches book's abbreviations list
let abbrevMismatches = [];
let bookAbbrevMap = {};
db.books.find({}).forEach(b => {
    for (let abbr of (b.abbreviations || [])) {
        bookAbbrevMap[abbr] = b._id;
    }
});

db.passages.find({}).forEach(p => {
    let abbr = p._id.split('_')[0];
    let expectedBookId = bookAbbrevMap[abbr];
    if (expectedBookId && expectedBookId !== p.book_id) {
        abbrevMismatches.push(p._id + ": abbrev " + abbr + " -> " + expectedBookId + ", but book_id is " + p.book_id);
    }
    if (!expectedBookId) {
        abbrevMismatches.push(p._id + ": abbrev " + abbr + " not found in any book");
    }
});
if (abbrevMismatches.length > 0) {
    logIssue("ID_FIELD", abbrevMismatches.length + " passages with abbreviation/book_id mismatch",
        abbrevMismatches.slice(0, 10));
}

print("  Checked: chapter/verse field consistency, abbreviation mapping");

// ============================================================
// 11. CHARACTER/ENCODING INTEGRITY
// ============================================================
print("\n[11] CHECKING CHARACTER/ENCODING INTEGRITY...");

// Control characters (0x00-0x1F except tab, newline, carriage return)
let controlCharPassages = db.passages.find({
    text: {$regex: /[\x00-\x08\x0B\x0C\x0E-\x1F]/}
}).toArray();
if (controlCharPassages.length > 0) {
    logIssue("ENCODING", controlCharPassages.length + " passages with control characters",
        controlCharPassages.slice(0, 5).map(p => p._id));
}

let controlCharAnnotations = db.annotations.find({
    text: {$regex: /[\x00-\x08\x0B\x0C\x0E-\x1F]/}
}).toArray();
if (controlCharAnnotations.length > 0) {
    logIssue("ENCODING", controlCharAnnotations.length + " annotations with control characters",
        controlCharAnnotations.slice(0, 5).map(a => a._id));
}

// Zero-width characters (invisible corruption)
// Check client-side since MongoDB regex has issues with Unicode escapes
let zeroWidthPassages = [];
let zeroWidthPattern = /[\u200B\u200C\u200D\u200E\u200F\u2060\uFEFF]/;
db.passages.find({}).forEach(p => {
    if (p.text && zeroWidthPattern.test(p.text)) {
        zeroWidthPassages.push(p._id);
    }
});
if (zeroWidthPassages.length > 0) {
    logWarning("ENCODING", zeroWidthPassages.length + " passages with zero-width characters",
        zeroWidthPassages.slice(0, 5));
}

// Unencoded HTML entities (parsing missed decoding)
let htmlEntityPassages = db.passages.find({
    text: {$regex: /&(amp|lt|gt|nbsp|quot|apos|#\d+|#x[0-9a-fA-F]+);/}
}).toArray();
if (htmlEntityPassages.length > 0) {
    logIssue("ENCODING", htmlEntityPassages.length + " passages with unencoded HTML entities",
        htmlEntityPassages.slice(0, 5).map(p => p._id + ': "' + p.text.match(/&[^;]+;/)[0] + '"'));
}

let htmlEntityAnnotations = db.annotations.find({
    text: {$regex: /&(amp|lt|gt|nbsp|quot|apos|#\d+|#x[0-9a-fA-F]+);/}
}).toArray();
if (htmlEntityAnnotations.length > 0) {
    logIssue("ENCODING", htmlEntityAnnotations.length + " annotations with unencoded HTML entities",
        htmlEntityAnnotations.slice(0, 5).map(a => a._id));
}

// Replacement character (encoding failure marker)
// Check client-side for Unicode replacement character
let replacementCharPassages = [];
db.passages.find({}).forEach(p => {
    if (p.text && p.text.includes('\uFFFD')) {
        replacementCharPassages.push(p._id);
    }
});
if (replacementCharPassages.length > 0) {
    logIssue("ENCODING", replacementCharPassages.length + " passages with replacement character (encoding failure)",
        replacementCharPassages.slice(0, 5));
}

print("  Checked: control characters, zero-width characters, HTML entities, replacement chars");

// ============================================================
// 12. DUPLICATE TEXT DETECTION
// ============================================================
print("\n[12] CHECKING FOR DUPLICATE TEXT...");

// Find passages with identical text (minimum 30 chars to avoid short common phrases)
let textToIds = {};
db.passages.find({}).forEach(p => {
    if (p.text && p.text.length >= 30) {
        let key = p.text.trim();
        if (!textToIds[key]) textToIds[key] = [];
        textToIds[key].push(p._id);
    }
});

let duplicateTexts = [];
for (let text in textToIds) {
    if (textToIds[text].length > 1) {
        duplicateTexts.push({
            ids: textToIds[text],
            preview: text.substring(0, 50) + "..."
        });
    }
}

if (duplicateTexts.length > 0) {
    logWarning("DUPLICATE", duplicateTexts.length + " sets of passages with identical text",
        duplicateTexts.slice(0, 5).map(d => d.ids.join(", ") + ': "' + d.preview + '"'));
}

// Check for annotations with identical text
let annTextToIds = {};
db.annotations.find({}).forEach(a => {
    if (a.text && a.text.length >= 50) {
        let key = a.text.trim();
        if (!annTextToIds[key]) annTextToIds[key] = [];
        annTextToIds[key].push(a._id);
    }
});

let duplicateAnnTexts = [];
for (let text in annTextToIds) {
    if (annTextToIds[text].length > 1) {
        duplicateAnnTexts.push(annTextToIds[text]);
    }
}

if (duplicateAnnTexts.length > 0) {
    logWarning("DUPLICATE", duplicateAnnTexts.length + " sets of annotations with identical text",
        duplicateAnnTexts.slice(0, 5).map(ids => ids.join(", ")));
}

print("  Checked: duplicate passage text, duplicate annotation text");

// ============================================================
// 13. TRUNCATION DETECTION
// ============================================================
print("\n[13] CHECKING FOR TEXT TRUNCATION...");

// Text with unbalanced quotes (potential truncation)
let unbalancedQuotes = [];
db.passages.find({}).forEach(p => {
    if (p.text) {
        // Count curly/smart quote types
        let leftDouble = (p.text.match(/\u201C/g) || []).length;   // "
        let rightDouble = (p.text.match(/\u201D/g) || []).length;  // "
        let leftSingle = (p.text.match(/\u2018/g) || []).length;   // '
        let rightSingle = (p.text.match(/\u2019/g) || []).length;  // '

        // Smart double quotes should be balanced
        if (leftDouble !== rightDouble && (leftDouble + rightDouble) > 0) {
            unbalancedQuotes.push(p._id + ': curly " mismatch (' + leftDouble + ' open, ' + rightDouble + ' close)');
        }
    }
});

if (unbalancedQuotes.length > 0) {
    logWarning("TRUNCATION", unbalancedQuotes.length + " passages with unbalanced smart quotes",
        unbalancedQuotes.slice(0, 10));
}

// Text with unbalanced parentheses
let unbalancedParens = [];
db.passages.find({}).forEach(p => {
    if (p.text) {
        let opens = (p.text.match(/\(/g) || []).length;
        let closes = (p.text.match(/\)/g) || []).length;
        if (opens !== closes) {
            unbalancedParens.push(p._id + ': (' + opens + ' open, ' + closes + ' close)');
        }
    }
});

if (unbalancedParens.length > 0) {
    logWarning("TRUNCATION", unbalancedParens.length + " passages with unbalanced parentheses",
        unbalancedParens.slice(0, 10));
}

// Text starting with lowercase (possible continuation error) - excluding poetry
// Also strip leading <i>/<b> tags before checking (they're preserved for styling)
let lowercaseStart = [];
db.passages.find({format: "prose"}).forEach(p => {
    if (p.text) {
        let textToCheck = p.text.replace(/^<[ib]>/, '');
        if (/^[a-z]/.test(textToCheck)) {
            lowercaseStart.push(p._id + ': "' + p.text.substring(0, 30) + '..."');
        }
    }
});

if (lowercaseStart.length > 0) {
    logWarning("TRUNCATION", lowercaseStart.length + " prose passages starting with lowercase",
        lowercaseStart.slice(0, 10));
}

print("  Checked: unbalanced quotes, unbalanced parentheses, lowercase starts");

// ============================================================
// 14. EXPECTED CHAPTER COUNTS
// ============================================================
print("\n[14] CHECKING EXPECTED CHAPTER COUNTS...");

// Expected chapter counts for biblical books (LXX/Orthodox numbering)
// These are the CORRECT counts for the Orthodox Study Bible
const EXPECTED_CHAPTERS = {
    "genesis": 50, "exodus": 40, "leviticus": 27, "numbers": 36,
    "deuteronomy": 34, "joshua": 24, "judges": 21, "ruth": 4,
    "1samuel": 31, "2samuel": 24, "1kings": 22, "2kings": 25,
    "1chronicles": 29, "2chronicles": 37, "1esdras": 9, "2esdras": 23,
    "esther": 10, "judith": 16, "tobit": 14, "1maccabees": 16,
    "2maccabees": 15, "3maccabees": 7, "4maccabees": 18,
    "psalms": 151, "job": 42, "proverbs": 31, "ecclesiastes": 12,
    "songofsongs": 8, "wisdomofsolomon": 19, "sirach": 51,
    "isaiah": 66, "jeremiah": 52, "lamentations": 5, "baruch": 5,
    "letterofjeremiah": 1, "ezekiel": 48, "dan": 12,
    "sus": 1, "bel": 1, "hosea": 14, "amos": 9, "micah": 7,
    "joel": 4, "obadiah": 1, "jonah": 4, "nahum": 3, "habakkuk": 3,
    "zephaniah": 3, "haggai": 2, "zechariah": 14, "malachi": 3,
    "matthew": 28, "mark": 16, "luke": 24, "john": 21,
    "acts": 28, "romans": 16, "1corinthians": 16, "2corinthians": 13,
    "galatians": 6, "ephesians": 6, "philippians": 4, "colossians": 4,
    "1thessalonians": 5, "2thessalonians": 3, "1timothy": 6, "2timothy": 4,
    "titus": 3, "philemon": 1, "hebrews": 13, "james": 5,
    "1peter": 5, "2peter": 3, "1john": 5, "2john": 1, "3john": 1,
    "jude": 1, "revelation": 22
};

let chapterMismatches = [];
let checkedBooks = 0;

for (let bookId in EXPECTED_CHAPTERS) {
    let expected = EXPECTED_CHAPTERS[bookId];
    let chapters = db.passages.distinct("chapter", {book_id: bookId});
    let actual = chapters.length;

    if (actual === 0) {
        // Book might not exist or have different ID - skip
        continue;
    }

    checkedBooks++;
    let maxChapter = Math.max(...chapters);

    if (actual !== expected) {
        chapterMismatches.push(bookId + ": expected " + expected + " chapters, found " + actual + " (max: " + maxChapter + ")");
    }
}

if (chapterMismatches.length > 0) {
    logWarning("CHAPTERS", chapterMismatches.length + " books with unexpected chapter counts",
        chapterMismatches.slice(0, 15));
}

print("  Checked " + checkedBooks + " books against expected chapter counts");

// ============================================================
// 15. ANNOTATION VERSE_DISPLAY VALIDATION
// ============================================================
print("\n[15] CHECKING ANNOTATION VERSE_DISPLAY CONSISTENCY...");

// Annotation text should start with something resembling verse_display
let verseDisplayMismatches = [];
db.annotations.find({verse_display: {$ne: "", $exists: true}}).forEach(a => {
    if (a.text && a.verse_display) {
        // Normalize verse_display for matching (e.g., "1:1" or "1:1-3")
        let vd = a.verse_display.trim();
        // Strip <b> tags from text start for comparison (we preserve <b> for styling)
        let textForMatch = a.text.replace(/^<b>/, '').replace(/<\/b>/, '');
        // The text should start with the verse reference
        // Allow for some flexibility (space, colon variations, different dash types)
        // Escape regex special chars, then make dashes/colons flexible
        let escaped = vd.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        let normalized = escaped.replace(/[-\u2013\u2014]/g, '[-\\u2013\\u2014]').replace(/:/g, '[:]?');
        let pattern = new RegExp('^\\s*' + normalized);

        if (!pattern.test(textForMatch) && a.text.length > 10) {
            let textStart = a.text.substring(0, 30).replace(/\n/g, ' ');
            verseDisplayMismatches.push(a._id + ': verse_display="' + vd + '", text starts="' + textStart + '..."');
        }
    }
});

if (verseDisplayMismatches.length > 0) {
    logWarning("ANNOTATION", verseDisplayMismatches.length + " annotations where text doesn't start with verse_display",
        verseDisplayMismatches.slice(0, 10));
}

// Check for empty verse_display on annotations with passages
let emptyVerseDisplay = db.annotations.find({
    passage_ids: {$exists: true, $not: {$size: 0}},
    $or: [{verse_display: ""}, {verse_display: null}, {verse_display: {$exists: false}}]
}).toArray();

if (emptyVerseDisplay.length > 0) {
    logWarning("ANNOTATION", emptyVerseDisplay.length + " annotations with passages but empty verse_display",
        emptyVerseDisplay.slice(0, 5).map(a => a._id));
}

print("  Checked: verse_display consistency, empty verse_display");

// ============================================================
// 16. POETRY/PROSE FORMAT SANITY
// ============================================================
print("\n[16] CHECKING POETRY/PROSE FORMAT DISTRIBUTION...");

// Books that should be predominantly poetry
const POETRY_BOOKS = ["psalms", "proverbs", "songofsongs", "lamentations", "sirach"];
// Books that should be predominantly prose
const PROSE_BOOKS = ["genesis", "exodus", "matthew", "mark", "luke", "john", "acts"];

let formatAnomalies = [];

for (let bookId of POETRY_BOOKS) {
    let total = db.passages.countDocuments({book_id: bookId});
    let poetry = db.passages.countDocuments({book_id: bookId, format: "poetry"});
    if (total > 0) {
        let ratio = poetry / total;
        if (ratio < 0.3) {
            formatAnomalies.push(bookId + ": expected poetry-heavy, but only " + Math.round(ratio * 100) + "% poetry");
        }
    }
}

for (let bookId of PROSE_BOOKS) {
    let total = db.passages.countDocuments({book_id: bookId});
    let prose = db.passages.countDocuments({book_id: bookId, format: "prose"});
    if (total > 0) {
        let ratio = prose / total;
        if (ratio < 0.5) {
            formatAnomalies.push(bookId + ": expected prose-heavy, but only " + Math.round(ratio * 100) + "% prose");
        }
    }
}

if (formatAnomalies.length > 0) {
    logWarning("FORMAT", formatAnomalies.length + " books with unexpected poetry/prose distribution",
        formatAnomalies);
}

// Check for unknown format values
let unknownFormats = db.passages.find({
    format: {$nin: ["prose", "poetry"]}
}).toArray();
if (unknownFormats.length > 0) {
    logIssue("FORMAT", unknownFormats.length + " passages with invalid format value",
        unknownFormats.slice(0, 5).map(p => p._id + ": " + p.format));
}

print("  Checked: poetry/prose distribution, valid format values");

// ============================================================
// 17. DANIEL/SUSANNA/BEL SEPARATION
// ============================================================
print("\n[17] CHECKING DANIEL/SUSANNA/BEL BOOK SEPARATION...");

// These should be separate books with expected verse ranges
let susCount = db.passages.countDocuments({book_id: "sus"});
let danCount = db.passages.countDocuments({book_id: "dan"});
let belCount = db.passages.countDocuments({book_id: "bel"});

print("  Susanna: " + susCount + " verses (expected ~64)");
print("  Daniel: " + danCount + " verses (expected ~357)");
print("  Bel and Dragon: " + belCount + " verses (expected ~42)");

// Check reasonable ranges
if (susCount > 0 && (susCount < 50 || susCount > 80)) {
    logWarning("DANIEL_SPLIT", "Susanna verse count (" + susCount + ") outside expected range 50-80");
}
if (danCount > 0 && (danCount < 300 || danCount > 450)) {
    logWarning("DANIEL_SPLIT", "Daniel verse count (" + danCount + ") outside expected range 300-450");
}
if (belCount > 0 && (belCount < 30 || belCount > 60)) {
    logWarning("DANIEL_SPLIT", "Bel verse count (" + belCount + ") outside expected range 30-60");
}

// Check that no passages have "daniel" as book_id (should be "dan")
let oldDanielRefs = db.passages.countDocuments({book_id: "daniel"});
if (oldDanielRefs > 0) {
    logIssue("DANIEL_SPLIT", oldDanielRefs + " passages still using 'daniel' instead of 'dan' as book_id");
}

// ============================================================
// 18. CROSS-REFERENCE SELF-REFERENCE CHECK
// ============================================================
print("\n[18] CHECKING FOR SELF-REFERENTIAL CROSS-REFERENCES...");

let selfRefs = [];
db.passages.find({cross_ref_targets: {$exists: true, $not: {$size: 0}}}).forEach(p => {
    if (p.cross_ref_targets.includes(p._id)) {
        selfRefs.push(p._id);
    }
});

if (selfRefs.length > 0) {
    logWarning("CROSS_REF", selfRefs.length + " passages with self-referential cross-references",
        selfRefs.slice(0, 10));
}

// Check cross-references to same chapter (might be intentional but worth reviewing)
let sameChapterRefs = [];
db.passages.find({cross_ref_targets: {$exists: true, $not: {$size: 0}}}).forEach(p => {
    let sourceMatch = p._id.match(/^([A-Za-z]+)_vchap(\d+)/);
    if (sourceMatch) {
        let sourceBook = sourceMatch[1];
        let sourceChapter = sourceMatch[2];
        for (let target of p.cross_ref_targets) {
            let targetMatch = target.match(/^([A-Za-z]+)_vchap(\d+)/);
            if (targetMatch && targetMatch[1] === sourceBook && targetMatch[2] === sourceChapter) {
                sameChapterRefs.push(p._id + " -> " + target);
            }
        }
    }
});

if (sameChapterRefs.length > 0) {
    // This is informational, not necessarily an issue
    print("  Found " + sameChapterRefs.length + " cross-references within same chapter (may be intentional)");
}

print("  Checked: self-references, same-chapter references");

// ============================================================
// 19. ABBREVIATION COMPLETENESS
// ============================================================
print("\n[19] CHECKING ABBREVIATION COMPLETENESS...");

// Every unique abbreviation in passage IDs should map to exactly one book
let passageAbbrevs = new Set();
db.passages.find({}).forEach(p => {
    let abbr = p._id.split('_')[0];
    passageAbbrevs.add(abbr);
});

let bookAbbrevs = new Set();
db.books.find({}).forEach(b => {
    for (let abbr of (b.abbreviations || [])) {
        bookAbbrevs.add(abbr);
    }
});

// Abbreviations in passages but not in books
let unmappedAbbrevs = [];
passageAbbrevs.forEach(abbr => {
    if (!bookAbbrevs.has(abbr)) {
        unmappedAbbrevs.push(abbr);
    }
});

if (unmappedAbbrevs.length > 0) {
    logIssue("ABBREV", unmappedAbbrevs.length + " abbreviations in passages not mapped to any book",
        unmappedAbbrevs);
}

// Abbreviations in books but not in any passage
let unusedAbbrevs = [];
bookAbbrevs.forEach(abbr => {
    if (!passageAbbrevs.has(abbr)) {
        unusedAbbrevs.push(abbr);
    }
});

if (unusedAbbrevs.length > 0) {
    logWarning("ABBREV", unusedAbbrevs.length + " abbreviations in books with no passages",
        unusedAbbrevs);
}

print("  Checked: unmapped abbreviations, unused abbreviations");

// ============================================================
// 20. ANNOTATION DENSITY OUTLIERS
// ============================================================
print("\n[20] CHECKING ANNOTATION DENSITY OUTLIERS...");

let densityByBook = db.passages.aggregate([
    {$project: {
        book_id: 1,
        hasAnnotation: {$gt: [{$size: {$ifNull: ["$study_note_ids", []]}}, 0]}
    }},
    {$group: {
        _id: "$book_id",
        total: {$sum: 1},
        withAnnotations: {$sum: {$cond: ["$hasAnnotation", 1, 0]}}
    }},
    {$project: {
        book_id: "$_id",
        total: 1,
        withAnnotations: 1,
        density: {$cond: [{$eq: ["$total", 0]}, 0, {$divide: ["$withAnnotations", "$total"]}]}
    }},
    {$sort: {density: 1}}
]).toArray();

// Calculate mean density
let totalDensity = densityByBook.reduce((sum, b) => sum + b.density, 0);
let meanDensity = totalDensity / densityByBook.length;

// Find outliers (books with 0% annotation when mean is >5%)
let zeroAnnotationBooks = [];
if (meanDensity > 0.05) {
    for (let book of densityByBook) {
        if (book.density === 0 && book.total > 20) {
            zeroAnnotationBooks.push(book._id + " (" + book.total + " verses, 0 annotations)");
        }
    }
}

if (zeroAnnotationBooks.length > 0) {
    logWarning("DENSITY", zeroAnnotationBooks.length + " books with zero annotations (mean density: " + Math.round(meanDensity * 100) + "%)",
        zeroAnnotationBooks);
}

print("  Mean annotation density: " + Math.round(meanDensity * 100) + "%");
print("  Lowest: " + densityByBook[0]._id + " (" + Math.round(densityByBook[0].density * 100) + "%)");
print("  Highest: " + densityByBook[densityByBook.length-1]._id + " (" + Math.round(densityByBook[densityByBook.length-1].density * 100) + "%)");

// ============================================================
// 21. STATISTICAL ANALYSIS
// ============================================================
print("\n[21] STATISTICAL ANALYSIS...");

// Verses per book distribution
let versesPerBook = db.passages.aggregate([
    {$group: {_id: "$book_id", count: {$sum: 1}}},
    {$sort: {count: -1}}
]).toArray();

let totalVerses = versesPerBook.reduce((s, b) => s + b.count, 0);
let avgVersesPerBook = totalVerses / versesPerBook.length;
print("  Average verses per book: " + Math.round(avgVersesPerBook));
print("  Most verses: " + versesPerBook[0]._id + " (" + versesPerBook[0].count + ")");
print("  Fewest verses: " + versesPerBook[versesPerBook.length-1]._id + " (" + versesPerBook[versesPerBook.length-1].count + ")");

// Books with unusually few verses (< 20)
let tinyBooks = versesPerBook.filter(b => b.count < 20);
if (tinyBooks.length > 0) {
    logWarning("STATS", tinyBooks.length + " books with <20 verses",
        tinyBooks.map(b => b._id + ": " + b.count));
}

// Annotation coverage
let passagesWithStudyNotes = db.passages.countDocuments({
    study_note_ids: {$exists: true, $not: {$size: 0}}
});
let totalPassagesCount = db.passages.countDocuments({});
let coverage = Math.round(100 * passagesWithStudyNotes / totalPassagesCount);
print("  Passages with study notes: " + passagesWithStudyNotes + "/" + totalPassagesCount + " (" + coverage + "%)");

// Annotation counts by type
let studyCount = db.annotations.countDocuments({type: "study"});
let liturgicalCount = db.annotations.countDocuments({type: "liturgical"});
let articleCount = db.annotations.countDocuments({type: "article"});
print("  Study annotations: " + studyCount);
print("  Liturgical annotations: " + liturgicalCount);
print("  Article annotations: " + articleCount);

// ============================================================
// SUMMARY
// ============================================================
print("\n" + "=".repeat(70));
print("VALIDATION SUMMARY");
print("=".repeat(70));

print("\nISSUES (require attention): " + issues.length);
for (let issue of issues) {
    print("  [" + issue.category + "] " + issue.msg);
    if (issue.samples.length > 0) {
        for (let s of issue.samples) {
            print("    - " + s);
        }
    }
}

print("\nWARNINGS (review recommended): " + warnings.length);
for (let warn of warnings) {
    print("  [" + warn.category + "] " + warn.msg);
    if (warn.samples.length > 0) {
        for (let i = 0; i < Math.min(5, warn.samples.length); i++) {
            print("    - " + warn.samples[i]);
        }
        if (warn.samples.length > 5) {
            print("    - ... and " + (warn.samples.length - 5) + " more");
        }
    }
}

print("\n" + "=".repeat(70));
if (issues.length === 0) {
    print("+ NO CRITICAL ISSUES FOUND");
} else {
    print("X " + issues.length + " CRITICAL ISSUES REQUIRE ATTENTION");
}
print("=".repeat(70));
