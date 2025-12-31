<!--
  LibraryReader Component

  Scroll-based reader with paragraph anchors.
  Handles:
  - Click/swipe navigation (scrolls by viewport)
  - Paragraph anchor tracking
  - Text size adjustments
-->
<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { goto, replaceState } from '$app/navigation';
	import { page } from '$app/stores';
	import { preferences } from '$lib/stores';
	import { libraryStore } from '$lib/stores/library.svelte';
	import type { LibraryNodeNavigation } from '$lib/api';
	import type { Snippet } from 'svelte';

	interface Props {
		children: Snippet;
		navigation?: LibraryNodeNavigation;
		workId: string;
		nodeId: string;
	}

	let { children, navigation, workId, nodeId }: Props = $props();

	// Computed hrefs for node navigation
	const prevNodeHref = $derived(
		navigation?.prev ? `/library/${workId}/${navigation.prev.id}` : null
	);
	const nextNodeHref = $derived(
		navigation?.next ? `/library/${workId}/${navigation.next.id}` : null
	);

	// Element refs
	let containerEl = $state<HTMLElement | undefined>(undefined);

	// Touch handling for swipe
	let touchStartX = 0;
	let touchStartY = 0;

	// Track if we can scroll further
	let canScrollUp = $state(false);
	let canScrollDown = $state(true);

	// Track first visible paragraph for URL hash
	let firstVisibleId = $state<string | null>(null);

	// Get all paragraph elements
	function getParagraphs(): HTMLElement[] {
		if (!containerEl) return [];
		return Array.from(containerEl.querySelectorAll('[id^="od-lib-p"]'));
	}

	// Find first visible paragraph
	function getFirstVisibleParagraph(): HTMLElement | null {
		const paragraphs = getParagraphs();
		if (!containerEl) return null;

		const containerTop = containerEl.scrollTop;

		for (const p of paragraphs) {
			const pTop = p.offsetTop;
			if (pTop >= containerTop - 10) {
				return p;
			}
		}
		return paragraphs[paragraphs.length - 1] || null;
	}

	// Find last visible paragraph
	function getLastVisibleParagraph(): HTMLElement | null {
		const paragraphs = getParagraphs();
		if (!containerEl) return null;

		const containerBottom = containerEl.scrollTop + containerEl.clientHeight;

		let lastVisible: HTMLElement | null = null;
		for (const p of paragraphs) {
			const pTop = p.offsetTop;
			if (pTop < containerBottom) {
				lastVisible = p;
			} else {
				break;
			}
		}
		return lastVisible;
	}

	// Update scroll state
	function updateScrollState() {
		if (!containerEl) return;
		canScrollUp = containerEl.scrollTop > 10;
		canScrollDown = containerEl.scrollTop < containerEl.scrollHeight - containerEl.clientHeight - 10;
	}

	// Navigate to next "page" (scroll last visible to top)
	function navigateNext() {
		const lastVisible = getLastVisibleParagraph();
		if (lastVisible && canScrollDown) {
			lastVisible.scrollIntoView({ behavior: 'smooth', block: 'start' });
		} else if (nextNodeHref) {
			goto(nextNodeHref);
		}
	}

	// Navigate to previous "page" (scroll first visible to bottom)
	function navigatePrev() {
		if (!containerEl) return;

		const firstVisible = getFirstVisibleParagraph();
		if (firstVisible && canScrollUp) {
			// Find the paragraph that should be at top to put firstVisible at bottom
			const paragraphs = getParagraphs();
			const firstVisibleIndex = paragraphs.indexOf(firstVisible);
			const viewportHeight = containerEl.clientHeight;

			// Walk backwards to find target paragraph
			let targetParagraph = firstVisible;
			let accumulatedHeight = 0;

			for (let i = firstVisibleIndex; i >= 0; i--) {
				const p = paragraphs[i];
				accumulatedHeight += p.offsetHeight;
				if (accumulatedHeight >= viewportHeight) {
					targetParagraph = p;
					break;
				}
				targetParagraph = p;
			}

			targetParagraph.scrollIntoView({ behavior: 'smooth', block: 'start' });
		} else if (prevNodeHref) {
			goto(prevNodeHref);
		}
	}

	// Handle URL hash on mount and set up IntersectionObserver
	// NOTE: Parent component should use {#key nodeId} to remount on node change
	onMount(() => {
		updateScrollState();
		containerEl?.addEventListener('scroll', updateScrollState);

		// Scroll to anchor after content is rendered
		tick().then(() => {
			const hash = $page.url.hash;
			if (hash && containerEl) {
				const target = containerEl.querySelector(hash);
				if (target) {
					// Use instant scroll for back navigation to feel immediate
					target.scrollIntoView({ block: 'start', behavior: 'instant' });
				}
			} else if (containerEl) {
				// No hash - scroll to top for new chapter
				containerEl.scrollTop = 0;
			}
			updateScrollState();
		});

		// IntersectionObserver to track first visible paragraph
		// Use the actual scrolling container (.reader-pane) as root, or null for viewport
		const scrollRoot = containerEl?.closest('.reader-pane') as HTMLElement | null;
		const visibleParagraphs = new Set<string>();
		const observer = new IntersectionObserver(
			(entries) => {
				for (const entry of entries) {
					if (entry.isIntersecting) {
						visibleParagraphs.add(entry.target.id);
					} else {
						visibleParagraphs.delete(entry.target.id);
					}
				}
				// Find the first visible paragraph (lowest number)
				if (visibleParagraphs.size > 0) {
					const sorted = Array.from(visibleParagraphs).sort((a, b) => {
						const numA = parseInt(a.replace('od-lib-p', ''));
						const numB = parseInt(b.replace('od-lib-p', ''));
						return numA - numB;
					});
					const newFirst = sorted[0];
					if (newFirst !== firstVisibleId) {
						firstVisibleId = newFirst;
						// Update URL hash without affecting back button
						const newHash = `#${newFirst}`;
						if (window.location.hash !== newHash) {
							replaceState(newHash, {});
						}
						// Update store anchor (for resume reading)
						libraryStore.setAnchor(newFirst);
					}
				}
			},
			{ root: scrollRoot, threshold: 0 }
		);

		// Observe all paragraphs after content renders
		tick().then(() => {
			for (const p of getParagraphs()) {
				observer.observe(p);
			}
		});

		return () => {
			containerEl?.removeEventListener('scroll', updateScrollState);
			observer.disconnect();
		};
	});

	// Touch handlers for swipe navigation
	function handleTouchStart(e: TouchEvent) {
		touchStartX = e.touches[0].clientX;
		touchStartY = e.touches[0].clientY;
	}

	function handleTouchEnd(e: TouchEvent) {
		const touchEndX = e.changedTouches[0].clientX;
		const touchEndY = e.changedTouches[0].clientY;
		const deltaX = touchEndX - touchStartX;
		const deltaY = touchEndY - touchStartY;

		// Only trigger if horizontal swipe is dominant and significant
		if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 50) {
			if (deltaX < 0) {
				// Swipe left = next
				navigateNext();
			} else {
				// Swipe right = prev
				navigatePrev();
			}
		}
	}

