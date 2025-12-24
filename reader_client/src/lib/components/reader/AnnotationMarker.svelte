<!--
  Annotation Marker Component

  A clickable marker that indicates an annotation is available.
  Different colors for different annotation types.
-->
<script lang="ts">
	import type { AnnotationType } from '$lib/api';

	interface Props {
		id: string;
		type: AnnotationType;
		active?: boolean;
		onclick: () => void;
	}

	let { id, type, active = false, onclick }: Props = $props();

	// Marker symbols by type
	const markers: Record<AnnotationType, string> = {
		study: '\u2020', // †
		liturgical: '\u00A7', // §
		variant: '\u2021', // ‡
		citation: '\u00B6', // ¶
		article: '\u25C6' // ◆
	};
</script>

<button
	class="marker marker-{type}"
	class:active
	onclick={(e) => { e.stopPropagation(); onclick(); }}
	aria-label="View {type} note"
	title="{type} note"
>
	{markers[type]}
</button>

<style>
	.marker {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		font-family: var(--font-body);
		font-size: var(--font-sm);
		font-weight: var(--font-semibold);
		min-width: 1.25em;
		padding: 0 0.15em;
		vertical-align: super;
		border-radius: var(--radius-sm);
		transition:
			background var(--transition-fast),
			color var(--transition-fast);
		cursor: pointer;
	}

	.marker:hover {
		background: var(--color-bg-hover);
	}

	.marker.active {
		background: var(--color-bg-hover);
	}

	/* Type-specific colors */
	.marker-study {
		color: var(--color-annotation-study);
	}

	.marker-study.active {
		background: var(--color-gold-muted);
	}

	.marker-liturgical {
		color: var(--color-annotation-liturgical);
	}

	.marker-liturgical.active {
		background: var(--color-burgundy-dark);
	}

	.marker-variant {
		color: var(--color-annotation-variant);
	}

	.marker-citation {
		color: var(--color-annotation-crossref);
	}

	.marker-article {
		color: var(--color-annotation-article);
	}
</style>
