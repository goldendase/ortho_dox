/**
 * Base API Client
 *
 * Handles HTTP communication, error handling, and URL construction.
 */

import { browser } from '$app/environment';
import { goto } from '$app/navigation';
import type { ApiErrorResponse } from './types';

// ─────────────────────────────────────────────────────────────────────────────
// Configuration
// ─────────────────────────────────────────────────────────────────────────────

const API_BASE = browser
	? (import.meta.env.VITE_API_URL ?? 'http://localhost:8080')
	: (process.env.API_URL ?? 'http://localhost:8080');

const AUTH_STORAGE_KEY = 'orthodox_reader_secret';
const AUTH_HEADER = 'hmog-secret';

// ─────────────────────────────────────────────────────────────────────────────
// Auth Helpers
// ─────────────────────────────────────────────────────────────────────────────

function getAuthSecret(): string | null {
	if (!browser) return null;
	try {
		return localStorage.getItem(AUTH_STORAGE_KEY);
	} catch {
		return null;
	}
}

function clearAuthSecret(): void {
	if (!browser) return;
	try {
		localStorage.removeItem(AUTH_STORAGE_KEY);
	} catch {
		// Ignore errors
	}
}

function handleUnauthorized(): void {
	if (!browser) return;
	clearAuthSecret();
	// Use goto for client-side redirect
	goto('/auth', { replaceState: true });
}

// ─────────────────────────────────────────────────────────────────────────────
// Error Class
// ─────────────────────────────────────────────────────────────────────────────

export class ApiError extends Error {
	constructor(
		public status: number,
		public detail: string,
		public errors?: ApiErrorResponse['errors']
	) {
		super(detail);
		this.name = 'ApiError';
	}

	static isNotFound(error: unknown): error is ApiError {
		return error instanceof ApiError && error.status === 404;
	}

	static isValidationError(error: unknown): error is ApiError {
		return error instanceof ApiError && error.status === 422;
	}

	static isUnauthorized(error: unknown): error is ApiError {
		return error instanceof ApiError && error.status === 401;
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// Request Helper
// ─────────────────────────────────────────────────────────────────────────────

type QueryParams = Record<string, string | number | boolean | undefined>;

export interface ApiRequestOptions extends RequestInit {
	/** Auth secret to use (for server-side requests where localStorage isn't available) */
	authSecret?: string;
}

function buildAuthHeaders(authSecret?: string): Record<string, string> {
	const headers: Record<string, string> = {
		'Content-Type': 'application/json'
	};

	// Use provided authSecret (SSR) or fall back to localStorage (client)
	const secret = authSecret ?? getAuthSecret();
	if (secret) {
		headers[AUTH_HEADER] = secret;
	}

	return headers;
}

async function request<T>(
	path: string,
	params?: QueryParams,
	options?: ApiRequestOptions
): Promise<T> {
	const url = new URL(path, API_BASE);

	// Add query parameters, filtering out undefined values
	if (params) {
		for (const [key, value] of Object.entries(params)) {
			if (value !== undefined) {
				url.searchParams.set(key, String(value));
			}
		}
	}

	const { authSecret, ...fetchOptions } = options ?? {};

	const response = await fetch(url.href, {
		headers: {
			...buildAuthHeaders(authSecret),
			...fetchOptions?.headers
		},
		...fetchOptions
	});

	if (!response.ok) {
		// Handle 401 by redirecting to auth (client-side only)
		if (response.status === 401) {
			handleUnauthorized();
		}

		let errorBody: ApiErrorResponse;
		try {
			errorBody = await response.json();
		} catch {
			errorBody = { detail: `HTTP ${response.status}: ${response.statusText}` };
		}
		throw new ApiError(response.status, errorBody.detail, errorBody.errors);
	}

	return response.json();
}

async function post<T, B>(path: string, body: B): Promise<T> {
	const url = new URL(path, API_BASE);

	const response = await fetch(url.href, {
		method: 'POST',
		headers: buildAuthHeaders(),
		body: JSON.stringify(body)
	});

	if (!response.ok) {
		// Handle 401 by redirecting to auth
		if (response.status === 401) {
			handleUnauthorized();
		}

		let errorBody: ApiErrorResponse;
		try {
			errorBody = await response.json();
		} catch {
			errorBody = { detail: `HTTP ${response.status}: ${response.statusText}` };
		}
		throw new ApiError(response.status, errorBody.detail, errorBody.errors);
	}

	return response.json();
}

// ─────────────────────────────────────────────────────────────────────────────
// Exported Client
// ─────────────────────────────────────────────────────────────────────────────

export const api = {
	get: request,
	post,
	baseUrl: API_BASE
};
