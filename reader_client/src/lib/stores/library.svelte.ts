/**
 * Library State Store
 *
 * Manages library-specific state:
 * - Current work and node
 * - TOC data
 * - Position persistence (paragraph anchors)
 */

import { browser } from '$app/environment';
import type { LibraryWorkDetail, TocNode, LibraryNodeLeaf } from '$lib/api';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export interface LibraryPosition {
	work: string;
	workTitle?: string;
	node: string;
	nodeTitle?: string;
	anchor?: string; // Paragraph anchor e.g. "od-lib-p5"
}

export interface SelectedParagraph {
	workId: string;
	nodeId: string;
	nodeTitle: string; // For display when user navigates away
	index: number; // Paragraph number (1-based, from od-lib-p1)
	text: string; // First ~150 chars for context
}

const STORAGE_KEY = 'orthodox_library_position';
const SELECTED_PARAGRAPH_KEY = 'orthodox_library_selected_paragraph';

// ─────────────────────────────────────────────────────────────────────────────
// Persistence
// ─────────────────────────────────────────────────────────────────────────────

function loadPosition(): LibraryPosition | null {
	if (!browser) return null;
	try {
		const stored = localStorage.getItem(STORAGE_KEY);
		return stored ? JSON.parse(stored) : null;
	} catch {
		return null;
	}
}

function savePosition(pos: LibraryPosition | null): void {
	if (!browser) return;
	if (pos) {
		localStorage.setItem(STORAGE_KEY, JSON.stringify(pos));
	} else {
		localStorage.removeItem(STORAGE_KEY);
	}
}

function loadSelectedParagraph(): SelectedParagraph | null {
	if (!browser) return null;
	try {
		const stored = localStorage.getItem(SELECTED_PARAGRAPH_KEY);
		return stored ? JSON.parse(stored) : null;
	} catch {
		return null;
	}
}

