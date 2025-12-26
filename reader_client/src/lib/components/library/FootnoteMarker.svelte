<!--
  FootnoteMarker Component

  Renders a clickable footnote marker that shows the footnote content
  in the side panel when clicked.

  This component injects itself into the DOM at the placeholder location
  using a portal-like pattern with onMount.
-->
<script lang="ts">
	import { onMount } from 'svelte';
	import { ui } from '$lib/stores';

	interface Props {
		id: string;
		marker: string;
		content: string;
	}

	let { id, marker, content }: Props = $props();

	onMount(() => {
		// Find the placeholder in the DOM and replace it with the marker
		const placeholder = document.querySelector(`.footnote-placeholder[data-id="${id}"]`);
		if (placeholder) {
			const markerEl = document.createElement('sup');
			markerEl.className = 'footnote-marker';
			markerEl.dataset.id = id;
			markerEl.textContent = marker;
			markerEl.addEventListener('click', handleClick);

			placeholder.replaceWith(markerEl);

			return () => {
				markerEl.removeEventListener('click', handleClick);
			};
		}
	});

	function handleClick(e: Event) {
		e.preventDefault();
		e.stopPropagation();

		// Show footnote in side panel as an article
		ui.showArticle({
			id,
			type: 'article',
			text: `<strong>Note ${marker}</strong><br><br>${content}`
		});
	}
</script>

<!-- No visible render - this component operates via DOM manipulation -->
