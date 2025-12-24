<!--
  Book Picker Component

  Three-level navigation: Testament → Book → Chapter
  Remembers position based on current reading location.
-->
<script lang="ts">
	import { goto } from '$app/navigation';
	import type { Book, BookDetail } from '$lib/api';
	import { books as booksApi } from '$lib/api';
	import { reader } from '$lib/stores';
	import Icon from '$lib/components/ui/Icon.svelte';

	interface Props {
		books: Book[];
		onSelect?: () => void;
		open?: boolean;
	}

	let { books, onSelect, open = false }: Props = $props();

	// Navigation state
	let testament = $state<'old' | 'new' | null>(null);
	let selectedBook = $state<BookDetail | null>(null);
	let isLoadingBook = $state(false);
	let hasInitialized = $state(false);

	// Filtered books by testament (with null safety)
	const oldTestament = $derived(books?.filter((b) => b.testament === 'old') ?? []);
	const newTestament = $derived(books?.filter((b) => b.testament === 'new') ?? []);

	// Initialize picker based on current reading position when opened
	$effect(() => {
		if (open && !hasInitialized && reader.position && books.length > 0) {
			initializeFromPosition();
		}
		// Reset initialization flag when closed
		if (!open) {
			hasInitialized = false;
		}
	});

	async function initializeFromPosition() {
		const pos = reader.position;
		if (!pos) return;

		// Find the book in our list
		const book = books.find((b) => b.id === pos.book);
		if (!book) return;

		// Set testament and load book details
		testament = book.testament;
		isLoadingBook = true;
		hasInitialized = true;

		try {
			selectedBook = await booksApi.get(book.id);
		} finally {
			isLoadingBook = false;
		}
	}

	function selectTestament(t: 'old' | 'new') {
		testament = t;
		selectedBook = null;
	}

	let loadError = $state<string | null>(null);

	async function selectBook(book: Book) {
		isLoadingBook = true;
		loadError = null;
		try {
			selectedBook = await booksApi.get(book.id);
		} catch (err) {
			console.error('Failed to load book:', err);
			loadError = err instanceof Error ? err.message : 'Failed to load chapters';
		} finally {
			isLoadingBook = false;
		}
	}

	function selectChapter(chapter: number) {
		if (!selectedBook) return;
		goto(`/read/${selectedBook.id}/${chapter}`);
		onSelect?.();
		// Don't reset state - keep position for next open
	}

	function goBack() {
		if (selectedBook) {
			selectedBook = null;
		} else if (testament) {
			testament = null;
		}
	}
</script>

