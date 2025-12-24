/**
 * Root Layout Server Load
 *
 * Loads the book list for navigation - this data is used across
 * all pages and rarely changes, so we load it once at the root.
 */

import type { LayoutServerLoad } from './$types';
import { redirect } from '@sveltejs/kit';
import { books } from '$lib/api';

export const load: LayoutServerLoad = async ({ locals, url }) => {
	// Skip auth check for auth page to avoid redirect loop
	if (url.pathname === '/auth') {
		return { books: [] };
	}

	// No auth - redirect to login (authSecret is set by hooks.server.ts)
	if (!locals.authSecret) {
		throw redirect(303, '/auth');
	}

	// API errors (including 401) will bubble up to hooks.server.ts
	const booksData = await books.list(undefined, { authSecret: locals.authSecret });

	return {
		books: booksData.books
	};
};
