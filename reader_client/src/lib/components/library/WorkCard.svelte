<!--
  WorkCard Component

  Displays a library work in brief or expanded mode.
  - Brief: title, author, era badge, work type badge
  - Expanded: + description, contributors, reading level, "Begin Reading"
-->
<script lang="ts">
	import type { LibraryWorkSummary } from '$lib/api/types';
	import Icon from '$lib/components/ui/Icon.svelte';
	import { getToc } from '$lib/api';
	import { libraryStore, findFirstLeafNode, workPositionToPath } from '$lib/stores/library.svelte';

	interface Props {
		work: LibraryWorkSummary;
		expanded?: boolean;
		onToggle?: () => void;
	}

	let { work, expanded = false, onToggle }: Props = $props();

	// Era display config
	const eraConfig: Record<string, { label: string; className: string }> = {
		apostolic: { label: 'Apostolic', className: 'era-apostolic' },
		nicene: { label: 'Nicene', className: 'era-nicene' },
		byzantine: { label: 'Byzantine', className: 'era-byzantine' },
		early_modern: { label: 'Early Modern', className: 'era-early-modern' },
		modern: { label: 'Modern', className: 'era-modern' }
	};

	// Work type display names
	const workTypeLabels: Record<string, string> = {
		commentary: 'Commentary',
		ascetical: 'Ascetical',
		pastoral: 'Pastoral',
		doctrinal: 'Doctrinal',
		historical: 'Historical'
	};

	// Reading level as dot count (difficulty)
	const readingLevelDots: Record<string, number> = {
		inquirer: 1,
		catechumen: 2,
		faithful: 3,
		scholar: 4
	};

	// Contributor role display names
	const roleLabels: Record<string, string> = {
		translator: 'Translated by',
		editor: 'Edited by',
		compiler: 'Compiled by'
	};

	const era = $derived(eraConfig[work.era] || { label: work.era, className: '' });
	const workTypeLabel = $derived(workTypeLabels[work.work_type] || work.work_type);
	const difficultyDots = $derived(readingLevelDots[work.reading_level] || 1);

	// Check for saved reading position (reads fresh from localStorage)
	const savedPosition = $derived(libraryStore.getWorkPosition(work.id));
	const hasProgress = $derived(!!savedPosition);

	// Reading path: use saved position if available, otherwise load first leaf when expanded
	let firstLeafPath = $state<string | null>(null);

	// Compute reading path: prefer saved position, fall back to first leaf
	const readingPath = $derived(
		savedPosition
			? workPositionToPath(work.id, savedPosition)
			: firstLeafPath
	);

	// Load first leaf only when expanded and no saved position
	$effect(() => {
		if (expanded && !savedPosition && !firstLeafPath) {
			loadFirstLeaf();
		}
	});

	async function loadFirstLeaf() {
		try {
			const toc = await getToc(work.id);
			if (toc?.root) {
				const firstLeaf = findFirstLeafNode(toc.root);
				if (firstLeaf) {
					firstLeafPath = `/library/${work.id}/${firstLeaf.id}`;
				}
			}
		} catch (e) {
			// Fallback to work page
			firstLeafPath = `/library/${work.id}`;
		}
	}

	function handleCardClick(e: MouseEvent) {
		// Don't toggle if clicking a link or button
		const target = e.target as HTMLElement;
		if (target.closest('a') || target.closest('button')) {
			return;
		}
		onToggle?.();
	}

	function handleKeyDown(e: KeyboardEvent) {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			onToggle?.();
		}
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="work-card"
	class:expanded
	onclick={handleCardClick}
	onkeydown={handleKeyDown}
	tabindex="0"
	role="button"
	aria-expanded={expanded}
