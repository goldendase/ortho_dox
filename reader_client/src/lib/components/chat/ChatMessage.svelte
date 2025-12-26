<!--
  Chat Message Component

  Displays a single chat message with role-appropriate styling.
  User messages appear as subtle query headers.
  Assistant messages render as flowing report content with markdown.
-->
<script lang="ts">
	import type { ChatMessage, ReaderPosition, LibraryPosition } from '$lib/stores';
	import { formatPosition, formatLibraryPosition } from '$lib/stores';
	import ChatMessageContent from './ChatMessageContent.svelte';

	interface Props {
		message: ChatMessage;
	}

	let { message }: Props = $props();

	const timeFormatter = new Intl.DateTimeFormat('en-US', {
		hour: 'numeric',
		minute: '2-digit',
		hour12: true
	});

	// Type guard for ReaderPosition (OSB)
	function isReaderPosition(ctx: ReaderPosition | LibraryPosition): ctx is ReaderPosition {
		return 'book' in ctx && 'chapter' in ctx;
	}

	// Format context based on type
	function formatContext(ctx: ReaderPosition | LibraryPosition): string {
		if (isReaderPosition(ctx)) {
			return formatPosition(ctx);
		}
		return formatLibraryPosition(ctx);
	}
</script>

{#if message.role === 'user'}
	<!-- User message: Query/prompt style -->
	<div class="user-query">
		<div class="query-header">
			<span class="query-label font-ui">Question</span>
			{#if message.context}
				<span class="query-context text-muted font-ui">
					{formatContext(message.context)}
				</span>
			{/if}
			<span class="query-time text-muted font-ui">
				{timeFormatter.format(message.timestamp)}
			</span>
		</div>
		<div class="query-text">
			{message.content}
		</div>
	</div>
{:else}
	<!-- Assistant message: Report content style -->
	<div class="assistant-response">
		<ChatMessageContent content={message.content} />
	</div>
{/if}

<style>
	/* ─────────────────────────────────────────────────────
	   User Query Styling
	   ───────────────────────────────────────────────────── */
	.user-query {
		padding: var(--space-3) var(--space-4);
		background: var(--color-bg-elevated);
		border-left: 3px solid var(--color-gold);
		margin-bottom: var(--space-2);
	}

	.query-header {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		margin-bottom: var(--space-2);
		font-size: var(--font-xs);
	}

	.query-label {
		color: var(--color-gold);
		font-weight: var(--font-semibold);
		text-transform: uppercase;
		letter-spacing: var(--tracking-wide);
	}

	.query-context {
		color: var(--color-text-muted);
	}

	.query-context::before {
		content: '·';
		margin-right: var(--space-3);
	}

	.query-time {
		margin-left: auto;
		color: var(--color-text-muted);
	}

	.query-text {
		color: var(--color-text-primary);
		line-height: var(--leading-normal);
		font-family: var(--font-body);
	}

	/* ─────────────────────────────────────────────────────
	   Assistant Response Styling
	   ───────────────────────────────────────────────────── */
	.assistant-response {
		padding: var(--space-2) 0 var(--space-4) 0;
	}
</style>
