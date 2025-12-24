/**
 * Markdown Utility
 *
 * Parses markdown content while preserving custom annotation syntax.
 * Annotations are converted to data-attributed buttons that can be
 * handled via event delegation in the component.
 */
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import {
	parseMessageSegments,
	getAnnotationDisplayText,
	type ChatAnnotation
} from './chatAnnotations';

// Configure marked for safe, consistent output
marked.setOptions({
	gfm: true, // GitHub-flavored markdown
	breaks: true // Convert \n to <br>
});

// Placeholder format that survives markdown parsing
// Using ~~ which is strikethrough in GFM but we'll replace before that matters
// Actually, use a format that markdown won't touch at all
const PLACEHOLDER_PREFIX = 'XANNX';
const PLACEHOLDER_SUFFIX = 'XNNAX';

/**
 * Parse markdown content with embedded annotations.
 * Returns sanitized HTML with annotation buttons that have data attributes.
 * The component should use event delegation to handle button clicks.
 */
export function parseMarkdownWithAnnotations(content: string): {
	html: string;
	annotations: Map<string, ChatAnnotation>;
} {
	// First, extract all annotations and replace with placeholders
	const annotations = new Map<string, ChatAnnotation>();
	const segments = parseMessageSegments(content);

	let textWithPlaceholders = '';
	let annotationIndex = 0;

	segments.forEach((segment) => {
		if (segment.type === 'text') {
			textWithPlaceholders += segment.content;
		} else if (segment.annotation) {
			// Store annotation with unique ID
			const id = `ann_${annotationIndex++}`;
			annotations.set(id, segment.annotation);
			textWithPlaceholders += `${PLACEHOLDER_PREFIX}${id}${PLACEHOLDER_SUFFIX}`;
		}
	});

	// Parse markdown
	const rawHtml = marked.parse(textWithPlaceholders, { async: false }) as string;

	// Replace placeholders with button elements BEFORE sanitization
	// This way DOMPurify will validate the buttons
	let htmlWithButtons = rawHtml;
	const placeholderRegex = new RegExp(
		`${escapeRegex(PLACEHOLDER_PREFIX)}(ann_\\d+)${escapeRegex(PLACEHOLDER_SUFFIX)}`,
		'g'
	);

	htmlWithButtons = htmlWithButtons.replace(placeholderRegex, (_, id) => {
		const annotation = annotations.get(id);
		if (!annotation) return '';

		const displayText = getAnnotationDisplayText(annotation);
		const typeClass = getAnnotationTypeClass(annotation.type);

		// Encode annotation data as JSON in data attribute
		const dataJson = encodeURIComponent(JSON.stringify({
			type: annotation.type,
			value: annotation.value,
			scriptureRef: annotation.scriptureRef
		}));

		return `<button class="annotation-link ${typeClass}" data-annotation="${dataJson}" data-annotation-id="${id}">${escapeHtml(displayText)}</button>`;
	});

	// Sanitize HTML, allowing our button elements
	const cleanHtml = DOMPurify.sanitize(htmlWithButtons, {
		ALLOWED_TAGS: [
			'p', 'br', 'strong', 'b', 'em', 'i', 'u', 's', 'del',
			'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
			'ul', 'ol', 'li',
			'blockquote', 'pre', 'code',
			'a', 'hr',
			'table', 'thead', 'tbody', 'tr', 'th', 'td',
			'sup', 'sub', 'mark',
			'button' // Allow our annotation buttons
		],
		ALLOWED_ATTR: [
			'href', 'title', 'class', 'target', 'rel',
			'data-annotation', 'data-annotation-id' // Allow our data attributes
		]
	});

	return { html: cleanHtml, annotations };
}

/**
 * Simple markdown parse without annotation handling.
 * Useful for content that doesn't contain annotations.
 */
export function parseMarkdown(content: string): string {
	const rawHtml = marked.parse(content, { async: false }) as string;
	return DOMPurify.sanitize(rawHtml, {
		ALLOWED_TAGS: [
			'p', 'br', 'strong', 'b', 'em', 'i', 'u', 's', 'del',
			'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
			'ul', 'ol', 'li',
			'blockquote', 'pre', 'code',
			'a', 'hr',
			'table', 'thead', 'tbody', 'tr', 'th', 'td',
			'sup', 'sub', 'mark'
		],
		ALLOWED_ATTR: ['href', 'title', 'class', 'target', 'rel']
	});
}

/**
 * Get CSS class for annotation type
 */
function getAnnotationTypeClass(type: ChatAnnotation['type']): string {
	switch (type) {
		case 'scripture':
		case 'book':
			return 'ref-scripture';
		case 'study':
			return 'ref-study';
		case 'liturgical':
			return 'ref-liturgical';
		case 'variant':
			return 'ref-variant';
		case 'citation':
			return 'ref-citation';
		case 'article':
			return 'ref-article';
		default:
			return '';
	}
}

/**
 * Escape special regex characters in a string
 */
function escapeRegex(str: string): string {
	return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Escape HTML special characters
 */
function escapeHtml(str: string): string {
	return str
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;')
		.replace(/'/g, '&#039;');
}