>
	<!-- Header with badges -->
	<div class="card-header">
		<span class="era-badge {era.className}">{era.label}</span>
		<span class="type-badge">{workTypeLabel}</span>
		{#if work.has_images}
			<Icon name="image" size={14} />
		{/if}
	</div>

	<!-- Title -->
	<h3 class="work-title">{work.title}</h3>

	<!-- Author -->
	<p class="work-author">{work.author}</p>

	<!-- Expanded content -->
	{#if expanded}
		<div class="expanded-content">
			<!-- Subtitle (only in expanded view) -->
			{#if work.subtitle}
				<p class="work-subtitle">{work.subtitle}</p>
			{/if}
			<!-- Description -->
			{#if work.description}
				<p class="work-description">{work.description}</p>
			{/if}

			<!-- Notes (edition/translation caveats) -->
			{#if work.notes}
				<p class="work-notes">{work.notes}</p>
			{/if}

			<!-- Contributors -->
			{#if work.contributors.length > 0}
				<div class="contributors">
					{#each work.contributors as contributor}
						<span class="contributor">
							{roleLabels[contributor.role] || contributor.role} {contributor.name}
						</span>
					{/each}
				</div>
			{/if}

			<!-- Meta info -->
			<div class="work-meta">
				<span class="meta-item difficulty-indicator" title="Difficulty">
					{#each Array(difficultyDots) as _}
						<span class="difficulty-dot filled"></span>
					{/each}
					{#each Array(4 - difficultyDots) as _}
						<span class="difficulty-dot"></span>
					{/each}
				</span>
				<span class="meta-item">
					<Icon name="list" size={14} />
					{work.node_count} sections
				</span>
			</div>

			<!-- Actions -->
			<div class="card-actions">
				<a
					href={readingPath || `/library/${work.id}`}
					class="begin-reading-btn"
				>
					{hasProgress ? 'Continue Reading' : 'Begin Reading'}
					<Icon name="arrow-right" size={16} />
				</a>
			</div>
		</div>
	{/if}
</div>

<style>
	.work-card {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		padding: var(--space-4);
		background: var(--color-bg-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-lg);
		cursor: pointer;
		transition:
			background var(--transition-fast),
			border-color var(--transition-fast),
			box-shadow var(--transition-fast);
	}

	.work-card:hover {
		background: var(--color-bg-hover);
		border-color: var(--color-gold-dim);
	}

	.work-card:focus-visible {
		outline: 2px solid var(--color-gold);
		outline-offset: 2px;
	}

	.work-card.expanded {
		background: var(--color-bg-elevated);
		border-color: var(--color-gold-dim);
		box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
	}

	.card-header {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		color: var(--color-text-muted);
	}

	.era-badge {
		font-size: var(--font-xs);
		font-family: var(--font-ui);
		text-transform: uppercase;
		letter-spacing: var(--tracking-wide);
		padding: var(--space-1) var(--space-2);
		border-radius: var(--radius-sm);
	}

	/* Era color coding */
	.era-apostolic {
		color: var(--color-gold);
		background: var(--color-gold-dim-bg);
	}

	.era-nicene {
		color: #7b9ec9;
		background: rgba(123, 158, 201, 0.15);
	}

	.era-byzantine {
		color: var(--color-burgundy-light);
		background: rgba(147, 64, 72, 0.15);
	}

	.era-early-modern {
		color: #b8a070;
		background: rgba(184, 160, 112, 0.12);
	}

	.era-modern {
		color: var(--color-text-secondary);
		background: var(--color-bg-elevated);
	}

	.type-badge {
		font-size: var(--font-xs);
		font-family: var(--font-ui);
		color: var(--color-text-muted);
		padding: var(--space-1) var(--space-2);
		background: var(--color-bg-elevated);
		border-radius: var(--radius-sm);
	}

	.work-title {
		font-size: var(--text-size, 1.125rem);
		font-weight: var(--font-medium);
		color: var(--color-text-primary);
		line-height: var(--line-height-tight);
		margin: 0;
		transition: color var(--transition-fast);
	}

	.work-card:hover .work-title {
		color: var(--color-gold);
	}

	.work-subtitle {
		font-size: calc(var(--text-size, 1rem) * 0.9);
		color: var(--color-text-secondary);
		margin: 0;
		line-height: var(--line-height-normal);
		font-style: italic;
	}

	.work-author {
		font-size: calc(var(--text-size, 1rem) * 0.9);
		color: var(--color-text-secondary);
		margin: 0;
		font-family: var(--font-ui);
	}

	/* Expanded content */
	.expanded-content {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		margin-top: var(--space-3);
		padding-top: var(--space-3);
		border-top: 1px solid var(--color-border);
		animation: fadeIn 0.2s ease-out;
	}

	@keyframes fadeIn {
		from {
			opacity: 0;
			transform: translateY(-8px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.work-description {
		font-size: calc(var(--text-size, 1rem) * 0.9);
		color: var(--color-text-secondary);
		margin: 0;
		line-height: var(--line-height-normal);
	}

	.work-notes {
		font-size: calc(var(--text-size, 1rem) * 0.9);
		color: var(--color-text-muted);
		margin: 0;
		line-height: var(--line-height-normal);
		font-style: italic;
		padding-left: var(--space-3);
		border-left: 2px solid var(--color-border);
	}

	.contributors {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.contributor {
		font-size: var(--font-sm);
		font-family: var(--font-ui);
		color: var(--color-text-muted);
	}

	.work-meta {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-3);
	}

	.meta-item {
		display: flex;
		align-items: center;
		gap: var(--space-1);
		font-size: var(--font-xs);
		font-family: var(--font-ui);
		color: var(--color-text-muted);
	}

	.difficulty-indicator {
		gap: 3px;
	}

	.difficulty-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--color-bg-elevated);
		border: 1px solid var(--color-border);
	}

	.difficulty-dot.filled {
		background: var(--color-gold);
		border-color: var(--color-gold);
	}

	.card-actions {
		margin-top: var(--space-2);
	}

	.begin-reading-btn {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-4);
		font-size: var(--font-sm);
		font-family: var(--font-ui);
		font-weight: var(--font-medium);
		color: var(--color-bg-base);
		background: var(--color-gold);
		border: none;
		border-radius: var(--radius-md);
		text-decoration: none;
		cursor: pointer;
		transition:
			background var(--transition-fast),
			transform var(--transition-fast);
	}

	.begin-reading-btn:hover {
		background: var(--color-gold-bright);
		transform: translateX(2px);
	}
</style>
