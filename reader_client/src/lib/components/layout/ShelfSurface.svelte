<!--
  ShelfSurface Component

  Reading history manager - view and manage recently read content
  from both Scripture (OSB) and Library.
-->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { layout } from '$lib/stores/layout.svelte';
	import { reader, bookPositionToPath, type BookPosition } from '$lib/stores/reader.svelte';
	import { libraryStore, workPositionToPath, type WorkPosition } from '$lib/stores/library.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';

	// Filter state
	type FilterType = 'all' | 'scripture' | 'library';
	let filter = $state<FilterType>('all');

	// Combined reading history item
	interface ShelfItem {
		type: 'scripture' | 'library';
		id: string;
		title: string;
		subtitle: string;
		lastRead: number;
		path: string;
	}

	// Build combined reading history
	function getShelfItems(): ShelfItem[] {
		const items: ShelfItem[] = [];

		// Get Scripture (OSB) reading history
		if (filter === 'all' || filter === 'scripture') {
			const recentBooks = reader.getRecentBooks(20);
			for (const book of recentBooks) {
				const verseStr = book.verse ? `:${book.verse}` : '';
				items.push({
					type: 'scripture',
					id: `osb-${book.bookId}`,
					title: book.bookName,
					subtitle: `Chapter ${book.chapter}${verseStr}`,
					lastRead: book.lastRead,
					path: bookPositionToPath(book.bookId, book)
				});
			}
		}

		// Get Library reading history
		if (filter === 'all' || filter === 'library') {
			const recentWorks = libraryStore.getRecentWorks(20);
			for (const work of recentWorks) {
				items.push({
					type: 'library',
					id: `lib-${work.workId}`,
					title: work.workTitle,
					subtitle: work.author + (work.nodeTitle ? ` - ${work.nodeTitle}` : ''),
					lastRead: work.lastRead,
					path: workPositionToPath(work.workId, work)
				});
			}
		}

		// Sort by most recent first
		items.sort((a, b) => b.lastRead - a.lastRead);

		return items;
	}

	// Reactive items list
	let items = $state<ShelfItem[]>([]);

	// Refresh items when filter changes or on mount
	$effect(() => {
		// Re-run when filter changes
		filter;
		items = getShelfItems();
	});

	// Truncate text to max length with ellipsis
	function truncate(text: string, maxLength: number): string {
		if (text.length <= maxLength) return text;
		return text.slice(0, maxLength - 3) + '...';
	}

	// Time formatting
	function formatTimeAgo(timestamp: number): string {
		const now = Date.now();
		const diff = now - timestamp;

		const minutes = Math.floor(diff / 60000);
		const hours = Math.floor(diff / 3600000);
		const days = Math.floor(diff / 86400000);

		if (minutes < 1) return 'Just now';
		if (minutes < 60) return `${minutes}m ago`;
		if (hours < 24) return `${hours}h ago`;
		if (days === 1) return 'Yesterday';
		if (days < 7) return `${days}d ago`;

		// Format as date
		return new Date(timestamp).toLocaleDateString(undefined, {
			month: 'short',
			day: 'numeric'
		});
	}

	// Navigation
	function continueReading(item: ShelfItem) {
		goto(item.path);
		layout.setMode('read');
	}

	// Remove from history
	function removeItem(item: ShelfItem) {
		if (!browser) return;

		if (item.type === 'scripture') {
			// Remove from OSB book positions
			const bookId = item.id.replace('osb-', '');
			const key = 'orthodox_reader_book_positions';
			try {
				const stored = localStorage.getItem(key);
				if (stored) {
					const positions = JSON.parse(stored);
					delete positions[bookId];
					localStorage.setItem(key, JSON.stringify(positions));
				}
			} catch {
				// Ignore errors
			}
		} else {
			// Remove from Library work positions
			const workId = item.id.replace('lib-', '');
			const key = 'orthodox_library_work_positions';
			try {
				const stored = localStorage.getItem(key);
				if (stored) {
					const positions = JSON.parse(stored);
					delete positions[workId];
					localStorage.setItem(key, JSON.stringify(positions));
				}
			} catch {
				// Ignore errors
			}
		}

		// Refresh the list
		items = getShelfItems();
	}

	// Clear all history
	function clearAll() {
		if (!browser) return;

		if (filter === 'all' || filter === 'scripture') {
			localStorage.removeItem('orthodox_reader_book_positions');
		}
		if (filter === 'all' || filter === 'library') {
			localStorage.removeItem('orthodox_library_work_positions');
		}

		items = getShelfItems();
	}

	// Check if there are any items
	let hasItems = $derived(items.length > 0);
