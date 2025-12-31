/**
 * Library State Store
 *
 * Manages library-specific state:
 * - Current work, TOC, and node (for NavigationDrawer)
 * - Per-work position tracking (for "Continue Reading" feature)
 * - Paragraph selection (for chat context)
 *
 * NOTE: Current reading position is tracked by studyContext (single source of truth).
 * This store handles library-specific UI state and per-work bookmarking.
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

const SELECTED_PARAGRAPH_KEY = 'orthodox_library_selected_paragraph';
const WORK_POSITIONS_KEY = 'orthodox_library_work_positions';

// ─────────────────────────────────────────────────────────────────────────────
// Per-Work Position Tracking
// ─────────────────────────────────────────────────────────────────────────────

export interface WorkPosition {
	// Navigation data
	node: string;
	anchor?: string;
	// Display metadata (for "resume reading" UI)
	workTitle: string;
	author: string;
	nodeTitle?: string;
	nodeLabel?: string;
	// Timestamp for sorting by recency
	lastRead: number;
}

/** Map of workId -> last reading position within that work */
export type WorkPositionsMap = Record<string, WorkPosition>;

// ─────────────────────────────────────────────────────────────────────────────
// Persistence
// ─────────────────────────────────────────────────────────────────────────────

function loadSelectedParagraph(): SelectedParagraph | null {
	if (!browser) return null;
	try {
		const stored = localStorage.getItem(SELECTED_PARAGRAPH_KEY);
		return stored ? JSON.parse(stored) : null;
	} catch {
		return null;
	}
}

function loadWorkPositions(): WorkPositionsMap {
	if (!browser) return {};
	try {
		const stored = localStorage.getItem(WORK_POSITIONS_KEY);
		return stored ? JSON.parse(stored) : {};
	} catch {
		return {};
	}
}

function saveWorkPositions(positions: WorkPositionsMap): void {
	if (!browser) return;
	localStorage.setItem(WORK_POSITIONS_KEY, JSON.stringify(positions));
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
	// Runtime state for TOC/reader display
	#currentWork = $state<LibraryWorkDetail | null>(null);
	#toc = $state<TocNode | null>(null);
	#currentNode = $state<LibraryNodeLeaf | null>(null);
	#currentAnchor = $state<string | undefined>(undefined);

	// Chat context selection
	#selectedParagraph = $state<SelectedParagraph | null>(loadSelectedParagraph());

	// Per-work position tracking (for "Continue Reading" feature)
	#workPositions = $state<WorkPositionsMap>(loadWorkPositions());

	// TOC drawer state
	#tocOpen = $state(false);

	// ─────────────────────────────────────────────────────────────────────────
	// Getters
	// ─────────────────────────────────────────────────────────────────────────

	/** Current work/node as a position object (derived, for compatibility) */
	get position(): LibraryPosition | null {
		if (!this.#currentWork || !this.#currentNode) return null;
		return {
			work: this.#currentWork.id,
			workTitle: this.#currentWork.title,
			node: this.#currentNode.id,
			nodeTitle: this.#currentNode.title,
			anchor: this.#currentAnchor
		};
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

	/** Per-work reading positions (for resume reading UI) */
	get workPositions() {
		return this.#workPositions;
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Navigation
	// ─────────────────────────────────────────────────────────────────────────

	/**
	 * Update anchor (called when scrolling)
	 * Also saves to per-work position for resume reading feature
	 */
	setAnchor(anchor: string): void {
		this.#currentAnchor = anchor;
		this.#saveWorkPositionToStorage();
	}

	/**
	 * Internal: save current position to per-work storage
	 * Uses currentWork/currentNode state
	 */
	#saveWorkPositionToStorage(): void {
		if (!this.#currentWork || !this.#currentNode) return;

		const workPos: WorkPosition = {
			node: this.#currentNode.id,
			anchor: this.#currentAnchor,
			workTitle: this.#currentWork.title,
			author: this.#currentWork.author,
			nodeTitle: this.#currentNode.title,
			nodeLabel: this.#currentNode.label,
			lastRead: Date.now()
		};

		const positions = loadWorkPositions();
		positions[this.#currentWork.id] = workPos;
		saveWorkPositions(positions);
	}

	/**
	 * Save current position to per-work storage (for resume reading)
	 * Call this AFTER setting work and node - uses queueMicrotask
	 * to escape reactive context and avoid infinite loops
	 */
	saveWorkPosition(): void {
		queueMicrotask(() => {
			this.#saveWorkPositionToStorage();
		});
	}

	/**
	 * Get saved position for a specific work (for resume navigation)
	 * Reads directly from localStorage to get latest data
	 */
	getWorkPosition(workId: string): WorkPosition | null {
		const positions = loadWorkPositions();
		return positions[workId] ?? null;
	}

	/**
	 * Get all work positions sorted by most recently read
	 * Reads directly from localStorage to get latest data
	 */
	getRecentWorks(limit = 10): Array<{ workId: string } & WorkPosition> {
		const positions = loadWorkPositions();
		return Object.entries(positions)
			.map(([workId, pos]) => ({ workId, ...pos }))
			.sort((a, b) => b.lastRead - a.lastRead)
			.slice(0, limit);
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
	 * Resets anchor since we're on a new node
	 */
	setNode(node: LibraryNodeLeaf): void {
		this.#currentNode = node;
		this.#currentAnchor = undefined;
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
		this.#currentWork = null;
		this.#toc = null;
		this.#currentNode = null;
		this.#currentAnchor = undefined;
		this.#selectedParagraph = null;
		this.#workPositions = {};
		this.#tocOpen = false;
		if (browser) {
			localStorage.removeItem(SELECTED_PARAGRAPH_KEY);
			localStorage.removeItem(WORK_POSITIONS_KEY);
		}
	}

	/**
	 * Clear runtime state (for navigating away from library)
	 */
	clearRuntimeState(): void {
		this.#currentWork = null;
		this.#toc = null;
		this.#currentNode = null;
		this.#currentAnchor = undefined;
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
 * Build URL path from a saved work position (for resume reading)
 */
export function workPositionToPath(workId: string, pos: WorkPosition): string {
	const base = `/library/${workId}/${pos.node}`;
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
