<!--
  Verse Component

  Renders a single verse with:
  - Entire verse clickable to toggle in reading context (focusStack)
  - Text with HTML markup (<i>, <b>)
  - Annotation markers (clickable independently via stopPropagation)
  - Poetry line breaks preserved
  - Hover-only favorite button
-->
<script lang="ts">
	import type { PassageWithAnnotations, StudyNote, LiturgicalNote, VariantNote } from '$lib/api';
	import { ui, favorites } from '$lib/stores';
	import { studyContext, type FocusItem } from '$lib/stores/studyContext.svelte';
	import { layout } from '$lib/stores/layout.svelte';
	import { toast } from '$lib/stores/toast.svelte';
	import AnnotationMarker from './AnnotationMarker.svelte';
	import FavoriteButton from '$lib/components/ui/FavoriteButton.svelte';

	interface Props {
		passage: PassageWithAnnotations;
		studyNotes: StudyNote[];
		liturgicalNotes: LiturgicalNote[];
		variantNotes: VariantNote[];
	}

	let { passage, studyNotes, liturgicalNotes, variantNotes }: Props = $props();

	// Hover state for showing favorite button
	let isHovered = $state(false);

	// Check if this verse has any annotations to show (using filtered props, not raw passage data)
	const hasAnnotations = $derived(
		studyNotes.length > 0 ||
			liturgicalNotes.length > 0 ||
			variantNotes.length > 0
	);

	// Check if this passage is favorited
	const isFavorited = $derived(
		favorites.isPassageFavorited(passage.book_id, passage.chapter, passage.verse)
	);

	// Check if this verse is in the reading context (focusStack)
	const isInContext = $derived(
		studyContext.focusStack.some(
			(item) => item.type === 'verse' && item.passageId === passage.id
		)
	);

	// Check if a specific note is active (for marker highlighting)
	function isNoteActive(noteId: string): boolean {
		const content = ui.sidePanelContent;
		if (!content) return false;
		if (content.type === 'study') return content.note.id === noteId;
		if (content.type === 'liturgical') return content.note.id === noteId;
		if (content.type === 'variant') return content.note.id === noteId;
		return false;
	}

	function handleToggleFavorite() {
		const bookName = studyContext.scripturePosition?.bookName ?? passage.book_id;
		favorites.togglePassage({
			book: passage.book_id,
			bookName,
			chapter: passage.chapter,
			verse: passage.verse,
			preview: passage.text.replace(/<[^>]*>/g, '').slice(0, 100)
		});
	}

	function handleToggleContext() {
		const bookName = studyContext.scripturePosition?.bookName ?? passage.book_id;

		// Build focus item for this verse
		const focusItem: FocusItem = {
			type: 'verse',
			book: passage.book_id,
			bookName,
			chapter: passage.chapter,
			verse: passage.verse,
			passageId: passage.id,
			text: passage.text.replace(/<[^>]*>/g, '').slice(0, 150)
		};

		// Toggle: remove if already in context, add if not
		if (isInContext) {
			studyContext.removeFocus(focusItem);
		} else {
			const success = studyContext.pushFocus(focusItem);
			if (!success) {
				toast.warning('Context limit reached (15 items). Remove some items first.');
			}
		}
	}
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_noninteractive_element_to_interactive_role -->
<p
	class="verse scripture-text"
	class:selected={isInContext}
	id="osb-{passage.book_id}-{passage.chapter}-{passage.verse}"
	onclick={handleToggleContext}
	onmouseenter={() => (isHovered = true)}
	onmouseleave={() => (isHovered = false)}
	role="button"
	tabindex="0"
	aria-pressed={isInContext}
	title={isInContext ? 'Click to remove from reading context' : 'Click to add to reading context'}
>
	<span class="verse-num" class:selected={isInContext}>{passage.verse}</span>
	<span class="verse-text">
		{@html passage.text}
	</span>
	{#if hasAnnotations}
		<span class="verse-markers">
			{#each studyNotes as note (note.id)}
				<AnnotationMarker
					id={note.id}
					type="study"
					active={isNoteActive(note.id)}
					onclick={() => ui.showStudyNote(note)}
				/>
			{/each}
			{#each liturgicalNotes as note (note.id)}
				<AnnotationMarker
					id={note.id}
					type="liturgical"
					active={isNoteActive(note.id)}
					onclick={() => ui.showLiturgicalNote(note)}
				/>
			{/each}
			{#each variantNotes as note (note.id)}
				<AnnotationMarker
					id={note.id}
					type="variant"
					active={isNoteActive(note.id)}
					onclick={() => ui.showVariantNote(note)}
				/>
			{/each}
		</span>
	{/if}
	<span class="verse-favorite" class:visible={isHovered || isFavorited}>
		<FavoriteButton {isFavorited} onToggle={handleToggleFavorite} size="sm" />
	</span>
</p>

<style>
	.verse {
		position: relative;
		margin-bottom: var(--space-2);
		line-height: var(--leading-relaxed);
		/* Preserve poetry line breaks from \n in text */
		white-space: pre-wrap;
		padding-right: var(--space-8);
		padding-left: var(--space-2);
		margin-left: calc(-1 * var(--space-2));
		border-left: 2px solid transparent;
		border-radius: var(--radius-sm);
		cursor: pointer;
		transition: border-color var(--transition-fast), background var(--transition-fast);
	}

	.verse:hover {
		background: rgba(201, 162, 39, 0.03);
	}

	.verse.selected {
		border-left-color: var(--color-gold);
		background: rgba(201, 162, 39, 0.08);
	}

	.verse:focus-visible {
		outline: 2px solid var(--color-gold-dim);
		outline-offset: 2px;
	}

	.verse-num {
		font-family: var(--font-ui);
		font-size: var(--font-xs);
		font-weight: var(--font-semibold);
		color: var(--color-gold);
		vertical-align: super;
		margin-right: 0.3em;
		user-select: none;
		padding: 0.1em 0.3em;
		border-radius: var(--radius-sm);
		transition: background var(--transition-fast), color var(--transition-fast);
	}

	.verse-num.selected {
		background: var(--color-gold);
		color: var(--color-bg-base);
	}

	/* .verse-text inherits from global.css .scripture-text */

	.verse-markers {
		display: inline;
		margin-left: var(--space-1);
	}

	.verse-favorite {
		position: absolute;
		right: 0;
		top: 0;
		opacity: 0;
		transition: opacity var(--transition-fast);
	}

	.verse-favorite.visible {
		opacity: 1;
	}

	/* On touch devices, always show favorited items but not hover */
	@media (hover: none) {
		.verse-favorite {
			opacity: 0;
		}

		.verse-favorite.visible {
			opacity: 1;
		}
	}
</style>
