<!--
  ScriptureRef Component

  Renders a clickable Scripture reference in library content.
  Behavior depends on user preference:
  - 'preview': Show verse in side panel
  - 'navigate': Navigate directly to OSB reader

  Can also be used inline in rendered HTML via data attributes
  and event delegation.
-->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { preferences, ui, reader, libraryStore } from '$lib/stores';
	import { getPassage } from '$lib/api';
	import type { LibraryScriptureRefTarget } from '$lib/api';

	interface Props {
		/** The reference text as displayed (e.g., "Matt. 5:3") */
		referenceText: string;
		/** Target passage info */
		target: LibraryScriptureRefTarget;
	}

	let { referenceText, target }: Props = $props();

	let loading = $state(false);

	const osbHref = $derived(
		`/read/${target.book_id}/${target.chapter}#v${target.verse_start}`
	);

	async function handleClick(e: MouseEvent) {
		e.preventDefault();

		if (preferences.scriptureRefBehavior === 'navigate') {
			// Navigate directly - save current library position to history
			// The reader store will handle this when we navigate
			goto(osbHref);
		} else {
			// Preview mode - show in side panel
			await showPreview();
		}
	}

	async function showPreview() {
		loading = true;
		try {
			const passage = await getPassage(target.passage_id, 'annotations');
			ui.showPassage(passage, `${target.book_name} ${target.chapter}:${target.verse_start}`);
		} catch (error) {
			console.error('Failed to load passage preview:', error);
			// Fall back to navigate
			goto(osbHref);
		} finally {
			loading = false;
		}
	}

	function handleNavigate(e: MouseEvent) {
		e.preventDefault();
		e.stopPropagation();
		goto(osbHref);
	}
</script>

<span class="scripture-ref" class:loading>
	<a
		href={osbHref}
		class="ref-link"
		onclick={handleClick}
		title={preferences.scriptureRefBehavior === 'preview'
			? 'Click to preview, Ctrl+Click to navigate'
			: 'Click to open in OSB'}
	>
		{referenceText}
	</a>
</span>

<style>
	.scripture-ref {
		display: inline;
	}

	.ref-link {
		color: var(--color-annotation-crossref);
		text-decoration: none;
		border-bottom: 1px dotted currentColor;
		cursor: pointer;
		transition: color var(--transition-fast);
	}

	.ref-link:hover {
		color: var(--color-gold);
	}

	.scripture-ref.loading .ref-link {
		opacity: 0.5;
		cursor: wait;
	}
</style>
