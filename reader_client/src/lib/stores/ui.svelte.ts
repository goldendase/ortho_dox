/**
 * UI State Store
 *
 * Manages UI-level state that doesn't persist:
 * - Side panel content (delegated to layout store for unified handling)
 * - Mobile sheet visibility
 * - Book picker visibility
 *
 * Note: The show* methods delegate to the layout store which manages
 * the actual study panel content. This keeps the API surface stable
 * for existing components.
 */

import type { StudyNote, LiturgicalNote, VariantNote, Article, PassageWithAnnotations } from '$lib/api';
import { layout } from './layout.svelte';

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
export type SidePanelTab = 'notes' | 'settings';

class UIStore {
	/**
	 * Side panel content - proxied to layout store for unified handling.
	 * This getter maintains backwards compatibility with components that
	 * read ui.sidePanelContent directly.
	 */
	get sidePanelContent(): SidePanelContent | null {
		const content = layout.studyPanelContent;
		if (!content) return null;

		// Map layout.StudyPanelContent to ui.SidePanelContent
		// (they're similar but layout has 'mode' prefix)
		switch (content.type) {
			case 'study':
				return { type: 'study', note: content.note };
			case 'liturgical':
				return { type: 'liturgical', note: content.note };
			case 'variant':
				return { type: 'variant', note: content.note };
			case 'article':
				return { type: 'article', article: content.article };
			case 'passage':
			case 'scripture-preview':
				return { type: 'passage', passage: content.passage, title: content.title };
			case 'footnote':
				// Footnote maps to article-like display
				return { type: 'article', article: { id: 'footnote', type: 'article', text: content.footnote.content } };
			default:
				return null;
		}
	}

	/** Side panel open state (for mobile sheet) */
	sidePanelOpen = $state(false);

	/** Side panel collapsed state (desktop) */
	sidePanelCollapsed = $state(false);

	/** Active tab in side panel */
	sidePanelTab = $state<SidePanelTab>('notes');

	// ─────────────────────────────────────────────────────────────────────────
	// Tab Actions
	// ─────────────────────────────────────────────────────────────────────────

	/** Switch to a specific tab */
	setTab(tab: SidePanelTab): void {
		this.sidePanelTab = tab;
		this.sidePanelOpen = true; // Open panel on mobile when switching tabs
		this.sidePanelCollapsed = false; // Expand panel when switching tabs
	}

	/** Toggle side panel collapsed state (desktop) */
	toggleSidePanelCollapsed(): void {
		this.sidePanelCollapsed = !this.sidePanelCollapsed;
	}

	/** Expand side panel */
	expandSidePanel(): void {
		this.sidePanelCollapsed = false;
	}

	/** Collapse side panel */
	collapseSidePanel(): void {
		this.sidePanelCollapsed = true;
	}

	/** Switch to notes tab */
	openNotes(): void {
		this.setTab('notes');
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Side Panel Actions (Delegated to Layout Store)
	// ─────────────────────────────────────────────────────────────────────────

	/** Show a study note in the side panel */
	showStudyNote(note: StudyNote): void {
		layout.showStudyNote(note);
		this.sidePanelTab = 'notes';
		this.sidePanelOpen = true;
		this.sidePanelCollapsed = false;
	}

	/** Show a liturgical note in the side panel */
	showLiturgicalNote(note: LiturgicalNote): void {
		layout.showLiturgicalNote(note);
		this.sidePanelTab = 'notes';
		this.sidePanelOpen = true;
		this.sidePanelCollapsed = false;
	}

	/** Show a variant note in the side panel */
	showVariantNote(note: VariantNote): void {
		layout.showVariantNote(note);
		this.sidePanelTab = 'notes';
		this.sidePanelOpen = true;
		this.sidePanelCollapsed = false;
	}

	/** Show an article in the side panel */
	showArticle(article: Article): void {
		layout.showArticle(article);
		this.sidePanelTab = 'notes';
		this.sidePanelOpen = true;
		this.sidePanelCollapsed = false;
	}

	/** Show a passage preview in the side panel (from cross-ref click) */
	showPassage(passage: PassageWithAnnotations, title: string): void {
		layout.showPassagePreview(passage, title);
		this.sidePanelTab = 'notes';
		this.sidePanelOpen = true;
		this.sidePanelCollapsed = false;
	}

	/** Close the side panel (mobile) and clear content */
	closeSidePanel(): void {
		layout.closeStudyPanel();
		this.sidePanelOpen = false;
	}

	/** Clear side panel content */
	clearSidePanel(): void {
		layout.closeStudyPanel();
		this.sidePanelOpen = false;
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Reset
	// ─────────────────────────────────────────────────────────────────────────

	reset(): void {
		layout.closeStudyPanel();
		this.sidePanelOpen = false;
		this.sidePanelCollapsed = false;
		this.sidePanelTab = 'notes';
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// Singleton Export
// ─────────────────────────────────────────────────────────────────────────────

export const ui = new UIStore();
