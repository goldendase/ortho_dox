/**
 * Library Work Page Server Load
 *
 * Redirects to the first readable node in the work.
 */

import type { PageServerLoad } from './$types';
import { redirect, error } from '@sveltejs/kit';
import { library, ApiError } from '$lib/api';
import { findFirstLeafNode } from '$lib/stores';

export const load: PageServerLoad = async ({ params, locals }) => {
	// Auth check
	if (!locals.authSecret) {
		throw redirect(303, '/auth');
	}

	const { work: workId } = params;

	try {
		// Get TOC to find first leaf node
		const toc = await library.getToc(workId, { authSecret: locals.authSecret });

		const firstLeaf = findFirstLeafNode(toc.root);

		if (firstLeaf) {
			// Redirect to first leaf node
			throw redirect(303, `/library/${workId}/${firstLeaf.id}`);
		}

		// No leaf nodes found - show error
		throw error(404, 'This work has no readable content');
	} catch (e) {
		if (ApiError.isNotFound(e)) {
			throw error(404, `Work not found: ${workId}`);
		}
		throw e;
	}
};
