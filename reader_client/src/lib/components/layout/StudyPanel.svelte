<!--
  StudyPanel Component

  Right-side contextual panel for displaying:
  - Study notes
  - Liturgical notes
  - Variant notes
  - Articles
  - Passage previews (cross-references)
  - Library footnotes

  Appears when annotation/cross-ref is clicked, dismissible.
-->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { layout, type StudyPanelContent } from '$lib/stores/layout.svelte';
	import { favorites } from '$lib/stores/favorites.svelte';
	import { studyContext, type FocusItem } from '$lib/stores/studyContext.svelte';
	import { toast } from '$lib/stores/toast.svelte';
	import { books, passages, type PassageWithAnnotations } from '$lib/api';
	import type { ScriptureRef, PatristicCitation } from '$lib/api';
	import Icon from '$lib/components/ui/Icon.svelte';
	import FavoriteButton from '$lib/components/ui/FavoriteButton.svelte';
	import {
		processScriptureMarkers,
		parseScriptureRef,
		formatScriptureDisplay
	} from '$lib/utils/chatAnnotations';

	// Get content from layout store
	let content = $derived(layout.studyPanelContent);

	// Derive panel title from content type
	let panelTitle = $derived(() => {
		if (!content) return 'Notes';

		switch (content.type) {
			case 'study':
				return 'Study Note';
			case 'liturgical':
				return 'Liturgical Reference';
			case 'variant':
				return 'Manuscript Variant';
			case 'article':
				return 'Article';
			case 'passage':
			case 'scripture-preview':
				return content.title;
			case 'footnote':
				return 'Footnote';
		}
	});

	// Check if content is favorited
	let isFavorited = $derived(() => {
		if (!content) return false;

		if (content.type === 'passage' || content.type === 'scripture-preview') {
			return favorites.isPassageFavorited(
				content.passage.book_id,
				content.passage.chapter,
				content.passage.verse
			);
		}
		if (content.type === 'study') {
			return favorites.isNoteFavorited(content.note.id);
		}
		return false;
	});

	function handleToggleFavorite() {
		if (!content) return;

		if (content.type === 'passage' || content.type === 'scripture-preview') {
			favorites.togglePassage({
				book: content.passage.book_id,
				bookName: content.title.split(' ')[0],
				chapter: content.passage.chapter,
				verse: content.passage.verse,
				preview: content.passage.text.replace(/<[^>]*>/g, '').slice(0, 100)
			});
		} else if (content.type === 'study') {
			favorites.toggleNote({
				id: content.note.id,
				type: 'study',
				verseDisplay: content.note.verse_display,
				preview: content.note.text.replace(/<[^>]*>/g, '').slice(0, 100)
			});
		}
	}

	// Handle cross-reference click - fetch passage and display
	async function handleRefClick(ref: ScriptureRef) {
		try {
			const passage = await passages.get(ref.id, 'annotations');
			layout.showPassagePreview(passage as PassageWithAnnotations, ref.display);
		} catch (e) {
			console.error('Failed to fetch passage:', e);
		}
	}

	// Navigate to full passage
	function handleGoToPassage() {
		if (!content) return;
		if (content.type === 'passage' || content.type === 'scripture-preview') {
			const { book_id, chapter, verse } = content.passage;
			goto(`/read/${book_id}/${chapter}#osb-${book_id}-${chapter}-${verse}`);
			layout.closeStudyPanel();
		}
	}

	// Handle scripture link clicks in article content
	let loadingScriptureRef = $state<string | null>(null);

	async function handleArticleClick(e: MouseEvent) {
		const target = e.target as HTMLElement;

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

				const response = await books.getVerseRange(
					ref.bookId,
					ref.chapter,
					verse,
					verseEnd,
					'annotations'
				);
				if (response.passages.length > 0) {
					const passage = response.passages[0] as PassageWithAnnotations;
					const displayText = formatScriptureDisplay(ref);
					layout.showPassagePreview(passage, displayText);
				}
			} catch (error) {
				console.error('Failed to load scripture passage:', error);
			} finally {
				loadingScriptureRef = null;
				target.classList.remove('loading');
			}
		}
	}

	// Helper for patristic citations
	function getPatristicName(citation: string | PatristicCitation): string {
		if (typeof citation === 'string') {
			return citation;
		}
		return citation.name;
	}

	// Process article text to convert scripture markers to clickable links
	function processNoteContent(text: string): string {
		return processScriptureMarkers(text);
	}

	// ─────────────────────────────────────────────────────────────────────────
	// Context Management
	// ─────────────────────────────────────────────────────────────────────────

	// Check if current study note is in reading context
	const isStudyNoteInContext = $derived(() => {
		if (!content || content.type !== 'study') return false;
		return studyContext.focusStack.some(
			(item) => item.type === 'osb-note' && item.noteId === content.note.id
		);
	});

	// Check if current liturgical note is in reading context
	const isLiturgicalNoteInContext = $derived(() => {
		if (!content || content.type !== 'liturgical') return false;
		return studyContext.focusStack.some(
			(item) => item.type === 'osb-note' && item.noteId === content.note.id
		);
	});

	// Check if current variant note is in reading context
	const isVariantNoteInContext = $derived(() => {
		if (!content || content.type !== 'variant') return false;
		return studyContext.focusStack.some(
			(item) => item.type === 'osb-note' && item.noteId === content.note.id
		);
	});

	// Check if current article is in reading context
	const isArticleInContext = $derived(() => {
		if (!content || content.type !== 'article') return false;
		return studyContext.focusStack.some(
			(item) => item.type === 'osb-article' && item.articleId === content.article.id
		);
	});

	// Check if current passage is in reading context
	const isPassageInContext = $derived(() => {
		if (!content || (content.type !== 'passage' && content.type !== 'scripture-preview')) return false;
		return studyContext.focusStack.some(
			(item) => item.type === 'verse' && item.passageId === content.passage.id
		);
	});

	// Check if current footnote is in reading context
	const isFootnoteInContext = $derived(() => {
		if (!content || content.type !== 'footnote') return false;
		return studyContext.focusStack.some(
			(item) => item.type === 'library-footnote' && item.footnoteId === content.footnote.id
		);
	});

	// Build full verse display with book name
	function getFullVerseDisplay(verseDisplay: string): string {
		const bookName = studyContext.scripturePosition?.bookName;
		if (bookName && !verseDisplay.includes(bookName)) {
			return `${bookName} ${verseDisplay}`;
		}
		return verseDisplay;
	}

	// Helper to add to context with limit check
	function addToContext(item: FocusItem): void {
		const success = studyContext.pushFocus(item);
		if (!success) {
			toast.warning('Context limit reached (15 items). Remove some items first.');
		}
	}

	// Add study note to context
	function handleAddStudyNoteToContext() {
		if (!content || content.type !== 'study') return;
		const note = content.note;
		const focusItem: FocusItem = {
			type: 'osb-note',
			noteType: 'study',
			noteId: note.id,
			verseDisplay: getFullVerseDisplay(note.verse_display),
			text: note.text.replace(/<[^>]*>/g, '').slice(0, 300)
		};
		if (isStudyNoteInContext()) {
			studyContext.removeFocus(focusItem);
		} else {
			addToContext(focusItem);
		}
	}

	// Add liturgical note to context
	function handleAddLiturgicalNoteToContext() {
		if (!content || content.type !== 'liturgical') return;
		const note = content.note;
		const focusItem: FocusItem = {
			type: 'osb-note',
			noteType: 'liturgical',
			noteId: note.id,
			verseDisplay: getFullVerseDisplay(note.verse_display),
			text: note.text.replace(/<[^>]*>/g, '').slice(0, 300)
		};
		if (isLiturgicalNoteInContext()) {
			studyContext.removeFocus(focusItem);
		} else {
			addToContext(focusItem);
		}
	}

	// Add variant note to context
	function handleAddVariantNoteToContext() {
		if (!content || content.type !== 'variant') return;
		const note = content.note;
		const focusItem: FocusItem = {
			type: 'osb-note',
			noteType: 'variant',
			noteId: note.id,
			verseDisplay: getFullVerseDisplay(note.verse_display),
			text: note.text.replace(/<[^>]*>/g, '').slice(0, 300)
		};
		if (isVariantNoteInContext()) {
			studyContext.removeFocus(focusItem);
		} else {
			addToContext(focusItem);
		}
	}

	// Add article to context
	function handleAddArticleToContext() {
		if (!content || content.type !== 'article') return;
		const article = content.article;
		const focusItem: FocusItem = {
			type: 'osb-article',
			articleId: article.id,
			text: article.text.replace(/<[^>]*>/g, '').slice(0, 300)
		};
		if (isArticleInContext()) {
			studyContext.removeFocus(focusItem);
		} else {
			addToContext(focusItem);
		}
	}

	// Add passage to context
	function handleAddPassageToContext() {
		if (!content || (content.type !== 'passage' && content.type !== 'scripture-preview')) return;
		const passage = content.passage;
		const bookName = studyContext.scripturePosition?.bookName ?? passage.book_id;
		const focusItem: FocusItem = {
			type: 'verse',
			book: passage.book_id,
			bookName,
			chapter: passage.chapter,
			verse: passage.verse,
			passageId: passage.id,
			text: passage.text.replace(/<[^>]*>/g, '').slice(0, 150)
		};
		if (isPassageInContext()) {
			studyContext.removeFocus(focusItem);
		} else {
			addToContext(focusItem);
		}
	}

	// Add footnote to context
	function handleAddFootnoteToContext() {
		if (!content || content.type !== 'footnote') return;
		const footnote = content.footnote;
		const focusItem: FocusItem = {
			type: 'library-footnote',
			footnoteId: footnote.id,
			footnoteType: footnote.type === 'endnote' ? 'endnote' : 'footnote',
			marker: footnote.marker,
			text: footnote.content.replace(/<[^>]*>/g, '').slice(0, 300)
		};
		if (isFootnoteInContext()) {
			studyContext.removeFocus(focusItem);
		} else {
			addToContext(focusItem);
		}
	}
