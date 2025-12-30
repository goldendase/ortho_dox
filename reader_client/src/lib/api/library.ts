/**
 * Library API Client
 *
 * Handles communication with the library endpoints for theological works.
 */

import { api, type ApiRequestOptions } from './client';
import type {
	LibraryWorksResponse,
	LibraryWorkDetail,
	TocResponse,
	LibraryNode,
	LibraryNodeLeaf,
	LibraryExpandMode,
	LibraryScriptureRefsResponse,
	LibraryAuthorsResponse,
	LibraryAuthorDetail,
	LibraryAuthorWorksResponse,
	LibraryNodeContext,
	FiltersResponse,
	Era,
	WorkType,
	ReadingLevel
} from './types';

// ─────────────────────────────────────────────────────────────────────────────
// Works
// ─────────────────────────────────────────────────────────────────────────────

export interface ListWorksParams {
	work_type?: WorkType;
	era?: Era;
	reading_level?: ReadingLevel;
	author?: string;
	limit?: number;
	offset?: number;
}

export async function listWorks(
	params?: ListWorksParams,
	options?: ApiRequestOptions
): Promise<LibraryWorksResponse> {
	return api.get<LibraryWorksResponse>(
		'/library/works',
		params as Record<string, string | number | boolean | undefined>,
		options
	);
}

export async function getWork(
	workId: string,
	options?: ApiRequestOptions
): Promise<LibraryWorkDetail> {
	return api.get<LibraryWorkDetail>(`/library/works/${workId}`, undefined, options);
}

export async function getFilters(options?: ApiRequestOptions): Promise<FiltersResponse> {
	return api.get<FiltersResponse>('/library/filters', undefined, options);
}

export async function getToc(
	workId: string,
	options?: ApiRequestOptions
): Promise<TocResponse> {
	return api.get<TocResponse>(`/library/works/${workId}/toc`, undefined, options);
}

// ─────────────────────────────────────────────────────────────────────────────
// Nodes
// ─────────────────────────────────────────────────────────────────────────────

export async function getNode(
	workId: string,
	nodeId: string,
	expand?: LibraryExpandMode,
	options?: ApiRequestOptions
): Promise<LibraryNode> {
	return api.get<LibraryNode>(
		`/library/works/${workId}/nodes/${nodeId}`,
		expand ? { expand } : undefined,
		options
	);
}

/** Type-safe helper when you know you're fetching a leaf node with components */
export async function getLeafNode(
	workId: string,
	nodeId: string,
	options?: ApiRequestOptions
): Promise<LibraryNodeLeaf> {
	// Use 'full' expand mode to get navigation data along with components
	const node = await api.get<LibraryNode>(
		`/library/works/${workId}/nodes/${nodeId}`,
		{ expand: 'full' },
		options
	);
	if (!node.is_leaf) {
		throw new Error(`Expected leaf node but got container: ${nodeId}`);
	}
	return node as LibraryNodeLeaf;
}

// ─────────────────────────────────────────────────────────────────────────────
// Scripture References
// ─────────────────────────────────────────────────────────────────────────────

export interface ScriptureRefsParams {
	book?: string;
	limit?: number;
	offset?: number;
}

export async function getWorkScriptureRefs(
	workId: string,
	params?: ScriptureRefsParams,
	options?: ApiRequestOptions
): Promise<LibraryScriptureRefsResponse> {
	return api.get<LibraryScriptureRefsResponse>(
		`/library/works/${workId}/scripture-refs`,
		params as Record<string, string | number | boolean | undefined>,
		options
	);
}

export async function getNodeScriptureRefs(
	workId: string,
	nodeId: string,
	options?: ApiRequestOptions
): Promise<LibraryScriptureRefsResponse> {
	return api.get<LibraryScriptureRefsResponse>(
		`/library/works/${workId}/nodes/${nodeId}/scripture-refs`,
		undefined,
		options
	);
}

// ─────────────────────────────────────────────────────────────────────────────
// Authors
// ─────────────────────────────────────────────────────────────────────────────

export async function listAuthors(
	role?: string,
	options?: ApiRequestOptions
): Promise<LibraryAuthorsResponse> {
	return api.get<LibraryAuthorsResponse>(
		'/library/authors',
		role ? { role } : undefined,
		options
	);
}

export async function getAuthor(
	authorId: string,
	options?: ApiRequestOptions
): Promise<LibraryAuthorDetail> {
	return api.get<LibraryAuthorDetail>(`/library/authors/${authorId}`, undefined, options);
}

export async function getAuthorWorks(
	authorId: string,
	options?: ApiRequestOptions
): Promise<LibraryAuthorWorksResponse> {
	return api.get<LibraryAuthorWorksResponse>(
		`/library/authors/${authorId}/works`,
		undefined,
		options
	);
}

// ─────────────────────────────────────────────────────────────────────────────
// Context (MCP)
// ─────────────────────────────────────────────────────────────────────────────

export async function getNodeContext(
	workId: string,
	nodeId: string,
	options?: ApiRequestOptions
): Promise<LibraryNodeContext> {
	return api.get<LibraryNodeContext>(
		`/library/context/${workId}/${nodeId}`,
		undefined,
		options
	);
}

// ─────────────────────────────────────────────────────────────────────────────
// Namespace export for cleaner imports
// ─────────────────────────────────────────────────────────────────────────────

export const library = {
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
};
