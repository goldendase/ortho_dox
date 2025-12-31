/**
 * Chat Annotation Parser
 *
 * Parses inline annotations from chat agent responses.
 * Format: [TYPE[value]]
 *
 * Supported types:
 * - SCRIPTURE: [SCRIPTURE[genesis:1:5]] or [SCRIPTURE[matthew:5:3-12]]
 * - study: [study[f1]]
 * - liturgical: [liturgical[fx1]]
 * - variant: [variant[fvar1]]
 * - citation: [citation[fcit1]]
 * - article: [article[creation]]
 * - book: [book[genesis]]
 */

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export type ChatAnnotationType =
	| 'scripture'
	| 'study'
	| 'liturgical'
	| 'variant'
	| 'citation'
	| 'article'
	| 'book'
	// Library reference types
	| 'lib-work'
	| 'lib-node'
	| 'lib-footnote';

export interface ScriptureRef {
	bookId: string;
	chapter: number;
	verseStart: number | null;
	verseEnd: number | null;
}

export interface LibraryRef {
	/** For lib-work: the work_id. For lib-node/lib-footnote: extracted from node_id */
	workId: string;
	/** For lib-node and lib-footnote */
	nodeId?: string;
	/** For lib-footnote only */
	componentId?: string;
}

export interface ChatAnnotation {
	type: ChatAnnotationType;
	value: string;
	fullMatch: string;
	start: number;
	end: number;
	/** Parsed scripture reference (only for type='scripture') */
	scriptureRef?: ScriptureRef;
	/** Parsed library reference (only for lib-work, lib-node, lib-footnote) */
	libraryRef?: LibraryRef;
}

/** A segment of parsed message content */
export type MessageSegment =
	| { type: 'text'; content: string }
	| { type: 'annotation'; annotation: ChatAnnotation };

// ─────────────────────────────────────────────────────────────────────────────
// Parser
// ─────────────────────────────────────────────────────────────────────────────

// Note: The trailing \]? makes the second closing bracket optional to handle
// edge cases where annotations may be formatted with single bracket (e.g., [SCRIPTURE[2maccabees:12:42-45]])
// Library types use hyphenated names: lib-work, lib-node, lib-footnote
const ANNOTATION_REGEX =
	/\[(SCRIPTURE|study|liturgical|variant|citation|article|book|lib-work|lib-node|lib-footnote)\[([^\]]+)\]\]?/g;

// Label prefixes that the API may include before annotations (e.g., "[study note][study[f1]]")
// These should be stripped out as they're redundant with our display text
const LABEL_PREFIX_REGEX = /\[(study note|liturgical note|variant note|textual variant|citation|article)\]\s*/gi;

/**
 * Strip label prefixes from text (e.g., "[study note]" before "[study[f1]]")
 */
export function stripLabelPrefixes(text: string): string {
	return text.replace(LABEL_PREFIX_REGEX, '');
}

/**
 * Parse all annotations from a chat message
 */
export function parseAnnotations(text: string): ChatAnnotation[] {
	// First strip any label prefixes
	const cleanedText = stripLabelPrefixes(text);

	const annotations: ChatAnnotation[] = [];
	let match;

	// Reset regex lastIndex for fresh search
	ANNOTATION_REGEX.lastIndex = 0;

	while ((match = ANNOTATION_REGEX.exec(cleanedText)) !== null) {
		const [fullMatch, type, value] = match;
		const annotationType = type.toLowerCase() as ChatAnnotationType;

		const annotation: ChatAnnotation = {
			type: annotationType,
			value,
			fullMatch,
			start: match.index,
			end: match.index + fullMatch.length
		};

		// Parse scripture references
		if (annotationType === 'scripture') {
			annotation.scriptureRef = parseScriptureRef(value);
		}

		// Parse library references
		if (annotationType === 'lib-work' || annotationType === 'lib-node' || annotationType === 'lib-footnote') {
			annotation.libraryRef = parseLibraryRef(annotationType, value);
		}

		annotations.push(annotation);
	}

	return annotations;
}

/**
 * Parse a library reference value.
 * - lib-work: "way-of-a-pilgrim" → { workId: "way-of-a-pilgrim" }
 * - lib-node: "work_id:node_id" → { workId, nodeId }
 * - lib-footnote: "work_id:node_id:component_id" → { workId, nodeId, componentId }
 */
export function parseLibraryRef(type: ChatAnnotationType, value: string): LibraryRef {
	if (type === 'lib-work') {
		return { workId: value };
	}

	const parts = value.split(':');

	if (type === 'lib-node' && parts.length >= 2) {
		// Format: work_id:node_id
		return { workId: parts[0], nodeId: parts[1] };
	}

	if (type === 'lib-footnote' && parts.length >= 3) {
		// Format: work_id:node_id:component_id
		return { workId: parts[0], nodeId: parts[1], componentId: parts[2] };
	}

	// Fallback for malformed refs
	return { workId: value };
}

