/**
 * Library Browse Page Server Load
 *
 * Loads the list of works for browsing.
 */

import type { PageServerLoad } from './$types';
import { redirect } from '@sveltejs/kit';
import { library, type LibraryCategory } from '$lib/api';

const VALID_CATEGORIES: LibraryCategory[] = [
	'patristic',
	'biography',
	'church_history',
	'spiritual',
	'liturgical',
	'theological'
];

export const load: PageServerLoad = async ({ locals, url }) => {
	// Auth check
	if (!locals.authSecret) {
		throw redirect(303, '/auth');
	}

	// Get category filter from query params - validate against allowed values
	const rawCategory = url.searchParams.get('category');
	const category = rawCategory && VALID_CATEGORIES.includes(rawCategory as LibraryCategory)
		? (rawCategory as LibraryCategory)
		: undefined;

	const author = url.searchParams.get('author') || undefined;

	const worksData = await library.listWorks(
		{ category, author, limit: 50 },
		{ authSecret: locals.authSecret }
	);

	return {
		works: worksData.works,
		total: worksData.total,
		category,
		author
	};
};
