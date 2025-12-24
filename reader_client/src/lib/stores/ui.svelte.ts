/**
 * UI State Store
 *
 * Manages UI-level state that doesn't persist:
 * - Side panel content (unified panel for all content types)
 * - Mobile sheet visibility
 * - Book picker visibility
 */

import type { StudyNote, LiturgicalNote, VariantNote, Article, PassageWithAnnotations } from '$lib/api';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

/** Content that can be displayed in the side panel */
export type SidePanelContent =
	| { type: 'study'; note: StudyNote }
	| { type: 'liturgical'; note: LiturgicalNote }
	| { type: 'variant'; note: VariantNote }
	| { type: 'article'; article: Article }
	| { type: 'passage'; passage: PassageWithAnnotations; title: string };

// ─────────────────────────────────────────────────────────────────────────────
// Store Class
// ─────────────────────────────────────────────────────────────────────────────

/** Tabs available in the side panel */
export type SidePanelTab = 'notes' | 'chat';

class UIStore {
	/** Book picker sheet visibility */
	bookPickerOpen = $state(false);

	/** Side panel content - null means empty state */
	sidePanelContent = $state<SidePanelContent | null>(null);

	/** Side panel open state (for mobile sheet) */
	sidePanelOpen = $state(false);

	/** Active tab in side panel */
	sidePanelTab = $state<SidePanelTab>('notes');

	// ─────────────────────────────────────────────────────────────────────────
	// Tab Actions
	// ─────────────────────────────────────────────────────────────────────────

	/** Switch to a specific tab */
	setTab(tab: SidePanelTab): void {
		this.sidePanelTab = tab;
		this.sidePanelOpen = true; // Open panel on mobile when switching tabs
	}

	/** Switch to chat tab */
	openChat(): void {
		this.setTab('chat');
	}

	/** Switch to notes tab */
	openNotes(): void {
		this.setTab('notes');
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Book Picker Actions
	// ─────────────────────────────────────────────────────────────────────────

	openBookPicker(): void {
		this.bookPickerOpen = true;
	}

	closeBookPicker(): void {
		this.bookPickerOpen = false;
	}

	toggleBookPicker(): void {
		this.bookPickerOpen = !this.bookPickerOpen;
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Side Panel Actions
	// ─────────────────────────────────────────────────────────────────────────

	/** Show a study note in the side panel */
	showStudyNote(note: StudyNote): void {
		this.sidePanelContent = { type: 'study', note };
		this.sidePanelTab = 'notes';
		this.sidePanelOpen = true;
	}

	/** Show a liturgical note in the side panel */
	showLiturgicalNote(note: LiturgicalNote): void {
		this.sidePanelContent = { type: 'liturgical', note };
		this.sidePanelTab = 'notes';
		this.sidePanelOpen = true;
	}

	/** Show a variant note in the side panel */
	showVariantNote(note: VariantNote): void {
		this.sidePanelContent = { type: 'variant', note };
		this.sidePanelTab = 'notes';
		this.sidePanelOpen = true;
	}

	/** Show an article in the side panel */
	showArticle(article: Article): void {
		this.sidePanelContent = { type: 'article', article };
		this.sidePanelTab = 'notes';
		this.sidePanelOpen = true;
	}

	/** Show a passage preview in the side panel (from cross-ref click) */
	showPassage(passage: PassageWithAnnotations, title: string): void {
		this.sidePanelContent = { type: 'passage', passage, title };
		this.sidePanelTab = 'notes';
		this.sidePanelOpen = true;
	}

	/** Close the side panel (mobile) and clear content */
	closeSidePanel(): void {
		this.sidePanelOpen = false;
		// Don't clear content immediately - let animation finish
	}

	/** Clear side panel content */
	clearSidePanel(): void {
		this.sidePanelContent = null;
		this.sidePanelOpen = false;
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Reset
	// ─────────────────────────────────────────────────────────────────────────

	reset(): void {
		this.bookPickerOpen = false;
		this.sidePanelContent = null;
		this.sidePanelOpen = false;
		this.sidePanelTab = 'notes';
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// Singleton Export
// ─────────────────────────────────────────────────────────────────────────────

export const ui = new UIStore();
