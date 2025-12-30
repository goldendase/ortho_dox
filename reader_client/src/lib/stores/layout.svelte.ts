/**
 * Layout State Store
 *
 * Manages UI layout state:
 * - App mode (read, search, chat, settings)
 * - Navigation drawer (read mode only)
 * - Study panel content (read mode only)
 * - Mobile responsiveness
 */

import { browser } from '$app/environment';
import type {
	StudyNote,
	LiturgicalNote,
	VariantNote,
	Article,
	PassageWithAnnotations,
	LibraryFootnote
} from '$lib/api';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

/** App modes - what's displayed in main area */
export type AppMode = 'read' | 'search' | 'ask' | 'settings';

/** Mobile sheet states */
export type SheetState = 'closed' | 'peek' | 'half' | 'full';

/** Content that can be displayed in the study panel (read mode, right side) */
export type StudyPanelContent =
	// Scripture annotations
	| { mode: 'scripture'; type: 'study'; note: StudyNote }
	| { mode: 'scripture'; type: 'liturgical'; note: LiturgicalNote }
	| { mode: 'scripture'; type: 'variant'; note: VariantNote }
	| { mode: 'scripture'; type: 'article'; article: Article }
	| { mode: 'scripture'; type: 'passage'; passage: PassageWithAnnotations; title: string }
	// Library content
	| { mode: 'library'; type: 'footnote'; footnote: LibraryFootnote }
	| { mode: 'library'; type: 'scripture-preview'; passage: PassageWithAnnotations; title: string };

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────

const MOBILE_BREAKPOINT = 768;

// ─────────────────────────────────────────────────────────────────────────────
// Store Class
// ─────────────────────────────────────────────────────────────────────────────

class LayoutStore {
	// App mode
	#mode = $state<AppMode>('read');

	// Navigation drawer (read mode, desktop)
	#drawerOpen = $state(false);

	// Study panel (read mode, right side)
	#studyPanelContent = $state<StudyPanelContent | null>(null);

	// Mobile sheet states (read mode)
	#navSheetState = $state<SheetState>('closed');
	#studySheetState = $state<SheetState>('closed');

	// Responsive state
	#isMobile = $state(false);

	constructor() {
		if (browser) {
			this.#checkMobile();
			window.addEventListener('resize', this.#handleResize);
		}
	}

	#handleResize = (): void => {
		this.#checkMobile();
	};

	#checkMobile(): void {
		this.#isMobile = window.innerWidth < MOBILE_BREAKPOINT;
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Getters
	// ─────────────────────────────────────────────────────────────────────────

	get mode() {
		return this.#mode;
	}

	get drawerOpen() {
		return this.#drawerOpen;
	}

	get studyPanelContent() {
		return this.#studyPanelContent;
	}

	get hasStudyContent() {
		return this.#studyPanelContent !== null;
	}

	get isMobile() {
		return this.#isMobile;
	}

	get navSheetState() {
		return this.#navSheetState;
	}

	get studySheetState() {
		return this.#studySheetState;
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Mode Actions
	// ─────────────────────────────────────────────────────────────────────────

	setMode(mode: AppMode): void {
		this.#mode = mode;
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Navigation Drawer Actions (Read Mode)
	// ─────────────────────────────────────────────────────────────────────────

	openDrawer(): void {
		if (this.#isMobile) {
			this.#navSheetState = 'full';
		} else {
			this.#drawerOpen = true;
		}
	}

	closeDrawer(): void {
		if (this.#isMobile) {
			this.#navSheetState = 'closed';
		} else {
			this.#drawerOpen = false;
		}
	}

	toggleDrawer(): void {
		if (this.#isMobile) {
			this.#navSheetState = this.#navSheetState === 'closed' ? 'full' : 'closed';
		} else {
			this.#drawerOpen = !this.#drawerOpen;
		}
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Study Panel Actions (Read Mode, Right Side)
	// ─────────────────────────────────────────────────────────────────────────

	showStudyContent(content: StudyPanelContent): void {
		this.#studyPanelContent = content;
		if (this.#isMobile) {
			this.#studySheetState = 'half';
		}
	}

	closeStudyPanel(): void {
		this.#studyPanelContent = null;
		if (this.#isMobile) {
			this.#studySheetState = 'closed';
		}
	}

	// Convenience methods for scripture annotations
	showStudyNote(note: StudyNote): void {
		this.showStudyContent({ mode: 'scripture', type: 'study', note });
	}

	showLiturgicalNote(note: LiturgicalNote): void {
		this.showStudyContent({ mode: 'scripture', type: 'liturgical', note });
	}

	showVariantNote(note: VariantNote): void {
		this.showStudyContent({ mode: 'scripture', type: 'variant', note });
	}

	showArticle(article: Article): void {
		this.showStudyContent({ mode: 'scripture', type: 'article', article });
	}

	showPassagePreview(passage: PassageWithAnnotations, title: string): void {
		this.showStudyContent({ mode: 'scripture', type: 'passage', passage, title });
	}

	// Convenience methods for library content
	showFootnote(footnote: LibraryFootnote): void {
		this.showStudyContent({ mode: 'library', type: 'footnote', footnote });
	}

	showLibraryScripturePreview(passage: PassageWithAnnotations, title: string): void {
		this.showStudyContent({ mode: 'library', type: 'scripture-preview', passage, title });
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Mobile Sheet Actions
	// ─────────────────────────────────────────────────────────────────────────

	setNavSheetState(state: SheetState): void {
		this.#navSheetState = state;
	}

	setStudySheetState(state: SheetState): void {
		this.#studySheetState = state;
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Initialization
	// ─────────────────────────────────────────────────────────────────────────

	initMobileDetection(): void {
		if (browser) {
			this.#checkMobile();
		}
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Reset
	// ─────────────────────────────────────────────────────────────────────────

	reset(): void {
		this.#mode = 'read';
		this.#drawerOpen = false;
		this.#studyPanelContent = null;
		this.#navSheetState = 'closed';
		this.#studySheetState = 'closed';
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Cleanup
	// ─────────────────────────────────────────────────────────────────────────

	destroy(): void {
		if (browser) {
			window.removeEventListener('resize', this.#handleResize);
		}
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// Singleton Export
// ─────────────────────────────────────────────────────────────────────────────

export const layout = new LayoutStore();