</script>

<div
	class="library-reader"
	bind:this={containerEl}
	ontouchstart={handleTouchStart}
	ontouchend={handleTouchEnd}
	style="--text-size: {preferences.textSizeCss}"
	role="article"
	aria-label="Library reader"
>
	<div class="reader-content">
		{@render children()}
	</div>
</div>

<style>
	.library-reader {
		position: relative;
		flex: 1;
		min-height: 0;
		overflow-y: auto;
		overflow-x: hidden;
		cursor: default;
		scroll-behavior: smooth;
	}

	.reader-content {
		padding: var(--space-6) var(--space-8);
		max-width: 50rem;
		margin: 0 auto;
		font-size: var(--text-size, 1rem);
		line-height: var(--line-height-relaxed);
	}

	/* Global styles for content inside the reader */
	.reader-content :global(p) {
		margin: 0 0 var(--space-4);
		text-align: justify;
		hyphens: auto;
	}

	.reader-content :global(p:first-child) {
		text-indent: 0;
	}

	.reader-content :global(p + p) {
		text-indent: 1.5em;
	}

	.reader-content :global(h1),
	.reader-content :global(h2),
	.reader-content :global(h3) {
		margin: var(--space-6) 0 var(--space-3);
		color: var(--color-text-primary);
	}

	.reader-content :global(h1) {
		font-size: 1.5em;
	}

	.reader-content :global(h2) {
		font-size: 1.25em;
	}

	.reader-content :global(h3) {
		font-size: 1.1em;
	}

	.reader-content :global(blockquote) {
		margin: var(--space-4) var(--space-4);
		padding-left: var(--space-4);
		border-left: 2px solid var(--color-gold-dim);
		color: var(--color-text-secondary);
		font-style: italic;
	}

	.reader-content :global(figure) {
		margin: var(--space-4) 0;
		text-align: center;
	}

	.reader-content :global(figure img) {
		max-width: 100%;
		max-height: 60vh;
		object-fit: contain;
	}

	.reader-content :global(figcaption) {
		margin-top: var(--space-2);
		font-size: var(--font-sm);
		color: var(--color-text-muted);
		font-style: italic;
	}
</style>
