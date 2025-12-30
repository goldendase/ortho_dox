<!--
  Chat Message Content Component

  Parses chat message content with markdown formatting and renders inline annotations
  as clickable links. Handles navigation to scripture references and opening
  annotations in the side panel.

  Uses event delegation to handle clicks on annotation buttons rendered within
  the markdown HTML.
-->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { getAnnotation, ApiError } from '$lib/api';
	import { ui, reader } from '$lib/stores';
	import type { ChatAnnotation } from '$lib/utils/chatAnnotations';
	import { parseMarkdownWithAnnotations } from '$lib/utils/markdown';

	interface Props {
		content: string;
	}

	let { content }: Props = $props();

	// Parse message into HTML with embedded annotation buttons
	const parsed = $derived(parseMarkdownWithAnnotations(content));

	// Track loading state for annotation fetches
	let loadingAnnotationId = $state<string | null>(null);

	/**
	 * Handle click on a scripture reference
	 * Navigates to the chapter and selects the verse
	 */
	async function handleScriptureClick(annotation: ChatAnnotation) {
		const ref = annotation.scriptureRef;
		if (!ref) return;

		const { bookId, chapter, verseStart } = ref;

		// Check if we're already on this chapter
		const currentPos = reader.position;
		const isSameChapter =
			currentPos?.book === bookId && currentPos?.chapter === chapter;

		if (isSameChapter && verseStart !== null) {
			// Same chapter - just scroll to and select the verse
			const verseEl = document.getElementById(`osb-${bookId}-${chapter}-${verseStart}`);
			if (verseEl) {
				verseEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
				// Simulate clicking the verse to select it
				verseEl.click();
			}
		} else {
			// Different chapter - navigate with select param
			const verse = verseStart;
			let url = `/read/${bookId}/${chapter}`;
			if (verse !== null) {
				url += `?select=${verse}`;
			}
			await goto(url);
		}
	}

	/**
	 * Handle click on a book reference
	 * Navigates to chapter 1 of the book
	 */
	async function handleBookClick(annotation: ChatAnnotation) {
		const bookId = annotation.value;
		await goto(`/read/${bookId}/1`);
	}

	/**
	 * Handle click on an annotation reference (study, liturgical, variant, citation, article)
	 * Fetches the annotation and shows it in the side panel
	 */
	async function handleAnnotationClick(annotation: ChatAnnotation, buttonId: string) {
		const annotationId = annotation.value;

		// Don't re-fetch if already loading
		if (loadingAnnotationId === buttonId) return;

		loadingAnnotationId = buttonId;

		try {
			const result = await getAnnotation(annotationId);

			// Show in side panel based on type
			switch (result.type) {
				case 'study':
					ui.showStudyNote(result);
					break;
				case 'liturgical':
					ui.showLiturgicalNote(result);
					break;
				case 'variant':
					ui.showVariantNote(result);
					break;
				case 'article':
					ui.showArticle(result);
					break;
				default:
					console.warn(`Unhandled annotation type: ${result.type}`);
			}
		} catch (error) {
			if (ApiError.isNotFound(error)) {
				console.warn(`Annotation not found: ${annotationId}`);
			} else {
				console.error('Failed to fetch annotation:', error);
			}
		} finally {
			loadingAnnotationId = null;
		}
	}

	/**
	 * Handle click on any annotation button via event delegation
	 */
	function handleClick(event: MouseEvent) {
		const target = event.target as HTMLElement;
		const button = target.closest('button[data-annotation]') as HTMLButtonElement | null;

		if (!button) return;

		const dataAttr = button.getAttribute('data-annotation');
		const buttonId = button.getAttribute('data-annotation-id');

		if (!dataAttr || !buttonId) return;

		try {
			const annotation = JSON.parse(decodeURIComponent(dataAttr)) as ChatAnnotation;

			switch (annotation.type) {
				case 'scripture':
					handleScriptureClick(annotation);
					break;
				case 'book':
					handleBookClick(annotation);
					break;
				case 'study':
				case 'liturgical':
				case 'variant':
				case 'citation':
				case 'article':
					handleAnnotationClick(annotation, buttonId);
					break;
			}
		} catch (e) {
			console.error('Failed to parse annotation data:', e);
		}
	}
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div class="markdown-content" onclick={handleClick}>
	{@html parsed.html}
</div>

