/**
 * Reader State Store
 *
 * Manages:
 * - Current reading position (book, chapter, verse)
 * - Reading history for back navigation
 * - Position persistence to localStorage
 */

import { browser } from '$app/environment';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export interface ReaderPosition {
	book: string;
	bookName?: string;
	chapter: number;
	verse?: number;
}

export interface SelectedVerse {
	book: string;
	bookName: string;
	chapter: number;
	verse: number;
	passageId: string;
	text: string;
}

const STORAGE_KEY = 'orthodox_reader_position';
const HISTORY_KEY = 'orthodox_reader_history';
const SELECTED_VERSE_KEY = 'orthodox_reader_selected_verse';
const BOOK_POSITIONS_KEY = 'orthodox_reader_book_positions';
const MAX_HISTORY = 50;

// ─────────────────────────────────────────────────────────────────────────────
// Per-Book Position Tracking
// ─────────────────────────────────────────────────────────────────────────────

export interface BookPosition {
	// Navigation data
	chapter: number;
	verse?: number;
	// Display metadata
	bookName: string;
	// Timestamp for sorting by recency
	lastRead: number;
}

/** Map of bookId -> last reading position within that book */
export type BookPositionsMap = Record<string, BookPosition>;

// ─────────────────────────────────────────────────────────────────────────────
// State
// ─────────────────────────────────────────────────────────────────────────────

function loadPosition(): ReaderPosition | null {
	if (!browser) return null;
	try {
		const stored = localStorage.getItem(STORAGE_KEY);
		return stored ? JSON.parse(stored) : null;
	} catch {
		return null;
	}
}

function loadHistory(): ReaderPosition[] {
	if (!browser) return [];
	try {
		const stored = localStorage.getItem(HISTORY_KEY);
		return stored ? JSON.parse(stored) : [];
	} catch {
		return [];
	}
}

function loadSelectedVerse(): SelectedVerse | null {
	if (!browser) return null;
	try {
		const stored = localStorage.getItem(SELECTED_VERSE_KEY);
		return stored ? JSON.parse(stored) : null;
	} catch {
		return null;
	}
}

function loadBookPositions(): BookPositionsMap {
	if (!browser) return {};
	try {
		const stored = localStorage.getItem(BOOK_POSITIONS_KEY);
		return stored ? JSON.parse(stored) : {};
	} catch {
		return {};
	}
}

function saveBookPositions(positions: BookPositionsMap): void {
	if (!browser) return;
	localStorage.setItem(BOOK_POSITIONS_KEY, JSON.stringify(positions));
}

function savePosition(pos: ReaderPosition | null): void {
	if (!browser) return;
	if (pos) {
		localStorage.setItem(STORAGE_KEY, JSON.stringify(pos));
	} else {
		localStorage.removeItem(STORAGE_KEY);
	}
}

function saveHistory(history: ReaderPosition[]): void {
	if (!browser) return;
	localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
}

