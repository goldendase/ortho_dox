<!--
  SidePanel Component

  Tabbed panel with two views:
  - Notes: Study notes, liturgical refs, variants, articles, passage previews
  - Chat: AI assistant for questions about the text

  Desktop: Always visible in sidebar
  Mobile: Rendered as a Sheet by parent
-->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { ui, favorites, chat, reader, formatPosition } from '$lib/stores';
	import { passages } from '$lib/api';
	import type { StudyNote, ScriptureRef, PatristicCitation } from '$lib/api';
	import Icon from '$lib/components/ui/Icon.svelte';
	import FavoriteButton from '$lib/components/ui/FavoriteButton.svelte';
	import ChatMessage from '$lib/components/chat/ChatMessage.svelte';

	// Chat input state
	let inputValue = $state('');
	let inputEl = $state<HTMLTextAreaElement | undefined>(undefined);
	let messagesEl = $state<HTMLElement | undefined>(undefined);

	// Derive panel title from content type (for notes tab)
	const panelTitle = $derived(() => {
		const content = ui.sidePanelContent;
		if (!content) return 'Notes';

		switch (content.type) {
			case 'study':
				return 'Study Note';
			case 'liturgical':
				return 'Liturgical Reference';
			case 'variant':
				return 'Manuscript Variant';
			case 'article':
				return 'Article';
			case 'passage':
				return content.title;
		}
	});

	// Chat handlers
	async function handleChatSubmit() {
		const message = inputValue.trim();
		if (!message || chat.isStreaming) return;

		inputValue = '';
		await chat.send(message);

		requestAnimationFrame(() => {
			messagesEl?.scrollTo({ top: messagesEl.scrollHeight, behavior: 'smooth' });
		});
	}

	function handleChatKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleChatSubmit();
		}
	}

	function handleChatInput(e: Event) {
		const target = e.target as HTMLTextAreaElement;
		target.style.height = 'auto';
		target.style.height = Math.min(target.scrollHeight, 150) + 'px';
	}

	function handleClearChat() {
		chat.clearSession();
		reader.clearSelectedVerse();
	}

	// Check if current content is favorited (for passages)
	const isFavorited = $derived(() => {
		const content = ui.sidePanelContent;
		if (!content) return false;

		if (content.type === 'passage') {
			return favorites.isPassageFavorited(
				content.passage.book_id,
				content.passage.chapter,
				content.passage.verse
			);
		}
		if (content.type === 'study') {
			return favorites.isNoteFavorited(content.note.id);
		}
		return false;
	});

	function handleToggleFavorite() {
		const content = ui.sidePanelContent;
		if (!content) return;

		if (content.type === 'passage') {
			favorites.togglePassage({
				book: content.passage.book_id,
				bookName: content.title.split(' ')[0],
				chapter: content.passage.chapter,
				verse: content.passage.verse,
				preview: content.passage.text.replace(/<[^>]*>/g, '').slice(0, 100)
			});
		} else if (content.type === 'study') {
			favorites.toggleNote({
				id: content.note.id,
				type: 'study',
				verseDisplay: content.note.verse_display,
				preview: content.note.text.replace(/<[^>]*>/g, '').slice(0, 100)
			});
		}
	}

	// Handle cross-reference click - fetch passage and display
	async function handleRefClick(ref: ScriptureRef) {
		try {
			const passage = await passages.get(ref.id, 'annotations');
			ui.showPassage(passage, ref.display);
		} catch (e) {
			console.error('Failed to fetch passage:', e);
		}
	}

	// Navigate to full passage
	function handleGoToPassage() {
		const content = ui.sidePanelContent;
		if (content?.type === 'passage') {
			const { book_id, chapter, verse } = content.passage;
			goto(`/read/${book_id}/${chapter}#v${verse}`);
			ui.closeSidePanel();
		}
	}

	// Helper for patristic citations
	function getPatristicName(citation: string | PatristicCitation): string {
		if (typeof citation === 'string') {
			return citation;
		}
		return citation.name;
	}
</script>

