<!--
  Library Reader Page

  Displays library content (patristic writings, etc.)
  within the unified AppShell layout.

  Navigation is handled by:
  - NavigationDrawer (left drawer with TOC)
  - AppShell (layout management)
-->
<script lang="ts">
	import { untrack } from 'svelte';
	import { page } from '$app/stores';
	import { libraryStore, getTocNodeTitle } from '$lib/stores/library.svelte';
	import { studyContext } from '$lib/stores/studyContext.svelte';
	import { layout } from '$lib/stores/layout.svelte';
	import LibraryReader from '$lib/components/library/LibraryReader.svelte';
	import NodeContent from '$lib/components/library/NodeContent.svelte';
	import PageNav from '$lib/components/library/PageNav.svelte';

	let { data } = $props();

	// Update stores when page data changes
	$effect(() => {
		// Update library store (for TOC in NavigationDrawer)
		libraryStore.setWork(data.work);
		libraryStore.setToc(data.toc);
		libraryStore.setNode(data.node);
		libraryStore.setPosition({
			work: data.work.id,
			workTitle: data.work.title,
			node: data.node.id,
			nodeTitle: getTocNodeTitle(data.node)
		});

		// Update study context (single source of truth)
		const pos = {
			type: 'library' as const,
			workId: data.work.id,
			workTitle: data.work.title,
			nodeId: data.node.id,
			nodeTitle: getTocNodeTitle(data.node)
		};
		untrack(() => studyContext.navigate(pos));

		// Set navigation links
		const nav = data.node.navigation;
		untrack(() =>
			studyContext.setNavigation({
				prev: nav?.prev ? `/library/${data.work.id}/${nav.prev.id}` : undefined,
				next: nav?.next ? `/library/${data.work.id}/${nav.next.id}` : undefined
			})
		);

		// Scroll to top when node changes (unless there's a hash)
		if (!window.location.hash) {
			const readerPane = document.querySelector('.reader-pane');
			if (readerPane) {
				readerPane.scrollTo({ top: 0, behavior: 'instant' });
			}
		}
	});

	// Close drawer when navigating on mobile
	$effect(() => {
		$page.params.node;
		if (layout.isMobile) {
			layout.closeDrawer();
		}
	});
</script>

<svelte:head>
	<title>{data.node.title || data.work.title} | Orthodox Reader</title>
</svelte:head>

<article class="library-page">
	<header class="node-header">
		<h1 class="node-title">
			{data.node.title || data.node.label || data.work.title}
		</h1>
		{#if data.node.title && data.work.title !== data.node.title}
			<p class="work-subtitle text-secondary">{data.work.title}</p>
		{/if}
	</header>

	{#key data.node.id}
		<LibraryReader
			navigation={data.node.navigation}
			workId={data.work.id}
			nodeId={data.node.id}
		>
			<NodeContent node={data.node} />
		</LibraryReader>
	{/key}

	<PageNav navigation={data.node.navigation} workId={data.work.id} />
</article>

<style>
	.library-page {
		max-width: var(--content-max-width);
		margin: 0 auto;
		padding: var(--space-6) var(--space-4);
		padding-bottom: var(--space-2);
	}

	.node-header {
		margin-bottom: var(--space-8);
		text-align: center;
	}

	.node-title {
		font-size: var(--font-2xl);
		font-weight: var(--font-normal);
		color: var(--color-text-primary);
	}

	.work-subtitle {
		font-size: var(--font-base);
		margin-top: var(--space-2);
	}
</style>
