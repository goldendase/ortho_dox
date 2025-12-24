/**
 * Root Layout Server Load
 *
 * Loads the book list for navigation - this data is used across
 * all pages and rarely changes, so we load it once at the root.
 */

import type { LayoutServerLoad } from './$types';
import { books } from '$lib/api';

export const load: LayoutServerLoad = async () => {
	const booksData = await books.list();

	return {
		books: booksData.books
	};
};
