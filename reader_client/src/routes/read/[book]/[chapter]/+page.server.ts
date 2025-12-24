/**
 * Reader Page Server Load
 *
 * Fetches chapter data with annotations for SSR.
 */

import type { PageServerLoad } from './$types';
import { books, ApiError } from '$lib/api';
import { error } from '@sveltejs/kit';

export const load: PageServerLoad = async ({ params, locals }) => {
	const { book, chapter: chapterStr } = params;
	const chapter = parseInt(chapterStr, 10);

	if (isNaN(chapter) || chapter < 1) {
		throw error(400, 'Invalid chapter number');
	}

	try {
		const chapterData = await books.getChapterPassages(
			book,
			chapter,
			'annotations',
			{ authSecret: locals.authSecret ?? undefined }
		);

		return {
			chapter: chapterData
		};
	} catch (err) {
		if (ApiError.isNotFound(err)) {
			throw error(404, `${book} chapter ${chapter} not found`);
		}
		throw err;
	}
};
