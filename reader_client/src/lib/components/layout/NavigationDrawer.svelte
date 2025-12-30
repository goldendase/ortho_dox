<!--
  NavigationDrawer Component

  Left drawer containing:
  - Mode switcher (Scripture / Library)
  - Tree navigation for Scripture (Testament → Book → Chapter)
  - Tree navigation for Library (recursive TOC)
-->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { layout } from '$lib/stores/layout.svelte';
	import { studyContext } from '$lib/stores/studyContext.svelte';
	import { libraryStore, getTocNodeTitle } from '$lib/stores/library.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import type { Book, TocNode } from '$lib/api';

	interface Props {
		books?: Book[];
		isLibraryMode?: boolean;
	}

	let { books = [], isLibraryMode = false }: Props = $props();

	// Active tab in drawer
	let activeTab = $state<'scripture' | 'library'>(isLibraryMode ? 'library' : 'scripture');

	// Expanded nodes tracking (works for both Scripture and Library)
	// Keys: 'ot', 'nt', book IDs, or library node IDs
	let expandedNodes = $state<Set<string>>(new Set());

	// Track last auto-expanded position to avoid re-expanding on every render
	let lastAutoExpandedBook = $state<string | null>(null);
	let lastAutoExpandedLibraryNode = $state<string | null>(null);

	// Group books by testament
	let oldTestament = $derived(books.filter((b) => b.testament === 'old'));
	let newTestament = $derived(books.filter((b) => b.testament === 'new'));

	// Current scripture position for highlighting and auto-expand
	let currentBook = $derived(studyContext.scripturePosition?.book);
	let currentChapter = $derived(studyContext.scripturePosition?.chapter);

	// Current library position
	let currentLibraryNode = $derived(libraryStore.position?.node);

	// Auto-expand to current scripture position (only when position changes)
	$effect(() => {
		if (currentBook && currentBook !== lastAutoExpandedBook) {
			lastAutoExpandedBook = currentBook;

			const isOld = oldTestament.some((b) => b.id === currentBook);
			const isNew = newTestament.some((b) => b.id === currentBook);

			// Expand testament and book containing current chapter
			const newExpanded = new Set(expandedNodes);
			if (isOld) newExpanded.add('ot');
			if (isNew) newExpanded.add('nt');
			newExpanded.add(currentBook);
			expandedNodes = newExpanded;
		}
	});

	// Auto-expand to current library position (only when position changes)
	$effect(() => {
		if (currentLibraryNode && libraryStore.toc && currentLibraryNode !== lastAutoExpandedLibraryNode) {
			lastAutoExpandedLibraryNode = currentLibraryNode;

			// Find path to current node and expand all ancestors
			const path = findNodePath(libraryStore.toc, currentLibraryNode);
			if (path.length > 0) {
				const newExpanded = new Set(expandedNodes);
				for (const nodeId of path) {
					newExpanded.add(nodeId);
				}
				expandedNodes = newExpanded;
			}
		}
	});

	// Find path from root to target node (returns array of node IDs to expand)
	function findNodePath(node: TocNode, targetId: string, path: string[] = []): string[] {
		if (node.id === targetId) {
			return path;
		}
		if (node.children) {
			for (const child of node.children) {
				const result = findNodePath(child, targetId, [...path, node.id]);
				if (result.length > 0) {
					return result;
				}
			}
		}
		return [];
	}

	// Toggle node expansion
	function toggleNode(nodeId: string) {
		if (expandedNodes.has(nodeId)) {
			expandedNodes.delete(nodeId);
		} else {
			expandedNodes.add(nodeId);
		}
		expandedNodes = new Set(expandedNodes);
	}

	// Navigate to scripture chapter
	function navigateToChapter(bookId: string, chapter: number) {
		goto(`/read/${bookId}/${chapter}`);
		layout.closeDrawer();
	}

	// Navigate to library
	function navigateToLibrary() {
		goto('/library');
		layout.closeDrawer();
	}

	// Navigate to library leaf node
	function navigateToLibraryNode(node: TocNode) {
		if (!libraryStore.currentWork) return;
		goto(`/library/${libraryStore.currentWork.id}/${node.id}`);
		layout.closeDrawer();
	}

	// Handle library node click - expand if container, navigate if leaf
	function handleLibraryNodeClick(node: TocNode) {
		if (node.is_leaf) {
			navigateToLibraryNode(node);
		} else {
			toggleNode(node.id);
		}
	}

	// Generate chapter numbers array for a book
	function getChapters(book: Book): number[] {
		return Array.from({ length: book.chapter_count }, (_, i) => i + 1);
	}
