/**
 * Chat State Store
 *
 * Manages:
 * - Chat messages (UI format with metadata)
 * - Conversation history (API format for requests)
 * - Streaming state
 * - Context from studyContext.focusStack (multi-item)
 * - Persistence to localStorage
 */

import { browser } from '$app/environment';
import { studyContext, type FocusItem } from './studyContext.svelte';
import { sendChatMessage } from '$lib/api';
import type { ChatContext as ApiChatContext, ChatMessage as ApiChatMessage } from '$lib/api';

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

	/** Error message if last request failed */
	error = $state<string | null>(null);

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
	 * Send a message to the chat API
	 *
	 * Sends the full conversation history + current context with each request.
	 * The API is stateless - we manage conversation state client-side.
	 */
	async send(content: string): Promise<void> {
		if (this.isStreaming) return;

		this.error = null;
		this.#addUserMessage(content);
		this.isStreaming = true;

		try {
			const response = await sendChatMessage(
				this.#conversationHistory,
				this.currentContext
			);

			// Add assistant response to our state
			this.#addAssistantMessage(response.message.content);

			// Check for API-level errors (agent had issues but returned gracefully)
			if (response.error) {
				console.warn('Chat API error:', response.error);
			}
		} catch (err) {
			this.error = err instanceof Error ? err.message : 'Failed to send message';
		} finally {
			this.isStreaming = false;
		}
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Session Management
	// ─────────────────────────────────────────────────────────────────────────

	/**
	 * Clear all messages and start a new conversation
	 */
	clearSession(): void {
		this.messages = [];
		this.#conversationHistory = [];
		this.error = null;
		this.isStreaming = false;

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
