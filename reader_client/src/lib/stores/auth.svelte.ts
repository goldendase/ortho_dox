/**
 * Auth State Store
 *
 * Manages:
 * - The shared secret for API authentication
 * - Persistence to localStorage
 * - Auth state checks
 */

import { browser } from '$app/environment';

// ─────────────────────────────────────────────────────────────────────────────
// Configuration
// ─────────────────────────────────────────────────────────────────────────────

const STORAGE_KEY = 'orthodox_reader_secret';
const COOKIE_NAME = 'hmog_secret';

// ─────────────────────────────────────────────────────────────────────────────
// State
// ─────────────────────────────────────────────────────────────────────────────

function loadSecret(): string | null {
	if (!browser) return null;
	try {
		return localStorage.getItem(STORAGE_KEY);
	} catch {
		return null;
	}
}

function saveSecret(secret: string | null): void {
	if (!browser) return;
	if (secret) {
		localStorage.setItem(STORAGE_KEY, secret);
		// Also set cookie for SSR (server-side requests need auth too)
		document.cookie = `${COOKIE_NAME}=${encodeURIComponent(secret)}; path=/; max-age=${60 * 60 * 24 * 365}; SameSite=Lax`;
	} else {
		localStorage.removeItem(STORAGE_KEY);
		// Clear the cookie
		document.cookie = `${COOKIE_NAME}=; path=/; max-age=0`;
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// Store Class
// ─────────────────────────────────────────────────────────────────────────────

class AuthStore {
	#secret = $state<string | null>(loadSecret());

	/** The current secret (null if not authenticated) */
	get secret() {
		return this.#secret;
	}

	/** Whether the user has authenticated (secret is set) */
	get isAuthenticated() {
		return this.#secret !== null && this.#secret.length > 0;
	}

	/**
	 * Set the authentication secret
	 */
	setSecret(secret: string): void {
		this.#secret = secret;
		saveSecret(secret);
	}

	/**
	 * Clear the secret (logout or on 401)
	 */
	clearSecret(): void {
		this.#secret = null;
		saveSecret(null);
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// Singleton Export
// ─────────────────────────────────────────────────────────────────────────────

export const auth = new AuthStore();
