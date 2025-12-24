/**
 * API Module Barrel Export
 *
 * Usage:
 *   import { books, passages, context, ApiError } from '$lib/api';
 *
 *   const chapter = await books.getChapterPassages('genesis', 1, 'annotations');
 */

export { api, ApiError, type ApiRequestOptions } from './client';
export { books, listBooks, getBook, getChapterMeta, getChapterPassages, getVerseRange } from './books';
export { passages, getPassage, batchPassages } from './passages';
export { annotations, getAnnotation, type AnnotationResult } from './annotations';
export { context, getContext, getCrossRefs } from './context';
export { chatApi, sendChatMessage } from './chat';
export * from './types';
