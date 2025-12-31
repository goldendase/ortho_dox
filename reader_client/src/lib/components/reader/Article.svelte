<!--
  Article Component

  Displays a study article (appears before its associated verse).
  These are topical studies like "CREATION", "TRINITY", etc.
  Collapsed by default, expandable on click.
-->
<script lang="ts">
	import type { Article } from '$lib/api';

	interface Props {
		article: Article;
	}

	let { article }: Props = $props();

	// Collapsed by default
	let isExpanded = $state(false);

	// Extract title from article text (usually first line in caps)
	// Article text format is typically "TITLE\n\nBody text..."
	const parts = $derived(() => {
		const text = article.text;
		const firstNewline = text.indexOf('\n');
		if (firstNewline > 0 && firstNewline < 50) {
			const title = text.slice(0, firstNewline).trim();
			const body = text.slice(firstNewline).trim();
			// Check if title looks like a title (mostly uppercase)
			if (title === title.toUpperCase() && title.length > 2) {
				return { title, body };
			}
		}
		// Fallback: use "Study Article" as title, full text as body
		return { title: 'Study Article', body: text };
	});

	function toggle() {
		isExpanded = !isExpanded;
	}
</script>

<aside class="article" class:expanded={isExpanded} id="article-{article.id}">
	<div class="article-border"></div>
	<div class="article-content">
		<button class="article-header" onclick={toggle} aria-expanded={isExpanded}>
			<span class="article-label">Article:</span>
			<span class="article-title">{parts().title}</span>
			<span class="article-chevron">{isExpanded ? '▾' : '▸'}</span>
		</button>
		{#if isExpanded}
			<div class="article-body scripture-text">
				{@html parts().body}
			</div>
		{/if}
	</div>
</aside>

<style>
	.article {
		display: flex;
		gap: var(--space-4);
		margin: var(--space-4) 0;
		padding: var(--space-2) 0;
	}

	.article.expanded {
		margin: var(--space-6) 0;
		padding: var(--space-4) 0;
	}

	.article-border {
		width: 3px;
		background: linear-gradient(
			to bottom,
			var(--color-gold-dim),
			var(--color-burgundy-dark)
		);
		border-radius: var(--radius-full);
		flex-shrink: 0;
	}

	.article-content {
		flex: 1;
	}

	.article-header {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		width: 100%;
		padding: 0;
		border: none;
		background: none;
		cursor: pointer;
		text-align: left;
		font-family: var(--font-ui);
	}

	.article-header:hover .article-title {
		color: var(--color-gold);
	}

	.article-label {
		font-size: var(--font-xs);
		color: var(--color-text-muted);
		text-transform: uppercase;
		letter-spacing: var(--tracking-wide);
	}

	.article-title {
		font-size: var(--font-sm);
		font-weight: var(--font-semibold);
		letter-spacing: var(--tracking-wider);
		color: var(--color-gold-dim);
		text-transform: uppercase;
		transition: color var(--transition-fast);
	}

	.article-chevron {
		font-size: var(--font-xs);
		color: var(--color-text-muted);
		margin-left: auto;
	}

	.article-body {
		font-size: var(--text-size, 1rem);
		color: var(--color-text-secondary);
		line-height: var(--leading-relaxed);
		white-space: pre-wrap;
		margin-top: var(--space-3);
	}
</style>
