<!--
  FavoriteButton Component

  A heart icon button for favoriting items.
  Shows outline when not favorited, filled gold when favorited.
-->
<script lang="ts">
	interface Props {
		isFavorited: boolean;
		onToggle: () => void;
		size?: 'sm' | 'md';
		class?: string;
	}

	let { isFavorited, onToggle, size = 'md', class: className = '' }: Props = $props();

	const iconSize = $derived(size === 'sm' ? 16 : 20);
</script>

<button
	class="favorite-button {size} {className}"
	class:favorited={isFavorited}
	onclick={(e) => {
		e.stopPropagation();
		onToggle();
	}}
	aria-label={isFavorited ? 'Remove from favorites' : 'Add to favorites'}
	aria-pressed={isFavorited}
>
	<svg
		width={iconSize}
		height={iconSize}
		viewBox="0 0 24 24"
		fill={isFavorited ? 'currentColor' : 'none'}
		stroke="currentColor"
		stroke-width="1.5"
		stroke-linecap="round"
		stroke-linejoin="round"
		aria-hidden="true"
	>
		{#if isFavorited}
			<path
				d="M11.645 20.91l-.007-.003-.022-.012a15.247 15.247 0 01-.383-.218 25.18 25.18 0 01-4.244-3.17C4.688 15.36 2.25 12.174 2.25 8.25 2.25 5.322 4.714 3 7.688 3A5.5 5.5 0 0112 5.052 5.5 5.5 0 0116.313 3c2.973 0 5.437 2.322 5.437 5.25 0 3.925-2.438 7.111-4.739 9.256a25.175 25.175 0 01-4.244 3.17 15.247 15.247 0 01-.383.219l-.022.012-.007.004-.003.001a.752.752 0 01-.704 0l-.003-.001z"
			/>
		{:else}
			<path
				d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12Z"
			/>
		{/if}
	</svg>
</button>

<style>
	.favorite-button {
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: var(--radius-md);
		color: var(--color-text-muted);
		transition:
			color var(--transition-fast),
			background var(--transition-fast),
			transform var(--transition-fast);
	}

	.favorite-button:hover {
		color: var(--color-gold);
		background: var(--color-bg-hover);
	}

	.favorite-button:active {
		transform: scale(0.95);
	}

	.favorite-button.favorited {
		color: var(--color-gold);
	}

	/* Size variants */
	.favorite-button.sm {
		padding: var(--space-1);
	}

	.favorite-button.md {
		padding: var(--space-2);
	}
</style>
