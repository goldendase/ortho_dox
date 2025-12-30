/**
 * Reference Resolver Service
 *
 * Unified handling for all DSL markers and reference types.
 * Used by:
 * - NodeContent.svelte (library scripture links)
 * - ChatMessageContent.svelte (chat annotation clicks)
 * - Cross-reference navigation
 *
 * Centralizes the logic for:
 * - Parsing references from DSL markers
 * - Generating URLs for references
 * - Navigating to references
 * - Showing annotation content in study panel
 */

import { goto } from '$app/navigation';
import { studyContext, type FocusItem } from '$lib/stores/studyContext.svelte';
import { layout } from '$lib/stores/layout.svelte';
import * as api from '$lib/api';
import {
	parseScriptureRef,
	formatScriptureDisplay,
	getBookDisplayName,
	type ScriptureRef,
	type ChatAnnotationType
} from '$lib/utils/chatAnnotations';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

/** Scripture reference */
export interface ScriptureReference {
	type: 'scripture';
	book: string;
	bookName: string;
	chapter: number;
	verse?: number;
	endVerse?: number;
}

/** Library node reference */
export interface LibraryReference {
	type: 'library';
	workId: string;
	nodeId: string;
	anchor?: string;
}

/** Book navigation reference */
export interface BookReference {
	type: 'book';
	bookId: string;
	bookName: string;
}

/** Annotation reference (to be fetched and shown in study panel) */
export interface AnnotationReference {
	type: 'annotation';
	annotationType: 'study' | 'liturgical' | 'variant' | 'citation' | 'article';
	id: string;
}

/** Union of all reference types */
export type Reference =
	| ScriptureReference
	| LibraryReference
	| BookReference
	| AnnotationReference;

// ─────────────────────────────────────────────────────────────────────────────
// Parsing
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Parse a DSL marker into a Reference
 *
 * @param markerType - The marker type (SCRIPTURE, study, book, etc.)
 * @param value - The value inside the marker
 */
export function parseReference(markerType: string, value: string): Reference | null {
	const type = markerType.toLowerCase() as ChatAnnotationType;

	switch (type) {
		case 'scripture': {
			const ref = parseScriptureRef(value);
			return {
				type: 'scripture',
				book: ref.bookId,
				bookName: getBookDisplayName(ref.bookId),
				chapter: ref.chapter,
				verse: ref.verseStart ?? undefined,
				endVerse: ref.verseEnd ?? undefined
			};
		}

		case 'book': {
			return {
				type: 'book',
				bookId: value,
				bookName: getBookDisplayName(value)
			};
		}

		case 'study':
		case 'liturgical':
		case 'variant':
		case 'citation':
		case 'article': {
			return {
				type: 'annotation',
				annotationType: type,
				id: value
			};
		}

		default:
			return null;
	}
}

/**
 * Parse a scripture reference string (e.g., "genesis:1:5")
 * Re-exports from chatAnnotations for convenience
 */
export { parseScriptureRef, formatScriptureDisplay, getBookDisplayName };

// ─────────────────────────────────────────────────────────────────────────────
// URL Generation
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Generate URL for a reference
 */
export function referenceToUrl(ref: Reference): string {
	switch (ref.type) {
		case 'scripture': {
			let path = `/read/${ref.book}/${ref.chapter}`;
			if (ref.verse) {
				path += `#osb-${ref.book}-${ref.chapter}-${ref.verse}`;
			}
			return path;
		}

		case 'library': {
			const base = `/library/${ref.workId}/${ref.nodeId}`;
			return ref.anchor ? `${base}#${ref.anchor}` : base;
		}

		case 'book': {
			return `/read/${ref.bookId}/1`;
		}

		case 'annotation': {
			// Annotations don't have URLs - they're shown in the study panel
			return '#';
		}
	}
}

/**
 * Generate scripture URL from parsed ScriptureRef
 */
