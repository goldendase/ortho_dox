<!--
  TocDrawer Component

  Left-side drawer showing the table of contents for a library work.
  Similar pattern to BookPicker but for library navigation.
-->
<script lang="ts">
	import type { TocNode as TocNodeType, LibraryWorkDetail } from '$lib/api';
	import TocNode from './TocNode.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';

	interface Props {
		work: LibraryWorkDetail;
		toc: TocNodeType;
		workId: string;
		onClose?: () => void;
	}

	let { work, toc, workId, onClose }: Props = $props();
</script>

<div class="toc-drawer">
	<header class="drawer-header">
		<h2 class="work-title">{work.title}</h2>
		{#if work.author}
			<p class="work-author">{work.author}</p>
		{/if}
	</header>

	<nav class="toc-nav">
		<h3 class="toc-heading">Contents</h3>
		<div class="toc-tree">
			{#if toc.children && toc.children.length > 0}
				{#each toc.children as node (node.id)}
					<TocNode {node} {workId} onSelect={onClose} />
				{/each}
			{:else if toc.is_leaf}
				<!-- Root is a single leaf node - show it directly -->
				<TocNode node={toc} {workId} onSelect={onClose} />
			{:else}
				<p class="empty-toc">No table of contents available</p>
			{/if}
		</div>
	</nav>

	<footer class="drawer-footer">
		<a href="/library" class="back-link">
			<Icon name="arrow-left" size={16} />
			<span>Library</span>
		</a>
	</footer>
</div>

<style>
	.toc-drawer {
		display: flex;
		flex-direction: column;
		height: 100%;
		background: var(--color-bg-surface);
	}

	.drawer-header {
		flex-shrink: 0;
		padding: var(--space-4);
		border-bottom: 1px solid var(--color-border);
	}

	.work-title {
		font-size: var(--font-base);
		font-weight: var(--font-medium);
		color: var(--color-text-primary);
		margin: 0 0 var(--space-1);
		line-height: var(--line-height-tight);
	}

	.work-author {
		font-size: var(--font-sm);
		color: var(--color-text-secondary);
		margin: 0;
	}

	.toc-nav {
		flex: 1;
		overflow-y: auto;
		min-height: 0;
	}

	.toc-heading {
		padding: var(--space-3) var(--space-4);
		font-size: var(--font-xs);
		font-family: var(--font-ui);
		font-weight: var(--font-medium);
		text-transform: uppercase;
		letter-spacing: var(--tracking-wide);
		color: var(--color-text-muted);
		margin: 0;
	}

	.toc-tree {
		padding: 0 var(--space-2) var(--space-4);
	}

	.empty-toc {
		padding: var(--space-4);
		font-size: var(--font-sm);
		font-family: var(--font-ui);
		color: var(--color-text-muted);
		text-align: center;
	}

	.drawer-footer {
		flex-shrink: 0;
		padding: var(--space-4);
		border-top: 1px solid var(--color-border);
		background: var(--color-bg-surface);
	}

	.back-link {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		font-size: var(--font-sm);
		font-family: var(--font-ui);
		color: var(--color-gold);
		text-decoration: none;
		transition: opacity var(--transition-fast);
	}

	.back-link:hover {
		opacity: 0.8;
	}
</style>
