<!--
  Header Component

  Contains:
  - Logo/title
  - Current position breadcrumb
  - Book picker trigger
-->
<script lang="ts">
	import { reader, formatPosition, ui } from '$lib/stores';
	import type { Book } from '$lib/api';
	import Icon from '$lib/components/ui/Icon.svelte';
	import BookPicker from './BookPicker.svelte';
	import Sheet from '$lib/components/ui/Sheet.svelte';

	interface Props {
		books?: Book[];
	}

	let { books = [] }: Props = $props();
</script>

<header class="header">
	<div class="header-left">
		<button
			class="book-picker-trigger touch-target"
			onclick={() => ui.openBookPicker()}
			aria-label="Select book"
		>
			<Icon name="book" size={20} />
			<span class="position-text font-ui">
				{#if reader.position}
					{formatPosition(reader.position)}
				{:else}
					Select Book
				{/if}
			</span>
			<Icon name="chevron-down" size={16} />
		</button>
	</div>

	<div class="header-center">
		<span class="logo font-body">Orthodox Reader</span>
	</div>

	<div class="header-right">
		<!-- Placeholder for future actions (settings, etc.) -->
	</div>
</header>

<!-- Book picker sheet -->
<Sheet bind:open={ui.bookPickerOpen} position="left">
	<BookPicker {books} open={ui.bookPickerOpen} onSelect={() => ui.closeBookPicker()} />
</Sheet>

<!-- Book picker dropdown would go here for desktop -->

<style>
	.header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 var(--space-4);
		background: var(--color-bg-surface);
		border-bottom: 1px solid var(--color-border);
		height: var(--header-height);
	}

	.header-left,
	.header-right {
		flex: 1;
		display: flex;
		align-items: center;
	}

	.header-right {
		justify-content: flex-end;
	}

	.header-center {
		flex-shrink: 0;
	}

	.logo {
		font-size: var(--font-lg);
		font-weight: var(--font-medium);
		color: var(--color-gold);
		letter-spacing: var(--tracking-wide);
	}

	.book-picker-trigger {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-3);
		border-radius: var(--radius-md);
		color: var(--color-text-secondary);
		transition: background var(--transition-fast), color var(--transition-fast);
	}

	.book-picker-trigger:hover {
		background: var(--color-bg-hover);
		color: var(--color-text-primary);
	}

	.position-text {
		font-size: var(--font-sm);
		max-width: 10rem;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	/* Hide logo on mobile to save space */
	@media (max-width: 768px) {
		.header-center {
			display: none;
		}

		.header-left {
			flex: none;
		}
	}
</style>
