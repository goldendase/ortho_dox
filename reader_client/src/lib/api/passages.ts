/**
 * Passages API
 *
 * Endpoints for fetching individual passages and batch lookups.
 */

import { api } from './client';
import type {
	BatchPassagesResponse,
	ExpandMode,
	PassageBase,
	PassageWithAnnotations,
	PassageFull
} from './types';

// ─────────────────────────────────────────────────────────────────────────────
// Single Passage
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Get a single passage by ID
 *
 * Used for cross-reference lookups and deep linking
 */
export async function getPassage(
	passageId: string,
	expand: 'none'
): Promise<PassageBase>;

export async function getPassage(
	passageId: string,
	expand: 'annotations'
): Promise<PassageWithAnnotations>;

export async function getPassage(
	passageId: string,
	expand: 'full'
): Promise<PassageFull>;

export async function getPassage(
	passageId: string,
	expand?: ExpandMode
): Promise<PassageBase | PassageWithAnnotations | PassageFull>;

export async function getPassage(
	passageId: string,
	expand: ExpandMode = 'annotations'
): Promise<PassageBase | PassageWithAnnotations | PassageFull> {
	return api.get(`/passages/${passageId}`, { expand });
}

// ─────────────────────────────────────────────────────────────────────────────
// Batch Fetch
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Fetch multiple passages by ID (max 500)
 *
 * Useful for pre-fetching cross-references or building reading lists
 */
export async function batchPassages(
	ids: string[],
	expand: 'none'
): Promise<BatchPassagesResponse<PassageBase>>;

export async function batchPassages(
	ids: string[],
	expand: 'annotations'
): Promise<BatchPassagesResponse<PassageWithAnnotations>>;

export async function batchPassages(
	ids: string[],
	expand: 'full'
): Promise<BatchPassagesResponse<PassageFull>>;

export async function batchPassages(
	ids: string[],
	expand?: ExpandMode
): Promise<BatchPassagesResponse>;

export async function batchPassages(
	ids: string[],
	expand: ExpandMode = 'none'
): Promise<BatchPassagesResponse> {
	if (ids.length === 0) {
		return { passages: [], total: 0 };
	}

	if (ids.length > 500) {
		throw new Error('Batch fetch limited to 500 passages');
	}

	return api.get<BatchPassagesResponse>('/passages', {
		ids: ids.join(','),
		expand
	});
}

// ─────────────────────────────────────────────────────────────────────────────
// Convenience Exports
// ─────────────────────────────────────────────────────────────────────────────

export const passages = {
	get: getPassage,
	batch: batchPassages
};
