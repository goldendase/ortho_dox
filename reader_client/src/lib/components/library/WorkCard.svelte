<!--
  WorkCard Component

  Displays a library work in the browse list with:
  - Title and subtitle
  - Author(s)
  - Category badge
  - Subject tags (optional)
-->
<script lang="ts">
	import type { LibraryWorkSummary } from '$lib/api';
	import Icon from '$lib/components/ui/Icon.svelte';

	interface Props {
		work: LibraryWorkSummary;
		href?: string;
	}

	let { work, href = `/library/${work.id}` }: Props = $props();

	// Category display names
	const categoryLabels: Record<string, string> = {
		patristic: 'Patristic',
		biography: 'Biography',
		church_history: 'Church History',
		spiritual: 'Spiritual',
		liturgical: 'Liturgical',
		theological: 'Theological'
	};

	const categoryLabel = $derived(categoryLabels[work.category] || work.category);
	const primaryAuthor = $derived(work.authors.find((a) => a.role === 'author') || work.authors[0]);
</script>

<a {href} class="work-card">
	<div class="work-header">
		<span class="category-badge">{categoryLabel}</span>
		{#if work.has_images}
			<Icon name="image" size={14} />
		{/if}
	</div>

	<h3 class="work-title">{work.title}</h3>

	{#if work.subtitle}
		<p class="work-subtitle">{work.subtitle}</p>
	{/if}

	{#if primaryAuthor}
		<p class="work-author">
			{primaryAuthor.name}
			{#if primaryAuthor.dates}
				<span class="author-dates">({primaryAuthor.dates})</span>
			{/if}
		</p>
	{/if}

	{#if work.subjects.length > 0}
		<div class="work-subjects">
			{#each work.subjects.slice(0, 3) as subject}
				<span class="subject-tag">{subject}</span>
			{/each}
			{#if work.subjects.length > 3}
				<span class="subject-tag more">+{work.subjects.length - 3}</span>
			{/if}
		</div>
	{/if}

	<div class="work-meta">
		<span class="meta-item">
			<Icon name="list" size={12} />
			{work.node_count} sections
		</span>
	</div>
</a>

<style>
	.work-card {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		padding: var(--space-4);
		background: var(--color-bg-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-lg);
		text-decoration: none;
		color: inherit;
		transition:
			background var(--transition-fast),
			border-color var(--transition-fast),
			transform var(--transition-fast);
	}

	.work-card:hover {
		background: var(--color-bg-hover);
		border-color: var(--color-gold-dim);
		transform: translateY(-2px);
	}

	.work-header {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		color: var(--color-text-muted);
	}

	.category-badge {
		font-size: var(--font-xs);
		font-family: var(--font-ui);
		text-transform: uppercase;
		letter-spacing: var(--tracking-wide);
		color: var(--color-gold);
		background: var(--color-gold-dim-bg);
		padding: var(--space-1) var(--space-2);
		border-radius: var(--radius-sm);
	}

	.work-title {
		font-size: var(--font-lg);
		font-weight: var(--font-medium);
		color: var(--color-text-primary);
		line-height: var(--line-height-tight);
		margin: 0;
	}

	.work-subtitle {
		font-size: var(--font-sm);
		color: var(--color-text-secondary);
		margin: 0;
		line-height: var(--line-height-normal);
	}

	.work-author {
		font-size: var(--font-sm);
		color: var(--color-text-secondary);
		margin: 0;
		font-family: var(--font-ui);
	}

	.author-dates {
		color: var(--color-text-muted);
	}

	.work-subjects {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-1);
		margin-top: var(--space-1);
	}

	.subject-tag {
		font-size: var(--font-xs);
		font-family: var(--font-ui);
		color: var(--color-text-muted);
		background: var(--color-bg-elevated);
		padding: 2px var(--space-2);
		border-radius: var(--radius-sm);
	}

	.subject-tag.more {
		color: var(--color-text-secondary);
	}

	.work-meta {
		display: flex;
		gap: var(--space-3);
		margin-top: auto;
		padding-top: var(--space-2);
		border-top: 1px solid var(--color-border);
	}

	.meta-item {
		display: flex;
		align-items: center;
		gap: var(--space-1);
		font-size: var(--font-xs);
		font-family: var(--font-ui);
		color: var(--color-text-muted);
	}
</style>
