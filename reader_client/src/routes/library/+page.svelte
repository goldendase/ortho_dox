<!--
  Library Browse Page

  Displays filterable grid of theological works with:
  - Search (fuzzy match on title + author)
  - Filter chips (era, work type, reading level)
  - Author dropdown (searchable)
  - Brief/expanded card views
-->
<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import WorkCard from '$lib/components/library/WorkCard.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import Sheet from '$lib/components/ui/Sheet.svelte';
	import type { Era, WorkType, LibraryWorkSummary } from '$lib/api/types';

	let { data } = $props();

	// Filter state
	let searchQuery = $state('');
	let selectedEra = $state<Era | null>(null);
	let selectedType = $state<WorkType | null>(null);
	let selectedAuthor = $state<string | null>(null);

	// UI state
	let expandedWorkId = $state<string | null>(null);
	let showMobileFilters = $state(false);
	let eraDropdownOpen = $state(false);
	let typeDropdownOpen = $state(false);
	let authorDropdownOpen = $state(false);
	let authorSearchQuery = $state('');

	// Display configs
	const eraLabels: Record<Era, string> = {
		apostolic: 'Apostolic',
		nicene: 'Nicene',
		byzantine: 'Byzantine',
		early_modern: 'Early Modern',
		modern: 'Modern'
	};

	const typeLabels: Record<WorkType, string> = {
		commentary: 'Commentary',
		ascetical: 'Ascetical',
		pastoral: 'Pastoral',
		doctrinal: 'Doctrinal',
		historical: 'Historical'
	};

	// Read URL params on mount
	$effect(() => {
		if (browser) {
			const url = new URL($page.url);
			searchQuery = url.searchParams.get('q') || '';
			selectedEra = (url.searchParams.get('era') as Era) || null;
			selectedType = (url.searchParams.get('type') as WorkType) || null;
			selectedAuthor = url.searchParams.get('author') || null;
		}
	});

	// Update URL when filters change (debounced)
	let urlUpdateTimeout: ReturnType<typeof setTimeout>;
	function updateUrl() {
		clearTimeout(urlUpdateTimeout);
		urlUpdateTimeout = setTimeout(() => {
			if (!browser) return;
			const url = new URL($page.url);

			if (searchQuery) url.searchParams.set('q', searchQuery);
			else url.searchParams.delete('q');

			if (selectedEra) url.searchParams.set('era', selectedEra);
			else url.searchParams.delete('era');

			if (selectedType) url.searchParams.set('type', selectedType);
			else url.searchParams.delete('type');

			if (selectedAuthor) url.searchParams.set('author', selectedAuthor);
			else url.searchParams.delete('author');

			goto(url.toString(), { replaceState: true, keepFocus: true, noScroll: true });
		}, 300);
	}

	// Client-side filtering
	function matchesSearch(work: LibraryWorkSummary, query: string): boolean {
		const q = query.toLowerCase();
		return (
			work.title.toLowerCase().includes(q) ||
			work.author.toLowerCase().includes(q) ||
			(work.subtitle?.toLowerCase().includes(q) ?? false)
		);
	}

	let filteredWorks = $derived.by(() => {
		return data.works.filter((work) => {
			if (searchQuery && !matchesSearch(work, searchQuery)) return false;
			if (selectedEra && work.era !== selectedEra) return false;
			if (selectedType && work.work_type !== selectedType) return false;
			if (selectedAuthor && work.author !== selectedAuthor) return false;
			return true;
		});
	});

	// Filtered authors for dropdown
	let filteredAuthors = $derived.by(() => {
		if (!authorSearchQuery) return data.filters.authors;
		const q = authorSearchQuery.toLowerCase();
		return data.filters.authors.filter((a) => a.name.toLowerCase().includes(q));
	});

	// Check if any filters are active
	let hasActiveFilters = $derived(
		!!searchQuery || !!selectedEra || !!selectedType || !!selectedAuthor
	);

	// Handlers
	function selectEra(era: Era | null) {
		selectedEra = era;
		eraDropdownOpen = false;
		updateUrl();
	}

	function selectType(type: WorkType | null) {
		selectedType = type;
		typeDropdownOpen = false;
		updateUrl();
	}

	function selectAuthor(author: string | null) {
		selectedAuthor = author;
		authorDropdownOpen = false;
		authorSearchQuery = '';
		updateUrl();
	}

	function closeAllDropdowns() {
		eraDropdownOpen = false;
		typeDropdownOpen = false;
		authorDropdownOpen = false;
	}

	function clearAllFilters() {
		searchQuery = '';
		selectedEra = null;
		selectedType = null;
		selectedAuthor = null;
		updateUrl();
	}

	function toggleExpanded(workId: string) {
		expandedWorkId = expandedWorkId === workId ? null : workId;
	}

	function handleSearchInput() {
		updateUrl();
	}

	function handleClickOutsideDropdowns(e: MouseEvent) {
		const target = e.target as HTMLElement;
		if (!target.closest('.filter-dropdown')) {
			closeAllDropdowns();
		}
	}
