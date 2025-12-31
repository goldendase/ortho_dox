<!--
  ActionBar Component

  Bottom mode selector:
  - Read (go to current reading position, or library if none)
  - Search
  - Ask (AI assistant)
  - Settings
-->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { layout } from '$lib/stores/layout.svelte';
	import { studyContext, positionToPath } from '$lib/stores/studyContext.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';

	function handleRead() {
		layout.setMode('read');
		const pos = studyContext.position;
		if (pos) {
			goto(positionToPath(pos));
		} else {
			goto('/library');
		}
	}
</script>

<div class="action-bar">
	<button
		class="action-btn"
		class:active={layout.mode === 'read'}
		onclick={handleRead}
		aria-label="Read"
	>
		<Icon name="book-open" size={20} />
		<span class="action-label">Read</span>
	</button>

	<button
		class="action-btn"
		class:active={layout.mode === 'shelf'}
		onclick={() => layout.setMode('shelf')}
		aria-label="Shelf"
	>
		<Icon name="shelf" size={20} />
		<span class="action-label">Shelf</span>
	</button>

	<button
		class="action-btn"
		class:active={layout.mode === 'search'}
		onclick={() => layout.setMode('search')}
		aria-label="Search"
	>
		<Icon name="search" size={20} />
		<span class="action-label">Search</span>
	</button>

	<button
		class="action-btn"
		class:active={layout.mode === 'ask'}
		onclick={() => layout.setMode('ask')}
		aria-label="Ask"
	>
		<Icon name="message-circle" size={20} />
		<span class="action-label">Ask</span>
	</button>
</div>

<style>
	.action-bar {
		display: flex;
		align-items: center;
		justify-content: space-around;
		padding: var(--space-1) var(--space-2);
		background: var(--color-bg-surface);
		border-top: 1px solid var(--color-border);
		height: var(--action-bar-height, 48px);
	}

	.action-btn {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: var(--space-1);
		padding: var(--space-1) var(--space-3);
		border-radius: var(--radius-md);
		color: var(--color-text-secondary);
		font-family: var(--font-ui);
		transition: background var(--transition-fast), color var(--transition-fast);
		min-width: 60px;
	}

	.action-btn:hover {
		background: var(--color-bg-hover);
		color: var(--color-text-primary);
	}

	.action-btn.active {
		color: var(--color-gold);
		background: var(--color-gold-dim-bg);
	}

	.action-label {
		font-size: var(--font-xs);
		font-weight: var(--font-medium);
	}

	@media (max-width: 768px) {
		.action-bar {
			height: var(--action-bar-height, 56px);
			padding-bottom: env(safe-area-inset-bottom, var(--space-1));
		}

		.action-btn {
			padding: var(--space-2);
			min-width: 56px;
		}
	}
</style>
