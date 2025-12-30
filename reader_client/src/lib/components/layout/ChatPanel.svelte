<!--
  ChatPanel Component

  Full-page chat mode for AI conversation.

  Features:
  - Context indicator showing what's being discussed
  - Message history
  - Input with streaming support
-->
<script lang="ts">
	import { layout } from '$lib/stores/layout.svelte';
	import { chat } from '$lib/stores/chat.svelte';
	import { studyContext, formatFocusItem } from '$lib/stores/studyContext.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import ChatMessage from '$lib/components/chat/ChatMessage.svelte';

	// Chat input state
	let inputValue = $state('');
	let inputEl = $state<HTMLTextAreaElement | undefined>(undefined);
	let messagesEl = $state<HTMLElement | undefined>(undefined);

	// Derive context display
	let contextDisplay = $derived(() => {
		const focus = studyContext.primaryFocus;
		if (focus) {
			return formatFocusItem(focus);
		}
		const pos = studyContext.position;
		if (pos) {
			if (pos.type === 'scripture') {
				return `${pos.bookName || pos.book} ${pos.chapter}`;
			}
			if (pos.type === 'library') {
				return pos.nodeTitle || pos.workTitle || 'Library';
			}
		}
		return null;
	});

	// Chat handlers
	async function handleSubmit() {
		const message = inputValue.trim();
		if (!message || chat.isStreaming) return;

		inputValue = '';

		// Reset textarea height
		if (inputEl) {
			inputEl.style.height = 'auto';
		}

		await chat.send(message);

		requestAnimationFrame(() => {
			messagesEl?.scrollTo({ top: messagesEl.scrollHeight, behavior: 'smooth' });
		});
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleSubmit();
		}
	}

	function handleInput(e: Event) {
		const target = e.target as HTMLTextAreaElement;
		target.style.height = 'auto';
		target.style.height = Math.min(target.scrollHeight, 120) + 'px';
	}

	function handleClearChat() {
		chat.clearSession();
		studyContext.clearFocus();
	}

	function handleClearContext() {
		studyContext.clearFocus();
	}

	// Return to read mode
	function handleClose() {
		layout.setMode('read');
	}
</script>