export function scriptureRefToUrl(ref: ScriptureRef): string {
	const verse = ref.verseStart ?? 1;
	return `/read/${ref.bookId}/${ref.chapter}#osb-${ref.bookId}-${ref.chapter}-${verse}`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Navigation
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Navigate to a reference
 *
 * @param ref - The reference to navigate to
 * @param options - Navigation options
 */
export async function navigateToReference(
	ref: Reference,
	options: {
		/** Add to focus stack after navigation */
		addToFocus?: boolean;
		/** Fetch passage content for focus item */
		fetchContent?: boolean;
	} = {}
): Promise<void> {
	switch (ref.type) {
		case 'scripture': {
			const url = referenceToUrl(ref);
			await goto(url);

			if (options.addToFocus && ref.verse) {
				// Create focus item for the verse
				const focusItem: FocusItem = {
					type: 'verse',
					book: ref.book,
					bookName: ref.bookName,
					chapter: ref.chapter,
					verse: ref.verse,
					passageId: `${ref.book}_vchap${ref.chapter}-${ref.verse}`,
					text: '' // Will be populated when verse is clicked in UI
				};
				studyContext.pushFocus(focusItem);
			}
			break;
		}

		case 'library': {
			const url = referenceToUrl(ref);
			await goto(url);
			break;
		}

		case 'book': {
			await goto(`/read/${ref.bookId}/1`);
			break;
		}

		case 'annotation': {
			// Don't navigate - show in study panel instead
			await showAnnotationInStudyPanel(ref.annotationType, ref.id);
			break;
		}
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// Study Panel Integration
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Fetch annotation and show in study panel
 */
export async function showAnnotationInStudyPanel(
	annotationType: 'study' | 'liturgical' | 'variant' | 'citation' | 'article',
	id: string
): Promise<void> {
	try {
		const annotation = await api.annotations.get(id);

		switch (annotation.type) {
			case 'study':
				layout.showStudyNote(annotation);
				break;
			case 'liturgical':
				layout.showLiturgicalNote(annotation);
				break;
			case 'variant':
				layout.showVariantNote(annotation);
				break;
			case 'article':
				layout.showArticle(annotation);
				break;
			case 'citation':
				// Citation notes have similar structure to study notes
				// Cast through unknown for the type conversion
				layout.showStudyNote(annotation as unknown as api.StudyNote);
				break;
		}
	} catch (error) {
		console.error('Failed to fetch annotation:', error);
	}
}

/**
 * Show scripture passage preview in study panel
 */
export async function showScripturePreview(
	ref: ScriptureReference,
	options: { mode: 'scripture' | 'library' } = { mode: 'scripture' }
): Promise<void> {
	try {
		const passageId = ref.verse
			? `${ref.book}_vchap${ref.chapter}-${ref.verse}`
			: `${ref.book}_vchap${ref.chapter}-1`;

		const passage = await api.passages.get(passageId, 'annotations');
		const title = formatScriptureDisplay({
			bookId: ref.book,
			chapter: ref.chapter,
			verseStart: ref.verse ?? null,
			verseEnd: ref.endVerse ?? ref.verse ?? null
		});

		if (options.mode === 'library') {
			layout.showLibraryScripturePreview(passage as api.PassageWithAnnotations, title);
		} else {
			layout.showPassagePreview(passage as api.PassageWithAnnotations, title);
		}
	} catch (error) {
		console.error('Failed to fetch passage preview:', error);
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// Handler for Click Events (used by components)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Handle a click on a DSL marker
 *
 * @param markerType - The marker type
 * @param value - The marker value
 * @param behavior - 'navigate' or 'preview'
 */
export async function handleMarkerClick(
	markerType: string,
	value: string,
	behavior: 'navigate' | 'preview' = 'navigate'
): Promise<void> {
	const ref = parseReference(markerType, value);
	if (!ref) return;

	if (ref.type === 'annotation') {
		// Annotations always show in study panel
		await showAnnotationInStudyPanel(ref.annotationType, ref.id);
		return;
	}

	if (behavior === 'preview' && ref.type === 'scripture') {
		await showScripturePreview(ref);
		return;
	}

	await navigateToReference(ref);
}

// ─────────────────────────────────────────────────────────────────────────────
// Export Types
// ─────────────────────────────────────────────────────────────────────────────

export type { ScriptureRef };
