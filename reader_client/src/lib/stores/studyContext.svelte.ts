/**
 * Study Context Store
 *
 * SINGLE SOURCE OF TRUTH for reading state.
 *
 * Manages:
 * - Current reading mode (scripture | library | null)
 * - Current position within that mode
 * - Focus stack (items explicitly selected for discussion)
 * - Position persistence to localStorage
 *
 * Replaces the fragmented position/selection logic from reader.svelte.ts and library.svelte.ts
 */

import { browser } from '$app/environment';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export type ReadingMode = 'scripture' | 'library' | null;

/** Scripture position (OSB) */
export interface ScripturePosition {
	type: 'scripture';
	book: string;
	bookName?: string;
	chapter: number;
	verse?: number;
}

/** Library position */
export interface LibraryPosition {
	type: 'library';
	workId: string;
	workTitle?: string;
	nodeId: string;
	nodeTitle?: string;
	anchor?: string; // Paragraph anchor e.g. "od-lib-p5"
}

/** Discriminated union for any position */
export type Position = ScripturePosition | LibraryPosition;

/** Items that can be in the focus stack (selected for discussion) */
export type FocusItem =
	// Scripture verse
	| {
			type: 'verse';
			book: string;
			bookName: string;
			chapter: number;
			verse: number;
			passageId: string;
			text: string;
	  }
	// Scripture verse range
	| {
			type: 'verse-range';
			book: string;
			bookName: string;
			chapter: number;
			startVerse: number;
			endVerse: number;
			passageIds: string[];
			text: string;
	  }
	// Library paragraph
	| {
			type: 'paragraph';
			workId: string;
			workTitle: string;
			nodeId: string;
			nodeTitle: string;
			index: number;
			text: string;
	  }
	// OSB annotation (study note, liturgical, variant)
	| {
			type: 'osb-note';
			noteType: 'study' | 'liturgical' | 'variant';
			noteId: string;
			verseDisplay: string;
			text: string;
	  }
	// OSB article
	| {
			type: 'osb-article';
			articleId: string;
			text: string;
	  }
	// Library footnote/endnote
	| {
			type: 'library-footnote';
			footnoteId: string;
			footnoteType: 'footnote' | 'endnote';
			marker: string;
			text: string;
	  };

// ─────────────────────────────────────────────────────────────────────────────
// Storage Keys
// ─────────────────────────────────────────────────────────────────────────────

const POSITION_KEY = 'orthodox_study_position';
const FOCUS_KEY = 'orthodox_study_focus';
const HISTORY_KEY = 'orthodox_study_history';
const MAX_HISTORY = 50;
const MAX_CONTEXT_ITEMS = 15;

// ─────────────────────────────────────────────────────────────────────────────
// Persistence Helpers
// ─────────────────────────────────────────────────────────────────────────────

function loadPosition(): Position | null {
	if (!browser) return null;
	try {
		const stored = localStorage.getItem(POSITION_KEY);
		return stored ? JSON.parse(stored) : null;
	} catch {
		return null;
	}
}

function savePosition(pos: Position | null): void {
	if (!browser) return;
	if (pos) {
		localStorage.setItem(POSITION_KEY, JSON.stringify(pos));
	} else {
		localStorage.removeItem(POSITION_KEY);
	}
}

function loadFocusStack(): FocusItem[] {
	if (!browser) return [];
	try {
		const stored = localStorage.getItem(FOCUS_KEY);
		return stored ? JSON.parse(stored) : [];
	} catch {
		return [];
	}
}

function saveFocusStack(stack: FocusItem[]): void {
	if (!browser) return;
	if (stack.length > 0) {
		localStorage.setItem(FOCUS_KEY, JSON.stringify(stack));
	} else {
		localStorage.removeItem(FOCUS_KEY);
	}
}

function loadHistory(): Position[] {
	if (!browser) return [];
	try {
		const stored = localStorage.getItem(HISTORY_KEY);
		return stored ? JSON.parse(stored) : [];
	} catch {
		return [];
	}
}

function saveHistory(history: Position[]): void {
	if (!browser) return;
	localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
}

// ─────────────────────────────────────────────────────────────────────────────
// Store Class
// ─────────────────────────────────────────────────────────────────────────────

/** Navigation links for prev/next */
interface NavLinks {
	prev?: string;
	next?: string;
}

class StudyContextStore {
	#position = $state<Position | null>(loadPosition());
	#focusStack = $state<FocusItem[]>(loadFocusStack());
	#history = $state<Position[]>(loadHistory());
	#navLinks = $state<NavLinks>({});

	// ─────────────────────────────────────────────────────────────────────────
	// Getters
	// ─────────────────────────────────────────────────────────────────────────

