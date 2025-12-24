/**
 * Chat API Client
 *
 * Sends messages to the /chat endpoint for AI-assisted Bible study.
 */

import { api } from './client';
import type { ChatRequest, ChatResponse, ChatContext, ChatMessage } from './types';

/**
 * Send a chat message and get a response
 *
 * @param messages - Full conversation history (user manages this)
 * @param context - Current reading position context
 * @returns The assistant's response
 */
export async function sendChatMessage(
	messages: ChatMessage[],
	context: ChatContext
): Promise<ChatResponse> {
	const request: ChatRequest = { messages, context };
	return api.post<ChatResponse, ChatRequest>('/chat', request);
}

/** Chat API namespace */
export const chatApi = {
	send: sendChatMessage
};
