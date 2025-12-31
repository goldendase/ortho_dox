/**
 * API Module Barrel Export
 *
 * Usage:
 *   import { books, passages, context, library, ApiError } from '$lib/api';
 *
 *   const chapter = await books.getChapterPassages('genesis', 1, 'annotations');
 *   const works = await library.listWorks();
 */

export { api, ApiError, type ApiRequestOptions } from './client';
export { books, listBooks, getBook, getChapterMeta, getChapterPassages, getVerseRange } from './books';
export { passages, getPassage, batchPassages } from './passages';
export { annotations, getAnnotation, type AnnotationResult } from './annotations';
export { context, getContext, getCrossRefs } from './context';
export { chatApi, sendChatMessage, sendChatMessageStream } from './chat';
export {
	library,
	listWorks,
	getWork,
	getFilters,
	getToc,
	getNode,
	getLeafNode,
	getWorkScriptureRefs,
	getNodeScriptureRefs,
	listAuthors,
	getAuthor,
	getAuthorWorks,
	getNodeContext
} from './library';
export {
	semanticSearch,
	searchOSB,
	searchLibrary,
	type OSBSearchResult,
	type LibrarySearchResult,
	type OSBSearchResponse,
	type LibrarySearchResponse,
	type OSBSearchOptions,
	type LibrarySearchOptions
} from './semanticSearch';
export * from './types';
