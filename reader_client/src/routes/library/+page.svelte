<!--
  Library Browse Page

  Displays a grid of available works with category filtering.
-->
<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import WorkCard from '$lib/components/library/WorkCard.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';

	let { data } = $props();

	const categories = [
		{ value: '', label: 'All' },
		{ value: 'patristic', label: 'Patristic' },
		{ value: 'biography', label: 'Biography' },
		{ value: 'church_history', label: 'Church History' },
		{ value: 'spiritual', label: 'Spiritual' },
		{ value: 'liturgical', label: 'Liturgical' },
		{ value: 'theological', label: 'Theological' }
	];

	function handleCategoryChange(category: string) {
		const url = new URL($page.url);
		if (category) {
			url.searchParams.set('category', category);
		} else {
			url.searchParams.delete('category');
		}
		goto(url.toString());
	}
</script>

<svelte:head>
	<title>Library | Orthodox Reader</title>
</svelte:head>

<div class="library-page">
	<header class="page-header">
		<div class="header-content">
			<h1 class="page-title">
				<Icon name="library" size={24} />
				Theological Library
			</h1>
			<p class="page-description">
				Explore patristic writings, saints' biographies, and spiritual texts
			</p>
		</div>

		<div class="filters">
			<div class="category-filter">
				{#each categories as cat}
					<button
						class="category-btn"
						class:active={data.category === cat.value || (!data.category && cat.value === '')}
						onclick={() => handleCategoryChange(cat.value)}
					>
						{cat.label}
					</button>
				{/each}
			</div>
		</div>
	</header>

	<div class="works-grid">
		{#if data.works.length === 0}
			<div class="empty-state">
				<Icon name="book-open" size={48} />
				<p>No works found</p>
				{#if data.category}
					<button class="clear-filter" onclick={() => handleCategoryChange('')}>
						Clear filter
					</button>
				{/if}
			</div>
		{:else}
			{#each data.works as work (work.id)}
				<WorkCard {work} />
			{/each}
		{/if}
	</div>

	{#if data.total > data.works.length}
		<div class="pagination-hint">
			Showing {data.works.length} of {data.total} works
		</div>
	{/if}
</div>

<style>
	.library-page {
		padding: var(--space-6);
		max-width: 1200px;
		margin: 0 auto;
	}

	.page-header {
		margin-bottom: var(--space-6);
	}

	.header-content {
		margin-bottom: var(--space-4);
	}

	.page-title {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		font-size: var(--font-2xl);
		font-weight: var(--font-medium);
		color: var(--color-gold);
		margin: 0 0 var(--space-2);
	}

	.page-description {
		font-size: var(--font-base);
		color: var(--color-text-secondary);
		margin: 0;
	}

	.filters {
		display: flex;
		gap: var(--space-4);
		flex-wrap: wrap;
	}

	.category-filter {
		display: flex;
		gap: var(--space-2);
		flex-wrap: wrap;
	}

	.category-btn {
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-sm);
		font-family: var(--font-ui);
		color: var(--color-text-secondary);
		background: var(--color-bg-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		cursor: pointer;
		transition:
			background var(--transition-fast),
			color var(--transition-fast),
			border-color var(--transition-fast);
	}

	.category-btn:hover {
		background: var(--color-bg-hover);
		color: var(--color-text-primary);
	}

	.category-btn.active {
		background: var(--color-gold-dim-bg);
		color: var(--color-gold);
		border-color: var(--color-gold-dim);
	}

	.works-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
		gap: var(--space-4);
	}

	.empty-state {
		grid-column: 1 / -1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: var(--space-3);
		padding: var(--space-8);
		color: var(--color-text-muted);
		text-align: center;
	}

	.clear-filter {
		padding: var(--space-2) var(--space-4);
		font-size: var(--font-sm);
		color: var(--color-gold);
		background: transparent;
		border: 1px solid var(--color-gold-dim);
		border-radius: var(--radius-md);
		cursor: pointer;
	}

	.clear-filter:hover {
		background: var(--color-gold-dim-bg);
	}

	.pagination-hint {
		margin-top: var(--space-6);
		text-align: center;
		font-size: var(--font-sm);
		color: var(--color-text-muted);
	}

	@media (max-width: 768px) {
		.library-page {
			padding: var(--space-4);
		}

		.page-title {
			font-size: var(--font-xl);
		}

		.category-filter {
			overflow-x: auto;
			flex-wrap: nowrap;
			padding-bottom: var(--space-2);
			-webkit-overflow-scrolling: touch;
		}

		.category-btn {
			flex-shrink: 0;
		}

		.works-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
