/**
 * Library State Store
 *
 * Manages library-specific state:
 * - Current work and node
 * - TOC data
 * - Position persistence (paragraph anchors)
 */

import { browser } from '$app/environment';
import type { LibraryWork, TocNode, LibraryNodeLeaf } from '$lib/api';

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

const STORAGE_KEY = 'orthodox_library_position';

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

// ─────────────────────────────────────────────────────────────────────────────
// Store Class
// ─────────────────────────────────────────────────────────────────────────────

class LibraryStore {
	#position = $state<LibraryPosition | null>(loadPosition());
	#currentWork = $state<LibraryWork | null>(null);
	#toc = $state<TocNode | null>(null);
	#currentNode = $state<LibraryNodeLeaf | null>(null);

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

	// ─────────────────────────────────────────────────────────────────────────
	// Navigation
	// ─────────────────────────────────────────────────────────────────────────

	/**
	 * Set current position (called when navigating to a library page)
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
	setWork(work: LibraryWork): void {
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
	// Reset
	// ─────────────────────────────────────────────────────────────────────────

	reset(): void {
		this.#position = null;
		this.#currentWork = null;
		this.#toc = null;
		this.#currentNode = null;
		this.#tocOpen = false;
		if (browser) {
			localStorage.removeItem(STORAGE_KEY);
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
export function getTocNodeTitle(node: TocNode): string {
	if (node.label && node.title) {
		return `${node.label}. ${node.title}`;
	}
	return node.title || node.label || 'Untitled';
}

/**
 * Find first leaf node in a TOC tree (for redirecting from work page)
 */
export function findFirstLeafNode(node: TocNode): TocNode | null {
	if (node.is_leaf) {
		return node;
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
	return node.children.flatMap(flattenTocLeaves);
}
