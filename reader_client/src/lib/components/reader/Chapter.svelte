<!--
  Chapter Component

  Renders all verses in a chapter with:
  - Article insertion before appropriate verses
  - Annotation placement based on verse_display field
  - Verse text with HTML markup
-->
<script lang="ts">
	import type { PassageWithAnnotations, StudyNote, LiturgicalNote, VariantNote } from '$lib/api';
	import Verse from './Verse.svelte';
	import Article from './Article.svelte';

	interface Props {
		passages: PassageWithAnnotations[];
	}

	let { passages }: Props = $props();

	/**
	 * Parse verse_display and extract the verse number where annotation should be displayed.
	 *
	 * Formats:
	 * - "1:3" → verse 3
	 * - "1:9-11" → verse 9 (first verse of range)
	 * - "1:5a" → verse 5 (sub-verse reference)
	 *
	 * Returns { chapter, verse } or null if parsing fails.
	 */
	function parseVerseDisplay(verseDisplay: string): { chapter: number; verse: number } | null {
		// Match patterns like "1:3", "1:9-11", "1:5a", "1:5b"
		const match = verseDisplay.match(/^(\d+):(\d+)/);
		if (!match) return null;
		return {
			chapter: parseInt(match[1], 10),
			verse: parseInt(match[2], 10)
		};
	}

	/**
	 * Check if an annotation's verse_display matches a given chapter:verse.
	 */
	function shouldDisplayOnVerse(
		verseDisplay: string,
		chapter: number,
		verse: number
	): boolean {
		const parsed = parseVerseDisplay(verseDisplay);
		if (!parsed) return false;
		return parsed.chapter === chapter && parsed.verse === verse;
	}

	/**
	 * Filter study notes to only those that should display on this verse.
	 * Uses verse_display field to determine correct placement.
	 */
	function getStudyNotesForVerse(passage: PassageWithAnnotations): StudyNote[] {
		if (!passage.annotations?.study_notes) return [];
		return passage.annotations.study_notes.filter((note) =>
			shouldDisplayOnVerse(note.verse_display, passage.chapter, passage.verse)
		);
	}

	/**
	 * Filter liturgical notes to only those that should display on this verse.
	 */
	function getLiturgicalNotesForVerse(passage: PassageWithAnnotations): LiturgicalNote[] {
		if (!passage.annotations?.liturgical) return [];
		return passage.annotations.liturgical.filter((note) =>
			shouldDisplayOnVerse(note.verse_display, passage.chapter, passage.verse)
		);
	}

	/**
	 * Filter variant notes to only those that should display on this verse.
	 */
	function getVariantNotesForVerse(passage: PassageWithAnnotations): VariantNote[] {
		if (!passage.annotations?.variants) return [];
		return passage.annotations.variants.filter((note) =>
			shouldDisplayOnVerse(note.verse_display, passage.chapter, passage.verse)
		);
	}
</script>

<div class="chapter">
	{#each passages as passage (passage.id)}
		<!-- Articles render BEFORE their verse -->
		{#if passage.annotations?.articles?.length}
			{#each passage.annotations.articles as article (article.id)}
				<Article {article} />
			{/each}
		{/if}

		<Verse
			{passage}
			studyNotes={getStudyNotesForVerse(passage)}
			liturgicalNotes={getLiturgicalNotesForVerse(passage)}
			variantNotes={getVariantNotesForVerse(passage)}
		/>
	{/each}
</div>

<style>
	.chapter {
		font-family: var(--font-body);
		font-size: var(--font-base);
		color: var(--color-text-primary);
	}
</style>