<style>
	/* ─────────────────────────────────────────────────────
	   Markdown Content Container
	   ───────────────────────────────────────────────────── */
	.markdown-content {
		font-size: var(--text-size, 1rem);
		line-height: var(--leading-relaxed);
		color: var(--color-text-primary);
	}

	/* Paragraphs */
	.markdown-content :global(p) {
		margin: 0 0 var(--space-3) 0;
	}

	.markdown-content :global(p:last-child) {
		margin-bottom: 0;
	}

	/* Headings */
	.markdown-content :global(h1),
	.markdown-content :global(h2),
	.markdown-content :global(h3),
	.markdown-content :global(h4),
	.markdown-content :global(h5),
	.markdown-content :global(h6) {
		font-family: var(--font-ui);
		font-weight: var(--font-semibold);
		color: var(--color-text-primary);
		margin: var(--space-4) 0 var(--space-2) 0;
		line-height: var(--leading-tight);
	}

	.markdown-content :global(h1:first-child),
	.markdown-content :global(h2:first-child),
	.markdown-content :global(h3:first-child),
	.markdown-content :global(h4:first-child) {
		margin-top: 0;
	}

	.markdown-content :global(h1) {
		font-size: var(--font-xl);
		border-bottom: 1px solid var(--color-border);
		padding-bottom: var(--space-2);
	}

	.markdown-content :global(h2) {
		font-size: var(--font-lg);
		color: var(--color-gold);
	}

	.markdown-content :global(h3) {
		font-size: var(--font-base);
		text-transform: uppercase;
		letter-spacing: var(--tracking-wide);
		color: var(--color-text-secondary);
	}

	.markdown-content :global(h4),
	.markdown-content :global(h5),
	.markdown-content :global(h6) {
		font-size: var(--font-sm);
		color: var(--color-text-secondary);
	}

	/* Lists */
	.markdown-content :global(ul),
	.markdown-content :global(ol) {
		margin: 0 0 var(--space-3) 0;
		padding-left: var(--space-5);
	}

	.markdown-content :global(li) {
		margin-bottom: var(--space-1);
	}

	.markdown-content :global(li:last-child) {
		margin-bottom: 0;
	}

	.markdown-content :global(ul) {
		list-style-type: disc;
	}

	.markdown-content :global(ol) {
		list-style-type: decimal;
	}

	/* Nested lists */
	.markdown-content :global(li ul),
	.markdown-content :global(li ol) {
		margin-top: var(--space-1);
		margin-bottom: 0;
	}

	/* Blockquotes */
	.markdown-content :global(blockquote) {
		margin: var(--space-3) 0;
		padding: var(--space-3) var(--space-4);
		border-left: 3px solid var(--color-gold-dim);
		background: var(--color-bg-surface);
		color: var(--color-text-secondary);
		font-style: italic;
	}

	.markdown-content :global(blockquote p:last-child) {
		margin-bottom: 0;
	}

	/* Code */
	.markdown-content :global(code) {
		font-family: var(--font-mono, 'SF Mono', Monaco, 'Cascadia Code', monospace);
		font-size: 0.9em;
		padding: 0.15em 0.4em;
		background: var(--color-bg-elevated);
		border-radius: var(--radius-sm);
		color: var(--color-gold);
	}

	.markdown-content :global(pre) {
		margin: var(--space-3) 0;
		padding: var(--space-3) var(--space-4);
		background: var(--color-bg-elevated);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		overflow-x: auto;
	}

	.markdown-content :global(pre code) {
		padding: 0;
		background: none;
		font-size: var(--font-sm);
		color: var(--color-text-primary);
	}

	/* Links */
	.markdown-content :global(a) {
		color: var(--color-gold);
		text-decoration: underline;
		text-decoration-style: dotted;
		text-underline-offset: 2px;
		transition: color var(--transition-fast);
	}

	.markdown-content :global(a:hover) {
		color: var(--color-gold-bright);
		text-decoration-style: solid;
	}

	/* Horizontal rules */
	.markdown-content :global(hr) {
		margin: var(--space-4) 0;
		border: none;
		border-top: 1px solid var(--color-border);
	}

	/* Tables */
	.markdown-content :global(table) {
		width: 100%;
		margin: var(--space-3) 0;
		border-collapse: collapse;
		font-size: var(--font-sm);
	}

	.markdown-content :global(th),
	.markdown-content :global(td) {
		padding: var(--space-2) var(--space-3);
		border: 1px solid var(--color-border);
		text-align: left;
	}

	.markdown-content :global(th) {
		background: var(--color-bg-elevated);
		font-family: var(--font-ui);
		font-weight: var(--font-semibold);
		color: var(--color-text-secondary);
	}

	.markdown-content :global(tr:nth-child(even) td) {
		background: var(--color-bg-surface);
	}

	/* Strong and emphasis */
	.markdown-content :global(strong),
	.markdown-content :global(b) {
		font-weight: var(--font-semibold);
		color: var(--color-text-primary);
	}

	.markdown-content :global(em),
	.markdown-content :global(i) {
		font-style: italic;
	}

	.markdown-content :global(mark) {
		background: rgba(201, 162, 39, 0.25);
		color: inherit;
		padding: 0.1em 0.2em;
		border-radius: var(--radius-sm);
	}

	/* ─────────────────────────────────────────────────────
	   Annotation Links (rendered via {@html})
	   ───────────────────────────────────────────────────── */
	.markdown-content :global(.annotation-link) {
		/* Reset button styles */
		background: none;
		border: none;
		padding: 0;
		margin: 0;
		font: inherit;

		/* Link styling */
		color: var(--color-gold);
		text-decoration: underline;
		text-decoration-style: dotted;
		text-underline-offset: 2px;
		cursor: pointer;
		transition: color var(--transition-fast), opacity var(--transition-fast);
	}

	.markdown-content :global(.annotation-link:hover) {
		color: var(--color-gold-bright, #d4af37);
		text-decoration-style: solid;
	}

	.markdown-content :global(.annotation-link:focus-visible) {
		outline: 2px solid var(--color-gold-dim);
		outline-offset: 2px;
		border-radius: var(--radius-sm);
	}

	.markdown-content :global(.annotation-link.loading) {
		opacity: 0.6;
		cursor: wait;
	}

	/* Type-specific colors */
	.markdown-content :global(.ref-scripture) {
		color: var(--color-gold);
	}

	.markdown-content :global(.ref-study) {
		color: var(--color-annotation-study, var(--color-gold));
	}

	.markdown-content :global(.ref-liturgical) {
		color: var(--color-annotation-liturgical, #7eb8da);
	}

	.markdown-content :global(.ref-variant) {
		color: var(--color-annotation-variant, #a8a29e);
	}

	.markdown-content :global(.ref-citation) {
		color: var(--color-annotation-citation, #c9a227);
	}

	.markdown-content :global(.ref-article) {
		color: var(--color-annotation-article, #c084fc);
	}
</style>
