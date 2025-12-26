/**
 * Library Reader Page Server Load
 *
 * Loads the work, TOC, and node content for reading.
 */

import type { PageServerLoad } from './$types';
import { redirect, error } from '@sveltejs/kit';
import { library, ApiError } from '$lib/api';

export const load: PageServerLoad = async ({ params, locals }) => {
	// Auth check
	if (!locals.authSecret) {
		throw redirect(303, '/auth');
	}

	const { work: workId, node: nodeId } = params;

	try {
		// Load work, TOC, and node content in parallel
		const [work, tocData, node] = await Promise.all([
			library.getWork(workId, { authSecret: locals.authSecret }),
			library.getToc(workId, { authSecret: locals.authSecret }),
			library.getLeafNode(workId, nodeId, { authSecret: locals.authSecret })
		]);

		return {
			work,
			toc: tocData.root,
			node
		};
	} catch (e) {
		if (ApiError.isNotFound(e)) {
			throw error(404, `Content not found: ${workId}/${nodeId}`);
		}
		throw e;
	}
};
