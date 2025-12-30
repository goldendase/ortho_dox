<!--
  Chapter Navigation Component

  Previous/Next chapter buttons at the bottom of the reader.
-->
<script lang="ts">
	import Icon from '$lib/components/ui/Icon.svelte';

	interface Props {
		prevChapter: string | null;
		nextChapter: string | null;
		onNavigate: (url: string) => void;
	}

	let { prevChapter, nextChapter, onNavigate }: Props = $props();

	function extractChapterInfo(url: string | null): string | null {
		if (!url) return null;
		// URL format: /books/genesis/chapters/2/passages
		const match = url.match(/\/books\/([^/]+)\/chapters\/(\d+)/);
		if (match) {
			// Capitalize first letter of book name
			const book = match[1].charAt(0).toUpperCase() + match[1].slice(1);
			return `${book} ${match[2]}`;
		}
		return null;
	}

	const prevLabel = $derived(extractChapterInfo(prevChapter));
	const nextLabel = $derived(extractChapterInfo(nextChapter));
</script>

<nav class="chapter-nav">
	<button
		class="nav-button prev touch-target"
		disabled={!prevChapter}
		onclick={() => prevChapter && onNavigate(prevChapter)}
		aria-label={prevLabel ? `Previous: ${prevLabel}` : 'No previous chapter'}
	>
		<Icon name="chevron-left" size={20} />
		<span class="nav-text">
			{#if prevLabel}
				<span class="nav-label text-muted">Previous</span>
				<span class="nav-chapter">{prevLabel}</span>
			{:else}
				<span class="nav-label text-muted">Beginning</span>
			{/if}
		</span>
	</button>

	<button
		class="nav-button next touch-target"
		disabled={!nextChapter}
		onclick={() => nextChapter && onNavigate(nextChapter)}
		aria-label={nextLabel ? `Next: ${nextLabel}` : 'No next chapter'}
	>
		<span class="nav-text">
			{#if nextLabel}
				<span class="nav-label text-muted">Next</span>
				<span class="nav-chapter">{nextLabel}</span>
			{:else}
				<span class="nav-label text-muted">End</span>
			{/if}
		</span>
		<Icon name="chevron-right" size={20} />
	</button>
</nav>

<style>
	.chapter-nav {
		display: flex;
		justify-content: space-between;
		gap: var(--space-4);
		margin-top: var(--space-4);
		padding-top: var(--space-4);
		border-top: 1px solid var(--color-border);
	}

	.nav-button {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-3) var(--space-4);
		border-radius: var(--radius-md);
		color: var(--color-text-secondary);
		transition:
			background var(--transition-fast),
			color var(--transition-fast);
	}

	.nav-button:hover:not(:disabled) {
		background: var(--color-bg-hover);
		color: var(--color-text-primary);
	}

	.nav-button:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.nav-button.prev {
		margin-right: auto;
	}

	.nav-button.next {
		margin-left: auto;
	}

	.nav-text {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.nav-button.prev .nav-text {
		align-items: flex-start;
	}

	.nav-button.next .nav-text {
		align-items: flex-end;
	}

	.nav-label {
		font-family: var(--font-ui);
		font-size: var(--font-xs);
		text-transform: uppercase;
		letter-spacing: var(--tracking-wide);
	}

	.nav-chapter {
		font-family: var(--font-body);
		font-size: var(--font-base);
		color: var(--color-text-primary);
	}
</style>