</script>

<div class="study-panel">
	<header class="panel-header">
		<h2 class="panel-title font-ui">{panelTitle()}</h2>
		<div class="panel-actions">
			{#if content && (content.type === 'passage' || content.type === 'scripture-preview' || content.type === 'study')}
				<FavoriteButton isFavorited={isFavorited()} onToggle={handleToggleFavorite} size="sm" />
			{/if}
			<button
				class="close-btn touch-target"
				onclick={() => layout.closeStudyPanel()}
				aria-label="Close panel"
			>
				<Icon name="x" size={18} />
			</button>
		</div>
	</header>

	<div class="panel-content">
		{#if content}
			{#if content.type === 'study'}
				{@const note = content.note}
				<div class="content-section">
					<div class="verse-ref text-muted font-ui">{note.verse_display}</div>
					<div class="note-text scripture-text">{@html note.text}</div>

					{#if note.patristic_citations?.length}
						<div class="subsection">
							<h4 class="subsection-title font-ui">Church Fathers</h4>
							<ul class="tag-list">
								{#each note.patristic_citations as citation}
									<li class="tag tag-burgundy">{getPatristicName(citation)}</li>
								{/each}
							</ul>
						</div>
					{/if}

					{#if note.scripture_refs?.length}
						<div class="subsection">
							<h4 class="subsection-title font-ui">Cross-References</h4>
							<ul class="tag-list">
								{#each note.scripture_refs as ref}
									<li>
										<button class="tag tag-green" onclick={() => handleRefClick(ref)}>
											{ref.display}
										</button>
									</li>
								{/each}
							</ul>
						</div>
					{/if}

					<div class="context-actions">
						<button
							class="context-button touch-target"
							class:in-context={isStudyNoteInContext()}
							onclick={handleAddStudyNoteToContext}
							title={isStudyNoteInContext() ? 'Remove from reading context' : 'Add to reading context'}
						>
							<Icon name={isStudyNoteInContext() ? 'check' : 'plus'} size={16} />
							<span>{isStudyNoteInContext() ? 'In context' : 'Add to context'}</span>
						</button>
					</div>
				</div>
			{:else if content.type === 'liturgical'}
				{@const note = content.note}
				<div class="content-section">
					<div class="verse-ref text-muted font-ui">{note.verse_display}</div>
					<div class="note-text scripture-text">{@html note.text}</div>

					<div class="context-actions">
						<button
							class="context-button touch-target"
							class:in-context={isLiturgicalNoteInContext()}
							onclick={handleAddLiturgicalNoteToContext}
							title={isLiturgicalNoteInContext() ? 'Remove from reading context' : 'Add to reading context'}
						>
							<Icon name={isLiturgicalNoteInContext() ? 'check' : 'plus'} size={16} />
							<span>{isLiturgicalNoteInContext() ? 'In context' : 'Add to context'}</span>
						</button>
					</div>
				</div>
			{:else if content.type === 'variant'}
				{@const note = content.note}
				<div class="content-section">
					<div class="verse-ref text-muted font-ui">{note.verse_display}</div>
					<div class="note-text scripture-text">{@html note.text}</div>

					<div class="context-actions">
						<button
							class="context-button touch-target"
							class:in-context={isVariantNoteInContext()}
							onclick={handleAddVariantNoteToContext}
							title={isVariantNoteInContext() ? 'Remove from reading context' : 'Add to reading context'}
						>
							<Icon name={isVariantNoteInContext() ? 'check' : 'plus'} size={16} />
							<span>{isVariantNoteInContext() ? 'In context' : 'Add to context'}</span>
						</button>
					</div>
				</div>
			{:else if content.type === 'article'}
				{@const article = content.article}
				<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
				<div class="content-section" onclick={handleArticleClick}>
					<div class="note-text scripture-text">{@html processNoteContent(article.text)}</div>

					<div class="context-actions">
						<button
							class="context-button touch-target"
							class:in-context={isArticleInContext()}
							onclick={handleAddArticleToContext}
							title={isArticleInContext() ? 'Remove from reading context' : 'Add to reading context'}
						>
							<Icon name={isArticleInContext() ? 'check' : 'plus'} size={16} />
							<span>{isArticleInContext() ? 'In context' : 'Add to context'}</span>
						</button>
					</div>
				</div>
			{:else if content.type === 'passage' || content.type === 'scripture-preview'}
				{@const passage = content.passage}
				<div class="content-section">
					<div class="passage-preview">
						<span class="verse-num">{passage.verse}</span>
						<span class="verse-text scripture-text">{@html passage.text}</span>
					</div>

					<div class="passage-actions">
						<button
							class="context-button touch-target"
							class:in-context={isPassageInContext()}
							onclick={handleAddPassageToContext}
							title={isPassageInContext() ? 'Remove from reading context' : 'Add to reading context'}
						>
							<Icon name={isPassageInContext() ? 'check' : 'plus'} size={16} />
							<span>{isPassageInContext() ? 'In context' : 'Add to context'}</span>
						</button>
						<button class="go-button touch-target" onclick={handleGoToPassage}>
							<span>Go to passage</span>
							<Icon name="arrow-right" size={18} />
						</button>
					</div>
				</div>
			{:else if content.type === 'footnote'}
				{@const footnote = content.footnote}
				<div class="content-section">
					<div class="footnote-marker text-muted font-ui">
						{footnote.marker}
					</div>
					<div class="note-text scripture-text">{@html footnote.content}</div>

					<div class="context-actions">
						<button
							class="context-button touch-target"
							class:in-context={isFootnoteInContext()}
							onclick={handleAddFootnoteToContext}
							title={isFootnoteInContext() ? 'Remove from reading context' : 'Add to reading context'}
						>
							<Icon name={isFootnoteInContext() ? 'check' : 'plus'} size={16} />
							<span>{isFootnoteInContext() ? 'In context' : 'Add to context'}</span>
						</button>
					</div>
				</div>
			{/if}
		{:else}
			<p class="empty-state text-muted">
				Click an annotation marker or cross-reference to view details here.
			</p>
		{/if}
	</div>
</div>

<style>
	.study-panel {
		display: flex;
		flex-direction: column;
		height: 100%;
		background: var(--color-bg-surface);
	}

	.panel-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--space-3) var(--space-4);
		border-bottom: 1px solid var(--color-border);
		background: var(--color-bg-elevated);
		flex-shrink: 0;
	}

	.panel-title {
		font-size: var(--font-sm);
		font-weight: var(--font-semibold);
		text-transform: uppercase;
		letter-spacing: var(--tracking-wide);
		color: var(--color-text-secondary);
	}

	.panel-actions {
		display: flex;
		align-items: center;
		gap: var(--space-1);
	}

	.close-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: var(--space-2);
		color: var(--color-text-muted);
		border-radius: var(--radius-md);
		transition: color var(--transition-fast), background var(--transition-fast);
	}

	.close-btn:hover {
		color: var(--color-text-primary);
		background: var(--color-bg-hover);
	}

	.panel-content {
		flex: 1;
		overflow-y: auto;
		padding: var(--space-4);
	}

	.content-section {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.verse-ref,
	.footnote-marker {
		font-size: var(--font-sm);
		font-weight: var(--font-semibold);
	}

	.note-text {
		line-height: var(--leading-relaxed);
		white-space: pre-wrap;
	}

	/* Scripture references in notes */
	.note-text :global(.scripture-ref) {
		color: var(--color-gold);
		text-decoration: none;
		border-bottom: 1px dotted var(--color-gold-dim);
		cursor: pointer;
		transition: color var(--transition-fast), border-color var(--transition-fast);
	}

	.note-text :global(.scripture-ref:hover) {
		color: var(--color-gold-bright);
		border-bottom-color: var(--color-gold);
	}

	.note-text :global(.scripture-ref.loading) {
		opacity: 0.5;
		cursor: wait;
	}

	.subsection {
		padding-top: var(--space-3);
		border-top: 1px solid var(--color-border);
	}

	.subsection-title {
		font-size: var(--font-xs);
		font-weight: var(--font-semibold);
		text-transform: uppercase;
		letter-spacing: var(--tracking-wide);
		color: var(--color-text-muted);
		margin-bottom: var(--space-2);
	}

	.tag-list {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
	}

	.tag {
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		padding: var(--space-1) var(--space-2);
		border-radius: var(--radius-sm);
		transition: background var(--transition-fast);
	}

	.tag-burgundy {
		color: var(--color-burgundy-light);
		background: var(--color-burgundy-dark);
	}

	.tag-green {
		color: var(--color-annotation-crossref);
		background: rgba(91, 138, 114, 0.15);
	}

	button.tag-green:hover {
		background: rgba(91, 138, 114, 0.25);
	}

	.passage-preview {
		line-height: var(--leading-relaxed);
	}

	.verse-num {
		font-family: var(--font-ui);
		font-size: var(--font-xs);
		font-weight: var(--font-semibold);
		color: var(--color-gold);
		vertical-align: super;
		margin-right: 0.3em;
	}

	.go-button {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: var(--space-2);
		width: 100%;
		padding: var(--space-3) var(--space-4);
		background: var(--color-bg-elevated);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		color: var(--color-text-secondary);
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		font-weight: var(--font-medium);
		transition: background var(--transition-fast), color var(--transition-fast),
			border-color var(--transition-fast);
	}

	.go-button:hover {
		background: var(--color-bg-hover);
		color: var(--color-gold);
		border-color: var(--color-gold-dim);
	}

	.context-actions {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		padding-top: var(--space-4);
		border-top: 1px solid var(--color-border);
	}

	.passage-actions {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.context-button {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: var(--space-2);
		width: 100%;
		padding: var(--space-3) var(--space-4);
		background: var(--color-bg-elevated);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		color: var(--color-text-secondary);
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		font-weight: var(--font-medium);
		transition: background var(--transition-fast), color var(--transition-fast),
			border-color var(--transition-fast);
	}

	.context-button:hover {
		background: var(--color-bg-hover);
		color: var(--color-gold);
		border-color: var(--color-gold-dim);
	}

	.context-button.in-context {
		color: var(--color-gold);
		border-color: var(--color-gold-dim);
		background: rgba(212, 175, 55, 0.1);
	}

	.empty-state {
		text-align: center;
		padding: var(--space-8);
		font-family: var(--font-ui);
		font-size: var(--font-sm);
	}
</style>
