/**
 * Favorites Store
 *
 * Manages favorited passages and study notes with localStorage persistence.
 * All data lives client-side.
 */

import { browser } from '$app/environment';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export interface FavoritePassage {
	id: string; // "genesis-1-5" format
	book: string;
	bookName: string;
	chapter: number;
	verse: number;
	preview: string; // First ~100 chars of verse text
	addedAt: number; // Timestamp
}

export interface FavoriteNote {
	id: string; // Annotation ID from API
	type: 'study' | 'liturgical' | 'variant';
	verseDisplay: string; // "Genesis 1:1"
	preview: string; // First ~100 chars
	addedAt: number; // Timestamp
}

const PASSAGES_KEY = 'orthodox_reader_favorite_passages';
const NOTES_KEY = 'orthodox_reader_favorite_notes';

// ─────────────────────────────────────────────────────────────────────────────
// localStorage Helpers
// ─────────────────────────────────────────────────────────────────────────────

function loadPassages(): FavoritePassage[] {
	if (!browser) return [];
	try {
		const stored = localStorage.getItem(PASSAGES_KEY);
		return stored ? JSON.parse(stored) : [];
	} catch {
		return [];
	}
}

function savePassages(passages: FavoritePassage[]): void {
	if (!browser) return;
	localStorage.setItem(PASSAGES_KEY, JSON.stringify(passages));
}

function loadNotes(): FavoriteNote[] {
	if (!browser) return [];
	try {
		const stored = localStorage.getItem(NOTES_KEY);
		return stored ? JSON.parse(stored) : [];
	} catch {
		return [];
	}
}

function saveNotes(notes: FavoriteNote[]): void {
	if (!browser) return;
	localStorage.setItem(NOTES_KEY, JSON.stringify(notes));
}

// ─────────────────────────────────────────────────────────────────────────────
// Helper: Generate passage ID
// ─────────────────────────────────────────────────────────────────────────────

export function makePassageId(book: string, chapter: number, verse: number): string {
	return `${book}-${chapter}-${verse}`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Store Class
// ─────────────────────────────────────────────────────────────────────────────

class FavoritesStore {
	#passages = $state<FavoritePassage[]>(loadPassages());
	#notes = $state<FavoriteNote[]>(loadNotes());

	// ─────────────────────────────────────────────────────────────────────────
	// Getters
	// ─────────────────────────────────────────────────────────────────────────

	get passages(): FavoritePassage[] {
		return this.#passages;
	}

	get notes(): FavoriteNote[] {
		return this.#notes;
	}

	get passageCount(): number {
		return this.#passages.length;
	}

	get noteCount(): number {
		return this.#notes.length;
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Passage Methods
	// ─────────────────────────────────────────────────────────────────────────

	isPassageFavorited(book: string, chapter: number, verse: number): boolean {
		const id = makePassageId(book, chapter, verse);
		return this.#passages.some((p) => p.id === id);
	}

	addPassage(passage: Omit<FavoritePassage, 'id' | 'addedAt'>): void {
		const id = makePassageId(passage.book, passage.chapter, passage.verse);

		// Don't add duplicates
		if (this.#passages.some((p) => p.id === id)) return;

		const newPassage: FavoritePassage = {
			...passage,
			id,
			addedAt: Date.now()
		};

		this.#passages = [...this.#passages, newPassage];
		savePassages(this.#passages);
	}

	removePassage(book: string, chapter: number, verse: number): void {
		const id = makePassageId(book, chapter, verse);
		this.#passages = this.#passages.filter((p) => p.id !== id);
		savePassages(this.#passages);
	}

	togglePassage(passage: Omit<FavoritePassage, 'id' | 'addedAt'>): boolean {
		const isFav = this.isPassageFavorited(passage.book, passage.chapter, passage.verse);
		if (isFav) {
			this.removePassage(passage.book, passage.chapter, passage.verse);
			return false;
		} else {
			this.addPassage(passage);
			return true;
		}
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Note Methods
	// ─────────────────────────────────────────────────────────────────────────

	isNoteFavorited(noteId: string): boolean {
		return this.#notes.some((n) => n.id === noteId);
	}

	addNote(note: Omit<FavoriteNote, 'addedAt'>): void {
		// Don't add duplicates
		if (this.#notes.some((n) => n.id === note.id)) return;

		const newNote: FavoriteNote = {
			...note,
			addedAt: Date.now()
		};

		this.#notes = [...this.#notes, newNote];
		saveNotes(this.#notes);
	}

	removeNote(noteId: string): void {
		this.#notes = this.#notes.filter((n) => n.id !== noteId);
		saveNotes(this.#notes);
	}

	toggleNote(note: Omit<FavoriteNote, 'addedAt'>): boolean {
		const isFav = this.isNoteFavorited(note.id);
		if (isFav) {
			this.removeNote(note.id);
			return false;
		} else {
			this.addNote(note);
			return true;
		}
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Reset
	// ─────────────────────────────────────────────────────────────────────────

	reset(): void {
		this.#passages = [];
		this.#notes = [];
		if (browser) {
			localStorage.removeItem(PASSAGES_KEY);
			localStorage.removeItem(NOTES_KEY);
		}
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// Singleton Export
// ─────────────────────────────────────────────────────────────────────────────

export const favorites = new FavoritesStore();