function saveSelectedVerse(verse: SelectedVerse | null): void {
	if (!browser) return;
	if (verse) {
		localStorage.setItem(SELECTED_VERSE_KEY, JSON.stringify(verse));
	} else {
		localStorage.removeItem(SELECTED_VERSE_KEY);
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// Store Class
// ─────────────────────────────────────────────────────────────────────────────

class ReaderStore {
	#position = $state<ReaderPosition | null>(loadPosition());
	#history = $state<ReaderPosition[]>(loadHistory());
	#selectedVerse = $state<SelectedVerse | null>(loadSelectedVerse());
	#bookPositions = $state<BookPositionsMap>(loadBookPositions());

	/** Current reading position */
	get position() {
		return this.#position;
	}

	/** Currently selected verse for chat context (null = chapter-level context) */
	get selectedVerse() {
		return this.#selectedVerse;
	}

	/** Can navigate back in history */
	get canGoBack() {
		return this.#history.length > 0;
	}

	/** History depth */
	get historyLength() {
		return this.#history.length;
	}

	/** Per-book reading positions (for resume reading UI) */
	get bookPositions() {
		return this.#bookPositions;
	}

	/**
	 * Navigate to a new position
	 *
	 * @param pos - The new position
	 * @param pushHistory - Whether to save current position to history (default: true)
	 */
	navigate(pos: ReaderPosition, pushHistory = true): void {
		// Don't push to history if navigating to same location
		const isSameLocation =
			this.#position?.book === pos.book &&
			this.#position?.chapter === pos.chapter;

		if (pushHistory && this.#position && !isSameLocation) {
			this.#history = [...this.#history.slice(-(MAX_HISTORY - 1)), this.#position];
			saveHistory(this.#history);
		}

		// Clear selected verse when navigating to a different chapter
		if (!isSameLocation) {
			this.#selectedVerse = null;
			saveSelectedVerse(null);
		}

		this.#position = pos;
		savePosition(pos);

		// Also update per-book position
		this.#updateBookPosition(pos);
	}

	/**
	 * Internal: update the per-book position map
	 * NOTE: Only saves to localStorage, doesn't update reactive state to avoid
	 * infinite loops when called from $effect (navigate is called from effects)
	 */
	#updateBookPosition(pos: ReaderPosition): void {
		const bookPos: BookPosition = {
			chapter: pos.chapter,
			verse: pos.verse,
			bookName: pos.bookName ?? pos.book,
			lastRead: Date.now()
		};

		// Save directly to localStorage without updating reactive state
		const positions = loadBookPositions();
		positions[pos.book] = bookPos;
		saveBookPositions(positions);
	}

	/**
	 * Get saved position for a specific book (for resume navigation)
	 * Reads directly from localStorage to get latest data
	 */
	getBookPosition(bookId: string): BookPosition | null {
		const positions = loadBookPositions();
		return positions[bookId] ?? null;
	}

	/**
	 * Get all book positions sorted by most recently read
	 * Reads directly from localStorage to get latest data
	 */
	getRecentBooks(limit = 10): Array<{ bookId: string } & BookPosition> {
		const positions = loadBookPositions();
		return Object.entries(positions)
			.map(([bookId, pos]) => ({ bookId, ...pos }))
			.sort((a, b) => b.lastRead - a.lastRead)
			.slice(0, limit);
	}

	/**
	 * Navigate back to previous position in history
	 */
	back(): ReaderPosition | null {
		if (this.#history.length === 0) return null;

		const prev = this.#history[this.#history.length - 1];
		this.#history = this.#history.slice(0, -1);
		saveHistory(this.#history);

		this.#position = prev;
		savePosition(prev);

		return prev;
	}

	/**
	 * Update verse within current chapter (doesn't push history)
	 */
	scrollToVerse(verse: number): void {
		if (!this.#position) return;
		this.#position = { ...this.#position, verse };
		savePosition(this.#position);
	}

	/**
	 * Select a verse for chat context
	 */
	selectVerse(verse: SelectedVerse): void {
		this.#selectedVerse = verse;
		saveSelectedVerse(verse);
	}

	/**
	 * Clear selected verse (reverts to chapter-level context for chat)
	 */
	clearSelectedVerse(): void {
		this.#selectedVerse = null;
		saveSelectedVerse(null);
	}

	/**
	 * Clear all state (for testing/reset)
	 */
	reset(): void {
		this.#position = null;
		this.#history = [];
		this.#selectedVerse = null;
		this.#bookPositions = {};
		if (browser) {
			localStorage.removeItem(STORAGE_KEY);
			localStorage.removeItem(HISTORY_KEY);
			localStorage.removeItem(SELECTED_VERSE_KEY);
			localStorage.removeItem(BOOK_POSITIONS_KEY);
		}
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// Singleton Export
// ─────────────────────────────────────────────────────────────────────────────

export const reader = new ReaderStore();

// ─────────────────────────────────────────────────────────────────────────────
// Utility Functions
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Format position for display: "Genesis 1:15" or "Genesis 1"
 */
export function formatPosition(pos: ReaderPosition): string {
	const name = pos.bookName ?? pos.book;
	const base = `${name} ${pos.chapter}`;
	return pos.verse ? `${base}:${pos.verse}` : base;
}

/**
 * Build URL path from position
 */
export function positionToPath(pos: ReaderPosition): string {
	let path = `/read/${pos.book}/${pos.chapter}`;
	if (pos.verse) {
		path += `#v${pos.verse}`;
	}
	return path;
}

/**
 * Build URL path from a saved book position (for resume reading)
 */
export function bookPositionToPath(bookId: string, pos: BookPosition): string {
	let path = `/read/${bookId}/${pos.chapter}`;
	if (pos.verse) {
		path += `#v${pos.verse}`;
	}
	return path;
}
