/**
 * Chat State Store
 *
 * Manages:
 * - Chat messages (UI format with metadata)
 * - Conversation history (API format for requests)
 * - Streaming state with thinking/status parsing
 * - Context from studyContext.focusStack (multi-item)
 * - Persistence to localStorage
 */

import { browser } from '$app/environment';
import { studyContext, type FocusItem } from './studyContext.svelte';
import { preferences } from './preferences.svelte';
import { sendChatMessageStream, cancelChatStream, type StreamHandle } from '$lib/api';
import type { ChatContext as ApiChatContext, ChatMessage as ApiChatMessage } from '$lib/api';
import { DspyStreamParser, type ParsedStreamState } from '$lib/utils/dspyStreamParser';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

/** Internal message format with UI metadata */
export interface ChatMessage {
	id: string;
	role: 'user' | 'assistant';
	content: string;
	timestamp: Date;
}

/** Re-export the API context type for convenience */
export type ChatContext = ApiChatContext;

// ─────────────────────────────────────────────────────────────────────────────
// Persistence
// ─────────────────────────────────────────────────────────────────────────────

const MESSAGES_KEY = 'orthodox_reader_chat_messages';
const HISTORY_KEY = 'orthodox_reader_chat_history';

/** Stored format with ISO date strings instead of Date objects */
interface StoredChatMessage extends Omit<ChatMessage, 'timestamp'> {
	timestamp: string;
}

function loadMessages(): ChatMessage[] {
	if (!browser) return [];
	try {
		const stored = localStorage.getItem(MESSAGES_KEY);
		if (!stored) return [];
		const parsed: StoredChatMessage[] = JSON.parse(stored);
		// Convert ISO strings back to Date objects
		return parsed.map((msg) => ({
			...msg,
			timestamp: new Date(msg.timestamp)
		}));
	} catch {
		return [];
	}
}

function loadHistory(): ApiChatMessage[] {
	if (!browser) return [];
	try {
		const stored = localStorage.getItem(HISTORY_KEY);
		return stored ? JSON.parse(stored) : [];
	} catch {
		return [];
	}
}

function saveMessages(messages: ChatMessage[]): void {
	if (!browser) return;
	try {
		// Convert Date objects to ISO strings for storage
		const toStore: StoredChatMessage[] = messages.map((msg) => ({
			...msg,
			timestamp: msg.timestamp.toISOString()
		}));
		localStorage.setItem(MESSAGES_KEY, JSON.stringify(toStore));
	} catch {
		// Ignore storage errors (quota exceeded, etc.)
	}
}

