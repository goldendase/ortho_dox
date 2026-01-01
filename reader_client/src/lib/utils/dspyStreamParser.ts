/**
 * DSPy Stream Parser
 *
 * Parses raw DSPy ReAct streaming output to extract thinking, tool calls, and responses.
 *
 * DSPy markers:
 * - [[ ## next_thought ## ]] - Start of reasoning/thinking block
 * - [[ ## next_tool_name ## ]] - Tool name follows
 * - [[ ## next_tool_args ## ]] - Tool arguments follow (JSON)
 * - [[ ## completed ## ]] - Tool call completed, may be followed by another thought
 * - [[ ## answer ## ]] - Final answer (when reasoning is done)
 */

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

/** A single entry in the thinking log */
export interface ThinkingEntry {
	type: 'thought' | 'tool';
	content: string;
	/** For tool entries, the tool name */
	toolName?: string;
}

export interface ParsedStreamState {
	/** Current phase of parsing */
	phase: 'idle' | 'thinking' | 'tool_name' | 'tool_args' | 'answer' | 'done';
	/** Log of thinking entries (thoughts and tool calls) */
	thinkingEntries: ThinkingEntry[];
	/** Current thinking block being accumulated */
	currentThought: string;
	/** Current tool name being accumulated (buffered until next marker) */
	currentToolName: string;
	/** Human-readable status text */
	statusText: string;
	/** Whether we're in the final answer phase */
	isAnswering: boolean;
	/** Accumulated answer content */
	answerContent: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Tool Display Names
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Human-readable tool descriptions for UI display
 * Thematically appropriate for an Orthodox theological study app
 */
const TOOL_STATUS_MAP: Record<string, string> = {
	// Scripture tools
	get_passage: 'Opening Scripture...',
	get_chapter: 'Turning to the chapter...',
	get_study_note: 'Consulting the study notes...',
	get_connections: 'Tracing connections...',
	search_annotations: 'Searching the annotations...',

	// Library tools
	list_library_works: 'Surveying the library...',
	get_work_toc: 'Reviewing the contents...',
	get_library_content: 'Reading from the Fathers...',
	search_osb_content: 'Searching the Scriptures...',
	search_library_content: 'Searching the library...',

	// Completion
	finish: 'Composing response...'
};

/**
 * Get human-readable status text for a tool name
 */
export function getToolStatus(toolName: string): string {
	return TOOL_STATUS_MAP[toolName] || `Consulting ${toolName.replace(/_/g, ' ')}...`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Parser Class
// ─────────────────────────────────────────────────────────────────────────────

/** DSPy marker pattern - matches [[ ## marker_name ## ]] */
const MARKER_PATTERN = /\[\[\s*##\s*(\w+)\s*##\s*\]\]/g;

/**
 * Stateful parser for DSPy streaming output.
 *
 * Feed chunks via `processChunk()` and receive parsed events via callback.
 */
export class DspyStreamParser {
	/** Buffer for incomplete chunks */
	private buffer = '';

	/** Current parsing state */
	private state: ParsedStreamState = {
		phase: 'idle',
		thinkingEntries: [],
		currentThought: '',
		currentToolName: '',
		statusText: 'Thinking...',
		isAnswering: false,
		answerContent: ''
	};

	/** Callback for state changes */
	private onStateChange: (state: ParsedStreamState) => void;

	constructor(onStateChange: (state: ParsedStreamState) => void) {
		this.onStateChange = onStateChange;
	}

	/**
	 * Process an incoming chunk of text.
	 * Parses DSPy markers and updates state accordingly.
	 */
	processChunk(chunk: string): void {
		this.buffer += chunk;

		// Process all complete markers in the buffer
		let processedUpTo = 0;
		let match: RegExpExecArray | null;

		// Reset the regex for each call
		MARKER_PATTERN.lastIndex = 0;

		while ((match = MARKER_PATTERN.exec(this.buffer)) !== null) {
			const markerName = match[1];
			const markerStart = match.index;
			const markerEnd = match.index + match[0].length;

			// Process content before this marker (belongs to previous phase)
			if (markerStart > processedUpTo) {
				const content = this.buffer.slice(processedUpTo, markerStart);
				this.processContent(content);
			}

			// Handle the marker
			this.handleMarker(markerName);

			processedUpTo = markerEnd;
		}

		// Process any remaining content after the last marker
		if (processedUpTo < this.buffer.length) {
			const remaining = this.buffer.slice(processedUpTo);

			// Check if we might have an incomplete marker at the end
			// Markers are like [[ ## word ## ]] - max ~25 chars, so only check end
			const checkRegion = remaining.slice(-30);
			const potentialMarkerStart = checkRegion.lastIndexOf('[[');

			if (potentialMarkerStart !== -1) {
				// Found [[ near end - might be incomplete marker
				const absolutePos = remaining.length - 30 + potentialMarkerStart;
				const safePos = Math.max(0, absolutePos);

				// Process content before the potential marker
				const completeContent = remaining.slice(0, safePos);
				if (completeContent) {
					this.processContent(completeContent);
				}
				this.buffer = remaining.slice(safePos);
			} else {
				// No potential marker at end, process all remaining content
				this.processContent(remaining);
				this.buffer = '';
			}
		} else {
			this.buffer = '';
		}
	}

	/**
	 * Process content based on current phase
	 */
	private processContent(content: string): void {
		if (!content.trim()) return;

		switch (this.state.phase) {
			case 'thinking':
				this.state.currentThought += content;
				this.emitState();
				break;

			case 'tool_name':
				// Buffer tool name content - will be finalized when we see next marker
				this.state.currentToolName += content;
				// Don't emit yet - wait for complete tool name
				break;

			case 'tool_args':
				// Tool args - we don't need to parse these for UI
				// Just wait for next marker
				break;

			case 'answer':
				this.state.answerContent += content;
				this.emitState();
				break;

			case 'done':
				// Ignore any content after completion
				break;

			case 'idle':
				// Content before any marker - treat as thinking
				this.state.phase = 'thinking';
				this.state.currentThought += content;
				this.emitState();
				break;
		}
	}

	/**
	 * Finalize the buffered tool name and update state
	 */
	private finalizeToolName(): void {
		const toolName = this.state.currentToolName.trim();
		if (!toolName) return;

		// Check for "finish" tool - transition to answer phase
		if (toolName === 'finish') {
			this.state.phase = 'answer';
			this.state.isAnswering = true;
			this.state.statusText = 'Composing response...';
			this.finalizeCurrentThought();
		} else {
			this.state.statusText = getToolStatus(toolName);
			// Add tool entry to thinking log
			this.state.thinkingEntries = [
				...this.state.thinkingEntries,
				{ type: 'tool', content: getToolStatus(toolName), toolName }
			];
		}
		this.emitState();
	}

	/**
	 * Save the current thought to the entries log and reset
	 */
	private finalizeCurrentThought(): void {
		const thought = this.state.currentThought.trim();
		if (thought) {
			this.state.thinkingEntries = [
				...this.state.thinkingEntries,
				{ type: 'thought', content: thought }
			];
			this.state.currentThought = '';
		}
	}

	/**
	 * Handle a DSPy marker
	 */
	private handleMarker(markerName: string): void {
		switch (markerName) {
			case 'next_thought':
				// Finalize previous thought before starting new one
				this.finalizeCurrentThought();
				this.state.phase = 'thinking';
				// Only update status to "Thinking..." if we don't have a recent tool
				// (keeps showing tool status until new action)
				if (!this.state.currentToolName) {
					this.state.statusText = 'Thinking...';
				}
				this.emitState();
				break;

			case 'next_tool_name':
				// Finalize current thought before tool call
				this.finalizeCurrentThought();
				this.state.phase = 'tool_name';
				this.state.currentToolName = ''; // Reset buffer for new tool name
				// Will update status when we get the actual tool name
				break;

			case 'next_tool_args':
				// Tool name is now complete - finalize it
				this.finalizeToolName();
				this.state.phase = 'tool_args';
				break;

			case 'completed':
				// If completed after answer, we're done - stop processing
				if (this.state.phase === 'answer') {
					this.state.phase = 'done';
				}
				// Otherwise, tool completed - might be followed by another thought
				// Keep the tool status until next action
				break;

			case 'answer':
				// Finalize any remaining thought
				this.finalizeCurrentThought();
				this.state.phase = 'answer';
				this.state.isAnswering = true;
				this.state.statusText = 'Composing response...';
				this.emitState();
				break;
		}
	}

	/**
	 * Emit current state to callback
	 */
	private emitState(): void {
		this.onStateChange({ ...this.state });
	}

	/**
	 * Reset the parser for a new stream
	 */
	reset(): void {
		this.buffer = '';
		this.state = {
			phase: 'idle',
			thinkingEntries: [],
			currentThought: '',
			currentToolName: '',
			statusText: 'Thinking...',
			isAnswering: false,
			answerContent: ''
		};
	}

	/**
	 * Get current state (read-only)
	 */
	getState(): Readonly<ParsedStreamState> {
		return this.state;
	}
}
