/**
 * Stores Barrel Export
 *
 * Usage:
 *   import { reader, ui, chat, favorites, auth } from '$lib/stores';
 */

export { reader, formatPosition, positionToPath, type ReaderPosition, type SelectedVerse } from './reader.svelte';
export { ui, type SidePanelContent, type SidePanelTab } from './ui.svelte';
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
	type LibraryPosition
} from './library.svelte';
export {
	preferences,
	TEXT_SIZE_VALUES,
	TEXT_SIZE_LABELS,
	type TextSize,
	type ScriptureRefBehavior,
	type Preferences
} from './preferences.svelte';
