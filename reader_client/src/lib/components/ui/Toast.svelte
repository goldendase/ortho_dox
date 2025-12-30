<!--
  Toast Notification Component

  Displays toast notifications from the toast store.
  Auto-dismisses after duration, click to dismiss early.
-->
<script lang="ts">
	import { toast, type Toast as ToastType } from '$lib/stores/toast.svelte';
	import Icon from './Icon.svelte';

	function getIcon(type: ToastType['type']) {
		switch (type) {
			case 'error':
				return 'x';
			case 'warning':
				return 'bookmark';
			case 'info':
			default:
				return 'check';
		}
	}
</script>

{#if toast.toasts.length > 0}
	<div class="toast-container">
		{#each toast.toasts as t (t.id)}
			<button class="toast toast-{t.type}" onclick={() => toast.dismiss(t.id)}>
				<Icon name={getIcon(t.type)} size={16} />
				<span class="toast-message">{t.message}</span>
			</button>
		{/each}
	</div>
{/if}

<style>
	.toast-container {
		position: fixed;
		bottom: var(--space-4);
		left: 50%;
		transform: translateX(-50%);
		z-index: 1000;
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		max-width: 90vw;
		width: 400px;
	}

	.toast {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-3) var(--space-4);
		border-radius: var(--radius-md);
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
		cursor: pointer;
		transition: opacity var(--transition-fast), transform var(--transition-fast);
		text-align: left;
	}

	.toast:hover {
		opacity: 0.9;
	}

	.toast-error {
		background: var(--color-error);
		color: white;
	}

	.toast-warning {
		background: var(--color-gold);
		color: var(--color-bg-base);
	}

	.toast-info {
		background: var(--color-bg-elevated);
		color: var(--color-text-primary);
		border: 1px solid var(--color-border);
	}

	.toast-message {
		flex: 1;
		line-height: var(--leading-snug);
	}

	@media (max-width: 768px) {
		.toast-container {
			bottom: calc(var(--space-4) + 60px); /* Above mobile nav */
			width: calc(100vw - var(--space-8));
		}
	}
</style>
