<!--
  TocNode Component

  Recursive component for rendering a TOC tree node.
  Handles expansion state and navigation.
-->
<script lang="ts">
	import type { TocNode } from '$lib/api';
	import { page } from '$app/stores';
	import { getTocNodeTitle } from '$lib/stores';
	import Icon from '$lib/components/ui/Icon.svelte';

	interface Props {
		node: TocNode;
		workId: string;
		depth?: number;
		onSelect?: () => void;
	}

	let { node, workId, depth = 0, onSelect }: Props = $props();

	// Track expanded state for non-leaf nodes
	let expanded = $state(true); // Default expanded

	const title = $derived(getTocNodeTitle(node));
	const href = $derived(node.is_leaf ? `/library/${workId}/${node.id}` : undefined);

	// Check if this node or any child is currently active
	const isActive = $derived($page.params.node === node.id);
	const hasActiveChild = $derived(checkHasActiveChild(node, $page.params.node));

	function checkHasActiveChild(n: TocNode, activeNodeId: string | undefined): boolean {
		if (!activeNodeId) return false;
		if (n.id === activeNodeId) return true;
		return n.children.some((child) => checkHasActiveChild(child, activeNodeId));
	}

	function handleClick() {
		if (node.is_leaf) {
			onSelect?.();
		} else {
			expanded = !expanded;
		}
	}
</script>

<div class="toc-node" style="--depth: {depth}">
	{#if node.is_leaf}
		<a
			{href}
			class="toc-item"
			class:active={isActive}
			onclick={() => onSelect?.()}
		>
			<span class="toc-title">{title}</span>
		</a>
	{:else}
		<button
			class="toc-item expandable"
			class:expanded
			class:has-active-child={hasActiveChild}
			onclick={handleClick}
		>
			<Icon
				name="chevron-right"
				size={14}
				class="expand-icon"
			/>
			<span class="toc-title">{title}</span>
		</button>

		{#if expanded && node.children.length > 0}
			<div class="toc-children">
				{#each node.children as child (child.id)}
					<svelte:self node={child} {workId} depth={depth + 1} {onSelect} />
				{/each}
			</div>
		{/if}
	{/if}
</div>

<style>
	.toc-node {
		--indent: calc(var(--depth) * var(--space-4));
	}

	.toc-item {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		width: 100%;
		padding: var(--space-2) var(--space-3);
		padding-left: calc(var(--space-3) + var(--indent));
		font-size: var(--font-sm);
		font-family: var(--font-ui);
		color: var(--color-text-secondary);
		text-decoration: none;
		text-align: left;
		background: transparent;
		border: none;
		border-radius: var(--radius-sm);
		cursor: pointer;
		transition: background var(--transition-fast), color var(--transition-fast);
	}

	.toc-item:hover {
		background: var(--color-bg-hover);
		color: var(--color-text-primary);
	}

	.toc-item.active {
		background: var(--color-gold-dim-bg);
		color: var(--color-gold);
	}

	.toc-item.has-active-child {
		color: var(--color-text-primary);
	}

	.toc-item.expandable {
		font-weight: var(--font-medium);
	}

	.toc-title {
		flex: 1;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.toc-item :global(.expand-icon) {
		flex-shrink: 0;
		transition: transform var(--transition-fast);
	}

	.toc-item.expanded :global(.expand-icon) {
		transform: rotate(90deg);
	}

	.toc-children {
		/* Children are indented via --depth variable */
	}
</style>