function saveHistory(history: ApiChatMessage[]): void {
	if (!browser) return;
	try {
		localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
	} catch {
		// Ignore storage errors
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// Store Class
// ─────────────────────────────────────────────────────────────────────────────

class ChatStore {
	/** All messages in the current session (UI format with metadata) */
	messages = $state<ChatMessage[]>(loadMessages());

	/** Conversation history in API format (role + content only) */
	#conversationHistory = $state<ApiChatMessage[]>(loadHistory());

	/** Is the LLM currently responding */
	isStreaming = $state(false);

	/** Parsed thinking state from DSPy stream (in-progress) */
	thinkingState = $state<ParsedStreamState>({
		phase: 'idle',
		thinkingEntries: [],
		currentThought: '',
		currentToolName: '',
		statusText: 'Thinking...',
		isAnswering: false,
		answerContent: ''
	});

	/** Completed thinking from last response (persists until next send) */
	completedThinking = $state<{ entries: ParsedStreamState['thinkingEntries']; expanded: boolean } | null>(null);

	/** Is thinking panel expanded to show full content */
	thinkingExpanded = $state(false);

	/** Current streaming response text (for live updates) - now only for final answer phase */
	streamingContent = $state('');

	/** Error message if last request failed */
	error = $state<string | null>(null);

	/** Stream handle for cancelling (includes controller and stream ID) */
	#streamHandle: StreamHandle | null = null;

	/** DSPy stream parser instance */
	#streamParser: DspyStreamParser | null = null;

	/** Status history for fallback display when DSPy parsing doesn't capture entries */
	#statusHistory: string[] = [];

	/**
	 * Build the API context from studyContext.focusStack.
	 *
	 * Only items explicitly added to the context manager are sent.
	 * If context manager is empty, returns null for context-free chat.
	 */
	get currentContext(): ApiChatContext | null {
		const focusStack = studyContext.focusStack;

		// Only send context if user has explicitly selected items
		if (focusStack.length > 0) {
			return {
				context_items: focusStack.map((item) => this.#focusItemToContextItem(item))
			};
		}

		// Empty context manager = context-free chat
		return null;
	}

	/**
	 * Convert a FocusItem to a ContextItem for the API
	 */
	#focusItemToContextItem(item: FocusItem): ApiChatContext['context_items'] extends (infer T)[] | undefined ? T : never {
		switch (item.type) {
			case 'verse':
				return {
					type: 'verse',
					passage_id: item.passageId,
					book_id: item.book,
					book_name: item.bookName,
					chapter: item.chapter,
					verse: item.verse,
					text: item.text
				};
			case 'verse-range':
				return {
					type: 'verse-range',
					book_id: item.book,
					book_name: item.bookName,
					chapter: item.chapter,
					verse_start: item.startVerse,
					verse_end: item.endVerse,
					passage_ids: item.passageIds,
					text: item.text
				};
			case 'paragraph':
				return {
					type: 'paragraph',
					work_id: item.workId,
					work_title: item.workTitle,
					node_id: item.nodeId,
					node_title: item.nodeTitle,
					paragraph_index: item.index,
					text: item.text
				};
			case 'osb-note':
				return {
					type: 'osb-note',
					note_type: item.noteType,
					note_id: item.noteId,
					verse_display: item.verseDisplay,
					text: item.text
				};
			case 'osb-article':
				return {
					type: 'osb-article',
					article_id: item.articleId,
					text: item.text
				};
			case 'library-footnote':
				return {
					type: 'library-footnote',
					footnote_id: item.footnoteId,
					footnote_type: item.footnoteType,
					marker: item.marker,
					text: item.text
				};
		}
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Message Management
	// ─────────────────────────────────────────────────────────────────────────

	/**
	 * Add a user message (updates both UI messages and API history)
	 */
	#addUserMessage(content: string): ChatMessage {
		// Add to API conversation history
		this.#conversationHistory = [...this.#conversationHistory, { role: 'user', content }];
		saveHistory(this.#conversationHistory);

		// Add to UI messages with metadata
		const message: ChatMessage = {
			id: crypto.randomUUID(),
			role: 'user',
			content,
			timestamp: new Date()
		};
		this.messages = [...this.messages, message];
		saveMessages(this.messages);
		return message;
	}

	/**
	 * Add an assistant message (updates both UI messages and API history)
	 */
	#addAssistantMessage(content: string): ChatMessage {
		// Add to API conversation history
		this.#conversationHistory = [...this.#conversationHistory, { role: 'assistant', content }];
		saveHistory(this.#conversationHistory);

		// Add to UI messages with metadata
		const message: ChatMessage = {
			id: crypto.randomUUID(),
			role: 'assistant',
			content,
			timestamp: new Date()
		};
		this.messages = [...this.messages, message];
		saveMessages(this.messages);
		return message;
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Send Message
	// ─────────────────────────────────────────────────────────────────────────

	/**
	 * Handle parsed stream state updates
	 */
	#handleStreamState(state: ParsedStreamState): void {
		this.thinkingState = state;

		// Update streaming content when in answer phase
		if (state.isAnswering) {
			this.streamingContent = state.answerContent;
		}
	}

	/**
	 * Reset thinking state for a new stream
	 */
	#resetThinkingState(): void {
		this.thinkingState = {
			phase: 'idle',
			thinkingEntries: [],
			currentThought: '',
			currentToolName: '',
			statusText: 'Thinking...',
			isAnswering: false,
			answerContent: ''
		};
		this.thinkingExpanded = false;
	}

	/**
	 * Save current thinking entries as completed thinking
	 */
	#saveCompletedThinking(): void {
		let entries = [
			...this.thinkingState.thinkingEntries,
			// Include current thought if any
			...(this.thinkingState.currentThought.trim()
				? [{ type: 'thought' as const, content: this.thinkingState.currentThought.trim() }]
				: [])
		];

		// Fallback: if no parsed entries, use status history
		if (entries.length === 0 && this.#statusHistory.length > 0) {
			entries = this.#statusHistory.map((status) => ({
				type: 'tool' as const,
				content: status
			}));
		}

		if (entries.length > 0) {
			this.completedThinking = { entries, expanded: false };
		}
	}

	/**
	 * Toggle completed thinking expanded state
	 */
	toggleCompletedThinking(): void {
		if (this.completedThinking) {
			this.completedThinking = {
				...this.completedThinking,
				expanded: !this.completedThinking.expanded
			};
		}
	}

	/**
	 * Send a message to the chat API with streaming
	 *
	 * Sends the full conversation history + current context with each request.
	 * The API is stateless - we manage conversation state client-side.
	 */
	async send(content: string): Promise<void> {
		if (this.isStreaming) return;

		// Reset state
		this.error = null;
		this.#resetThinkingState();
		this.completedThinking = null; // Clear previous completed thinking
		this.#statusHistory = []; // Clear status history
		this.streamingContent = '';

		this.#addUserMessage(content);
		this.isStreaming = true;

		// Create parser for this stream
		this.#streamParser = new DspyStreamParser((state) => {
			this.#handleStreamState(state);
		});

		try {
			this.#streamHandle = await sendChatMessageStream(
				this.#conversationHistory,
				this.currentContext,
				{
					onStatus: (status) => {
						// Backend status events (tool start messages from OSBStatusProvider)
						// These are human-readable already, update our status
						this.thinkingState = {
							...this.thinkingState,
							statusText: status
						};
						// Track for fallback display
						this.#statusHistory.push(status);
					},
					onChunk: (text) => {
						// Process through DSPy parser
						this.#streamParser?.processChunk(text);
					},
					onDone: (_backendAnswer) => {
						// Use the answer we parsed from the stream, not the backend's
						// (backend may include extra DSPy metadata/JSON we don't want)
						const parsedAnswer = this.thinkingState.answerContent || this.streamingContent;

						// Save thinking entries before clearing
						this.#saveCompletedThinking();
						// Clear streaming state
						this.streamingContent = '';
						this.#resetThinkingState();
						this.#addAssistantMessage(parsedAnswer);
						this.isStreaming = false;
						this.#streamHandle = null;
						this.#streamParser = null;
					},
					onError: (error) => {
						this.error = error;
						this.isStreaming = false;
						this.streamingContent = '';
						this.#streamHandle = null;
						this.#streamParser = null;
					}
				},
				preferences.chatModel
			);
		} catch (err) {
			this.error = err instanceof Error ? err.message : 'Failed to send message';
			this.isStreaming = false;
			this.streamingContent = '';
			this.#streamParser = null;
		}
	}

	/**
	 * Cancel the current streaming request
	 *
	 * Aborts the client-side fetch AND notifies the backend to stop generation.
	 */
	cancelStream(): void {
		if (this.#streamHandle) {
			// Abort client-side immediately for responsiveness
			this.#streamHandle.controller.abort();

			// Notify backend to stop generation (fire and forget)
			if (this.#streamHandle.streamId) {
				cancelChatStream(this.#streamHandle.streamId);
			}

			this.#streamHandle = null;
			this.isStreaming = false;
			this.streamingContent = '';
			this.#resetThinkingState();
			this.#streamParser = null;
		}
	}

	/**
	 * Toggle thinking panel expanded state
	 */
	toggleThinkingExpanded(): void {
		this.thinkingExpanded = !this.thinkingExpanded;
	}

	/**
	 * Delete a message from the conversation
	 *
	 * Removes from both UI messages and API history.
	 * If deleting a user message, also deletes the following assistant response (if any).
	 */
	deleteMessage(messageId: string): void {
		const messageIndex = this.messages.findIndex((m) => m.id === messageId);
		if (messageIndex === -1) return;

		const message = this.messages[messageIndex];

		if (message.role === 'user') {
			// Find the corresponding assistant message (if it exists, it's the next one)
			const nextMessage = this.messages[messageIndex + 1];
			const deleteCount = nextMessage?.role === 'assistant' ? 2 : 1;

			// Remove from UI messages
			this.messages = [
				...this.messages.slice(0, messageIndex),
				...this.messages.slice(messageIndex + deleteCount)
			];

			// Remove from API history (same indices apply)
			this.#conversationHistory = [
				...this.#conversationHistory.slice(0, messageIndex),
				...this.#conversationHistory.slice(messageIndex + deleteCount)
			];
		} else {
			// Deleting an assistant message - just remove it and the preceding user message
			const deleteStart = messageIndex > 0 && this.messages[messageIndex - 1].role === 'user'
				? messageIndex - 1
				: messageIndex;
			const deleteCount = deleteStart === messageIndex - 1 ? 2 : 1;

			this.messages = [
				...this.messages.slice(0, deleteStart),
				...this.messages.slice(deleteStart + deleteCount)
			];

			this.#conversationHistory = [
				...this.#conversationHistory.slice(0, deleteStart),
				...this.#conversationHistory.slice(deleteStart + deleteCount)
			];
		}

		// Persist changes
		saveMessages(this.messages);
		saveHistory(this.#conversationHistory);
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Session Management
	// ─────────────────────────────────────────────────────────────────────────

	/**
	 * Clear all messages and start a new conversation
	 */
	clearSession(): void {
		// Cancel any ongoing stream
		this.cancelStream();

		this.messages = [];
		this.#conversationHistory = [];
		this.error = null;
		this.isStreaming = false;
		this.#resetThinkingState();
		this.streamingContent = '';

		// Clear from localStorage
		if (browser) {
			localStorage.removeItem(MESSAGES_KEY);
			localStorage.removeItem(HISTORY_KEY);
		}
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// Singleton Export
// ─────────────────────────────────────────────────────────────────────────────

export const chat = new ChatStore();
