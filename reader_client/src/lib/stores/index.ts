/**
 * Stores Barrel Export
 *
 * Usage:
 *   import { reader, ui, chat, favorites, auth } from '$lib/stores';
 */

// ─────────────────────────────────────────────────────────────────────────────
// New Architecture Stores
// ─────────────────────────────────────────────────────────────────────────────

export {
	studyContext,
	formatPosition,
	positionToPath,
	formatFocusItem,
	type ReadingMode,
	type ScripturePosition,
	type LibraryPosition,
	type Position,
	type FocusItem
} from './studyContext.svelte';

export {
	layout,
	type AppMode,
	type SheetState,
	type DrawerTab,
	type StudyPanelContent
} from './layout.svelte';

// ─────────────────────────────────────────────────────────────────────────────
// Legacy/Support Stores
// ─────────────────────────────────────────────────────────────────────────────

export { ui, type SidePanelContent as LegacySidePanelContent, type SidePanelTab } from './ui.svelte';

export { chat, type ChatMessage, type ChatContext } from './chat.svelte';

export {
	favorites,
	makePassageId,
	type FavoritePassage,
	type FavoriteNote
} from './favorites.svelte';

export { auth } from './auth.svelte';

export {
	libraryStore,
	formatLibraryPosition,
	libraryPositionToPath,
	getTocNodeTitle,
	findFirstLeafNode,
	flattenTocLeaves,
	type LibraryPosition as LegacyLibraryPosition,
	type SelectedParagraph
} from './library.svelte';

export {
	preferences,
	TEXT_SIZE_VALUES,
	TEXT_SIZE_LABELS,
	type TextSize,
	type ScriptureRefBehavior,
	type Preferences
} from './preferences.svelte';