</script>

<div class="nav-drawer">
	<!-- Mode Tabs -->
	<div class="mode-tabs">
		<button
			class="mode-tab"
			class:active={activeTab === 'scripture'}
			onclick={() => (activeTab = 'scripture')}
		>
			<Icon name="book-open" size={16} />
			<span>Scripture</span>
		</button>
		<button
			class="mode-tab"
			class:active={activeTab === 'library'}
			onclick={() => (activeTab = 'library')}
		>
			<Icon name="library" size={16} />
			<span>Library</span>
		</button>
	</div>

	<!-- Content based on active tab -->
	<div class="drawer-content">
		{#if activeTab === 'scripture'}
			<!-- Scripture Tree -->
			<div class="toc-tree">
				<!-- Old Testament -->
				{#if oldTestament.length > 0}
					<div class="tree-node">
						<button
							class="node-header"
							class:expanded={expandedNodes.has('ot')}
							onclick={() => toggleNode('ot')}
							aria-expanded={expandedNodes.has('ot')}
						>
							<Icon name="chevron-right" size={14} class="chevron" />
							<span class="node-label">Old Testament</span>
						</button>
						{#if expandedNodes.has('ot')}
							<div class="node-children">
								{#each oldTestament as book}
									<div class="tree-node">
										<button
											class="node-header"
											class:expanded={expandedNodes.has(book.id)}
											class:active={currentBook === book.id}
											onclick={() => toggleNode(book.id)}
											aria-expanded={expandedNodes.has(book.id)}
										>
											<Icon name="chevron-right" size={12} class="chevron" />
											<span class="node-label">{book.name}</span>
										</button>
										{#if expandedNodes.has(book.id)}
											<div class="node-children">
												{#each getChapters(book) as chapter}
													<button
														class="leaf-node"
														class:active={currentBook === book.id && currentChapter === chapter}
														onclick={() => navigateToChapter(book.id, chapter)}
													>
														Chapter {chapter}
													</button>
												{/each}
											</div>
										{/if}
									</div>
								{/each}
							</div>
						{/if}
					</div>
				{/if}

				<!-- New Testament -->
				{#if newTestament.length > 0}
					<div class="tree-node">
						<button
							class="node-header"
							class:expanded={expandedNodes.has('nt')}
							onclick={() => toggleNode('nt')}
							aria-expanded={expandedNodes.has('nt')}
						>
							<Icon name="chevron-right" size={14} class="chevron" />
							<span class="node-label">New Testament</span>
						</button>
						{#if expandedNodes.has('nt')}
							<div class="node-children">
								{#each newTestament as book}
									<div class="tree-node">
										<button
											class="node-header"
											class:expanded={expandedNodes.has(book.id)}
											class:active={currentBook === book.id}
											onclick={() => toggleNode(book.id)}
											aria-expanded={expandedNodes.has(book.id)}
										>
											<Icon name="chevron-right" size={12} class="chevron" />
											<span class="node-label">{book.name}</span>
										</button>
										{#if expandedNodes.has(book.id)}
											<div class="node-children">
												{#each getChapters(book) as chapter}
													<button
														class="leaf-node"
														class:active={currentBook === book.id && currentChapter === chapter}
														onclick={() => navigateToChapter(book.id, chapter)}
													>
														Chapter {chapter}
													</button>
												{/each}
											</div>
										{/if}
									</div>
								{/each}
							</div>
						{/if}
					</div>
				{/if}
			</div>
		{:else}
			<!-- Library Navigation -->
			<div class="library-nav">
				<button class="library-browse-btn" onclick={navigateToLibrary}>
					<Icon name="grid" size={18} />
					<span>Browse All Works</span>
				</button>

				<!-- Current work TOC (if in library) -->
				{#if libraryStore.currentWork && libraryStore.toc}
					<div class="current-work">
						<h3 class="work-title">{libraryStore.currentWork.title}</h3>
						{#if libraryStore.currentWork.author}
							<p class="work-author">{libraryStore.currentWork.author}</p>
						{/if}

						<div class="toc-tree">
							{#each libraryStore.toc.children ?? [] as node}
								{@render libraryNode(node, 0)}
							{/each}
						</div>
					</div>
				{/if}
			</div>
		{/if}
	</div>
</div>

<!-- Recursive snippet for library TOC nodes -->
{#snippet libraryNode(node: TocNode, depth: number)}
	<div class="tree-node" style="--depth: {depth}">
		{#if node.is_leaf}
			<!-- Leaf node - navigates -->
			<button
				class="leaf-node"
				class:active={currentLibraryNode === node.id}
				onclick={() => navigateToLibraryNode(node)}
			>
				{getTocNodeTitle(node)}
			</button>
		{:else}
			<!-- Container node - expands/collapses -->
			<button
				class="node-header"
				class:expanded={expandedNodes.has(node.id)}
				class:active={currentLibraryNode === node.id}
				onclick={() => toggleNode(node.id)}
				aria-expanded={expandedNodes.has(node.id)}
			>
				<Icon name="chevron-right" size={12} class="chevron" />
				<span class="node-label">{getTocNodeTitle(node)}</span>
			</button>
			{#if expandedNodes.has(node.id) && node.children?.length}
				<div class="node-children">
					{#each node.children as child}
						{@render libraryNode(child, depth + 1)}
					{/each}
				</div>
			{/if}
		{/if}
	</div>
{/snippet}

<style>
	.nav-drawer {
		display: flex;
		flex-direction: column;
		height: 100%;
	}

	.mode-tabs {
		display: flex;
		padding: var(--space-2);
		gap: var(--space-2);
		border-bottom: 1px solid var(--color-border);
		background: var(--color-bg-elevated);
	}

	.mode-tab {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-3);
		border-radius: var(--radius-md);
		color: var(--color-text-secondary);
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		font-weight: var(--font-medium);
		transition: all var(--transition-fast);
	}

	.mode-tab:hover {
		background: var(--color-bg-hover);
		color: var(--color-text-primary);
	}

	.mode-tab.active {
		background: var(--color-gold-dim-bg);
		color: var(--color-gold);
	}

	.drawer-content {
		flex: 1;
		overflow-y: auto;
		padding: var(--space-3);
	}

	/* Tree Structure */
	.toc-tree {
		display: flex;
		flex-direction: column;
	}

	.tree-node {
		display: flex;
		flex-direction: column;
	}

	.node-header {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2);
		border-radius: var(--radius-sm);
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		color: var(--color-text-secondary);
		text-align: left;
		transition: background var(--transition-fast), color var(--transition-fast);
	}

	.node-header:hover {
		background: var(--color-bg-hover);
		color: var(--color-text-primary);
	}

	.node-header.active {
		color: var(--color-gold);
	}

	.node-header :global(.chevron) {
		flex-shrink: 0;
		transition: transform var(--transition-fast);
	}

	.node-header.expanded :global(.chevron) {
		transform: rotate(90deg);
	}

	.node-label {
		flex: 1;
		min-width: 0;
	}

	.node-children {
		padding-left: var(--space-4);
		display: flex;
		flex-direction: column;
	}

	.leaf-node {
		display: block;
		padding: var(--space-1) var(--space-2);
		padding-left: calc(var(--space-4) + var(--space-2));
		border-radius: var(--radius-sm);
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		color: var(--color-text-muted);
		text-align: left;
		transition: background var(--transition-fast), color var(--transition-fast);
	}

	.leaf-node:hover {
		background: var(--color-bg-hover);
		color: var(--color-text-primary);
	}

	.leaf-node.active {
		background: var(--color-gold-dim-bg);
		color: var(--color-gold);
	}

	/* Library Navigation */
	.library-browse-btn {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		width: 100%;
		padding: var(--space-3);
		border-radius: var(--radius-md);
		background: var(--color-bg-elevated);
		color: var(--color-text-primary);
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		font-weight: var(--font-medium);
		transition: background var(--transition-fast);
		margin-bottom: var(--space-4);
	}

	.library-browse-btn:hover {
		background: var(--color-bg-hover);
	}

	.current-work {
		border-top: 1px solid var(--color-border);
		padding-top: var(--space-3);
	}

	.work-title {
		font-family: var(--font-serif);
		font-size: var(--font-base);
		font-weight: var(--font-semibold);
		color: var(--color-text-primary);
		margin-bottom: var(--space-1);
	}

	.work-author {
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		color: var(--color-text-muted);
		margin-bottom: var(--space-3);
	}
</style>
