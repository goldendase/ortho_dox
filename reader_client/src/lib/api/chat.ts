/**
 * Chat API Client
 *
 * Sends messages to the /chat endpoint for AI-assisted Bible study.
 * Supports both standard and streaming responses.
 */

import { browser } from '$app/environment';
import { api } from './client';
import type {
	ChatRequest,
	ChatResponse,
	ChatContext,
	ChatMessage,
	StreamEvent,
	StreamCallbacks
} from './types';

// Auth storage key (must match client.ts)
const AUTH_STORAGE_KEY = 'orthodox_reader_secret';
const AUTH_HEADER = 'hmog-secret';

function getAuthSecret(): string | null {
	if (!browser) return null;
	try {
		return localStorage.getItem(AUTH_STORAGE_KEY);
	} catch {
		return null;
	}
}

/**
 * Send a chat message and get a response (non-streaming)
 *
 * @param messages - Full conversation history (user manages this)
 * @param context - Current reading position context (null for general questions)
 * @returns The assistant's response
 */
export async function sendChatMessage(
	messages: ChatMessage[],
	context: ChatContext | null
): Promise<ChatResponse> {
	const request: ChatRequest = { messages, context };
	return api.post<ChatResponse, ChatRequest>('/chat', request);
}

/**
 * Send a chat message with streaming response (SSE)
 *
 * @param messages - Full conversation history
 * @param context - Current reading position context
 * @param callbacks - Callbacks for streaming events
 * @returns AbortController to cancel the stream
 */
export async function sendChatMessageStream(
	messages: ChatMessage[],
	context: ChatContext | null,
	callbacks: StreamCallbacks
): Promise<AbortController> {
	const controller = new AbortController();
	const request: ChatRequest = { messages, context };

	// Build headers with auth
	const headers: Record<string, string> = {
		'Content-Type': 'application/json'
	};
	const secret = getAuthSecret();
	if (secret) {
		headers[AUTH_HEADER] = secret;
	}

	try {
		const response = await fetch(`${api.baseUrl}/chat/stream`, {
			method: 'POST',
			headers,
			body: JSON.stringify(request),
			signal: controller.signal
		});

		if (!response.ok) {
			const error = await response.text();
			callbacks.onError?.(error || `HTTP ${response.status}`);
			return controller;
		}

		if (!response.body) {
			callbacks.onError?.('No response body');
			return controller;
		}

		// Read SSE stream
		const reader = response.body.getReader();
		const decoder = new TextDecoder();
		let buffer = '';

		while (true) {
			const { done, value } = await reader.read();
			if (done) break;

			buffer += decoder.decode(value, { stream: true });

			// Process complete SSE messages (data: {...}\n\n)
			const lines = buffer.split('\n');
			buffer = lines.pop() || ''; // Keep incomplete line in buffer

			for (const line of lines) {
				if (line.startsWith('data: ')) {
					try {
						const event: StreamEvent = JSON.parse(line.slice(6));

						switch (event.type) {
							case 'status':
								callbacks.onStatus?.(event.data as string);
								break;
							case 'chunk':
								callbacks.onChunk?.(event.data as string);
								break;
							case 'done': {
								const doneData = event.data as { answer: string; tool_calls: unknown[] };
								callbacks.onDone?.(doneData.answer, doneData.tool_calls as never[]);
								break;
							}
							case 'error':
								callbacks.onError?.(event.data as string);
								break;
						}
					} catch (parseErr) {
						console.warn('Failed to parse SSE event:', line, parseErr);
					}
				}
			}
		}
	} catch (err) {
		if ((err as Error).name !== 'AbortError') {
			callbacks.onError?.(err instanceof Error ? err.message : 'Stream error');
		}
	}

	return controller;
}

/** Chat API namespace */
export const chatApi = {
	send: sendChatMessage,
	stream: sendChatMessageStream
};
