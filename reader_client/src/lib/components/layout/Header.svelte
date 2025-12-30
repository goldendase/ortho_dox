<!--
  Header Component (New Architecture)

  Minimal header with:
  - Hamburger menu (opens navigation drawer)
  - Current position display (clickable for quick nav)
  - Prev/Next navigation arrows
  - Overflow menu
-->
<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { layout } from '$lib/stores/layout.svelte';
	import { studyContext, formatPosition } from '$lib/stores/studyContext.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import type { Book } from '$lib/api';

	interface Props {
		books?: Book[];
	}

	let { books = [] }: Props = $props();

	// Current position display
	let positionText = $derived(() => {
		const pos = studyContext.position;
		if (!pos) return 'Select Reading';
		return formatPosition(pos);
	});

	// Determine if we're in scripture or library mode
	let isScriptureMode = $derived(studyContext.mode === 'scripture');
	let isLibraryMode = $derived(studyContext.mode === 'library');

	// Navigation handlers
	function handlePrev() {
		if (studyContext.prevLink) {
			goto(studyContext.prevLink);
		}
	}

	function handleNext() {
		if (studyContext.nextLink) {
			goto(studyContext.nextLink);
		}
	}

</script>

<header class="header">
	<div class="header-left">
		<!-- Hamburger menu -->
		<button
			class="icon-btn touch-target"
			onclick={() => layout.toggleDrawer()}
			aria-label="Toggle navigation"
		>
			<Icon name="menu" size={20} />
		</button>
	</div>

	<div class="header-center">
		<!-- Position display -->
		<button class="position-display touch-target" onclick={() => layout.openDrawer()}>
			{#if isScriptureMode}
				<Icon name="book-open" size={16} />
			{:else if isLibraryMode}
				<Icon name="library" size={16} />
			{:else}
				<Icon name="book" size={16} />
			{/if}
			<span class="position-text">{positionText()}</span>
		</button>
	</div>

	<div class="header-right">
		<!-- Prev/Next navigation -->
		<button
			class="icon-btn touch-target"
			onclick={handlePrev}
			disabled={!studyContext.canGoPrev}
			aria-label="Previous"
		>
			<Icon name="chevron-left" size={20} />
		</button>
		<button
			class="icon-btn touch-target"
			onclick={handleNext}
			disabled={!studyContext.canGoNext}
			aria-label="Next"
		>
			<Icon name="chevron-right" size={20} />
		</button>
	</div>
</header>

<style>
	.header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 var(--space-2);
		background: var(--color-bg-surface);
		border-bottom: 1px solid var(--color-border);
		height: var(--header-height);
		gap: var(--space-2);
	}

	.header-left,
	.header-right {
		display: flex;
		align-items: center;
		gap: var(--space-1);
	}

	.header-center {
		flex: 1;
		display: flex;
		justify-content: center;
		min-width: 0;
	}

	.icon-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 40px;
		height: 40px;
		border-radius: var(--radius-md);
		color: var(--color-text-secondary);
		transition: background var(--transition-fast), color var(--transition-fast);
	}

	.icon-btn:hover:not(:disabled) {
		background: var(--color-bg-hover);
		color: var(--color-text-primary);
	}

	.icon-btn:disabled {
		opacity: 0.3;
		cursor: not-allowed;
	}

	.position-display {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-3);
		border-radius: var(--radius-md);
		color: var(--color-text-primary);
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		font-weight: var(--font-medium);
		transition: background var(--transition-fast);
		max-width: 100%;
	}

	.position-display:hover {
		background: var(--color-bg-hover);
	}

	.position-text {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	@media (max-width: 768px) {
		.header {
			padding: 0 var(--space-2);
		}

		.position-display {
			padding: var(--space-2);
		}
	}
</style>
