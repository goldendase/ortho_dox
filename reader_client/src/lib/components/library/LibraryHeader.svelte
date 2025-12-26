<!--
  LibraryHeader Component

  Header for library reading mode with:
  - TOC toggle
  - Current position (node title)
  - Text size control
  - Link to OSB mode
-->
<script lang="ts">
	import type { LibraryWork, LibraryNodeLeaf } from '$lib/api';
	import { libraryStore, reader } from '$lib/stores';
	import Icon from '$lib/components/ui/Icon.svelte';

	interface Props {
		work: LibraryWork;
		node: LibraryNodeLeaf;
	}

	let { work, node }: Props = $props();

	const nodeTitle = $derived(node.title || node.label || 'Reading');

	// Link to OSB - go to last position or default
	const osbHref = $derived(
		reader.position
			? `/read/${reader.position.book}/${reader.position.chapter}`
			: '/read/genesis/1'
	);
</script>

<header class="library-header">
	<div class="header-left">
		<button
			class="toc-toggle touch-target"
			onclick={() => libraryStore.toggleToc()}
			aria-label="Toggle table of contents"
			aria-expanded={libraryStore.tocOpen}
		>
			<Icon name="menu" size={20} />
		</button>

		<div class="position-info">
			<span class="work-title">{work.title}</span>
			<span class="node-title">{nodeTitle}</span>
		</div>
	</div>

	<div class="header-right">
		<a href={osbHref} class="mode-link touch-target" title="Orthodox Study Bible">
			<Icon name="book-open" size={18} />
			<span class="mode-label">OSB</span>
		</a>
		<div class="mode-link active" title="Theological Library">
			<Icon name="library" size={18} />
			<span class="mode-label">Library</span>
		</div>
	</div>
</header>

<style>
	.library-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 var(--space-4);
		height: var(--header-height);
		background: var(--color-bg-surface);
		border-bottom: 1px solid var(--color-border);
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		flex: 1;
		min-width: 0;
	}

	.header-right {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		flex-shrink: 0;
	}

	.toc-toggle {
		display: flex;
		align-items: center;
		justify-content: center;
		width: var(--touch-min);
		height: var(--touch-min);
		color: var(--color-text-secondary);
		background: transparent;
		border: none;
		border-radius: var(--radius-md);
		cursor: pointer;
		transition: background var(--transition-fast), color var(--transition-fast);
	}

	.toc-toggle:hover {
		background: var(--color-bg-hover);
		color: var(--color-text-primary);
	}

	.position-info {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}

	.work-title {
		font-size: var(--font-xs);
		font-family: var(--font-ui);
		color: var(--color-text-muted);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.node-title {
		font-size: var(--font-sm);
		font-weight: var(--font-medium);
		color: var(--color-text-primary);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.mode-link {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-3);
		color: var(--color-text-secondary);
		text-decoration: none;
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		border-radius: var(--radius-md);
		transition: background var(--transition-fast), color var(--transition-fast);
	}

	.mode-link:hover:not(.active) {
		background: var(--color-bg-hover);
		color: var(--color-text-primary);
	}

	.mode-link.active {
		color: var(--color-gold);
		background: var(--color-gold-dim-bg);
	}

	.mode-label {
		font-weight: var(--font-medium);
	}

	@media (max-width: 768px) {
		.work-title {
			display: none;
		}

		.mode-label {
			display: none;
		}

		.mode-link {
			padding: var(--space-2);
		}
	}
</style>
