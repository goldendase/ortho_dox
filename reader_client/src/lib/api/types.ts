/**
 * API Type Definitions
 *
 * These types mirror the API responses. Keep in sync with API_SPEC.md
 */

// ─────────────────────────────────────────────────────────────────────────────
// Enums & Literals
// ─────────────────────────────────────────────────────────────────────────────

export type Testament = 'old' | 'new';
export type ExpandMode = 'none' | 'annotations' | 'full';
export type AnnotationType = 'study' | 'liturgical' | 'variant' | 'citation' | 'article';
export type PassageFormat = 'prose' | 'poetry';

// ─────────────────────────────────────────────────────────────────────────────
// Books
// ─────────────────────────────────────────────────────────────────────────────

export interface Book {
	id: string;
	name: string;
	abbreviation: string;
	abbreviations: string[];
	order: number;
	testament: Testament;
	chapter_count: number;
	passage_count: number;
}

export interface BookDetail extends Book {
	chapters: ChapterInfo[];
}

export interface ChapterInfo {
	chapter: number;
	verse_count: number;
}

export interface BooksResponse {
	books: Book[];
	total: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Chapters
// ─────────────────────────────────────────────────────────────────────────────

export interface ChapterMeta {
	book_id: string;
	book_name: string;
	chapter: number;
	verse_count: number;
	first_verse_id: string;
	last_verse_id: string;
}

export interface ChapterNavigation {
	prev_chapter: string | null;
	next_chapter: string | null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Passages
// ─────────────────────────────────────────────────────────────────────────────

export interface PassageBase {
	id: string;
	book_id: string;
	chapter: number;
	verse: number;
	text: string;
	format: PassageFormat;
	study_note_ids: string[];
	liturgical_ids: string[];
	variant_ids: string[];
	citation_ids: string[];
	article_ids: string[];
	cross_ref_targets: string[];
}

export interface AnnotationMarker {
	id: string;
	type: AnnotationType | 'cross_ref';
	preceding: string;
}

export interface PassageWithAnnotations extends PassageBase {
	annotations: PassageAnnotations;
	annotation_markers: AnnotationMarker[];
}

export interface PassageFull extends PassageWithAnnotations {
	book_name: string;
	html?: string;
	cross_references?: CrossReferences;
	navigation?: PassageNavigation;
}

export interface PassageNavigation {
	prev: string | null;
	next: string | null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Annotations
// ─────────────────────────────────────────────────────────────────────────────

export interface ScriptureRef {
	id: string;
	display: string;
}

export interface PatristicCitation {
	id: string;
	name: string;
}

export interface StudyNote {
	id: string;
	type: 'study';
	verse_display: string;
	text: string;
	patristic_citations: string[] | PatristicCitation[];
	scripture_refs: ScriptureRef[];
}

export interface LiturgicalNote {
	id: string;
	type: 'liturgical';
	verse_display: string;
	text: string;
}

export interface VariantNote {
	id: string;
	type: 'variant';
	verse_display: string;
	text: string;
}

export interface CitationNote {
	id: string;
	type: 'citation';
	verse_display: string;
	text: string;
	target_passage_id?: string;
}

export interface Article {
	id: string;
	type: 'article';
	text: string;
}

export interface PassageAnnotations {
	study_notes: StudyNote[];
	liturgical: LiturgicalNote[];
	variants: VariantNote[];
	citations: CitationNote[];
	articles: Article[];
}

// ─────────────────────────────────────────────────────────────────────────────
// Cross-References
// ─────────────────────────────────────────────────────────────────────────────

export interface CrossRefTarget {
	id: string;
	book_id: string;
	book_name: string;
	chapter: number;
	verse: number;
	preview: string;
}

export interface CrossReferences {
	text?: string;
	targets: CrossRefTarget[];
}

export interface CrossRefContext {
	passage_id: string;
	outgoing: CrossRefTarget[];
	incoming: CrossRefTarget[];
}

// ─────────────────────────────────────────────────────────────────────────────
// Chapter Passages Response
// ─────────────────────────────────────────────────────────────────────────────

export interface ChapterPassagesResponse<T = PassageBase> {
	book_id: string;
	book_name: string;
	chapter: number;
	passages: T[];
	total: number;
	navigation: ChapterNavigation;
}

// ─────────────────────────────────────────────────────────────────────────────
// Batch Passages Response
// ─────────────────────────────────────────────────────────────────────────────

export interface BatchPassagesResponse<T = PassageBase> {
	passages: T[];
	total: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Patristic Sources
// ─────────────────────────────────────────────────────────────────────────────

export interface PatristicSource {
	id: string;
	name: string;
	citation_count: number;
}

export interface PatristicSourcesResponse {
	sources: PatristicSource[];
	total: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Annotations Query
// ─────────────────────────────────────────────────────────────────────────────

export interface AnnotationQueryParams {
	type?: AnnotationType;
	patristic_source?: string;
	book_id?: string;
	limit?: number;
	offset?: number;
}

export interface AnnotationBase {
	id: string;
	type: AnnotationType;
	passage_ids: string[];
	verse_display: string;
	text: string;
	patristic_citations?: string[];
	scripture_refs?: string[];
}

export interface AnnotationsResponse {
	annotations: AnnotationBase[];
	total: number;
	limit: number;
	offset: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Context (MCP)
// ─────────────────────────────────────────────────────────────────────────────

export interface ContextResponse {
	passage: PassageFull;
	cross_references: {
		outgoing: CrossRefTarget[];
		incoming: CrossRefTarget[];
	};
	patristic_sources: PatristicCitation[];
	related_articles: Article[];
}

// ─────────────────────────────────────────────────────────────────────────────
// Chat
// ─────────────────────────────────────────────────────────────────────────────

export type ChatRole = 'user' | 'assistant' | 'system';

export interface ChatMessage {
	role: ChatRole;
	content: string;
}

/**
 * A single context item - can be scripture, library content, or annotations
 */
export type ChatContextItem =
	// Scripture verse
	| {
			type: 'verse';
			passage_id: string;
			book_id: string;
			book_name: string;
			chapter: number;
			verse: number;
			text: string;
	  }
	// Scripture verse range
	| {
			type: 'verse-range';
			book_id: string;
			book_name: string;
			chapter: number;
			verse_start: number;
			verse_end: number;
			passage_ids: string[];
			text: string;
	  }
	// Library paragraph
	| {
			type: 'paragraph';
			work_id: string;
			work_title: string;
			node_id: string;
			node_title: string;
			paragraph_index: number;
			text: string;
	  }
	// OSB annotation (study note, liturgical, variant)
	| {
			type: 'osb-note';
			note_type: 'study' | 'liturgical' | 'variant';
			note_id: string;
			verse_display: string;
			text: string;
	  }
	// OSB article
	| {
			type: 'osb-article';
			article_id: string;
			text: string;
	  }
	// Library footnote/endnote
	| {
			type: 'library-footnote';
			footnote_id: string;
			footnote_type: 'footnote' | 'endnote';
			marker: string;
			text: string;
	  };

/**
 * Reading context sent with chat requests.
 *
 * Supports two patterns:
 * 1. Multi-item context: context_items array with specific selections
 * 2. Fallback context: just current reading position (book/chapter or work/node)
 *
 * Send explicit titles/names along with IDs so the agent doesn't waste
 * tool calls looking up things the frontend already knows.
 */
export interface ChatContext {
	// ─────────────────────────────────────────────────────────────────────────
	// Multi-item Context (explicit selections from reading)
	// ─────────────────────────────────────────────────────────────────────────

