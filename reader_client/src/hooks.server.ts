/**
 * Server Hooks
 *
 * Global request handling for authentication and error management.
 */

import type { Handle, HandleServerError } from '@sveltejs/kit';
import { redirect } from '@sveltejs/kit';
import { ApiError } from '$lib/api';

const AUTH_COOKIE = 'hmog_secret';

/**
 * Handle hook - runs for every request
 * Makes auth secret available to all load functions via locals
 */
export const handle: Handle = async ({ event, resolve }) => {
	event.locals.authSecret = event.cookies.get(AUTH_COOKIE) ?? null;
	return resolve(event);
};

/**
 * Error hook - catches unhandled errors
 * Converts 401 ApiErrors to redirects
 */
export const handleError: HandleServerError = async ({ error, event }) => {
	// If an API 401 error bubbles up, redirect to auth
	if (ApiError.isUnauthorized(error)) {
		// Clear the invalid cookie
		event.cookies.delete(AUTH_COOKIE, { path: '/' });
		throw redirect(303, '/auth');
	}

	// Log other errors for debugging
	console.error('Server error:', error);

	return {
		message: 'An unexpected error occurred'
	};
};
