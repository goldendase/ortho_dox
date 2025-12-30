<!--
  NodeContent Component

  Renders library node content with resolved components:
  - [footnote[id]] → clickable footnote markers
  - [image[id]] → inline images with captions
  - [quote[id]] → styled blockquotes
  - [epigraph[id]] → chapter epigraphs
  - [SCRIPTURE[book:chapter:verse]] → clickable scripture links (e.g., "Luke 11:23")

  Paragraphs are clickable to toggle in reading context (focusStack).
-->
<script lang="ts">
	import type { LibraryNodeLeaf, LibraryComponents, PassageWithAnnotations } from '$lib/api';
	import { books } from '$lib/api';
	import FootnoteMarker from './FootnoteMarker.svelte';
	import { ui, libraryStore } from '$lib/stores';
	import { studyContext, type FocusItem } from '$lib/stores/studyContext.svelte';
	import { layout } from '$lib/stores/layout.svelte';
	import { toast } from '$lib/stores/toast.svelte';
	import { parseScriptureRef, formatScriptureDisplay, type ScriptureRef } from '$lib/utils/chatAnnotations';

	interface Props {
		node: LibraryNodeLeaf;
	}

	let { node }: Props = $props();

	// Build lookup maps for components
	const components = $derived(node.components ?? {
		footnotes: [],
		endnotes: [],
		images: [],
		quotes: [],
		epigraphs: [],
		poems: [],
		letters: []
	});

	const footnotesMap = $derived(
		new Map([
			...components.footnotes.map((f) => [f.id, f] as const),
			...components.endnotes.map((f) => [f.id, f] as const)
		])
	);

	const imagesMap = $derived(
		new Map(components.images.map((i) => [i.id, i] as const))
	);

	const quotesMap = $derived(
		new Map([
			...components.quotes.map((q) => [q.id, q] as const),
			...components.epigraphs.map((q) => [q.id, q] as const)
		])
	);

	// Convert plain text to HTML paragraphs with anchored IDs
	function textToHtml(text: string): string {
		// Split on double newlines for paragraphs
		const paragraphs = text.split(/\n\n+/);
		let pIndex = 0;
		return paragraphs
			.map(p => {
				// Convert single newlines to <br> within paragraphs
				const withBreaks = p.trim().replace(/\n/g, '<br>');
				if (withBreaks) {
					pIndex++;
					return `<p id="od-lib-p${pIndex}">${withBreaks}</p>`;
				}
				return '';
			})
			.filter(Boolean)
			.join('\n');
	}

	// Process content to replace markers with rendered components
	function processContent(content: string): string {
		// Convert plain text to HTML paragraphs first
		let processed = textToHtml(content);

		// Replace footnote markers with placeholder spans
		processed = processed.replace(
			/\[footnote\[([^\]]+)\]\]/g,
			(_, id) => {
				const fn = footnotesMap.get(id);
				if (fn) {
					return `<span class="footnote-placeholder" data-id="${id}" data-marker="${fn.marker}"></span>`;
				}
				return '';
			}
		);

		// Replace endnote markers
		processed = processed.replace(
			/\[endnote\[([^\]]+)\]\]/g,
			(_, id) => {
				const fn = footnotesMap.get(id);
				if (fn) {
					return `<span class="footnote-placeholder" data-id="${id}" data-marker="${fn.marker}"></span>`;
				}
				return '';
			}
		);

		// Replace image markers with figure elements
		processed = processed.replace(
			/\[image\[([^\]]+)\]\]/g,
			(_, id) => {
				const img = imagesMap.get(id);
				if (img) {
					const caption = img.caption ? `<figcaption>${escapeHtml(img.caption)}</figcaption>` : '';
					const alt = escapeHtml(img.alt_text || img.caption || 'Image');
					return `<figure class="embedded-image"><img src="${img.image_path}" alt="${alt}" loading="lazy" />${caption}</figure>`;
				}
				return '';
			}
		);

		// Replace quote markers with blockquotes
		processed = processed.replace(
			/\[quote\[([^\]]+)\]\]/g,
			(_, id) => {
				const quote = quotesMap.get(id);
				if (quote) {
					const attribution = quote.attribution
						? `<cite>— ${escapeHtml(quote.attribution)}</cite>`
						: '';
					return `<blockquote class="embedded-quote">${escapeHtml(quote.content)}${attribution}</blockquote>`;
				}
				return '';
			}
		);

		// Replace epigraph markers
		processed = processed.replace(
			/\[epigraph\[([^\]]+)\]\]/g,
			(_, id) => {
				const epigraph = quotesMap.get(id);
				if (epigraph) {
					const attribution = epigraph.attribution
						? `<cite>— ${escapeHtml(epigraph.attribution)}</cite>`
						: '';
					return `<div class="epigraph"><blockquote>${escapeHtml(epigraph.content)}</blockquote>${attribution}</div>`;
				}
				return '';
			}
		);

		// Replace scripture markers with clickable links
		// Format: [SCRIPTURE[book:chapter:verse]] or [SCRIPTURE[book:chapter:start-end]]
		processed = processed.replace(
			/\[SCRIPTURE\[([^\]]+)\]\]/g,
			(_, refValue) => {
				const ref = parseScriptureRef(refValue);
				const displayText = formatScriptureDisplay(ref);
				const verse = ref.verseStart ?? 1;
				const href = `/read/${ref.bookId}/${ref.chapter}#osb-${ref.bookId}-${ref.chapter}-${verse}`;
				return `<a href="${href}" class="scripture-ref" data-scripture="${escapeHtml(refValue)}">${escapeHtml(displayText)}</a>`;
			}
		);

		return processed;
	}

	function escapeHtml(text: string): string {
		return text
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;')
			.replace(/"/g, '&quot;')
			.replace(/'/g, '&#039;');
	}

	const processedContent = $derived(processContent(node.content));

	// Track loading state for scripture refs
	let loadingScriptureRef = $state<string | null>(null);

	// Check if a paragraph is in the reading context
	function isParagraphInContext(paragraphIndex: number): boolean {
		return studyContext.focusStack.some(
			(item) =>
				item.type === 'paragraph' &&
				item.workId === node.work_id &&
				item.nodeId === node.id &&
				item.index === paragraphIndex
		);
	}

	// Handle paragraph click - toggle in/out of focusStack
	function handleParagraphClick(paragraphEl: HTMLElement) {
		const id = paragraphEl.id;
		const match = id.match(/^od-lib-p(\d+)$/);
		if (!match) return;

		const paragraphIndex = parseInt(match[1], 10);
		const text = paragraphEl.textContent?.slice(0, 150) ?? '';
		const nodeTitle = node.title || libraryStore.position?.nodeTitle || node.id;
		const workTitle = libraryStore.currentWork?.title || node.work_id;

		// Build focus item for this paragraph
		const focusItem: FocusItem = {
			type: 'paragraph',
			workId: node.work_id,
			workTitle,
			nodeId: node.id,
			nodeTitle,
			index: paragraphIndex,
			text
		};

		// Check if this paragraph is already in context
		const isInContext = isParagraphInContext(paragraphIndex);

		if (isInContext) {
			// Remove from context
			studyContext.removeFocus(focusItem);
			paragraphEl.classList.remove('selected');
		} else {
			// Add to context
			const success = studyContext.pushFocus(focusItem);
			if (success) {
				paragraphEl.classList.add('selected');
			} else {
				toast.warning('Context limit reached (15 items). Remove some items first.');
			}
		}
	}

	// Update paragraph visual state based on focusStack changes
	// This is needed because the HTML is generated, not reactive
	$effect(() => {
		const stack = studyContext.focusStack;
		// Get all paragraph elements
		const paragraphs = document.querySelectorAll('[id^="od-lib-p"]');
		paragraphs.forEach((el) => {
			const match = el.id.match(/^od-lib-p(\d+)$/);
			if (!match) return;
			const idx = parseInt(match[1], 10);
			const inContext = stack.some(
				(item) =>
					item.type === 'paragraph' &&
					item.workId === node.work_id &&
					item.nodeId === node.id &&
					item.index === idx
			);
			if (inContext) {
				el.classList.add('selected');
			} else {
				el.classList.remove('selected');
			}
		});
	});

	// Handle footnote and scripture ref clicks via event delegation
	async function handleContentClick(e: MouseEvent) {
		const target = e.target as HTMLElement;

		// Check if clicked on a footnote marker
		if (target.classList.contains('footnote-marker')) {
			const id = target.dataset.id;
			if (id) {
				const fn = footnotesMap.get(id);
				if (fn) {
					// Show footnote in side panel
					ui.showArticle({
						id: fn.id,
						type: 'article',
						text: fn.content
					});
				}
			}
			return;
		}

		// Check if clicked on a scripture reference
		if (target.classList.contains('scripture-ref')) {
			e.preventDefault();
			const refValue = target.dataset.scripture;
			if (!refValue || loadingScriptureRef) return;

			loadingScriptureRef = refValue;
			target.classList.add('loading');

			try {
				const ref = parseScriptureRef(refValue);
				const verse = ref.verseStart ?? 1;
				const verseEnd = ref.verseEnd ?? verse;

				// Fetch the passage(s) with annotations
				const response = await books.getVerseRange(ref.bookId, ref.chapter, verse, verseEnd, 'annotations');
				if (response.passages.length > 0) {
					const passage = response.passages[0] as PassageWithAnnotations;
					const displayText = formatScriptureDisplay(ref);
					ui.showPassage(passage, displayText);
				}
			} catch (error) {
				console.error('Failed to load scripture passage:', error);
			} finally {
				loadingScriptureRef = null;
				target.classList.remove('loading');
			}
			return;
		}

		// Check if clicked on a paragraph (or inside one)
		// Find closest paragraph with od-lib-p* id
		const paragraphEl = target.closest('[id^="od-lib-p"]') as HTMLElement | null;
		if (paragraphEl) {
			handleParagraphClick(paragraphEl);
		}
	}
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div class="node-content" onclick={handleContentClick}>
	{#if node.title}
		<h1 class="node-title">{node.title}</h1>
	{/if}

	<!-- eslint-disable-next-line svelte/no-at-html-tags -->
	<div class="content-body">{@html processedContent}</div>

	<!-- Render footnote markers via Svelte components for interactivity -->
	{#each Array.from(footnotesMap.values()) as fn (fn.id)}
		<FootnoteMarker
			id={fn.id}
			marker={fn.marker}
			content={fn.content}
		/>
	{/each}
</div>

<style>
	.node-content {
		color: var(--color-text-primary);
	}

	.node-title {
		font-size: 1.5em;
		font-weight: var(--font-medium);
		color: var(--color-gold);
		margin: 0 0 var(--space-6);
		text-align: center;
	}

	.content-body {
		/* Content styles handled by LibraryReader global styles */
	}

	/* Selectable paragraphs */
	.content-body :global(p[id^="od-lib-p"]) {
		cursor: pointer;
		padding-left: var(--space-2);
		margin-left: calc(-1 * var(--space-2));
		border-left: 2px solid transparent;
		border-radius: var(--radius-sm);
		transition: border-color var(--transition-fast), background var(--transition-fast);
	}

	.content-body :global(p[id^="od-lib-p"]:hover) {
		background: rgba(201, 162, 39, 0.03);
	}

	.content-body :global(p[id^="od-lib-p"].selected) {
		border-left-color: var(--color-gold);
		background: rgba(201, 162, 39, 0.08);
	}

	/* Footnote placeholders - will be enhanced with JS */
	.content-body :global(.footnote-placeholder) {
		display: none;
	}

	/* Footnote markers - added via JS */
	.content-body :global(.footnote-marker) {
		display: inline;
		font-size: 0.75em;
		vertical-align: super;
		color: var(--color-gold);
		cursor: pointer;
		padding: 0 2px;
		transition: color var(--transition-fast);
	}

	.content-body :global(.footnote-marker:hover) {
		color: var(--color-gold-bright);
	}

	/* Embedded images */
	.content-body :global(.embedded-image) {
		margin: var(--space-4) 0;
		text-align: center;
		break-inside: avoid;
	}

	.content-body :global(.embedded-image img) {
		max-width: 100%;
		max-height: 50vh;
		border-radius: var(--radius-md);
	}

	/* Epigraphs */
	.content-body :global(.epigraph) {
		margin: 0 0 var(--space-6);
		padding: var(--space-4);
		text-align: center;
		font-style: italic;
		color: var(--color-text-secondary);
	}

	.content-body :global(.epigraph blockquote) {
		margin: 0;
		padding: 0;
		border: none;
	}

	.content-body :global(.epigraph cite) {
		display: block;
		margin-top: var(--space-2);
		font-size: var(--font-sm);
	}

	/* Embedded quotes */
	.content-body :global(.embedded-quote) {
		margin: var(--space-4) var(--space-4);
		padding: var(--space-3) var(--space-4);
		border-left: 3px solid var(--color-gold-dim);
		background: var(--color-bg-elevated);
		border-radius: 0 var(--radius-md) var(--radius-md) 0;
	}

	.content-body :global(.embedded-quote cite) {
		display: block;
		margin-top: var(--space-2);
		font-size: var(--font-sm);
		color: var(--color-text-muted);
	}

	/* Scripture reference links */
	.content-body :global(.scripture-ref) {
		color: var(--color-gold);
		text-decoration: none;
		border-bottom: 1px dotted var(--color-gold-dim);
		transition: color var(--transition-fast), border-color var(--transition-fast);
	}

	.content-body :global(.scripture-ref:hover) {
		color: var(--color-gold-bright);
		border-bottom-color: var(--color-gold);
	}

	.content-body :global(.scripture-ref.loading) {
		opacity: 0.5;
		cursor: wait;
	}
</style>