	/** Array of selected context items (verses, paragraphs) */
	context_items?: ChatContextItem[];

	// ─────────────────────────────────────────────────────────────────────────
	// Fallback: OSB (Orthodox Study Bible / Scripture) Context
	// Used when no specific items are selected, just reading position
	// ─────────────────────────────────────────────────────────────────────────

	/** OSB: Specific verse ID (format: "Gen_vchap1-1") */
	passage_id?: string;
	/** OSB: Book ID (lowercase: "genesis") */
	book_id?: string;
	/** OSB: Chapter number */
	chapter?: number;
	/** OSB: Verse number */
	verse?: number;
	/** OSB: Human-readable book name (e.g., "Genesis") */
	book_name?: string;
	/** OSB: Actual verse text if a specific verse is selected */
	verse_text?: string;
	/** OSB: Full chapter text when reading a chapter (no verse selected) */
	chapter_text?: string;

	// ─────────────────────────────────────────────────────────────────────────
	// Fallback: Library (Theological Works) Context
	// Used when no specific items are selected, just reading position
	// ─────────────────────────────────────────────────────────────────────────

	/** Library: Work ID (slug) */
	work_id?: string;
	/** Library: Section/node ID */
	node_id?: string;
	/** Library: Human-readable work title */
	work_title?: string;
	/** Library: Human-readable section/chapter title */
	node_title?: string;
	/** Library: Full text content of the current node/section */
	node_content?: string;
	/** Library: Text of a selected paragraph (if user selected one) */
	paragraph_text?: string;
}

export interface ChatRequest {
	messages: ChatMessage[];
	context: ChatContext | null;
}

export interface ChatToolCall {
	name: string;
	arguments: Record<string, unknown>;
	result: unknown;
}

export interface ChatResponse {
	message: ChatMessage;
	tool_calls: ChatToolCall[];
	error: string | null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Chat Streaming
// ─────────────────────────────────────────────────────────────────────────────

/** SSE event types from the backend */
export type StreamEventType = 'status' | 'chunk' | 'done' | 'error';

export interface StreamEvent {
	type: StreamEventType;
	data: string | { answer: string; tool_calls: ChatToolCall[] } | null;
}

/** Callback for streaming events */
export interface StreamCallbacks {
	onStatus?: (status: string) => void;
	onChunk?: (text: string) => void;
	onDone?: (answer: string, toolCalls: ChatToolCall[]) => void;
	onError?: (error: string) => void;
}

// ─────────────────────────────────────────────────────────────────────────────
// Library - Enums
// ─────────────────────────────────────────────────────────────────────────────

export type Era = 'apostolic' | 'nicene' | 'byzantine' | 'early_modern' | 'modern';
export type WorkType = 'commentary' | 'ascetical' | 'pastoral' | 'doctrinal' | 'historical';
export type ReadingLevel = 'inquirer' | 'catechumen' | 'faithful' | 'scholar';
export type ContributorRole = 'translator' | 'editor' | 'compiler';
export type Tradition =
	| 'eastern_orthodox'
	| 'oriental_orthodox'
	| 'catholic'
	| 'protestant'
	| 'ecumenical'
	| 'heretical';

// ─────────────────────────────────────────────────────────────────────────────
// Library - Works
// ─────────────────────────────────────────────────────────────────────────────

export interface Contributor {
	name: string;
	role: ContributorRole;
}

export interface LibraryWorkSummary {
	id: string;
	title: string;
	subtitle?: string;
	description?: string;
	notes?: string;
	author: string;
	contributors: Contributor[];
	work_type: WorkType;
	era: Era;
	reading_level: ReadingLevel;
	tags: string[];
	node_count: number;
	has_images: boolean;
}

export interface LibraryWorkDetail extends LibraryWorkSummary {
	relevance?: string;
	tradition: Tradition;
	cover_image?: string;
	publication_year?: number;
	leaf_count: number;
	scripture_ref_count: number;
}

export interface LibraryWorksResponse {
	works: LibraryWorkSummary[];
	total: number;
	limit: number;
	offset: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Library - Filters
// ─────────────────────────────────────────────────────────────────────────────

export interface FilterAuthor {
	name: string;
	work_count: number;
}

export interface FiltersResponse {
	authors: FilterAuthor[];
	work_types: string[];
	eras: string[];
	reading_levels: string[];
}

// ─────────────────────────────────────────────────────────────────────────────
// Library - Nodes (TOC structure)
// ─────────────────────────────────────────────────────────────────────────────

export type LibraryNodeType =
	| 'book'
	| 'part'
	| 'chapter'
	| 'section'
	| 'essay'
	| 'letter';

export interface TocNode {
	id: string;
	title?: string;
	label?: string;
	node_type: LibraryNodeType;
	is_leaf: boolean;
	order: number;
	children: TocNode[];
}

export interface TocResponse {
	work_id: string;
	root: TocNode;
}

// ─────────────────────────────────────────────────────────────────────────────
// Library - Node Content & Components
// ─────────────────────────────────────────────────────────────────────────────

export type LibraryComponentType =
	| 'footnote'
	| 'endnote'
	| 'image'
	| 'quote'
	| 'epigraph'
	| 'poem'
	| 'letter';

export interface LibraryFootnote {
	id: string;
	type: 'footnote' | 'endnote';
	marker: string;
	content: string;
}

export interface LibraryImage {
	id: string;
	type: 'image';
	image_path: string;
	caption?: string;
	alt_text?: string;
}

export interface LibraryQuote {
	id: string;
	type: 'quote' | 'epigraph';
	content: string;
	attribution?: string;
}

export interface LibraryPoem {
	id: string;
	type: 'poem';
	content: string;
	attribution?: string;
}

export interface LibraryLetter {
	id: string;
	type: 'letter';
	content: string;
	header?: string;
}

export interface LibraryComponents {
	footnotes: LibraryFootnote[];
	endnotes: LibraryFootnote[];
	images: LibraryImage[];
	quotes: LibraryQuote[];
	epigraphs: LibraryQuote[];
	poems: LibraryPoem[];
	letters: LibraryLetter[];
}

export interface LibraryNodeNavigation {
	prev?: { id: string; title?: string; label?: string };
	next?: { id: string; title?: string; label?: string };
	parent?: { id: string; title?: string; label?: string };
}

/** Non-leaf node (container) */
export interface LibraryNodeContainer {
	id: string;
	work_id: string;
	title?: string;
	label?: string;
	node_type: LibraryNodeType;
	depth: number;
	is_leaf: false;
	content: null;
	children: Array<{
		id: string;
		title?: string;
		label?: string;
		node_type: LibraryNodeType;
		is_leaf: boolean;
	}>;
	navigation?: LibraryNodeNavigation; // Only with expand=full
}

/** Leaf node (has content) */
export interface LibraryNodeLeaf {
	id: string;
	work_id: string;
	title?: string;
	label?: string;
	node_type: LibraryNodeType;
	depth: number;
	is_leaf: true;
	content: string;
	components?: LibraryComponents;
	navigation?: LibraryNodeNavigation; // Only with expand=full
}

export type LibraryNode = LibraryNodeContainer | LibraryNodeLeaf;

export type LibraryExpandMode = 'none' | 'components' | 'full';

// ─────────────────────────────────────────────────────────────────────────────
// Library - Scripture References
// ─────────────────────────────────────────────────────────────────────────────

export interface LibraryScriptureRefTarget {
	passage_id: string;
	book_id: string;
	book_name: string;
	chapter: number;
	verse_start: number;
	verse_end?: number;
	preview: string;
}

export interface LibraryScriptureRef {
	id: string;
	source_node_id: string;
	source_node_title?: string;
	reference_text: string;
	target: LibraryScriptureRefTarget;
}

export interface LibraryScriptureRefsResponse {
	work_id: string;
	work_title: string;
	scripture_refs: LibraryScriptureRef[];
	total: number;
	limit: number;
	offset: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Library - Authors
// ─────────────────────────────────────────────────────────────────────────────

export interface LibraryAuthorDetail {
	id: string;
	name: string;
	dates?: string;
	description?: string;
	work_count: number;
}

export interface LibraryAuthorsResponse {
	authors: LibraryAuthorDetail[];
	total: number;
}

export interface LibraryAuthorWorksResponse {
	author: { id: string; name: string };
	works: Array<{
		id: string;
		title: string;
		role: ContributorRole;
		work_type: WorkType;
	}>;
	total: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Library - Context (MCP)
// ─────────────────────────────────────────────────────────────────────────────

export interface LibraryNodeContext {
	node: {
		id: string;
		work_id: string;
		work_title: string;
		title?: string;
		node_type: LibraryNodeType;
		content: string;
		components?: LibraryComponents;
	};
	author: {
		id: string;
		name: string;
		dates?: string;
	};
	scripture_references: Array<{
		reference_text: string;
		passage_id: string;
		book_name: string;
		chapter: number;
		verse: number;
		preview: string;
	}>;
	navigation: {
		prev?: { id: string; title?: string };
		next?: { id: string; title?: string };
		breadcrumb: Array<{ id: string; title?: string }>;
	};
}

// ─────────────────────────────────────────────────────────────────────────────
// Error Response
// ─────────────────────────────────────────────────────────────────────────────

export interface ApiErrorResponse {
	detail: string;
	errors?: Array<{
		field: string;
		message: string;
	}>;
}
