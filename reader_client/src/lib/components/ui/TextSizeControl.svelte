<!--
  TextSizeControl Component

  Simple +/- controls for adjusting text size in the library reader.
-->
<script lang="ts">
	import { preferences, TEXT_SIZE_LABELS } from '$lib/stores';
	import Icon from './Icon.svelte';
</script>

<div class="text-size-control">
	<button
		class="size-btn"
		onclick={() => preferences.decreaseTextSize()}
		disabled={!preferences.canDecreaseTextSize}
		aria-label="Decrease text size"
	>
		<Icon name="minus" size={16} />
	</button>

	<span class="size-label" title="Text size: {TEXT_SIZE_LABELS[preferences.textSize]}">
		<Icon name="type" size={16} />
	</span>

	<button
		class="size-btn"
		onclick={() => preferences.increaseTextSize()}
		disabled={!preferences.canIncreaseTextSize}
		aria-label="Increase text size"
	>
		<Icon name="plus" size={16} />
	</button>
</div>

<style>
	.text-size-control {
		display: flex;
		align-items: center;
		gap: var(--space-1);
		padding: var(--space-1);
		background: var(--color-bg-elevated);
		border-radius: var(--radius-md);
	}

	.size-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		color: var(--color-text-secondary);
		background: transparent;
		border: none;
		border-radius: var(--radius-sm);
		cursor: pointer;
		transition:
			background var(--transition-fast),
			color var(--transition-fast);
	}

	.size-btn:hover:not(:disabled) {
		background: var(--color-bg-hover);
		color: var(--color-text-primary);
	}

	.size-btn:disabled {
		opacity: 0.3;
		cursor: not-allowed;
	}

	.size-label {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 0 var(--space-2);
		color: var(--color-text-muted);
	}
</style>
