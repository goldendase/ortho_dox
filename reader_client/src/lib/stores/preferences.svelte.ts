/**
 * User Preferences Store
 *
 * Manages user preferences that persist to localStorage:
 * - Text size for library reader
 * - Scripture reference click behavior
 */

import { browser } from '$app/environment';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export type TextSize = 'sm' | 'md' | 'lg' | 'xl';
export type ScriptureRefBehavior = 'preview' | 'navigate';

export interface Preferences {
	textSize: TextSize;
	scriptureRefBehavior: ScriptureRefBehavior;
}

const STORAGE_KEY = 'orthodox_preferences';

const DEFAULT_PREFERENCES: Preferences = {
	textSize: 'md',
	scriptureRefBehavior: 'preview'
};

// Text sizes array for iteration
export const TEXT_SIZES: TextSize[] = ['sm', 'md', 'lg', 'xl'];

// Text size to CSS font-size mapping
export const TEXT_SIZE_VALUES: Record<TextSize, string> = {
	sm: '1rem',
	md: '1.125rem',
	lg: '1.25rem',
	xl: '1.4rem'
};

export const TEXT_SIZE_LABELS: Record<TextSize, string> = {
	sm: 'Small',
	md: 'Medium',
	lg: 'Large',
	xl: 'Extra Large'
};

// ─────────────────────────────────────────────────────────────────────────────
// Persistence
// ─────────────────────────────────────────────────────────────────────────────

function loadPreferences(): Preferences {
	if (!browser) return DEFAULT_PREFERENCES;
	try {
		const stored = localStorage.getItem(STORAGE_KEY);
		if (stored) {
			return { ...DEFAULT_PREFERENCES, ...JSON.parse(stored) };
		}
	} catch {
		// Ignore
	}
	return DEFAULT_PREFERENCES;
}

function savePreferences(prefs: Preferences): void {
	if (!browser) return;
	try {
		localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
	} catch {
		// Ignore
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// Store Class
// ─────────────────────────────────────────────────────────────────────────────

class PreferencesStore {
	#prefs = $state<Preferences>(loadPreferences());

	get textSize() {
		return this.#prefs.textSize;
	}

	get scriptureRefBehavior() {
		return this.#prefs.scriptureRefBehavior;
	}

	get textSizeCss() {
		return TEXT_SIZE_VALUES[this.#prefs.textSize];
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Text Size
	// ─────────────────────────────────────────────────────────────────────────

	setTextSize(size: TextSize): void {
		this.#prefs = { ...this.#prefs, textSize: size };
		savePreferences(this.#prefs);
	}

	increaseTextSize(): void {
		const sizes: TextSize[] = ['sm', 'md', 'lg', 'xl'];
		const currentIdx = sizes.indexOf(this.#prefs.textSize);
		if (currentIdx < sizes.length - 1) {
			this.setTextSize(sizes[currentIdx + 1]);
		}
	}

	decreaseTextSize(): void {
		const sizes: TextSize[] = ['sm', 'md', 'lg', 'xl'];
		const currentIdx = sizes.indexOf(this.#prefs.textSize);
		if (currentIdx > 0) {
			this.setTextSize(sizes[currentIdx - 1]);
		}
	}

	get canIncreaseTextSize() {
		return this.#prefs.textSize !== 'xl';
	}

	get canDecreaseTextSize() {
		return this.#prefs.textSize !== 'sm';
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Scripture Ref Behavior
	// ─────────────────────────────────────────────────────────────────────────

	setScriptureRefBehavior(behavior: ScriptureRefBehavior): void {
		this.#prefs = { ...this.#prefs, scriptureRefBehavior: behavior };
		savePreferences(this.#prefs);
	}

	toggleScriptureRefBehavior(): void {
		this.setScriptureRefBehavior(
			this.#prefs.scriptureRefBehavior === 'preview' ? 'navigate' : 'preview'
		);
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Reset
	// ─────────────────────────────────────────────────────────────────────────

	reset(): void {
		this.#prefs = DEFAULT_PREFERENCES;
		if (browser) {
			localStorage.removeItem(STORAGE_KEY);
		}
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// Singleton Export
// ─────────────────────────────────────────────────────────────────────────────

export const preferences = new PreferencesStore();
