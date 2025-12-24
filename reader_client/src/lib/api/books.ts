/**
 * Books API
 *
 * Endpoints for book listing, details, and chapter data.
 */

import { api, type ApiRequestOptions } from './client';
import type {
	Book,
	BookDetail,
	BooksResponse,
	ChapterMeta,
	ChapterPassagesResponse,
	ExpandMode,
	PassageBase,
	PassageWithAnnotations,
	PassageFull,
	Testament
} from './types';

// ─────────────────────────────────────────────────────────────────────────────
// Book Listing
// ─────────────────────────────────────────────────────────────────────────────

/**
 * List all books, optionally filtered by testament
 */
export async function listBooks(
	testament?: Testament,
	options?: ApiRequestOptions
): Promise<BooksResponse> {
	return api.get<BooksResponse>('/books', { testament }, options);
}

/**
 * Get detailed book info including chapter list
 */
export async function getBook(bookId: string): Promise<BookDetail> {
	return api.get<BookDetail>(`/books/${bookId}`);
}

// ─────────────────────────────────────────────────────────────────────────────
// Chapter Data
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Get chapter metadata (verse count, first/last verse IDs)
 */
export async function getChapterMeta(
	bookId: string,
	chapter: number
): Promise<ChapterMeta> {
	return api.get<ChapterMeta>(`/books/${bookId}/chapters/${chapter}`);
}

/**
 * Get chapter passages - the primary reader endpoint
 *
 * @param expand - 'none' for fast scanning, 'annotations' for reader display,
 *                 'full' for complete data including HTML
 */
export async function getChapterPassages(
	bookId: string,
	chapter: number,
	expand: 'none',
	options?: ApiRequestOptions
): Promise<ChapterPassagesResponse<PassageBase>>;

export async function getChapterPassages(
	bookId: string,
	chapter: number,
	expand: 'annotations',
	options?: ApiRequestOptions
): Promise<ChapterPassagesResponse<PassageWithAnnotations>>;

export async function getChapterPassages(
	bookId: string,
	chapter: number,
	expand: 'full',
	options?: ApiRequestOptions
): Promise<ChapterPassagesResponse<PassageFull>>;

export async function getChapterPassages(
	bookId: string,
	chapter: number,
	expand?: ExpandMode,
	options?: ApiRequestOptions
): Promise<ChapterPassagesResponse>;

export async function getChapterPassages(
	bookId: string,
	chapter: number,
	expand: ExpandMode = 'annotations',
	options?: ApiRequestOptions
): Promise<ChapterPassagesResponse> {
	return api.get<ChapterPassagesResponse>(
		`/books/${bookId}/chapters/${chapter}/passages`,
		{ expand },
		options
	);
}

/**
 * Get a range of verses within a chapter
 */
export async function getVerseRange(
	bookId: string,
	chapter: number,
	verseStart: number,
	verseEnd: number,
	expand: ExpandMode = 'annotations'
): Promise<ChapterPassagesResponse> {
	return api.get<ChapterPassagesResponse>(
		`/books/${bookId}/chapters/${chapter}/passages`,
		{
			expand,
			verse_start: verseStart,
			verse_end: verseEnd
		}
	);
}

// ─────────────────────────────────────────────────────────────────────────────
// Convenience Exports
// ─────────────────────────────────────────────────────────────────────────────

export const books = {
	list: listBooks,
	get: getBook,
	getChapterMeta,
	getChapterPassages,
	getVerseRange
};
