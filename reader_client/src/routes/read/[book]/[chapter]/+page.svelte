<!--
  Reader Page

  Displays a scripture chapter with verses and annotations.
  Uses StudyContext for position tracking (single source of truth).
-->
<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { reader } from '$lib/stores/reader.svelte';
	import { studyContext } from '$lib/stores/studyContext.svelte';
	import Chapter from '$lib/components/reader/Chapter.svelte';
	import ChapterNav from '$lib/components/navigation/ChapterNav.svelte';

	let { data } = $props();

	// Helper to convert API navigation URL to app route
	function navUrlToPath(url: string | null): string | undefined {
		if (!url) return undefined;
		// Convert "/books/genesis/chapters/2/passages" to "/read/genesis/2"
		const match = url.match(/\/books\/([^/]+)\/chapters\/(\d+)/);
		if (match) {
			return `/read/${match[1]}/${match[2]}`;
		}
		return undefined;
	}

	// Update position when page data changes
	$effect(() => {
		const pos = {
			type: 'scripture' as const,
			book: data.chapter.book_id,
			bookName: data.chapter.book_name,
			chapter: data.chapter.chapter
		};

		// Update StudyContext (single source of truth)
		untrack(() => studyContext.navigate(pos));

		// Set navigation links
		untrack(() =>
			studyContext.setNavigation({
				prev: navUrlToPath(data.chapter.navigation.prev_chapter),
				next: navUrlToPath(data.chapter.navigation.next_chapter)
			})
		);

		// Also update legacy reader store for existing components
		untrack(() =>
			reader.navigate({
				book: data.chapter.book_id,
				bookName: data.chapter.book_name,
				chapter: data.chapter.chapter
			})
		);

		// Scroll to top when chapter changes (unless there's a hash to scroll to)
		if (!window.location.hash) {
			const readerPane = document.querySelector('.reader-pane');
			if (readerPane) {
				readerPane.scrollTo({ top: 0, behavior: 'instant' });
			}
		}
	});

	// Scroll to verse if hash present
	// Supports both formats:
	// - #osb-genesis-1-15 (new distinct format for cross-links)
	// - #v15 (legacy format, still used for some links)
	// Also auto-select if 'select' query param present (from chat annotation links)
	onMount(() => {
		const hash = $page.url.hash;
		const selectParam = $page.url.searchParams.get('select');

		// Parse verse number from hash (check osb format first, then legacy #v format)
		let verseNum: string | null = null;
		const osbMatch = hash.match(/^#osb-[^-]+-\d+-(\d+)$/);
		if (osbMatch) {
			verseNum = osbMatch[1];
		} else if (hash.startsWith('#v')) {
			verseNum = hash.slice(2);
		} else if (selectParam) {
			verseNum = selectParam;
		}

		if (verseNum) {
			// Use the new ID format for lookup
			const verseEl = document.getElementById(
				`osb-${data.chapter.book_id}-${data.chapter.chapter}-${verseNum}`
			);
			if (verseEl) {
				verseEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
				reader.scrollToVerse(parseInt(verseNum, 10));

				// If 'select' param present, also select the verse for chat/focus context
				if (selectParam) {
					const verse = parseInt(selectParam, 10);
					const passage = data.chapter.passages.find((p) => p.verse === verse);
					if (passage) {
						// Update legacy reader store
						reader.selectVerse({
							book: passage.book_id,
							bookName: data.chapter.book_name,
							chapter: passage.chapter,
							verse: passage.verse,
							passageId: passage.id,
							text: passage.text.replace(/<[^>]*>/g, '').slice(0, 150)
						});

						// Also push to StudyContext focus stack
						studyContext.pushFocus({
							type: 'verse',
							book: passage.book_id,
							bookName: data.chapter.book_name,
							chapter: passage.chapter,
							verse: passage.verse,
							passageId: passage.id,
							text: passage.text.replace(/<[^>]*>/g, '').slice(0, 150)
						});
					}
				}
			}
		}
	});

	function handleNavigate(url: string) {
		// Extract book and chapter from URL like "/books/genesis/chapters/2/passages"
		const match = url.match(/\/books\/([^/]+)\/chapters\/(\d+)/);
		if (match) {
			goto(`/read/${match[1]}/${match[2]}`);
		}
	}
</script>

<svelte:head>
	<title>{data.chapter.book_name} {data.chapter.chapter} | Orthodox Reader</title>
</svelte:head>

<article class="reader-page">
	<header class="chapter-header">
		<h1 class="chapter-title">
			{data.chapter.book_name}
			<span class="chapter-number">{data.chapter.chapter}</span>
		</h1>
	</header>

	<div class="chapter-content">
		<Chapter passages={data.chapter.passages} />
	</div>

	<ChapterNav
		prevChapter={data.chapter.navigation.prev_chapter}
		nextChapter={data.chapter.navigation.next_chapter}
		onNavigate={handleNavigate}
	/>
</article>

<style>
	.reader-page {
		max-width: var(--content-max-width);
		margin: 0 auto;
		padding: var(--space-6) var(--space-4);
		padding-bottom: var(--space-2);
	}

	.chapter-header {
		margin-bottom: var(--space-8);
		text-align: center;
	}

	.chapter-title {
		font-size: var(--font-2xl);
		font-weight: var(--font-normal);
		color: var(--color-text-primary);
	}

	.chapter-number {
		color: var(--color-gold);
		margin-left: var(--space-2);
	}

	.chapter-content {
		line-height: var(--leading-relaxed);
	}
</style>