<div class="chat-panel">
	<!-- Header -->
	<div class="chat-header">
		<div class="header-left">
			<Icon name="message-circle" size={16} />
			<span class="header-title">Chat</span>

			{#if contextDisplay()}
				<div class="context-badge">
					<span class="context-text">{contextDisplay()}</span>
					<button
						class="context-clear"
						onclick={handleClearContext}
						aria-label="Clear context"
						title="Clear context"
					>
						<Icon name="x" size={12} />
					</button>
				</div>
			{/if}
		</div>

		<div class="header-right">
			{#if chat.messages.length > 0}
				<button class="header-btn" onclick={handleClearChat} title="New conversation">
					<Icon name="plus" size={16} />
					<span class="btn-label">New</span>
				</button>
			{/if}
		</div>
	</div>

	<!-- Messages -->
	<div class="messages" bind:this={messagesEl}>
		{#if chat.messages.length === 0}
			<div class="chat-empty-state">
				<p class="empty-title">Ask about what you're reading</p>
				<p class="empty-hint text-muted">
					The assistant has access to the full text, study notes, and cross-references for your
					current passage.
				</p>
			</div>
		{:else}
			{#each chat.messages as message (message.id)}
				<ChatMessage {message} />
			{/each}

			{#if chat.isStreaming}
				<div class="typing-indicator">
					<span class="dot"></span>
					<span class="dot"></span>
					<span class="dot"></span>
				</div>
			{/if}
		{/if}

		{#if chat.error}
			<div class="error-message">
				{chat.error}
			</div>
		{/if}
	</div>

	<!-- Input -->
	<form
		class="input-form"
		onsubmit={(e) => {
			e.preventDefault();
			handleSubmit();
		}}
	>
		<textarea
			bind:this={inputEl}
			bind:value={inputValue}
			onkeydown={handleKeydown}
			oninput={handleInput}
			placeholder="Ask a question..."
			rows="1"
			class="chat-input font-ui"
			disabled={chat.isStreaming}
		></textarea>
		<button
			type="submit"
			class="send-button touch-target"
			disabled={!inputValue.trim() || chat.isStreaming}
			aria-label="Send message"
		>
			<Icon name="send" size={18} />
		</button>
	</form>
</div>

<style>
	.chat-panel {
		display: flex;
		flex-direction: column;
		height: 100%;
		background: var(--color-bg-surface);
		overflow: hidden;
	}

	/* Header */
	.chat-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--space-2) var(--space-4);
		background: var(--color-bg-elevated);
		border-bottom: 1px solid var(--color-border);
		flex-shrink: 0;
		gap: var(--space-3);
	}

	.header-left,
	.header-right {
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}

	.header-title {
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		font-weight: var(--font-semibold);
		color: var(--color-text-primary);
	}

	.context-badge {
		display: flex;
		align-items: center;
		gap: var(--space-1);
		padding: var(--space-1) var(--space-2);
		background: var(--color-gold-dim-bg);
		border-radius: var(--radius-sm);
		color: var(--color-gold);
		font-size: var(--font-xs);
	}

	.context-text {
		font-family: var(--font-ui);
		font-weight: var(--font-medium);
	}

	.context-clear {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 2px;
		border-radius: var(--radius-sm);
		color: var(--color-gold);
		opacity: 0.7;
		transition: opacity var(--transition-fast);
	}

	.context-clear:hover {
		opacity: 1;
	}

	.header-btn {
		display: flex;
		align-items: center;
		gap: var(--space-1);
		padding: var(--space-1) var(--space-2);
		color: var(--color-text-muted);
		border-radius: var(--radius-sm);
		font-family: var(--font-ui);
		font-size: var(--font-xs);
		transition: color var(--transition-fast), background var(--transition-fast);
	}

	.header-btn:hover {
		color: var(--color-text-primary);
		background: var(--color-bg-hover);
	}

	.btn-label {
		font-weight: var(--font-medium);
	}

	/* Messages */
	.messages {
		flex: 1;
		overflow-y: auto;
		padding: var(--space-4);
		display: flex;
		flex-direction: column;
		gap: 0;
		min-height: 0;
	}

	.chat-empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		text-align: center;
		padding: var(--space-8);
		flex: 1;
		min-height: 120px;
	}

	.empty-title {
		font-family: var(--font-body);
		font-size: var(--font-base);
		color: var(--color-text-secondary);
		margin-bottom: var(--space-2);
	}

	.empty-hint {
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		max-width: 30rem;
		line-height: var(--leading-normal);
	}

	.typing-indicator {
		display: flex;
		gap: var(--space-1);
		padding: var(--space-2);
	}

	.dot {
		width: 6px;
		height: 6px;
		background: var(--color-text-muted);
		border-radius: var(--radius-full);
		animation: bounce 1.4s infinite ease-in-out both;
	}

	.dot:nth-child(1) {
		animation-delay: -0.32s;
	}
	.dot:nth-child(2) {
		animation-delay: -0.16s;
	}

	@keyframes bounce {
		0%,
		80%,
		100% {
			transform: scale(0);
		}
		40% {
			transform: scale(1);
		}
	}

	.error-message {
		padding: var(--space-3);
		background: rgba(204, 68, 68, 0.1);
		border: 1px solid var(--color-error);
		border-radius: var(--radius-md);
		color: var(--color-error);
		font-family: var(--font-ui);
		font-size: var(--font-sm);
	}

	/* Input */
	.input-form {
		display: flex;
		align-items: flex-end;
		gap: var(--space-2);
		padding: var(--space-3) var(--space-4);
		border-top: 1px solid var(--color-border);
		background: var(--color-bg-elevated);
		flex-shrink: 0;
	}

	.chat-input {
		flex: 1;
		resize: none;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		padding: var(--space-2) var(--space-3);
		background: var(--color-bg-surface);
		color: var(--color-text-primary);
		font-size: var(--font-sm);
		line-height: var(--leading-snug);
		max-height: 120px;
		transition: border-color var(--transition-fast);
	}

	.chat-input::placeholder {
		color: var(--color-text-muted);
	}

	.chat-input:focus {
		outline: none;
		border-color: var(--color-border-focus);
	}

	.chat-input:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.send-button {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: var(--space-2);
		background: var(--color-gold);
		color: var(--color-bg-base);
		border-radius: var(--radius-md);
		transition: background var(--transition-fast), opacity var(--transition-fast);
	}

	.send-button:hover:not(:disabled) {
		background: var(--color-gold-bright);
	}

	.send-button:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	@media (max-width: 768px) {
		.btn-label {
			display: none;
		}
	}
</style>
