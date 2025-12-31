<!--
  AskPanel Component

  Dedicated "Ask" mode for AI-assisted study.

  Features:
  - Multi-item context management (verses, paragraphs from reading)
  - Context items displayed at top with individual remove buttons
  - Clear all context button
  - Message history with markdown/annotation parsing
  - Input with streaming support
-->
<script lang="ts">
	import { layout } from '$lib/stores/layout.svelte';
	import { chat } from '$lib/stores/chat.svelte';
	import { studyContext, formatFocusItem, type FocusItem } from '$lib/stores/studyContext.svelte';
	import Icon, { type IconName } from '$lib/components/ui/Icon.svelte';
	import ChatMessage from '$lib/components/chat/ChatMessage.svelte';

	// Chat input state
	let inputValue = $state('');
	let inputEl = $state<HTMLTextAreaElement | undefined>(undefined);
	let messagesEl = $state<HTMLElement | undefined>(undefined);
	let isSubmitting = false; // Guard against double submission

	// Context section collapsed state
	let contextCollapsed = $state(true);

	// Track if user is near bottom (for smart auto-scroll)
	let isNearBottom = $state(true);

	// Check if scrolled near bottom (within 150px)
	function checkNearBottom() {
		if (!messagesEl) return;
		const threshold = 150;
		const distanceFromBottom = messagesEl.scrollHeight - messagesEl.scrollTop - messagesEl.clientHeight;
		isNearBottom = distanceFromBottom < threshold;
	}

	// Auto-scroll when streaming content updates, but only if user is near bottom
	$effect(() => {
		if (chat.streamingContent && messagesEl && isNearBottom) {
			// Use instant scroll to avoid animation artifacts during rapid updates
			messagesEl.scrollTop = messagesEl.scrollHeight;
		}
	});

	// Derive context items from focusStack
	let contextItems = $derived(studyContext.focusStack);
	let hasContext = $derived(contextItems.length > 0);

	// Get icon for focus item type
	function getItemIcon(item: FocusItem): IconName {
		switch (item.type) {
			case 'verse':
			case 'verse-range':
				return 'book-open';
			case 'paragraph':
				return 'file-text';
			case 'osb-note':
				// Different icons based on note type
				if (item.noteType === 'study') return 'note';
				if (item.noteType === 'liturgical') return 'calendar';
				if (item.noteType === 'variant') return 'layers';
				return 'note';
			case 'osb-article':
				return 'file-text';
			case 'library-footnote':
				return 'bookmark';
			default:
				return 'bookmark';
		}
	}

	// Get short label for focus item
	function getItemLabel(item: FocusItem): string {
		switch (item.type) {
			case 'verse':
				return `${item.bookName} ${item.chapter}:${item.verse}`;
			case 'verse-range':
				return `${item.bookName} ${item.chapter}:${item.startVerse}-${item.endVerse}`;
			case 'paragraph':
				return `${item.nodeTitle || item.workTitle} ¶${item.index}`;
			case 'osb-note':
				const noteTypeLabel = item.noteType === 'study' ? 'Study Note' :
					item.noteType === 'liturgical' ? 'Liturgical' :
					item.noteType === 'variant' ? 'Variant' : 'Note';
				return `${noteTypeLabel}: ${item.verseDisplay}`;
			case 'osb-article':
				return 'Article';
			case 'library-footnote':
				const fnLabel = item.footnoteType === 'endnote' ? 'Endnote' : 'Footnote';
				return `${fnLabel} ${item.marker}`;
			default:
				return formatFocusItem(item);
		}
	}

	// Get preview text for focus item
	function getItemPreview(item: FocusItem): string {
		return item.text.slice(0, 80) + (item.text.length > 80 ? '...' : '');
	}

	// Remove a specific context item
	function handleRemoveItem(item: FocusItem) {
		studyContext.removeFocus(item);
	}

	// Clear all context
	function handleClearContext() {
		studyContext.clearFocus();
	}

	// Toggle context section collapsed state
	function toggleContextCollapsed() {
		contextCollapsed = !contextCollapsed;
	}

	// Chat handlers
	async function handleSubmit() {
		const message = inputValue.trim();
		if (!message || chat.isStreaming || isSubmitting) return;

		// Guard against double submission
		isSubmitting = true;
		inputValue = '';

		// Reset textarea height
		if (inputEl) {
			inputEl.style.height = 'auto';
		}

		// Reset scroll tracking - user just sent a message, start auto-scrolling
		isNearBottom = true;

		try {
			// Start send (adds user message immediately, then starts streaming)
			const sendPromise = chat.send(message);

			// Scroll to show user message + thinking indicator after next render
			requestAnimationFrame(() => {
				if (messagesEl) messagesEl.scrollTop = messagesEl.scrollHeight;
			});

			await sendPromise;
		} finally {
			isSubmitting = false;
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		// Shift+Enter for newline, plain Enter submits form
		if (e.key === 'Enter' && !e.shiftKey) {
			// Prevent newline insertion - form submission handled by browser naturally
			e.preventDefault();
			// Explicitly submit to ensure it happens (browser behavior varies)
			const form = (e.target as HTMLElement).closest('form');
			form?.requestSubmit();
		}
	}

	function handleInput(e: Event) {
		const target = e.target as HTMLTextAreaElement;
		target.style.height = 'auto';
		target.style.height = Math.min(target.scrollHeight, 120) + 'px';
	}

	function handleNewConversation() {
		chat.clearSession();
	}
</script>

<div class="ask-panel">
	<!-- Header -->
	<div class="ask-header">
		<div class="header-left">
			<Icon name="message-circle" size={18} />
			<span class="header-title">Ask</span>
		</div>

		<div class="header-right">
			{#if chat.messages.length > 0}
				<button class="header-btn" onclick={handleNewConversation} title="New conversation">
					<span class="btn-label">New</span>
				</button>
			{/if}
		</div>
	</div>

	<!-- Context Section -->
	{#if hasContext}
		<div class="context-section" class:collapsed={contextCollapsed}>
			<div class="context-header">
				<button class="context-toggle" onclick={toggleContextCollapsed}>
					<Icon name={contextCollapsed ? 'chevron-right' : 'chevron-down'} size={14} />
					<Icon name="bookmark" size={14} />
					Reading Context
					<span class="context-count">({contextItems.length})</span>
				</button>
				<button
					class="context-clear-all"
					onclick={handleClearContext}
					title="Clear all context"
				>
					Clear all
				</button>
			</div>
			{#if !contextCollapsed}
				<div class="context-items">
					{#each contextItems as item}
						<div class="context-item">
							<div class="item-header">
								<Icon name={getItemIcon(item)} size={12} />
								<span class="item-label">{getItemLabel(item)}</span>
								<button
									class="item-remove"
									onclick={() => handleRemoveItem(item)}
									aria-label="Remove from context"
									title="Remove from context"
								>
									<Icon name="x" size={12} />
								</button>
							</div>
							<p class="item-preview">{getItemPreview(item)}</p>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	{/if}

	<!-- Messages -->
	<div class="messages" bind:this={messagesEl} onscroll={checkNearBottom}>
		{#if chat.messages.length === 0}
			<div class="ask-empty-state">
				<div class="empty-icon">
					<Icon name="message-circle" size={32} />
				</div>
				<p class="empty-title">Ask about what you're reading</p>
				<p class="empty-hint">
					{#if hasContext}
						Your selected passages are ready. Ask a question about them.
					{:else}
						Click verses or paragraphs while reading to add them as context, then ask questions here.
					{/if}
				</p>
			</div>
		{:else}
			{#each chat.messages as message, i (message.id)}
				{@const isLastAssistantMessage = message.role === 'assistant' && i === chat.messages.length - 1}
				{@const showCompletedThinkingHere = isLastAssistantMessage && !chat.isStreaming}
				<!-- Show completed thinking before the last assistant message -->
				{#if showCompletedThinkingHere && chat.completedThinking}
					{@const completed = chat.completedThinking}
					<div class="thinking-indicator done" class:expanded={completed.expanded}>
						<button
							class="thinking-header"
							onclick={() => chat.toggleCompletedThinking()}
							aria-expanded={completed.expanded}
						>
							<Icon name="check" size={12} />
							<span class="thinking-status">Reasoning</span>
							<Icon name={completed.expanded ? 'chevron-up' : 'chevron-down'} size={14} />
						</button>
						{#if completed.expanded}
							<div class="thinking-content">
								{#each [...completed.entries].reverse() as entry}
									<div class="thinking-entry {entry.type}">
										<span class="entry-label">{entry.type === 'tool' ? entry.toolName : 'Thought'}</span>
										<p>{entry.content}</p>
									</div>
								{/each}
							</div>
						{/if}
					</div>
				{/if}
				<ChatMessage {message} />
			{/each}

			{#if chat.isStreaming}
				{@const hasThinkingContent = chat.thinkingState.thinkingEntries.length > 0 || chat.thinkingState.currentThought}
				<!-- In-progress thinking indicator - always show while streaming -->
				<div class="thinking-indicator" class:expanded={chat.thinkingExpanded}>
					<button
						class="thinking-header"
						onclick={() => chat.toggleThinkingExpanded()}
						aria-expanded={chat.thinkingExpanded}
						disabled={!hasThinkingContent}
					>
						<span class="thinking-dot"></span>
						<span class="thinking-status">{chat.thinkingState.statusText}</span>
						{#if hasThinkingContent}
							<Icon name={chat.thinkingExpanded ? 'chevron-up' : 'chevron-down'} size={14} />
						{/if}
					</button>
					{#if chat.thinkingExpanded && hasThinkingContent}
						<div class="thinking-content">
							<!-- Current thought (streaming) at top -->
							{#if chat.thinkingState.currentThought}
								<div class="thinking-entry thought current">
									<span class="entry-label">Thinking</span>
									<p>{chat.thinkingState.currentThought}</p>
								</div>
							{/if}
							<!-- Previous entries in reverse order (most recent first) -->
							{#each [...chat.thinkingState.thinkingEntries].reverse() as entry, i}
								<div class="thinking-entry {entry.type}" class:first={i === 0 && !chat.thinkingState.currentThought}>
									<span class="entry-label">{entry.type === 'tool' ? entry.toolName : 'Thought'}</span>
									<p>{entry.content}</p>
								</div>
							{/each}
						</div>
					{/if}
				</div>

				<!-- Streaming answer content -->
				{#if chat.streamingContent}
					<div class="streaming-message">
						<ChatMessage
							message={{
								id: 'streaming',
								role: 'assistant',
								content: chat.streamingContent,
								timestamp: new Date()
							}}
						/>
					</div>
				{/if}
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
			class="ask-input font-ui"
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
	.ask-panel {
		display: flex;
		flex-direction: column;
		height: 100%;
		background: var(--color-bg-surface);
		overflow: hidden;
	}

	/* Header */
	.ask-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--space-3) var(--space-4);
		background: var(--color-bg-elevated);
		border-bottom: 1px solid var(--color-border);
		flex-shrink: 0;
	}

	.header-left,
	.header-right {
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}

	.header-left {
		color: var(--color-gold);
	}

	.header-title {
		font-family: var(--font-ui);
		font-size: var(--font-base);
		font-weight: var(--font-semibold);
		color: var(--color-text-primary);
	}

	.header-btn {
		display: flex;
		align-items: center;
		gap: var(--space-1);
		padding: var(--space-2) var(--space-3);
		color: var(--color-text-muted);
		border-radius: var(--radius-md);
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		transition: color var(--transition-fast), background var(--transition-fast);
	}

	.header-btn:hover {
		color: var(--color-text-primary);
		background: var(--color-bg-hover);
	}

	.btn-label {
		font-weight: var(--font-medium);
		color: var(--color-text-primary);
	}

	/* Context Section */
	.context-section {
		flex-shrink: 0;
		background: var(--color-bg-elevated);
		border-bottom: 1px solid var(--color-border);
	}

	.context-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--space-2) var(--space-4);
	}

	.context-section:not(.collapsed) .context-header {
		border-bottom: 1px solid var(--color-border);
	}

	.context-toggle {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		font-family: var(--font-ui);
		font-size: var(--font-xs);
		font-weight: var(--font-semibold);
		text-transform: uppercase;
		letter-spacing: var(--tracking-wide);
		color: var(--color-gold);
		padding: var(--space-1) var(--space-2);
		margin: calc(-1 * var(--space-1)) calc(-1 * var(--space-2));
		border-radius: var(--radius-sm);
		cursor: pointer;
		transition: background var(--transition-fast);
	}

	.context-toggle:hover {
		background: var(--color-bg-hover);
	}

	.context-count {
		color: var(--color-text-muted);
		font-weight: var(--font-normal);
	}

	.context-clear-all {
		font-family: var(--font-ui);
		font-size: var(--font-xs);
		color: var(--color-text-muted);
		padding: var(--space-1) var(--space-2);
		border-radius: var(--radius-sm);
		transition: color var(--transition-fast), background var(--transition-fast);
	}

	.context-clear-all:hover {
		color: var(--color-text-primary);
		background: var(--color-bg-hover);
	}

	.context-items {
		display: flex;
		flex-direction: column;
		gap: 1px;
		background: var(--color-border);
		max-height: 240px;
		overflow-y: auto;
	}

	.context-item {
		padding: var(--space-2) var(--space-4);
		background: var(--color-bg-surface);
	}

	.item-header {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		margin-bottom: var(--space-1);
	}

	.item-header :global(svg) {
		color: var(--color-gold);
		flex-shrink: 0;
	}

	.item-label {
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		font-weight: var(--font-medium);
		color: var(--color-text-primary);
		flex: 1;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.item-remove {
		flex-shrink: 0;
		padding: var(--space-1);
		color: var(--color-text-muted);
		border-radius: var(--radius-sm);
		transition: color var(--transition-fast), background var(--transition-fast);
	}

	.item-remove:hover {
		color: var(--color-error);
		background: rgba(204, 68, 68, 0.1);
	}

	.item-preview {
		font-family: var(--font-body);
		font-size: var(--font-sm);
		color: var(--color-text-muted);
		line-height: var(--leading-snug);
		overflow: hidden;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
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

	.ask-empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		text-align: center;
		padding: var(--space-8);
		flex: 1;
		min-height: 200px;
	}

	.empty-icon {
		color: var(--color-gold-dim);
		margin-bottom: var(--space-4);
		opacity: 0.5;
	}

	.empty-title {
		font-family: var(--font-body);
		font-size: var(--font-lg);
		color: var(--color-text-secondary);
		margin-bottom: var(--space-2);
	}

	.empty-hint {
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		color: var(--color-text-muted);
		max-width: 28rem;
		line-height: var(--leading-normal);
	}

	/* Thinking indicator */
	.thinking-indicator {
		background: var(--color-bg-elevated);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		margin-bottom: var(--space-2);
		overflow: hidden;
		position: relative;
		z-index: 1;
		flex-shrink: 0;
		min-height: 36px; /* Ensure always visible */
	}

	.thinking-header {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		width: 100%;
		padding: var(--space-2) var(--space-3);
		background: transparent;
		border: none;
		cursor: pointer;
		text-align: left;
		transition: background var(--transition-fast);
	}

	.thinking-header:hover {
		background: var(--color-bg-hover);
	}

	.thinking-dot {
		width: 6px;
		height: 6px;
		background: var(--color-gold);
		border-radius: var(--radius-full);
		animation: pulse 1.5s infinite;
		flex-shrink: 0;
	}

	@keyframes pulse {
		0%, 100% { opacity: 1; }
		50% { opacity: 0.4; }
	}

	.thinking-status {
		flex: 1;
		font-family: var(--font-ui);
		font-size: var(--font-xs);
		color: var(--color-text-secondary);
	}

	.thinking-header :global(svg) {
		color: var(--color-text-muted);
		flex-shrink: 0;
	}

	.thinking-content {
		padding: var(--space-2) var(--space-3);
		padding-top: 0;
		max-height: 250px;
		overflow-y: auto;
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.thinking-entry {
		padding: var(--space-2);
		background: var(--color-bg-surface);
		border-radius: var(--radius-sm);
		border-left: 2px solid var(--color-border);
	}

	.thinking-entry.thought {
		border-left-color: var(--color-gold-dim);
	}

	.thinking-entry.tool {
		border-left-color: var(--color-text-muted);
	}

	.thinking-entry.current {
		border-left-color: var(--color-gold);
	}

	.entry-label {
		display: block;
		font-family: var(--font-ui);
		font-size: 10px;
		font-weight: var(--font-semibold);
		text-transform: uppercase;
		letter-spacing: var(--tracking-wide);
		color: var(--color-text-muted);
		margin-bottom: var(--space-1);
	}

	.thinking-entry p {
		font-family: var(--font-ui);
		font-size: var(--font-xs);
		color: var(--color-text-secondary);
		line-height: var(--leading-relaxed);
		white-space: pre-wrap;
		margin: 0;
	}

	/* Done state */
	.thinking-indicator.done .thinking-header {
		cursor: pointer;
	}

	.thinking-indicator.done .thinking-dot {
		display: none;
	}

	.thinking-indicator.done .thinking-header :global(svg:first-child) {
		color: var(--color-success, #4ade80);
	}

	/* Streaming message */
	.streaming-message {
		opacity: 0.9;
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

	.ask-input {
		flex: 1;
		resize: none;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		padding: var(--space-3) var(--space-4);
		background: var(--color-bg-surface);
		color: var(--color-text-primary);
		font-size: var(--font-sm);
		line-height: var(--leading-snug);
		max-height: 120px;
		transition: border-color var(--transition-fast);
	}

	.ask-input::placeholder {
		color: var(--color-text-muted);
	}

	.ask-input:focus {
		outline: none;
		border-color: var(--color-border-focus);
	}

	.ask-input:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.send-button {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: var(--space-3);
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
		.ask-panel {
			max-width: none;
		}
	}
</style>