/**
 * Parse a scripture reference value like "genesis:1:5" or "matthew:5:3-12"
 */
export function parseScriptureRef(value: string): ScriptureRef {
	const parts = value.split(':');
	const bookId = parts[0];
	const chapter = parseInt(parts[1], 10);

	if (parts.length === 2) {
		// Chapter only: "psalms:22"
		return { bookId, chapter, verseStart: null, verseEnd: null };
	}

	const versePart = parts[2];
	if (versePart.includes('-')) {
		// Verse range: "matthew:5:3-12"
		const [start, end] = versePart.split('-').map((v) => parseInt(v, 10));
		return { bookId, chapter, verseStart: start, verseEnd: end };
	}

	// Single verse: "genesis:1:5"
	const verse = parseInt(versePart, 10);
	return { bookId, chapter, verseStart: verse, verseEnd: verse };
}

/**
 * Parse message into segments of text and annotations
 */
export function parseMessageSegments(text: string): MessageSegment[] {
	// First strip label prefixes so indices align correctly
	const cleanedText = stripLabelPrefixes(text);
	const annotations = parseAnnotations(cleanedText);

	if (annotations.length === 0) {
		return [{ type: 'text', content: cleanedText }];
	}

	const segments: MessageSegment[] = [];
	let lastIndex = 0;

	for (const annotation of annotations) {
		// Add text before this annotation
		if (annotation.start > lastIndex) {
			segments.push({
				type: 'text',
				content: cleanedText.slice(lastIndex, annotation.start)
			});
		}

		// Add the annotation
		segments.push({ type: 'annotation', annotation });

		lastIndex = annotation.end;
	}

	// Add remaining text after last annotation
	if (lastIndex < cleanedText.length) {
		segments.push({
			type: 'text',
			content: cleanedText.slice(lastIndex)
		});
	}

	return segments;
}

// ─────────────────────────────────────────────────────────────────────────────
// Display Helpers
// ─────────────────────────────────────────────────────────────────────────────

/** Book ID to display name mapping (common books) */
const BOOK_NAMES: Record<string, string> = {
	genesis: 'Genesis',
	exodus: 'Exodus',
	leviticus: 'Leviticus',
	numbers: 'Numbers',
	deuteronomy: 'Deuteronomy',
	joshua: 'Joshua',
	judges: 'Judges',
	ruth: 'Ruth',
	'1samuel': '1 Samuel',
	'2samuel': '2 Samuel',
	'1kings': '1 Kings',
	'2kings': '2 Kings',
	'1chronicles': '1 Chronicles',
	'2chronicles': '2 Chronicles',
	ezra: 'Ezra',
	nehemiah: 'Nehemiah',
	esther: 'Esther',
	job: 'Job',
	psalms: 'Psalms',
	proverbs: 'Proverbs',
	ecclesiastes: 'Ecclesiastes',
	songofsolomon: 'Song of Solomon',
	isaiah: 'Isaiah',
	jeremiah: 'Jeremiah',
	lamentations: 'Lamentations',
	ezekiel: 'Ezekiel',
	daniel: 'Daniel',
	hosea: 'Hosea',
	joel: 'Joel',
	amos: 'Amos',
	obadiah: 'Obadiah',
	jonah: 'Jonah',
	micah: 'Micah',
	nahum: 'Nahum',
	habakkuk: 'Habakkuk',
	zephaniah: 'Zephaniah',
	haggai: 'Haggai',
	zechariah: 'Zechariah',
	malachi: 'Malachi',
	matthew: 'Matthew',
	mark: 'Mark',
	luke: 'Luke',
	john: 'John',
	acts: 'Acts',
	romans: 'Romans',
	'1corinthians': '1 Corinthians',
	'2corinthians': '2 Corinthians',
	galatians: 'Galatians',
	ephesians: 'Ephesians',
	philippians: 'Philippians',
	colossians: 'Colossians',
	'1thessalonians': '1 Thessalonians',
	'2thessalonians': '2 Thessalonians',
	'1timothy': '1 Timothy',
	'2timothy': '2 Timothy',
	titus: 'Titus',
	philemon: 'Philemon',
	hebrews: 'Hebrews',
	james: 'James',
	'1peter': '1 Peter',
	'2peter': '2 Peter',
	'1john': '1 John',
	'2john': '2 John',
	'3john': '3 John',
	jude: 'Jude',
	revelation: 'Revelation',
	// Deuterocanonical
	tobit: 'Tobit',
	judith: 'Judith',
	wisdomofsolomon: 'Wisdom of Solomon',
	sirach: 'Sirach',
	baruch: 'Baruch',
	'1maccabees': '1 Maccabees',
	'2maccabees': '2 Maccabees',
	'3maccabees': '3 Maccabees',
	'4maccabees': '4 Maccabees',
	'1esdras': '1 Esdras',
	'2esdras': '2 Esdras',
	prayerofmanasseh: 'Prayer of Manasseh'
};