function saveSelectedParagraph(para: SelectedParagraph | null): void {
	if (!browser) return;
	if (para) {
		localStorage.setItem(SELECTED_PARAGRAPH_KEY, JSON.stringify(para));
	} else {
		localStorage.removeItem(SELECTED_PARAGRAPH_KEY);
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// Store Class
// ─────────────────────────────────────────────────────────────────────────────

class LibraryStore {
	#position = $state<LibraryPosition | null>(loadPosition());
	#currentWork = $state<LibraryWorkDetail | null>(null);
	#toc = $state<TocNode | null>(null);
	#currentNode = $state<LibraryNodeLeaf | null>(null);
	#selectedParagraph = $state<SelectedParagraph | null>(loadSelectedParagraph());

	// TOC drawer state
	#tocOpen = $state(false);

	// ─────────────────────────────────────────────────────────────────────────
	// Getters
	// ─────────────────────────────────────────────────────────────────────────

	get position() {
		return this.#position;
	}

	get currentWork() {
		return this.#currentWork;
	}

	get toc() {
		return this.#toc;
	}

	get currentNode() {
		return this.#currentNode;
	}

	get tocOpen() {
		return this.#tocOpen;
	}

	/** Currently selected paragraph for chat context */
	get selectedParagraph() {
		return this.#selectedParagraph;
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Navigation
	// ─────────────────────────────────────────────────────────────────────────

	/**
	 * Set current position (called when navigating to a library page)
	 * NOTE: Cannot clear selectedParagraph here - causes infinite loops
	 * because this is called from $effect. Display layer filters stale selections.
	 */
	setPosition(pos: LibraryPosition): void {
		this.#position = pos;
		savePosition(pos);
	}

	/**
	 * Update anchor in current position (called when scrolling)
	 */
	setAnchor(anchor: string): void {
		if (this.#position) {
			this.#position = { ...this.#position, anchor };
			savePosition(this.#position);
		}
	}

	/**
	 * Set current work data (from page load)
	 */
	setWork(work: LibraryWorkDetail): void {
		this.#currentWork = work;
	}

	/**
	 * Set TOC data (from page load)
	 */
	setToc(toc: TocNode): void {
		this.#toc = toc;
	}

	/**
	 * Set current node content (from page load)
	 */
	setNode(node: LibraryNodeLeaf): void {
		this.#currentNode = node;
	}

	// ─────────────────────────────────────────────────────────────────────────
	// TOC Drawer
	// ─────────────────────────────────────────────────────────────────────────

	openToc(): void {
		this.#tocOpen = true;
	}

	closeToc(): void {
		this.#tocOpen = false;
	}

	toggleToc(): void {
		this.#tocOpen = !this.#tocOpen;
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Paragraph Selection (for chat context)
	// ─────────────────────────────────────────────────────────────────────────

	/**
	 * Select a paragraph for chat context
	 */
	selectParagraph(para: SelectedParagraph): void {
		this.#selectedParagraph = para;
		saveSelectedParagraph(para);
	}

	/**
	 * Clear selected paragraph (reverts to node-level context for chat)
	 */
	clearSelectedParagraph(): void {
		this.#selectedParagraph = null;
		saveSelectedParagraph(null);
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Reset
	// ─────────────────────────────────────────────────────────────────────────

	reset(): void {
		this.#position = null;
		this.#currentWork = null;
		this.#toc = null;
		this.#currentNode = null;
		this.#selectedParagraph = null;
		this.#tocOpen = false;
		if (browser) {
			localStorage.removeItem(STORAGE_KEY);
			localStorage.removeItem(SELECTED_PARAGRAPH_KEY);
		}
	}

	/**
	 * Clear runtime state but keep position (for navigating away)
	 */
	clearRuntimeState(): void {
		this.#currentWork = null;
		this.#toc = null;
		this.#currentNode = null;
		this.#tocOpen = false;
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// Singleton Export
// ─────────────────────────────────────────────────────────────────────────────

export const libraryStore = new LibraryStore();

// ─────────────────────────────────────────────────────────────────────────────
// Utility Functions
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Format library position for display
 */
export function formatLibraryPosition(pos: LibraryPosition): string {
	if (pos.nodeTitle) {
		return pos.nodeTitle;
	}
	if (pos.workTitle) {
		return pos.workTitle;
	}
	return pos.work;
}

/**
 * Build URL path from library position (with anchor)
 */
export function libraryPositionToPath(pos: LibraryPosition): string {
	const base = `/library/${pos.work}/${pos.node}`;
	return pos.anchor ? `${base}#${pos.anchor}` : base;
}

/**
 * Get display title for a TOC node
 */
export function getTocNodeTitle(node: { label?: string; title?: string }): string {
	const MAX_LEN = 25;
	const hasLabel = !!node.label;
	const hasTitle = !!node.title;

	// 1. Construct full title
	let display = 'Untitled';
	if (hasLabel && hasTitle) {
		display = `${node.label}. ${node.title}`;
	} else if (hasTitle) {
		display = node.title!;
	} else if (hasLabel) {
		display = node.label!;
	}

	// 2. If short enough, use it
	if (display.length <= MAX_LEN) {
		return display;
	}

	// 3. Too long - prefer label
	if (hasLabel) {
		if (node.label!.length <= MAX_LEN) {
			return node.label!;
		}
		return node.label!.substring(0, MAX_LEN) + '...';
	}

	// 4. No label - truncate title
	if (hasTitle) {
		return node.title!.substring(0, MAX_LEN) + '...';
	}

	return display;
}

/**
 * Find first leaf node in a TOC tree (for redirecting from work page)
 */
export function findFirstLeafNode(node: TocNode): TocNode | null {
	if (node.is_leaf) {
		return node;
	}
	if (!node.children?.length) {
		return null;
	}
	for (const child of node.children) {
		const leaf = findFirstLeafNode(child);
		if (leaf) return leaf;
	}
	return null;
}

/**
 * Flatten TOC tree to array of leaf nodes (for prev/next navigation)
 */
export function flattenTocLeaves(node: TocNode): TocNode[] {
	if (node.is_leaf) {
		return [node];
	}
	return (node.children ?? []).flatMap(flattenTocLeaves);
}