</script>

<svelte:head>
	<title>Library | Orthodox Reader</title>
</svelte:head>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div class="library-page" onclick={handleClickOutsideDropdowns}>
	<!-- Header -->
	<header class="page-header">
		<h1 class="page-title">
			<Icon name="library" size={24} />
			Theological Library
		</h1>
		<p class="page-description">
			Explore patristic writings, saints' biographies, and spiritual texts
		</p>
	</header>

	<!-- Mobile Search + Filter Bar -->
	<div class="mobile-bar mobile-only">
		<div class="mobile-search-wrapper">
			<Icon name="search" size={16} />
			<input
				type="text"
				class="mobile-search-input"
				placeholder="Search works..."
				bind:value={searchQuery}
				oninput={handleSearchInput}
			/>
			{#if searchQuery}
				<button class="clear-search" onclick={() => { searchQuery = ''; updateUrl(); }}>
					<Icon name="x" size={14} />
				</button>
			{/if}
		</div>
		<button class="mobile-filter-btn" onclick={() => (showMobileFilters = true)}>
			<Icon name="filter" size={18} />
			<span>Filters</span>
			{#if hasActiveFilters && !searchQuery}
				<span class="filter-badge"></span>
			{/if}
		</button>
	</div>

	<!-- Desktop Filters + Search Row -->
	<div class="filter-bar desktop-only">
		<div class="filters">
			<!-- Era filter (dropdown) -->
			<div class="filter-group filter-dropdown">
			<span class="filter-label">Era</span>
			<div class="dropdown-wrapper">
				<button
					class="dropdown-trigger"
					class:active={!!selectedEra}
					onclick={() => {
						eraDropdownOpen = !eraDropdownOpen;
						typeDropdownOpen = false;
						authorDropdownOpen = false;
					}}
				>
					{selectedEra ? eraLabels[selectedEra] : 'All Eras'}
					<Icon name="chevron-down" size={14} />
				</button>

				{#if eraDropdownOpen}
					<div class="dropdown-menu">
						<button
							class="dropdown-option"
							class:selected={!selectedEra}
							onclick={() => selectEra(null)}
						>
							All Eras
						</button>
						{#each Object.entries(eraLabels) as [value, label]}
							<button
								class="dropdown-option"
								class:selected={selectedEra === value}
								onclick={() => selectEra(value as Era)}
							>
								{label}
							</button>
						{/each}
					</div>
				{/if}
			</div>
		</div>

		<!-- Work Type filter (dropdown) -->
		<div class="filter-group filter-dropdown">
			<span class="filter-label">Type</span>
			<div class="dropdown-wrapper">
				<button
					class="dropdown-trigger"
					class:active={!!selectedType}
					onclick={() => {
						typeDropdownOpen = !typeDropdownOpen;
						eraDropdownOpen = false;
						authorDropdownOpen = false;
					}}
				>
					{selectedType ? typeLabels[selectedType] : 'All Types'}
					<Icon name="chevron-down" size={14} />
				</button>

				{#if typeDropdownOpen}
					<div class="dropdown-menu">
						<button
							class="dropdown-option"
							class:selected={!selectedType}
							onclick={() => selectType(null)}
						>
							All Types
						</button>
						{#each Object.entries(typeLabels) as [value, label]}
							<button
								class="dropdown-option"
								class:selected={selectedType === value}
								onclick={() => selectType(value as WorkType)}
							>
								{label}
							</button>
						{/each}
					</div>
				{/if}
			</div>
		</div>

		<!-- Author filter (dropdown with search) -->
		<div class="filter-group filter-dropdown">
			<span class="filter-label">Author</span>
			<div class="dropdown-wrapper">
				<button
					class="dropdown-trigger"
					class:active={!!selectedAuthor}
					onclick={() => {
						authorDropdownOpen = !authorDropdownOpen;
						eraDropdownOpen = false;
						typeDropdownOpen = false;
					}}
				>
					{selectedAuthor || 'All Authors'}
					<Icon name="chevron-down" size={14} />
				</button>

				{#if authorDropdownOpen}
					<div class="dropdown-menu dropdown-menu-search">
						<input
							type="text"
							class="dropdown-search"
							placeholder="Search authors..."
							bind:value={authorSearchQuery}
							onclick={(e) => e.stopPropagation()}
						/>
						<div class="dropdown-list">
							<button
								class="dropdown-option"
								class:selected={!selectedAuthor}
								onclick={() => selectAuthor(null)}
							>
								All Authors
							</button>
							{#each filteredAuthors as author}
								<button
									class="dropdown-option"
									class:selected={selectedAuthor === author.name}
									onclick={() => selectAuthor(author.name)}
								>
									{author.name}
									<span class="option-count">({author.work_count})</span>
								</button>
							{/each}
						</div>
					</div>
				{/if}
			</div>
		</div>

			<!-- Clear all -->
			{#if hasActiveFilters}
				<button class="clear-filters-btn" onclick={clearAllFilters}>
					<Icon name="x" size={14} />
					Clear filters
				</button>
			{/if}
		</div>

		<!-- Search (right side) -->
		<div class="search-wrapper">
			<Icon name="search" size={16} />
			<input
				type="text"
				class="search-input"
				placeholder="Search by title or author..."
				bind:value={searchQuery}
				oninput={handleSearchInput}
			/>
			{#if searchQuery}
				<button class="clear-search" onclick={() => { searchQuery = ''; updateUrl(); }}>
					<Icon name="x" size={14} />
				</button>
			{/if}
		</div>
	</div>

	<!-- Results count -->
	<div class="results-info">
		<span class="results-count">
			{filteredWorks.length} {filteredWorks.length === 1 ? 'work' : 'works'}
			{#if hasActiveFilters}
				<span class="filtered-note">(filtered)</span>
			{/if}
		</span>
	</div>

	<!-- Works Grid -->
	<div class="works-grid">
		{#if filteredWorks.length === 0}
			<div class="empty-state">
				<Icon name="book-open" size={48} />
				<p>No works found</p>
				{#if hasActiveFilters}
					<button class="clear-filter-btn" onclick={clearAllFilters}>
						Clear filters
					</button>
				{/if}
			</div>
		{:else}
			{#each filteredWorks as work (work.id)}
				<WorkCard
					{work}
					expanded={expandedWorkId === work.id}
					onToggle={() => toggleExpanded(work.id)}
				/>
			{/each}
		{/if}
	</div>
</div>

<!-- Mobile Filter Sheet -->
<Sheet bind:open={showMobileFilters} position="bottom">
	<div class="mobile-filters">
		<div class="mobile-filters-header">
			<h2>Filters</h2>
			{#if hasActiveFilters}
				<button class="clear-all-btn" onclick={clearAllFilters}>
					Clear all
				</button>
			{/if}
		</div>

		<!-- Era -->
		<div class="mobile-filter-section">
			<h3>Era</h3>
			<select
				class="mobile-select"
				value={selectedEra || ''}
				onchange={(e) => selectEra((e.currentTarget.value as Era) || null)}
			>
				<option value="">All Eras</option>
				{#each Object.entries(eraLabels) as [value, label]}
					<option value={value}>{label}</option>
				{/each}
			</select>
		</div>

		<!-- Type -->
		<div class="mobile-filter-section">
			<h3>Type</h3>
			<select
				class="mobile-select"
				value={selectedType || ''}
				onchange={(e) => selectType((e.currentTarget.value as WorkType) || null)}
			>
				<option value="">All Types</option>
				{#each Object.entries(typeLabels) as [value, label]}
					<option value={value}>{label}</option>
				{/each}
			</select>
		</div>

		<!-- Author -->
		<div class="mobile-filter-section">
			<h3>Author</h3>
			<select
				class="mobile-select"
				value={selectedAuthor || ''}
				onchange={(e) => selectAuthor(e.currentTarget.value || null)}
			>
				<option value="">All Authors</option>
				{#each data.filters.authors as author}
					<option value={author.name}>{author.name} ({author.work_count})</option>
				{/each}
			</select>
		</div>

		<button class="apply-filters-btn" onclick={() => (showMobileFilters = false)}>
			Show {filteredWorks.length} {filteredWorks.length === 1 ? 'work' : 'works'}
		</button>
	</div>
</Sheet>

<style>
	.library-page {
		padding: var(--space-6);
		max-width: 1400px;
		margin: 0 auto;
	}

	/* Header - Centered */
	.page-header {
		text-align: center;
		margin-bottom: var(--space-6);
	}

	.page-title {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: var(--space-3);
		font-size: calc(var(--text-size, 1rem) * 1.5);
		font-weight: var(--font-medium);
		color: var(--color-gold);
		margin: 0 0 var(--space-2);
	}

	.page-description {
		font-size: var(--text-size, 1rem);
		color: var(--color-text-secondary);
		margin: 0;
	}

	/* Mobile Bar */
	.mobile-bar {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		margin-bottom: var(--space-4);
	}

	.mobile-only {
		display: none;
	}

	.mobile-bar .mobile-search-wrapper {
		flex: 1;
	}

	.mobile-filter-btn {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		position: relative;
		padding: var(--space-2) var(--space-3);
		background: var(--color-bg-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		color: var(--color-text-secondary);
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		cursor: pointer;
		transition: all var(--transition-fast);
		white-space: nowrap;
		flex-shrink: 0;
	}

	.mobile-filter-btn:hover {
		background: var(--color-bg-hover);
		color: var(--color-text-primary);
	}

	.filter-badge {
		width: 8px;
		height: 8px;
		background: var(--color-gold);
		border-radius: 50%;
		margin-left: var(--space-1);
	}

	/* Filter Bar - Contains filters + search */
	.filter-bar {
		display: flex;
		align-items: flex-end;
		gap: var(--space-4);
		margin-bottom: var(--space-4);
		padding-bottom: var(--space-4);
		border-bottom: 1px solid var(--color-border);
		flex-wrap: wrap;
	}

	/* Filters - Grouped together */
	.filters {
		display: flex;
		align-items: flex-end;
		gap: var(--space-4);
		flex-wrap: wrap;
	}

	.search-wrapper {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-3);
		background: var(--color-bg-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		transition: border-color var(--transition-fast);
		min-width: 200px;
	}

	.search-wrapper:focus-within {
		border-color: var(--color-gold-dim);
	}

	.search-input {
		flex: 1;
		background: none;
		border: none;
		font-size: var(--font-sm);
		font-family: var(--font-ui);
		color: var(--color-text-primary);
		outline: none;
		min-width: 140px;
	}

	.search-input::placeholder {
		color: var(--color-text-muted);
	}

	.clear-search {
		padding: var(--space-1);
		background: none;
		border: none;
		color: var(--color-text-muted);
		cursor: pointer;
		border-radius: var(--radius-sm);
	}

	.clear-search:hover {
		color: var(--color-text-primary);
		background: var(--color-bg-hover);
	}

	.filter-group {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.filter-label {
		font-size: var(--font-xs);
		font-family: var(--font-ui);
		color: var(--color-text-muted);
		text-transform: uppercase;
		letter-spacing: var(--tracking-wide);
	}

	/* Dropdown styles (unified for all filters) */
	.filter-dropdown {
		position: relative;
	}

	.dropdown-wrapper {
		position: relative;
	}

	.dropdown-trigger {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-1) var(--space-3);
		font-size: var(--font-sm);
		font-family: var(--font-ui);
		color: var(--color-text-secondary);
		background: var(--color-bg-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		cursor: pointer;
		min-width: 140px;
		justify-content: space-between;
		transition:
			background var(--transition-fast),
			color var(--transition-fast),
			border-color var(--transition-fast);
	}

	.dropdown-trigger:hover {
		background: var(--color-bg-hover);
		color: var(--color-text-primary);
	}

	.dropdown-trigger.active {
		background: var(--color-gold-dim-bg);
		color: var(--color-gold);
		border-color: var(--color-gold-dim);
	}

	.dropdown-menu {
		position: absolute;
		top: 100%;
		left: 0;
		margin-top: var(--space-1);
		background: var(--color-bg-elevated);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
		z-index: 100;
		min-width: 100%;
		overflow: hidden;
	}

	.dropdown-menu-search {
		max-height: 300px;
		display: flex;
		flex-direction: column;
		min-width: 200px;
	}

	.dropdown-search {
		padding: var(--space-2) var(--space-3);
		background: var(--color-bg-surface);
		border: none;
		border-bottom: 1px solid var(--color-border);
		font-size: var(--font-sm);
		font-family: var(--font-ui);
		color: var(--color-text-primary);
		outline: none;
	}

	.dropdown-list {
		overflow-y: auto;
		flex: 1;
	}

	.dropdown-option {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-2);
		width: 100%;
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-sm);
		font-family: var(--font-ui);
		color: var(--color-text-secondary);
		background: none;
		border: none;
		cursor: pointer;
		text-align: left;
		white-space: nowrap;
	}

	.dropdown-option:hover {
		background: var(--color-bg-hover);
		color: var(--color-text-primary);
	}

	.dropdown-option.selected {
		background: var(--color-gold-dim-bg);
		color: var(--color-gold);
	}

	.option-count {
		color: var(--color-text-muted);
		font-size: var(--font-xs);
	}

	/* Level dots in dropdowns */
	.level-dots {
		display: inline-flex;
		align-items: center;
		gap: 3px;
	}

	.dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--color-text-muted);
	}

	.dot.filled {
		background: var(--color-gold);
	}

	.dropdown-option:hover .dot {
		background: var(--color-text-secondary);
	}

	.dropdown-option:hover .dot.filled,
	.dropdown-option.selected .dot.filled {
		background: var(--color-gold);
	}

	/* Compact dots-only dropdown */
	.dropdown-trigger-dots {
		min-width: auto;
		padding: var(--space-2) var(--space-3);
	}

	.dropdown-menu-dots {
		min-width: auto;
	}

	.dropdown-menu-dots .dropdown-option {
		justify-content: flex-start;
	}

	.clear-filters-btn {
		display: flex;
		align-items: center;
		gap: var(--space-1);
		padding: var(--space-1) var(--space-3);
		font-size: var(--font-sm);
		font-family: var(--font-ui);
		color: var(--color-text-muted);
		background: none;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		cursor: pointer;
		height: fit-content;
	}

	.clear-filters-btn:hover {
		color: var(--color-text-primary);
		border-color: var(--color-text-muted);
	}

	/* Results info */
	.results-info {
		margin-bottom: var(--space-4);
	}

	.results-count {
		font-size: var(--font-sm);
		font-family: var(--font-ui);
		color: var(--color-text-muted);
	}

	.filtered-note {
		color: var(--color-gold);
	}

	/* Works Grid */
	.works-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
		gap: var(--space-4);
	}

	/* Empty state */
	.empty-state {
		grid-column: 1 / -1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: var(--space-3);
		padding: var(--space-8);
		color: var(--color-text-muted);
		text-align: center;
	}

	.clear-filter-btn {
		padding: var(--space-2) var(--space-4);
		font-size: var(--font-sm);
		color: var(--color-gold);
		background: transparent;
		border: 1px solid var(--color-gold-dim);
		border-radius: var(--radius-md);
		cursor: pointer;
	}

	.clear-filter-btn:hover {
		background: var(--color-gold-dim-bg);
	}

	/* Mobile Filters Sheet */
	.mobile-filters {
		padding: var(--space-4);
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.mobile-filters-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.mobile-filters-header h2 {
		font-size: var(--font-lg);
		font-weight: var(--font-medium);
		color: var(--color-text-primary);
		margin: 0;
	}

	.clear-all-btn {
		font-size: var(--font-sm);
		font-family: var(--font-ui);
		color: var(--color-gold);
		background: none;
		border: none;
		cursor: pointer;
	}

	.mobile-filter-section {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.mobile-filter-section h3 {
		font-size: var(--font-sm);
		font-family: var(--font-ui);
		font-weight: var(--font-medium);
		color: var(--color-text-secondary);
		margin: 0;
	}

	.mobile-select {
		width: 100%;
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-sm);
		font-family: var(--font-ui);
		color: var(--color-text-primary);
		background: var(--color-bg-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		cursor: pointer;
	}

	.mobile-select:focus {
		outline: none;
		border-color: var(--color-gold-dim);
	}

	.mobile-search-wrapper {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-3);
		background: var(--color-bg-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		color: var(--color-text-muted);
	}

	.mobile-search-input {
		flex: 1;
		background: none;
		border: none;
		font-size: var(--font-sm);
		font-family: var(--font-ui);
		color: var(--color-text-primary);
		outline: none;
	}

	.mobile-search-input::placeholder {
		color: var(--color-text-muted);
	}

	.apply-filters-btn {
		padding: var(--space-3);
		font-size: var(--font-sm);
		font-family: var(--font-ui);
		font-weight: var(--font-medium);
		color: var(--color-bg-base);
		background: var(--color-gold);
		border: none;
		border-radius: var(--radius-md);
		cursor: pointer;
		margin-top: var(--space-2);
	}

	.apply-filters-btn:hover {
		background: var(--color-gold-bright);
	}

	/* Responsive */
	@media (max-width: 768px) {
		.library-page {
			padding: var(--space-4);
		}

		.page-title {
			font-size: calc(var(--text-size, 1rem) * 1.25);
		}

		.desktop-only {
			display: none;
		}

		.mobile-only {
			display: block;
		}

		.works-grid {
			grid-template-columns: 1fr;
		}
	}

</style>
