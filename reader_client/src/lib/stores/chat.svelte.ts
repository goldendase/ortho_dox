/**
 * Chat State Store
 *
 * Manages:
 * - Chat messages (UI format with metadata)
 * - Conversation history (API format for requests)
 * - Streaming state
 * - Context from reader position or selected verse
 * - Persistence to localStorage
 */

import { browser } from '$app/environment';
import { reader, type ReaderPosition } from './reader.svelte';
import { libraryStore } from './library.svelte';
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
	/** The passage context when this message was sent (for display) */
	context?: ReaderPosition;
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
	 * Build the API context based on reading position.
	 *
	 * Sends explicit titles/names along with IDs so the agent doesn't waste
	 * tool calls looking up things we already know.
	 *
	 * Priority:
	 * 1. OSB selected verse (highest priority - user explicitly selected)
	 * 2. Library selected paragraph (user explicitly selected)
	 * 3. Library node position (user is reading library)
	 * 4. OSB chapter position (user is reading OSB)
	 */
	get currentContext(): ApiChatContext | null {
		// OSB: If a specific verse is selected, send full verse context
		const selectedVerse = reader.selectedVerse;
		if (selectedVerse) {
			return {
				passage_id: selectedVerse.passageId,
				book_id: selectedVerse.book,
				book_name: selectedVerse.bookName,
				chapter: selectedVerse.chapter,
				verse: selectedVerse.verse,
				verse_text: selectedVerse.text
			};
		}

		// Library: If a paragraph is selected, include paragraph text
		const selectedParagraph = libraryStore.selectedParagraph;
		if (selectedParagraph) {
			const work = libraryStore.currentWork;
			return {
				work_id: selectedParagraph.workId,
				work_title: work?.title,
				node_id: selectedParagraph.nodeId,
				node_title: selectedParagraph.nodeTitle,
				paragraph_text: selectedParagraph.text
			};
		}

		// Library: If reading a library node (no paragraph selected)
		const libPos = libraryStore.position;
		if (libPos) {
			const work = libraryStore.currentWork;
			const node = libraryStore.currentNode;
			return {
				work_id: libPos.work,
				work_title: libPos.workTitle ?? work?.title,
				node_id: libPos.node,
				node_title: libPos.nodeTitle ?? node?.title,
				node_content: node?.content ?? undefined
			};
		}

		// OSB: If reading a chapter (no verse selected)
		const osbPos = reader.position;
		if (osbPos) {
			return {
				book_id: osbPos.book,
				book_name: osbPos.bookName,
				chapter: osbPos.chapter
				// Note: chapter_text would require fetching - backend can handle this
			};
		}

		// No context
		return null;
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
			context: reader.position ?? undefined,
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
