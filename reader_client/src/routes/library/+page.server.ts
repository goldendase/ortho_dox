/**
 * Library Browse Page Server Load
 *
 * Loads all works and filter options for client-side filtering.
 * With ~41 works, we load everything upfront for instant filtering.
 */

import type { PageServerLoad } from './$types';
import { redirect } from '@sveltejs/kit';
import { library } from '$lib/api';

export const load: PageServerLoad = async ({ locals }) => {
	// Auth check
	if (!locals.authSecret) {
		throw redirect(303, '/auth');
	}

	// Load all works and filter options in parallel
	const [worksData, filters] = await Promise.all([
		library.listWorks({ limit: 100 }, { authSecret: locals.authSecret }),
		library.getFilters({ authSecret: locals.authSecret })
	]);

	return {
		works: worksData.works,
		filters
	};
};
