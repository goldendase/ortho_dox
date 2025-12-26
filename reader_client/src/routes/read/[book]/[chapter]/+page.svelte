<!--
  Reader Page

  Displays a chapter with verses and annotations.
-->
<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { reader } from '$lib/stores';
	import Chapter from '$lib/components/reader/Chapter.svelte';
	import ChapterNav from '$lib/components/navigation/ChapterNav.svelte';

	let { data } = $props();

	// Update reader position when page data changes
	// Use untrack to prevent the effect from depending on reader.position
	// (navigate() reads position internally to check isSameLocation)
	$effect(() => {
		const pos = {
			book: data.chapter.book_id,
			bookName: data.chapter.book_name,
			chapter: data.chapter.chapter
		};
		untrack(() => reader.navigate(pos));

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
			const verseEl = document.getElementById(`osb-${data.chapter.book_id}-${data.chapter.chapter}-${verseNum}`);
			if (verseEl) {
				verseEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
				reader.scrollToVerse(parseInt(verseNum, 10));

				// If 'select' param present, also select the verse for chat context
				if (selectParam) {
					const verse = parseInt(selectParam, 10);
					const passage = data.chapter.passages.find((p) => p.verse === verse);
					if (passage) {
						reader.selectVerse({
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
		padding-bottom: calc(var(--space-16) + var(--bottom-nav-height));
	}

	@media (min-width: 768px) {
		.reader-page {
			padding-bottom: var(--space-16);
		}
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