/**
 * Get display name for a book ID
 */
export function getBookDisplayName(bookId: string): string {
	return BOOK_NAMES[bookId.toLowerCase()] ?? bookId;
}

/**
 * Format a scripture reference for display
 * e.g., "Genesis 1:5" or "Matthew 5:3-12" or "Psalm 22"
 */
export function formatScriptureDisplay(ref: ScriptureRef): string {
	const bookName = getBookDisplayName(ref.bookId);

	if (ref.verseStart === null) {
		// Chapter only
		return `${bookName} ${ref.chapter}`;
	}

	if (ref.verseStart === ref.verseEnd) {
		// Single verse
		return `${bookName} ${ref.chapter}:${ref.verseStart}`;
	}

	// Verse range
	return `${bookName} ${ref.chapter}:${ref.verseStart}-${ref.verseEnd}`;
}

/**
 * Get display text for annotation links
 */
export function getAnnotationDisplayText(annotation: ChatAnnotation): string {
	switch (annotation.type) {
		case 'scripture':
			return annotation.scriptureRef
				? formatScriptureDisplay(annotation.scriptureRef)
				: annotation.value;
		case 'study':
			return '[study note]';
		case 'liturgical':
			return '[liturgical note]';
		case 'variant':
			return '[variant]';
		case 'citation':
			return '[citation]';
		case 'article':
			return '[article]';
		case 'book':
			return getBookDisplayName(annotation.value);
		// Library reference types
		case 'lib-work':
			return formatLibraryWorkDisplay(annotation.value);
		case 'lib-node':
			return formatLibraryNodeDisplay(annotation.value);
		case 'lib-footnote':
			return formatLibraryFootnoteDisplay(annotation.value);
		default:
			return annotation.value;
	}
}

/**
 * Format a library work ID for display.
 * Converts slugs like "way-of-a-pilgrim" to "Way of a Pilgrim"
 */
function formatLibraryWorkDisplay(workId: string): string {
	return workId
		.split('-')
		.map((word) => word.charAt(0).toUpperCase() + word.slice(1))
		.join(' ');
}

/**
 * Format a library node reference for display.
 * Value format: "work_id:node_id"
 * Just show a simple label - node IDs are opaque.
 */
function formatLibraryNodeDisplay(value: string): string {
	// Value is "work_id:node_id", show work title
	const colonIndex = value.indexOf(':');
	if (colonIndex !== -1) {
		const workId = value.slice(0, colonIndex);
		return formatLibraryWorkDisplay(workId);
	}
	return '[section]';
}

/**
 * Format a library footnote reference for display.
 * Value format: "work_id:node_id:component_id"
 */
function formatLibraryFootnoteDisplay(value: string): string {
	const parts = value.split(':');
	if (parts.length >= 3) {
		const componentId = parts[2];
		// Extract number from component ID like "fn_xxx_1"
		const numMatch = componentId.match(/_(\d+)$/);
		if (numMatch) {
			return `Footnote ${numMatch[1]}`;
		}
	}
	return '[footnote]';
}

// ─────────────────────────────────────────────────────────────────────────────
// Scripture Marker Processing (for library content/notes)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Escape HTML special characters
 */
function escapeHtml(text: string): string {
	return text
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;')
		.replace(/'/g, '&#039;');
}

/**
 * Process scripture markers in text, converting them to clickable links.
 * Format: [SCRIPTURE[book:chapter:verse]] or [SCRIPTURE[book:chapter:start-end]]
 *
 * Returns HTML string with scripture refs as anchor tags with data attributes.
 */
export function processScriptureMarkers(text: string): string {
	return text.replace(
		/\[SCRIPTURE\[([^\]]+)\]\]/g,
		(_, refValue) => {
			const ref = parseScriptureRef(refValue);
			const displayText = formatScriptureDisplay(ref);
			const verse = ref.verseStart ?? 1;
			const href = `/read/${ref.bookId}/${ref.chapter}#osb-${ref.bookId}-${ref.chapter}-${verse}`;
			return `<a href="${escapeHtml(href)}" class="scripture-ref" data-scripture="${escapeHtml(refValue)}">${escapeHtml(displayText)}</a>`;
		}
	);
}
