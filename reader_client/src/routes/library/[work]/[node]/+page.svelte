<!--
  Library Reader Page

  Full-height paginated reader for library content with:
  - Custom header (replaces main header)
  - TOC drawer
  - Paginated content
  - Page navigation
-->
<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { libraryStore, ui } from '$lib/stores';
	import Sheet from '$lib/components/ui/Sheet.svelte';
	import LibraryHeader from '$lib/components/library/LibraryHeader.svelte';
	import TocDrawer from '$lib/components/library/TocDrawer.svelte';
	import LibraryReader from '$lib/components/library/LibraryReader.svelte';
	import NodeContent from '$lib/components/library/NodeContent.svelte';
	import PageNav from '$lib/components/library/PageNav.svelte';
	import SidePanel from '$lib/components/SidePanel.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';

	let { data } = $props();

	// Track mobile for sheet vs sidebar
	let isMobile = $state(false);

	onMount(() => {
		const mediaQuery = window.matchMedia('(max-width: 768px)');
		isMobile = mediaQuery.matches;

		const handler = (e: MediaQueryListEvent) => {
			isMobile = e.matches;
		};
		mediaQuery.addEventListener('change', handler);

		return () => mediaQuery.removeEventListener('change', handler);
	});

	// Update store when page data changes
	$effect(() => {
		libraryStore.setWork(data.work);
		libraryStore.setToc(data.toc);
		libraryStore.setNode(data.node);
		libraryStore.setPosition({
			work: data.work.id,
			workTitle: data.work.title,
			node: data.node.id,
			nodeTitle: data.node.title || data.node.label
		});
	});

	// Close TOC when navigating on mobile
	$effect(() => {
		$page.params.node;
		if (isMobile) {
			libraryStore.closeToc();
		}
	});
</script>

<svelte:head>
	<title>{data.node.title || data.work.title} | Orthodox Reader</title>
</svelte:head>

<div class="library-layout">
	<!-- Custom header for library mode -->
	<LibraryHeader work={data.work} node={data.node} />

	<div class="library-main">
		<!-- Desktop: TOC sidebar -->
		{#if !isMobile}
			<aside class="toc-sidebar" class:open={libraryStore.tocOpen}>
				<TocDrawer
					work={data.work}
					toc={data.toc}
					workId={data.work.id}
					onClose={() => libraryStore.closeToc()}
				/>
			</aside>
		{/if}

		<!-- Reader area -->
		<div class="reader-area">
			{#key data.node.id}
				<LibraryReader
					navigation={data.node.navigation}
					workId={data.work.id}
					nodeId={data.node.id}
				>
					<NodeContent node={data.node} />
				</LibraryReader>
			{/key}

			<PageNav
				navigation={data.node.navigation}
				workId={data.work.id}
			/>
		</div>

		<!-- Desktop: Side panel -->
		{#if !isMobile}
			<aside class="sidebar-pane" class:collapsed={ui.sidePanelCollapsed}>
				{#if ui.sidePanelCollapsed}
					<button
						class="expand-rail"
						onclick={() => ui.expandSidePanel()}
						aria-label="Expand panel"
					>
						<Icon name="chevron-left" size={16} />
					</button>
				{:else}
					<SidePanel />
				{/if}
			</aside>
		{/if}
	</div>

	<!-- Mobile: TOC as sheet -->
	{#if isMobile}
		<Sheet bind:open={libraryStore.tocOpen} position="left">
			<TocDrawer
				work={data.work}
				toc={data.toc}
				workId={data.work.id}
				onClose={() => libraryStore.closeToc()}
			/>
		</Sheet>
	{/if}

	<!-- Mobile: Side panel as sheet -->
	{#if isMobile}
		<Sheet bind:open={ui.sidePanelOpen}>
			<SidePanel />
		</Sheet>
	{/if}
</div>

<style>
	.library-layout {
		display: flex;
		flex-direction: column;
		height: 100dvh;
		overflow: hidden;
		background: var(--color-bg-base);
	}

	.library-main {
		display: flex;
		flex: 1;
		min-height: 0;
		overflow: hidden;
	}

	.toc-sidebar {
		width: 280px;
		flex-shrink: 0;
		border-right: 1px solid var(--color-border);
		overflow: hidden;
		transition: margin-left var(--transition-normal);
	}

	.toc-sidebar:not(.open) {
		margin-left: -280px;
	}

	.reader-area {
		flex: 3; /* 3:2 reader:panel ratio */
		display: flex;
		flex-direction: column;
		min-width: 0;
		overflow: hidden;
	}

	.sidebar-pane {
		flex: 2; /* 3:2 reader:panel ratio */
		min-width: 300px;
		max-width: 50%;
		border-left: 1px solid var(--color-border);
		overflow: hidden;
		background: var(--color-bg-surface);
		transition: flex var(--transition-normal);
	}

	.sidebar-pane.collapsed {
		flex: 0 0 48px;
		min-width: 48px;
		display: flex;
		align-items: stretch;
	}

	.expand-rail {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 100%;
		height: 100%;
		color: var(--color-text-muted);
		background: var(--color-bg-elevated);
		cursor: pointer;
		transition: color var(--transition-fast), background var(--transition-fast);
	}

	.expand-rail:hover {
		color: var(--color-text-primary);
		background: var(--color-bg-hover);
	}

	@media (max-width: 768px) {
		.toc-sidebar {
			display: none;
		}

		.sidebar-pane {
			display: none;
		}
	}
</style>
