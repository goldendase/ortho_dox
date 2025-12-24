/**
 * Annotations API
 *
 * Endpoint for fetching individual annotations by ID.
 * Used by chat message links to fetch annotation content on demand.
 */

import { api } from './client';
import type { StudyNote, LiturgicalNote, VariantNote, CitationNote, Article } from './types';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

/** Union of all annotation types that can be fetched by ID */
export type AnnotationResult = StudyNote | LiturgicalNote | VariantNote | CitationNote | Article;

// ─────────────────────────────────────────────────────────────────────────────
// Single Annotation Fetch
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Get a single annotation by ID
 *
 * Works for study notes, liturgical notes, variants, citations, and articles.
 * The returned type field indicates which kind of annotation it is.
 */
export async function getAnnotation(annotationId: string): Promise<AnnotationResult> {
	return api.get(`/annotations/${annotationId}`);
}

// ─────────────────────────────────────────────────────────────────────────────
// Convenience Export
// ─────────────────────────────────────────────────────────────────────────────

export const annotations = {
	get: getAnnotation
};
