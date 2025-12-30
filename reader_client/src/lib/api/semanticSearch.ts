/**
 * Semantic Search API
 *
 * Vector-based search across OSB and Library content.
 */

import { api } from './client';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

/** OSB search result */
export interface OSBSearchResult {
	source_type: 'osb_study' | 'osb_article' | 'osb_chapter';
	score: number;
	text: string;
	annotation_id?: string;
	book_id?: string;
	book_name?: string;
	chapter?: number;
	verse_start?: number;
	verse_end?: number;
	passage_ids?: string[];
}

/** Library search result */
export interface LibrarySearchResult {
	score: number;
	text: string;
	work_id: string;
	node_id: string;
	node_title?: string;
	author_id?: string;
	chunk_sequence?: number;
	scripture_refs?: string[];
}

/** OSB search response */
export interface OSBSearchResponse {
	results: OSBSearchResult[];
	query: string;
	total: number;
}

/** Library search response */
export interface LibrarySearchResponse {
	results: LibrarySearchResult[];
	query: string;
	total: number;
}

/** Search options for OSB */
export interface OSBSearchOptions {
	limit?: number;
	sourceType?: 'osb_study' | 'osb_article' | 'osb_chapter';
}

/** Search options for Library */
export interface LibrarySearchOptions {
	limit?: number;
	author?: string;
	work?: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// API Functions
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Semantic search across OSB content (study notes, articles, chapters)
 */
export async function searchOSB(
	query: string,
	options: OSBSearchOptions = {}
): Promise<OSBSearchResponse> {
	const params: Record<string, string | number> = { q: query };

	if (options.limit) params.limit = options.limit;
	if (options.sourceType) params.source_type = options.sourceType;

	return api.get<OSBSearchResponse>('/semantic-search/osb', params);
}

/**
 * Semantic search across Library content (patristic texts, etc.)
 */
export async function searchLibrary(
	query: string,
	options: LibrarySearchOptions = {}
): Promise<LibrarySearchResponse> {
	const params: Record<string, string | number> = { q: query };

	if (options.limit) params.limit = options.limit;
	if (options.author) params.author = options.author;
	if (options.work) params.work = options.work;

	return api.get<LibrarySearchResponse>('/semantic-search/library', params);
}

// ─────────────────────────────────────────────────────────────────────────────
// Convenience Exports
// ─────────────────────────────────────────────────────────────────────────────

export const semanticSearch = {
	osb: searchOSB,
	library: searchLibrary
};
