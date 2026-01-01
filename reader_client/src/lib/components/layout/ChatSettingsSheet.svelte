<!--
  ChatSettingsSheet Component

  Settings sheet for the chat/ask panel.
  Includes text size control and experimental model selection.
-->
<script lang="ts">
	import Sheet from '$lib/components/ui/Sheet.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import {
		preferences,
		TEXT_SIZE_LABELS,
		CHAT_MODELS,
		type ChatModel
	} from '$lib/stores/preferences.svelte';

	interface Props {
		open: boolean;
	}

	let { open = $bindable() }: Props = $props();

	function handleModelChange(e: Event) {
		const select = e.target as HTMLSelectElement;
		const value = select.value === '' ? null : select.value as ChatModel;
		preferences.setChatModel(value);
	}
</script>

<Sheet bind:open position="bottom">
	<div class="settings-content">
		<h2 class="settings-title">Chat Settings</h2>

		<!-- Text Size -->
		<div class="setting-group">
			<label class="setting-label">Text Size</label>
			<div class="text-size-buttons">
				{#each ['sm', 'md', 'lg', 'xl'] as size}
					<button
						class="size-btn"
						class:active={preferences.textSize === size}
						onclick={() => preferences.setTextSize(size as 'sm' | 'md' | 'lg' | 'xl')}
					>
						{TEXT_SIZE_LABELS[size as 'sm' | 'md' | 'lg' | 'xl']}
					</button>
				{/each}
			</div>
		</div>

		<!-- Experimental Section -->
		<div class="experimental-section">
			<div class="experimental-header">
				<Icon name="alert-circle" size={14} />
				<span>EXPERIMENTAL</span>
			</div>
			<p class="experimental-warning">
				Don't touch this unless you know what you're doing. These models may produce unexpected results.
			</p>

			<div class="setting-group">
				<label class="setting-label" for="model-select">AI Model</label>
				<select
					id="model-select"
					class="model-select"
					value={preferences.chatModel ?? ''}
					onchange={handleModelChange}
				>
					{#each CHAT_MODELS as model}
						<option value={model.value ?? ''}>{model.label}</option>
					{/each}
				</select>
			</div>
		</div>
	</div>
</Sheet>

<style>
	.settings-content {
		padding: var(--space-4);
		padding-bottom: var(--space-8);
	}

	.settings-title {
		font-family: var(--font-ui);
		font-size: var(--font-lg);
		font-weight: var(--font-semibold);
		color: var(--color-text-primary);
		margin: 0 0 var(--space-6) 0;
	}

	.setting-group {
		margin-bottom: var(--space-4);
	}

	.setting-label {
		display: block;
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		font-weight: var(--font-medium);
		color: var(--color-text-secondary);
		margin-bottom: var(--space-2);
	}

	.text-size-buttons {
		display: flex;
		gap: var(--space-2);
	}

	.size-btn {
		flex: 1;
		padding: var(--space-2) var(--space-3);
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		color: var(--color-text-secondary);
		background: var(--color-bg-elevated);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.size-btn:hover {
		background: var(--color-bg-hover);
		color: var(--color-text-primary);
	}

	.size-btn.active {
		background: var(--color-gold);
		color: var(--color-bg-base);
		border-color: var(--color-gold);
	}

	/* Experimental Section */
	.experimental-section {
		margin-top: var(--space-6);
		padding: var(--space-4);
		background: rgba(204, 68, 68, 0.08);
		border: 1px solid rgba(204, 68, 68, 0.3);
		border-radius: var(--radius-md);
	}

	.experimental-header {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		font-family: var(--font-ui);
		font-size: var(--font-xs);
		font-weight: var(--font-bold);
		text-transform: uppercase;
		letter-spacing: var(--tracking-wide);
		color: var(--color-error, #cc4444);
		margin-bottom: var(--space-2);
	}

	.experimental-header :global(svg) {
		color: var(--color-error, #cc4444);
	}

	.experimental-warning {
		font-family: var(--font-ui);
		font-size: var(--font-xs);
		color: var(--color-text-muted);
		margin: 0 0 var(--space-4) 0;
		line-height: var(--leading-relaxed);
	}

	.experimental-section .setting-group {
		margin-bottom: 0;
	}

	.model-select {
		width: 100%;
		padding: var(--space-3);
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		color: var(--color-text-primary);
		background: var(--color-bg-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		cursor: pointer;
		transition: border-color var(--transition-fast);
	}

	.model-select:hover {
		border-color: var(--color-border-focus);
	}

	.model-select:focus {
		outline: none;
		border-color: var(--color-gold);
	}
</style>
