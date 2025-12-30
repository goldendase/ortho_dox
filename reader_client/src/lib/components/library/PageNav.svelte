<!--
  PageNav Component

  Shows prev/next chapter navigation at the bottom of the reader.
-->
<script lang="ts">
	import type { LibraryNodeNavigation } from '$lib/api';
	import Icon from '$lib/components/ui/Icon.svelte';

	interface Props {
		navigation?: LibraryNodeNavigation;
		workId: string;
	}

	let { navigation, workId }: Props = $props();

	const prevNodeHref = $derived(
		navigation?.prev ? `/library/${workId}/${navigation.prev.id}` : null
	);
	const nextNodeHref = $derived(
		navigation?.next ? `/library/${workId}/${navigation.next.id}` : null
	);
</script>

<nav class="page-nav">
	<div class="nav-controls">
		<!-- Previous chapter -->
		{#if prevNodeHref}
			<a href={prevNodeHref} class="nav-btn" aria-label="Previous section">
				<Icon name="chevron-left" size={20} />
				<span class="nav-label">{navigation?.prev?.title || navigation?.prev?.label || 'Previous'}</span>
			</a>
		{:else}
			<div class="nav-btn disabled">
				<Icon name="chevron-left" size={20} />
			</div>
		{/if}

		<!-- Spacer -->
		<div class="spacer"></div>

		<!-- Next chapter -->
		{#if nextNodeHref}
			<a href={nextNodeHref} class="nav-btn" aria-label="Next section">
				<span class="nav-label">{navigation?.next?.title || navigation?.next?.label || 'Next'}</span>
				<Icon name="chevron-right" size={20} />
			</a>
		{:else}
			<div class="nav-btn disabled">
				<Icon name="chevron-right" size={20} />
			</div>
		{/if}
	</div>
</nav>

<style>
	.page-nav {
		display: flex;
		justify-content: center;
		margin-top: var(--space-8);
		padding-top: var(--space-6);
		border-top: 1px solid var(--color-border);
	}

	.nav-controls {
		display: flex;
		align-items: center;
		gap: var(--space-4);
		width: 100%;
		max-width: 50rem;
	}

	.spacer {
		flex: 1;
	}

	.nav-btn {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-3);
		min-width: var(--touch-min);
		min-height: var(--touch-min);
		color: var(--color-text-secondary);
		background: transparent;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		text-decoration: none;
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		cursor: pointer;
		transition:
			background var(--transition-fast),
			color var(--transition-fast),
			border-color var(--transition-fast);
	}

	.nav-btn:hover:not(.disabled) {
		background: var(--color-bg-hover);
		color: var(--color-text-primary);
		border-color: var(--color-gold-dim);
	}

	.nav-btn.disabled {
		opacity: 0.3;
		cursor: not-allowed;
	}

	.nav-label {
		max-width: 12rem;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	@media (max-width: 768px) {
		.nav-label {
			max-width: 6rem;
		}

		.nav-btn {
			padding: var(--space-2);
		}
	}
</style>
