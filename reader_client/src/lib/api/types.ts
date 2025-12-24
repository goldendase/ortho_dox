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

/** Context for where the user is reading - sent with chat requests */
export type ChatContext =
	| { passage_id: string } // Specific verse selected
	| { book_id: string; chapter: number } // Reading a chapter, no verse selected
	| null; // General question, no context

export interface ChatRequest {
	messages: ChatMessage[];
	context: ChatContext;
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
// Error Response
// ─────────────────────────────────────────────────────────────────────────────

export interface ApiErrorResponse {
	detail: string;
	errors?: Array<{
		field: string;
		message: string;
	}>;
}