<div class="side-panel">
	<!-- Tab bar -->
	<div class="tab-bar">
		<button
			class="tab-button"
			class:active={ui.sidePanelTab === 'notes'}
			onclick={() => ui.setTab('notes')}
		>
			<Icon name="note" size={16} />
			<span>Notes</span>
		</button>
		<button
			class="tab-button"
			class:active={ui.sidePanelTab === 'chat'}
			onclick={() => ui.setTab('chat')}
		>
			<Icon name="message" size={16} />
			<span>Chat</span>
		</button>
		<button
			class="close-button touch-target mobile-only"
			onclick={() => ui.closeSidePanel()}
			aria-label="Close panel"
		>
			<Icon name="x" size={20} />
		</button>
	</div>

	<!-- Notes Tab -->
	<div class="tab-content" class:hidden={ui.sidePanelTab !== 'notes'}>
		<header class="panel-header">
			<h2 class="panel-title font-ui">{panelTitle()}</h2>
			<div class="panel-actions">
				{#if ui.sidePanelContent && (ui.sidePanelContent.type === 'passage' || ui.sidePanelContent.type === 'study')}
					<FavoriteButton isFavorited={isFavorited()} onToggle={handleToggleFavorite} size="sm" />
				{/if}
			</div>
		</header>

		<div class="panel-content">
		{#if ui.sidePanelContent}
			{#if ui.sidePanelContent.type === 'study'}
				{@const note = ui.sidePanelContent.note}
				<div class="content-section">
					<div class="verse-ref text-muted font-ui">{note.verse_display}</div>
					<div class="note-text scripture-text">{@html note.text}</div>

					{#if note.patristic_citations?.length}
						<div class="subsection">
							<h4 class="subsection-title font-ui">Church Fathers</h4>
							<ul class="tag-list">
								{#each note.patristic_citations as citation}
									<li class="tag tag-burgundy">{getPatristicName(citation)}</li>
								{/each}
							</ul>
						</div>
					{/if}

					{#if note.scripture_refs?.length}
						<div class="subsection">
							<h4 class="subsection-title font-ui">Cross-References</h4>
							<ul class="tag-list">
								{#each note.scripture_refs as ref}
									<li>
										<button class="tag tag-green" onclick={() => handleRefClick(ref)}>
											{ref.display}
										</button>
									</li>
								{/each}
							</ul>
						</div>
					{/if}
				</div>
			{:else if ui.sidePanelContent.type === 'liturgical'}
				{@const note = ui.sidePanelContent.note}
				<div class="content-section">
					<div class="verse-ref text-muted font-ui">{note.verse_display}</div>
					<div class="note-text scripture-text">{@html note.text}</div>
				</div>
			{:else if ui.sidePanelContent.type === 'variant'}
				{@const note = ui.sidePanelContent.note}
				<div class="content-section">
					<div class="verse-ref text-muted font-ui">{note.verse_display}</div>
					<div class="note-text scripture-text">{@html note.text}</div>
				</div>
			{:else if ui.sidePanelContent.type === 'article'}
				{@const article = ui.sidePanelContent.article}
				<div class="content-section">
					<div class="note-text scripture-text">{@html article.text}</div>
				</div>
			{:else if ui.sidePanelContent.type === 'passage'}
				{@const passage = ui.sidePanelContent.passage}
				<div class="content-section">
					<div class="passage-preview">
						<span class="verse-num">{passage.verse}</span>
						<span class="verse-text scripture-text">{@html passage.text}</span>
					</div>

					<div class="passage-actions">
						<button class="go-button touch-target" onclick={handleGoToPassage}>
							<span>Go to passage</span>
							<Icon name="arrow-right" size={18} />
						</button>
					</div>
				</div>
			{/if}
		{:else}
			<p class="empty-state text-muted">
				Click an annotation marker or cross-reference to view details here.
			</p>
		{/if}
		</div>
	</div>

	<!-- Chat Tab -->
	<div class="tab-content" class:hidden={ui.sidePanelTab !== 'chat'}>
		<div class="chat-container">
			<!-- Chat header with context and new chat button -->
			<div class="chat-header">
				<!-- Context badge - shows selected verse or chapter -->
				{#if reader.selectedVerse}
					<div class="context-badge context-badge-verse">
						<div class="context-header">
							<Icon name="bookmark" size={14} />
							<span class="context-ref font-ui">
								{reader.selectedVerse.bookName} {reader.selectedVerse.chapter}:{reader.selectedVerse.verse}
							</span>
							<button
								class="context-clear"
								onclick={() => reader.clearSelectedVerse()}
								aria-label="Clear selected verse"
								title="Clear verse selection"
							>
								<Icon name="x" size={14} />
							</button>
						</div>
						<p class="context-preview text-muted">
							{reader.selectedVerse.text}
						</p>
					</div>
				{:else if reader.position}
					<div class="context-badge">
						<Icon name="book" size={14} />
						<span class="context-text font-ui">
							{formatPosition(reader.position)}
						</span>
						<span class="context-hint text-muted">Click a verse to focus discussion</span>
					</div>
				{/if}

				<!-- New chat button - only show if there are messages -->
				{#if chat.messages.length > 0}
					<button
						class="new-chat-button"
						onclick={handleClearChat}
						title="Start new conversation"
					>
						<Icon name="plus" size={14} />
						<span>New Chat</span>
					</button>
				{/if}
			</div>

			<!-- Messages -->
			<div class="messages" bind:this={messagesEl}>
				{#if chat.messages.length === 0}
					<div class="chat-empty-state">
						<p class="empty-title">Ask about what you're reading</p>
						<p class="empty-hint text-muted">
							The assistant has access to the full text, study notes, and
							cross-references for your current passage.
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
			<form class="input-form" onsubmit={(e) => { e.preventDefault(); handleChatSubmit(); }}>
				<textarea
					bind:this={inputEl}
					bind:value={inputValue}
					onkeydown={handleChatKeydown}
					oninput={handleChatInput}
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
					<Icon name="send" size={20} />
				</button>
			</form>
		</div>
	</div>
</div>

<style>
	.side-panel {
		display: flex;
		flex-direction: column;
		height: 100%;
		background: var(--color-bg-surface);
		overflow: hidden;
	}

	/* Tab content wrapper - fills remaining space */
	.tab-content {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0; /* Critical for nested scroll */
		overflow: hidden;
	}

	.tab-content.hidden {
		display: none;
	}

	/* ─────────────────────────────────────────────────────
	   Tab Bar
	   ───────────────────────────────────────────────────── */
	.tab-bar {
		display: flex;
		align-items: center;
		gap: var(--space-1);
		padding: var(--space-2) var(--space-3);
		background: var(--color-bg-elevated);
		border-bottom: 1px solid var(--color-border);
		flex-shrink: 0;
	}

	.tab-button {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-3);
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		font-weight: var(--font-medium);
		color: var(--color-text-muted);
		border-radius: var(--radius-md);
		transition:
			color var(--transition-fast),
			background var(--transition-fast);
	}

	.tab-button:hover {
		color: var(--color-text-secondary);
		background: var(--color-bg-hover);
	}

	.tab-button.active {
		color: var(--color-gold);
		background: rgba(212, 175, 55, 0.1);
	}

	.close-button {
		display: flex;
		align-items: center;
		justify-content: center;
		margin-left: auto;
		padding: var(--space-2);
		color: var(--color-text-muted);
		border-radius: var(--radius-md);
		transition:
			color var(--transition-fast),
			background var(--transition-fast);
	}

	.close-button:hover {
		color: var(--color-text-primary);
		background: var(--color-bg-hover);
	}

	/* Show close button only on mobile */
	@media (min-width: 769px) {
		.mobile-only {
			display: none;
		}
	}

	/* ─────────────────────────────────────────────────────
	   Notes Tab
	   ───────────────────────────────────────────────────── */
	.panel-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--space-3) var(--space-4);
		border-bottom: 1px solid var(--color-border);
		flex-shrink: 0;
	}

	.panel-title {
		font-size: var(--font-sm);
		font-weight: var(--font-semibold);
		text-transform: uppercase;
		letter-spacing: var(--tracking-wide);
		color: var(--color-text-secondary);
	}

	.panel-actions {
		display: flex;
		align-items: center;
		gap: var(--space-1);
	}

	.panel-content {
		flex: 1;
		overflow-y: auto;
		padding: var(--space-4);
	}

	.content-section {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.verse-ref {
		font-size: var(--font-sm);
		font-weight: var(--font-semibold);
	}

	.note-text {
		line-height: var(--leading-relaxed);
		white-space: pre-wrap;
	}

	.subsection {
		padding-top: var(--space-3);
		border-top: 1px solid var(--color-border);
	}

	.subsection-title {
		font-size: var(--font-xs);
		font-weight: var(--font-semibold);
		text-transform: uppercase;
		letter-spacing: var(--tracking-wide);
		color: var(--color-text-muted);
		margin-bottom: var(--space-2);
	}

	.tag-list {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
	}

	.tag {
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		padding: var(--space-1) var(--space-2);
		border-radius: var(--radius-sm);
		transition: background var(--transition-fast);
	}

	.tag-burgundy {
		color: var(--color-burgundy-light);
		background: var(--color-burgundy-dark);
	}

	.tag-green {
		color: var(--color-annotation-crossref);
		background: rgba(91, 138, 114, 0.15);
	}

	button.tag-green:hover {
		background: rgba(91, 138, 114, 0.25);
	}

	.passage-preview {
		line-height: var(--leading-relaxed);
	}

	.verse-num {
		font-family: var(--font-ui);
		font-size: var(--font-xs);
		font-weight: var(--font-semibold);
		color: var(--color-gold);
		vertical-align: super;
		margin-right: 0.3em;
	}

	.passage-actions {
		padding-top: var(--space-4);
		border-top: 1px solid var(--color-border);
	}

	.go-button {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: var(--space-2);
		width: 100%;
		padding: var(--space-3) var(--space-4);
		background: var(--color-bg-elevated);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		color: var(--color-text-secondary);
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		font-weight: var(--font-medium);
		transition:
			background var(--transition-fast),
			color var(--transition-fast),
			border-color var(--transition-fast);
	}

	.go-button:hover {
		background: var(--color-bg-hover);
		color: var(--color-gold);
		border-color: var(--color-gold-dim);
	}

	.empty-state {
		text-align: center;
		padding: var(--space-8);
		font-family: var(--font-ui);
		font-size: var(--font-sm);
	}

	/* ─────────────────────────────────────────────────────
	   Chat Tab
	   ───────────────────────────────────────────────────── */
	.chat-container {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0; /* Allow proper scrolling */
		overflow: hidden;
	}

	.chat-header {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		background: var(--color-bg-elevated);
		border-bottom: 1px solid var(--color-border);
		flex-shrink: 0;
	}

	.new-chat-button {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-3);
		margin: 0 var(--space-3) var(--space-3);
		font-family: var(--font-ui);
		font-size: var(--font-xs);
		font-weight: var(--font-medium);
		color: var(--color-text-muted);
		background: var(--color-bg-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		transition: color var(--transition-fast), border-color var(--transition-fast);
	}

	.new-chat-button:hover {
		color: var(--color-text-primary);
		border-color: var(--color-text-muted);
	}

	.context-badge {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-3) var(--space-4);
		color: var(--color-gold);
		flex-wrap: wrap;
	}

	.context-badge-verse {
		flex-direction: column;
		align-items: stretch;
		gap: var(--space-2);
	}

	.context-header {
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}

	.context-ref {
		font-size: var(--font-sm);
		font-weight: var(--font-semibold);
	}

	.context-clear {
		margin-left: auto;
		padding: var(--space-1);
		color: var(--color-text-muted);
		border-radius: var(--radius-sm);
		transition: color var(--transition-fast), background var(--transition-fast);
	}

	.context-clear:hover {
		color: var(--color-text-primary);
		background: var(--color-bg-hover);
	}

	.context-preview {
		font-family: var(--font-body);
		font-size: var(--font-sm);
		line-height: var(--leading-snug);
		overflow: hidden;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
	}

	.context-text {
		font-size: var(--font-sm);
		font-weight: var(--font-medium);
	}

	.context-hint {
		font-size: var(--font-xs);
		flex-basis: 100%;
		margin-top: var(--space-1);
	}

	.messages {
		flex: 1;
		overflow-y: auto;
		padding: var(--space-4);
		display: flex;
		flex-direction: column;
		gap: 0; /* Report-style flow, no gap between messages */
		min-height: 0; /* Allow flex shrinking */
	}

	.chat-empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		text-align: center;
		padding: var(--space-8);
		flex: 1;
		min-height: 200px; /* Ensure visibility */
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
		max-width: 20rem;
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

	.dot:nth-child(1) { animation-delay: -0.32s; }
	.dot:nth-child(2) { animation-delay: -0.16s; }

	@keyframes bounce {
		0%, 80%, 100% { transform: scale(0); }
		40% { transform: scale(1); }
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
		padding: var(--space-3);
		background: var(--color-bg-surface);
		color: var(--color-text-primary);
		font-size: var(--font-sm);
		line-height: var(--leading-snug);
		max-height: 150px;
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
		padding: var(--space-3);
		background: var(--color-gold);
		color: var(--color-bg-base);
		border-radius: var(--radius-md);
		transition:
			background var(--transition-fast),
			opacity var(--transition-fast);
	}

	.send-button:hover:not(:disabled) {
		background: var(--color-gold-bright);
	}

	.send-button:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}
</style>