	/** Current reading mode derived from position */
	get mode(): ReadingMode {
		return this.#position?.type ?? null;
	}

	/** Current position */
	get position() {
		return this.#position;
	}

	/** Scripture position (only if mode is scripture) */
	get scripturePosition(): ScripturePosition | null {
		return this.#position?.type === 'scripture' ? this.#position : null;
	}

	/** Library position (only if mode is library) */
	get libraryPosition(): LibraryPosition | null {
		return this.#position?.type === 'library' ? this.#position : null;
	}

	/** Items explicitly selected for discussion */
	get focusStack() {
		return this.#focusStack;
	}

	/** Primary focused item (top of stack) */
	get primaryFocus(): FocusItem | null {
		return this.#focusStack[0] ?? null;
	}

	/** Whether there are items in focus */
	get hasFocus() {
		return this.#focusStack.length > 0;
	}

	/** Can navigate back */
	get canGoBack() {
		return this.#history.length > 0;
	}

	/** Previous page/chapter link */
	get prevLink() {
		return this.#navLinks.prev;
	}

	/** Next page/chapter link */
	get nextLink() {
		return this.#navLinks.next;
	}

	/** Can navigate to previous */
	get canGoPrev() {
		return !!this.#navLinks.prev;
	}

	/** Can navigate to next */
	get canGoNext() {
		return !!this.#navLinks.next;
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Navigation
	// ─────────────────────────────────────────────────────────────────────────

	/**
	 * Navigate to a new position
	 * Focus stack is preserved across navigation to support multi-source context
	 */
	navigate(pos: Position, pushHistory = true): void {
		const isSameLocation = this.#isSameLocation(this.#position, pos);

		// Push current position to history if navigating away
		if (pushHistory && this.#position && !isSameLocation) {
			this.#history = [...this.#history.slice(-(MAX_HISTORY - 1)), this.#position];
			saveHistory(this.#history);
		}

		this.#position = pos;
		savePosition(pos);
	}

	/**
	 * Navigate to scripture
	 */
	navigateToScripture(book: string, chapter: number, bookName?: string, verse?: number): void {
		this.navigate({
			type: 'scripture',
			book,
			bookName,
			chapter,
			verse
		});
	}

	/**
	 * Navigate to library
	 */
	navigateToLibrary(
		workId: string,
		nodeId: string,
		workTitle?: string,
		nodeTitle?: string,
		anchor?: string
	): void {
		this.navigate({
			type: 'library',
			workId,
			workTitle,
			nodeId,
			nodeTitle,
			anchor
		});
	}

	/**
	 * Go back in history
	 */
	back(): Position | null {
		if (this.#history.length === 0) return null;

		const prev = this.#history[this.#history.length - 1];
		this.#history = this.#history.slice(0, -1);
		saveHistory(this.#history);

		this.#position = prev;
		savePosition(prev);
		this.#focusStack = [];
		saveFocusStack([]);

		return prev;
	}

	/**
	 * Update scroll position without pushing history
	 */
	updateScroll(update: { verse?: number } | { anchor?: string }): void {
		if (!this.#position) return;

		if (this.#position.type === 'scripture' && 'verse' in update) {
			this.#position = { ...this.#position, verse: update.verse };
		} else if (this.#position.type === 'library' && 'anchor' in update) {
			this.#position = { ...this.#position, anchor: update.anchor };
		}
		savePosition(this.#position);
	}

	/**
	 * Set navigation links for prev/next
	 */
	setNavigation(links: NavLinks): void {
		this.#navLinks = links;
	}

	/**
	 * Clear navigation links
	 */
	clearNavigation(): void {
		this.#navLinks = {};
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Focus Stack Management
	// ─────────────────────────────────────────────────────────────────────────

	/**
	 * Push an item onto the focus stack
	 * Returns false if at max capacity and item is not already in stack
	 */
	pushFocus(item: FocusItem): boolean {
		// Check if already in stack
		const alreadyExists = this.#focusStack.some((f) => this.#isSameFocusItem(f, item));

		// If at max and not already in stack, reject
		if (!alreadyExists && this.#focusStack.length >= MAX_CONTEXT_ITEMS) {
			return false;
		}

		// Remove if already in stack (move to top)
		const filtered = this.#focusStack.filter((f) => !this.#isSameFocusItem(f, item));
		this.#focusStack = [item, ...filtered];
		saveFocusStack(this.#focusStack);
		return true;
	}

	/**
	 * Remove an item from the focus stack
	 */
	removeFocus(item: FocusItem): void {
		this.#focusStack = this.#focusStack.filter((f) => !this.#isSameFocusItem(f, item));
		saveFocusStack(this.#focusStack);
	}

	/**
	 * Pop the primary focus item
	 */
	popFocus(): FocusItem | null {
		if (this.#focusStack.length === 0) return null;
		const [first, ...rest] = this.#focusStack;
		this.#focusStack = rest;
		saveFocusStack(this.#focusStack);
		return first;
	}

	/**
	 * Clear all focus
	 */
	clearFocus(): void {
		this.#focusStack = [];
		saveFocusStack([]);
	}

	/**
	 * Replace entire focus stack
	 */
	replaceFocus(items: FocusItem[]): void {
		this.#focusStack = items;
		saveFocusStack(items);
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Helpers
	// ─────────────────────────────────────────────────────────────────────────

	#isSameLocation(a: Position | null, b: Position | null): boolean {
		if (!a || !b) return false;
		if (a.type !== b.type) return false;

		if (a.type === 'scripture' && b.type === 'scripture') {
			return a.book === b.book && a.chapter === b.chapter;
		}
		if (a.type === 'library' && b.type === 'library') {
			return a.workId === b.workId && a.nodeId === b.nodeId;
		}
		return false;
	}

	#isSameFocusItem(a: FocusItem, b: FocusItem): boolean {
		if (a.type !== b.type) return false;

		if (a.type === 'verse' && b.type === 'verse') {
			return a.passageId === b.passageId;
		}
		if (a.type === 'verse-range' && b.type === 'verse-range') {
			return (
				a.book === b.book &&
				a.chapter === b.chapter &&
				a.startVerse === b.startVerse &&
				a.endVerse === b.endVerse
			);
		}
		if (a.type === 'paragraph' && b.type === 'paragraph') {
			return a.workId === b.workId && a.nodeId === b.nodeId && a.index === b.index;
		}
		if (a.type === 'osb-note' && b.type === 'osb-note') {
			return a.noteId === b.noteId;
		}
		if (a.type === 'osb-article' && b.type === 'osb-article') {
			return a.articleId === b.articleId;
		}
		if (a.type === 'library-footnote' && b.type === 'library-footnote') {
			return a.footnoteId === b.footnoteId;
		}
		return false;
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Reset
	// ─────────────────────────────────────────────────────────────────────────

	reset(): void {
		this.#position = null;
		this.#focusStack = [];
		this.#history = [];
		if (browser) {
			localStorage.removeItem(POSITION_KEY);
			localStorage.removeItem(FOCUS_KEY);
			localStorage.removeItem(HISTORY_KEY);
		}
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// Singleton Export
// ─────────────────────────────────────────────────────────────────────────────

export const studyContext = new StudyContextStore();

// ─────────────────────────────────────────────────────────────────────────────
// Utility Functions
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Format position for display
 */
export function formatPosition(pos: Position): string {
	if (pos.type === 'scripture') {
		const name = pos.bookName ?? pos.book;
		const base = `${name} ${pos.chapter}`;
		return pos.verse ? `${base}:${pos.verse}` : base;
	}
	if (pos.type === 'library') {
		return pos.nodeTitle ?? pos.workTitle ?? pos.workId;
	}
	return '';
}

/**
 * Build URL path from position
 */
export function positionToPath(pos: Position): string {
	if (pos.type === 'scripture') {
		let path = `/read/${pos.book}/${pos.chapter}`;
		if (pos.verse) {
			path += `#osb-${pos.book}-${pos.chapter}-${pos.verse}`;
		}
		return path;
	}
	if (pos.type === 'library') {
		const base = `/library/${pos.workId}/${pos.nodeId}`;
		return pos.anchor ? `${base}#${pos.anchor}` : base;
	}
	return '/';
}

/**
 * Format focus item for display (e.g., in chat context indicator)
 */
export function formatFocusItem(item: FocusItem): string {
	switch (item.type) {
		case 'verse':
			return `${item.bookName} ${item.chapter}:${item.verse}`;
		case 'verse-range':
			return `${item.bookName} ${item.chapter}:${item.startVerse}-${item.endVerse}`;
		case 'paragraph':
			return `${item.nodeTitle || item.workTitle}, para. ${item.index}`;
		case 'osb-note': {
			const label = item.noteType === 'study' ? 'Study Note' :
				item.noteType === 'liturgical' ? 'Liturgical' :
				item.noteType === 'variant' ? 'Variant' : 'Note';
			return `${label}: ${item.verseDisplay}`;
		}
		case 'osb-article':
			return 'Article';
		case 'library-footnote': {
			const fnLabel = item.footnoteType === 'endnote' ? 'Endnote' : 'Footnote';
			return `${fnLabel} ${item.marker}`;
		}
	}
}
