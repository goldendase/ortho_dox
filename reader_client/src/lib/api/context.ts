/**
 * Context API
 *
 * Optimized endpoints for LLM consumption.
 * Used by the chat feature to provide passage context.
 */

import { api } from './client';
import type { ContextResponse, CrossRefContext } from './types';

// ─────────────────────────────────────────────────────────────────────────────
// Full Context Bundle
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Get full context bundle for a passage
 *
 * Includes passage with full expand, bidirectional cross-references,
 * patristic sources, and related articles.
 *
 * Primary endpoint for LLM context building.
 */
export async function getContext(passageId: string): Promise<ContextResponse> {
	return api.get<ContextResponse>(`/context/${passageId}`);
}

// ─────────────────────────────────────────────────────────────────────────────
// Cross-References Only
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Get bidirectional cross-references for a passage
 *
 * Lighter weight than full context when you only need refs.
 */
export async function getCrossRefs(passageId: string): Promise<CrossRefContext> {
	return api.get<CrossRefContext>(`/context/cross-refs/${passageId}`);
}

// ─────────────────────────────────────────────────────────────────────────────
// Convenience Exports
// ─────────────────────────────────────────────────────────────────────────────

export const context = {
	get: getContext,
	crossRefs: getCrossRefs
};