</script>

<div class="shelf-surface">
	<div class="shelf-container">
		<!-- Header -->
		<header class="page-header">
			<h1 class="page-title">Reading Shelf</h1>
			<p class="page-subtitle">
				Continue where you left off
			</p>
		</header>

		<!-- Filters -->
		<section class="filter-section">
			<div class="filter-tabs">
				<button
					class="filter-tab"
					class:active={filter === 'all'}
					onclick={() => filter = 'all'}
				>
					All
				</button>
				<button
					class="filter-tab"
					class:active={filter === 'scripture'}
					onclick={() => filter = 'scripture'}
				>
					<Icon name="book-open" size={14} />
					Scripture
				</button>
				<button
					class="filter-tab"
					class:active={filter === 'library'}
					onclick={() => filter = 'library'}
				>
					<Icon name="library" size={14} />
					Library
				</button>
			</div>

			{#if hasItems}
				<button class="clear-btn" onclick={clearAll}>
					<Icon name="trash" size={14} />
					Clear {filter === 'all' ? 'All' : filter === 'scripture' ? 'Scripture' : 'Library'}
				</button>
			{/if}
		</section>

		<!-- Items List -->
		<section class="items-section">
			{#if !hasItems}
				<div class="empty-state">
					<Icon name="clock" size={48} />
					<p class="empty-title">No reading history</p>
					<p class="empty-subtitle">
						{#if filter === 'scripture'}
							Start reading Scripture to see it here
						{:else if filter === 'library'}
							Start reading Library works to see them here
						{:else}
							Start reading to build your shelf
						{/if}
					</p>
					<button class="browse-btn" onclick={() => { goto('/library'); layout.setMode('read'); }}>
						Browse Library
					</button>
				</div>
			{:else}
				<ul class="items-list">
					{#each items as item (item.id)}
						<li class="item-card">
							<button class="item-main" onclick={() => continueReading(item)}>
								<div class="item-icon" class:scripture={item.type === 'scripture'} class:library={item.type === 'library'}>
									<Icon name={item.type === 'scripture' ? 'book-open' : 'library'} size={20} />
								</div>
								<div class="item-content">
									<span class="item-title">{item.title}</span>
									<span class="item-subtitle" title={item.subtitle}>{truncate(item.subtitle, 140)}</span>
								</div>
								<div class="item-meta">
									<span class="item-time">{formatTimeAgo(item.lastRead)}</span>
									<Icon name="arrow-right" size={16} class="item-arrow" />
								</div>
							</button>
							<button
								class="item-remove"
								onclick={() => removeItem(item)}
								aria-label="Remove from shelf"
							>
								<Icon name="x" size={16} />
							</button>
						</li>
					{/each}
				</ul>
			{/if}
		</section>
	</div>
</div>

<style>
	.shelf-surface {
		display: flex;
		flex-direction: column;
		align-items: center;
		height: 100%;
		overflow-y: auto;
		background: var(--color-bg-base);
		padding: var(--space-4);
		padding-bottom: var(--space-16);
		position: relative;
	}

	/* Container */
	.shelf-container {
		width: 100%;
		max-width: 560px;
		display: flex;
		flex-direction: column;
		gap: var(--space-6);
	}

	/* Header */
	.page-header {
		text-align: center;
		padding-top: var(--space-8);
	}

	.page-title {
		font-family: var(--font-body);
		font-size: var(--font-2xl);
		font-weight: var(--font-semibold);
		color: var(--color-text-primary);
		letter-spacing: -0.02em;
		margin-bottom: var(--space-2);
	}

	.page-subtitle {
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		color: var(--color-text-muted);
	}

	/* Filter section */
	.filter-section {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-3);
		flex-wrap: wrap;
	}

	.filter-tabs {
		display: flex;
		gap: var(--space-1);
		background: var(--color-bg-surface);
		padding: var(--space-1);
		border-radius: var(--radius-md);
		border: 1px solid var(--color-border);
	}

	.filter-tab {
		display: flex;
		align-items: center;
		gap: var(--space-1);
		padding: var(--space-2) var(--space-3);
		border-radius: var(--radius-sm);
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		font-weight: var(--font-medium);
		color: var(--color-text-secondary);
		transition: all var(--transition-fast);
	}

	.filter-tab:hover {
		color: var(--color-text-primary);
		background: var(--color-bg-hover);
	}

	.filter-tab.active {
		color: var(--color-bg-base);
		background: var(--color-gold);
	}

	.clear-btn {
		display: flex;
		align-items: center;
		gap: var(--space-1);
		padding: var(--space-2) var(--space-3);
		border-radius: var(--radius-sm);
		font-family: var(--font-ui);
		font-size: var(--font-xs);
		color: var(--color-text-muted);
		transition: color var(--transition-fast);
	}

	.clear-btn:hover {
		color: var(--color-error);
	}

	/* Items section */
	.items-section {
		min-height: 200px;
	}

	/* Empty state */
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: var(--space-3);
		padding: var(--space-12) var(--space-4);
		color: var(--color-text-muted);
		text-align: center;
	}

	.empty-title {
		font-family: var(--font-body);
		font-size: var(--font-lg);
		font-weight: var(--font-medium);
		color: var(--color-text-secondary);
	}

	.empty-subtitle {
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		max-width: 280px;
	}

	.browse-btn {
		margin-top: var(--space-4);
		padding: var(--space-3) var(--space-6);
		background: var(--color-gold);
		color: var(--color-bg-base);
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		font-weight: var(--font-medium);
		border-radius: var(--radius-md);
		transition: background var(--transition-fast);
	}

	.browse-btn:hover {
		background: var(--color-gold-bright);
	}

	/* Items list */
	.items-list {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.item-card {
		display: flex;
		align-items: stretch;
		background: var(--color-bg-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-lg);
		overflow: hidden;
		transition: border-color var(--transition-fast);
	}

	.item-card:hover {
		border-color: var(--color-gold-dim);
	}

	.item-main {
		flex: 1;
		display: flex;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-4);
		text-align: left;
		transition: background var(--transition-fast);
	}

	.item-main:hover {
		background: var(--color-bg-hover);
	}

	.item-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 44px;
		height: 44px;
		border-radius: var(--radius-md);
		flex-shrink: 0;
	}

	.item-icon.scripture {
		background: rgba(201, 162, 39, 0.15);
		color: var(--color-gold);
	}

	.item-icon.library {
		background: rgba(186, 135, 189, 0.15);
		color: #ba87bd;
	}

	.item-content {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.item-title {
		font-family: var(--font-body);
		font-size: var(--font-base);
		font-weight: var(--font-medium);
		color: var(--color-text-primary);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.item-subtitle {
		font-family: var(--font-ui);
		font-size: var(--font-xs);
		color: var(--color-text-muted);
		line-height: 1.4;
		/* Allow wrapping for long titles */
		white-space: normal;
		word-wrap: break-word;
	}

	.item-meta {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		flex-shrink: 0;
	}

	.item-time {
		font-family: var(--font-ui);
		font-size: var(--font-xs);
		color: var(--color-text-muted);
		white-space: nowrap;
	}

	.item-meta :global(.item-arrow) {
		color: var(--color-text-muted);
		opacity: 0;
		transition: opacity var(--transition-fast);
	}

	.item-main:hover .item-meta :global(.item-arrow) {
		opacity: 1;
	}

	.item-remove {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 44px;
		color: var(--color-text-muted);
		border-left: 1px solid var(--color-border);
		transition: color var(--transition-fast), background var(--transition-fast);
	}

	.item-remove:hover {
		color: var(--color-error);
		background: rgba(204, 68, 68, 0.1);
	}

	/* Desktop */
	@media (min-width: 768px) {
		.shelf-surface {
			padding: var(--space-8);
		}

		.shelf-container {
			max-width: 640px;
		}

		.page-header {
			padding-top: var(--space-12);
		}

		.page-title {
			font-size: var(--font-3xl);
		}
	}

	/* Large desktop */
	@media (min-width: 1024px) {
		.shelf-container {
			max-width: 720px;
		}

		.page-header {
			padding-top: var(--space-16);
			margin-bottom: var(--space-4);
		}
	}

	/* Mobile */
	@media (max-width: 480px) {
		.shelf-surface {
			padding: var(--space-3);
			padding-bottom: var(--space-12);
		}

		.page-header {
			padding-top: var(--space-6);
		}

		.page-title {
			font-size: var(--font-xl);
		}

		.filter-section {
			flex-direction: column;
			align-items: stretch;
		}

		.filter-tabs {
			justify-content: center;
		}

		.clear-btn {
			align-self: flex-end;
		}

		.item-main {
			padding: var(--space-3);
		}

		.item-icon {
			width: 40px;
			height: 40px;
		}

		.item-meta :global(.item-arrow) {
			display: none;
		}
	}
</style>