<div class="book-picker">
	<!-- Header with back button -->
	<div class="picker-header">
		{#if testament || selectedBook}
			<button class="back-button touch-target" onclick={goBack}>
				<Icon name="chevron-left" size={20} />
			</button>
		{/if}
		<h2 class="picker-title font-body">
			{#if selectedBook}
				{selectedBook.name}
			{:else if testament === 'old'}
				Old Testament
			{:else if testament === 'new'}
				New Testament
			{:else}
				Select Book
			{/if}
		</h2>
	</div>

	<div class="picker-content">
		{#if !testament}
			<!-- Testament selection -->
			<div class="testament-grid">
				<button
					class="testament-button"
					onclick={() => selectTestament('old')}
				>
					<span class="testament-name">Old Testament</span>
					<span class="testament-count text-muted">{oldTestament.length} books</span>
				</button>
				<button
					class="testament-button"
					onclick={() => selectTestament('new')}
				>
					<span class="testament-name">New Testament</span>
					<span class="testament-count text-muted">{newTestament.length} books</span>
				</button>
			</div>
		{:else if !selectedBook}
			<!-- Book list -->
			{#if loadError}
				<div class="error-message">{loadError}</div>
			{/if}
			{#if isLoadingBook}
				<div class="loading">Loading chapters...</div>
			{:else}
				<ul class="book-list">
					{#each testament === 'old' ? oldTestament : newTestament as book (book.id)}
						<li>
							<button
								class="book-item touch-target"
								onclick={() => selectBook(book)}
							>
								<span class="book-name">{book.name}</span>
								<span class="book-chapters text-muted">
									{book.chapter_count} ch
								</span>
								<Icon name="chevron-right" size={16} class="text-muted" />
							</button>
						</li>
					{/each}
				</ul>
			{/if}
		{:else}
			<!-- Chapter grid -->
			{#if isLoadingBook}
				<div class="loading">Loading chapters...</div>
			{:else}
				<div class="chapter-grid">
					{#each selectedBook.chapters as ch (ch.chapter)}
						<button
							class="chapter-button touch-target"
							onclick={() => selectChapter(ch.chapter)}
						>
							{ch.chapter}
						</button>
					{/each}
				</div>
			{/if}
		{/if}
	</div>
</div>

<style>
	.book-picker {
		display: flex;
		flex-direction: column;
		height: 100%;
	}

	.picker-header {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-4);
		border-bottom: 1px solid var(--color-border);
		flex-shrink: 0;
	}

	.back-button {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: var(--space-2);
		margin: calc(var(--space-2) * -1);
		color: var(--color-text-secondary);
		border-radius: var(--radius-md);
	}

	.back-button:hover {
		background: var(--color-bg-hover);
		color: var(--color-text-primary);
	}

	.picker-title {
		font-size: var(--font-lg);
		font-weight: var(--font-medium);
		color: var(--color-text-primary);
	}

	.picker-content {
		flex: 1;
		overflow-y: auto;
		padding: var(--space-4);
	}

	/* Testament selection */
	.testament-grid {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	.testament-button {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: var(--space-1);
		padding: var(--space-5);
		background: var(--color-bg-elevated);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		transition:
			background var(--transition-fast),
			border-color var(--transition-fast);
	}

	.testament-button:hover {
		background: var(--color-bg-hover);
		border-color: var(--color-gold-dim);
	}

	.testament-name {
		font-family: var(--font-body);
		font-size: var(--font-lg);
		font-weight: var(--font-medium);
		color: var(--color-text-primary);
	}

	.testament-count {
		font-family: var(--font-ui);
		font-size: var(--font-sm);
	}

	/* Book list */
	.book-list {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.book-item {
		display: flex;
		align-items: center;
		width: 100%;
		padding: var(--space-3) var(--space-2);
		border-radius: var(--radius-md);
		transition: background var(--transition-fast);
		touch-action: manipulation;
	}

	.book-item:hover {
		background: var(--color-bg-hover);
	}

	.book-name {
		flex: 1;
		text-align: left;
		font-family: var(--font-body);
		font-size: var(--font-base);
		color: var(--color-text-primary);
	}

	.book-chapters {
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		margin-right: var(--space-2);
	}

	/* Chapter grid */
	.chapter-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(3rem, 1fr));
		gap: var(--space-2);
	}

	.chapter-button {
		aspect-ratio: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		font-family: var(--font-ui);
		font-size: var(--font-base);
		font-weight: var(--font-medium);
		color: var(--color-text-secondary);
		background: var(--color-bg-elevated);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		transition:
			background var(--transition-fast),
			color var(--transition-fast),
			border-color var(--transition-fast);
	}

	.chapter-button:hover {
		background: var(--color-bg-hover);
		color: var(--color-gold);
		border-color: var(--color-gold-dim);
	}

	.loading {
		text-align: center;
		color: var(--color-text-muted);
		padding: var(--space-8);
	}

	.error-message {
		padding: var(--space-3) var(--space-4);
		margin-bottom: var(--space-3);
		background: rgba(239, 68, 68, 0.1);
		border: 1px solid rgba(239, 68, 68, 0.3);
		border-radius: var(--radius-md);
		color: #ef4444;
		font-size: var(--font-sm);
	}
</style>
