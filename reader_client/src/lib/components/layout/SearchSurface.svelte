<!--
  SearchSurface Component

  Semantic search across OSB and Library content.
-->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { layout } from '$lib/stores/layout.svelte';
	import {
		semanticSearch,
		type OSBSearchResult,
		type LibrarySearchResult
	} from '$lib/api';
	import { processScriptureMarkers } from '$lib/utils/chatAnnotations';
	import Icon from '$lib/components/ui/Icon.svelte';

	// Storage key
	const STORAGE_KEY = 'semantic-search-state';

	// Load persisted state
	function loadState() {
		if (!browser) return null;
		try {
			const saved = localStorage.getItem(STORAGE_KEY);
			return saved ? JSON.parse(saved) : null;
		} catch {
			return null;
		}
	}

	// Save state to localStorage
	function saveState() {
		if (!browser) return;
		try {
			localStorage.setItem(STORAGE_KEY, JSON.stringify({
				query,
				source,
				maxResults,
				scoreThreshold,
				osbResults,
				libraryResults,
				hasSearched
			}));
		} catch {
			// Ignore storage errors
		}
	}

	// Initialize from localStorage
	const savedState = loadState();

	// Filter state
	let source = $state<'osb' | 'library'>(savedState?.source ?? 'osb');
	let maxResults = $state(savedState?.maxResults ?? 10);
	let scoreThreshold = $state(savedState?.scoreThreshold ?? 0.35);

	// Search state
	let query = $state(savedState?.query ?? '');
	let isSearching = $state(false);
	let hasSearched = $state(savedState?.hasSearched ?? false);
	let error = $state<string | null>(null);

	// Results
	let osbResults = $state<OSBSearchResult[]>(savedState?.osbResults ?? []);
	let libraryResults = $state<LibrarySearchResult[]>(savedState?.libraryResults ?? []);

	// Expanded state (not persisted)
	let expandedIndices = $state<Set<number>>(new Set());

	// Current results based on source
	let results = $derived(source === 'osb' ? osbResults : libraryResults);
	let hasResults = $derived(results.length > 0);

	// Persist state on changes
	$effect(() => {
		saveState();
	});

	// Handle search
	async function handleSearch() {
		const q = query.trim();
		if (!q) return;

		isSearching = true;
		hasSearched = true;
		error = null;
		expandedIndices = new Set();

		try {
			if (source === 'osb') {
				const response = await semanticSearch.osb(q, { limit: maxResults });
				osbResults = response.results.filter(r => r.score >= scoreThreshold);
				libraryResults = [];
			} else {
				const response = await semanticSearch.library(q, { limit: maxResults });
				libraryResults = response.results.filter(r => r.score >= scoreThreshold);
				osbResults = [];
			}
		} catch (e) {
			console.error('Search failed:', e);
			error = e instanceof Error ? e.message : 'Search failed';
		} finally {
			isSearching = false;
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			handleSearch();
		}
		if (e.key === 'Escape') {
			layout.setMode('read');
		}
	}

	function clearSearch() {
		query = '';
		osbResults = [];
		libraryResults = [];
		hasSearched = false;
		error = null;
		expandedIndices = new Set();
	}

	// Toggle expansion
	function toggleExpand(index: number) {
		const newSet = new Set(expandedIndices);
		if (newSet.has(index)) {
			newSet.delete(index);
		} else {
			newSet.add(index);
		}
		expandedIndices = newSet;
	}

	// Navigation
	function goToOsbResult(result: OSBSearchResult) {
		if (result.book_id && result.chapter) {
			const verse = result.verse_start ?? 1;
			goto(`/read/${result.book_id}/${result.chapter}#osb-${result.book_id}-${result.chapter}-${verse}`);
			layout.setMode('read');
		}
	}

	function goToLibraryResult(result: LibrarySearchResult) {
		goto(`/library/${result.work_id}/${result.node_id}`);
		layout.setMode('read');
	}

	// Formatting helpers
	function formatOsbRef(result: OSBSearchResult): string | null {
		if (result.book_name && result.chapter) {
			if (result.verse_start && result.verse_end && result.verse_start !== result.verse_end) {
				return `${result.book_name} ${result.chapter}:${result.verse_start}-${result.verse_end}`;
			}
			if (result.verse_start) {
				return `${result.book_name} ${result.chapter}:${result.verse_start}`;
			}
			return `${result.book_name} ${result.chapter}`;
		}
		// Return null when no location - badge already shows the type
		return null;
	}

	function formatSourceType(type: string): string {
		switch (type) {
			case 'osb_study': return 'Study Note';
			case 'osb_article': return 'Article';
			case 'osb_chapter': return 'Scripture';
			default: return type;
		}
	}

	function formatScore(score: number): string {
		return `${Math.round(score * 100)}%`;
	}
</script>

<div class="search-surface">
	<div class="search-container">
		<!-- Header -->
		<header class="page-header">
			<h1 class="page-title">Semantic Search</h1>
			<p class="page-subtitle">
				Search across study notes, articles, and Scripture
			</p>
		</header>

		<!-- Filters -->
		<section class="filters-section">
			<h2 class="section-label">Filters</h2>
			<div class="filter-grid">
				<div class="filter-group">
					<label class="filter-label" for="source-select">Source</label>
					<select id="source-select" bind:value={source} class="filter-select">
						<option value="osb">Orthodox Study Bible</option>
						<option value="library">Theological Library</option>
					</select>
				</div>

				<div class="filter-group">
					<label class="filter-label" for="max-results">Max Results</label>
					<select id="max-results" bind:value={maxResults} class="filter-select">
						<option value={5}>5</option>
						<option value={10}>10</option>
						<option value={15}>15</option>
						<option value={20}>20</option>
					</select>
				</div>

				<div class="filter-group">
					<label class="filter-label" for="threshold">Score Threshold</label>
					<input
						id="threshold"
						type="number"
						bind:value={scoreThreshold}
						min="0"
						max="1"
						step="0.05"
						class="filter-input"
					/>
				</div>
			</div>
		</section>

		<!-- Search -->
		<section class="search-section">
			<div class="search-row">
				<div class="search-input-wrapper">
					<Icon name="search" size={18} />
					<input
						type="text"
						bind:value={query}
						onkeydown={handleKeydown}
						placeholder="Enter your search query..."
						class="search-input"
					/>
					{#if query}
						<button class="clear-input-btn" onclick={clearSearch} aria-label="Clear">
							<Icon name="x" size={16} />
						</button>
					{/if}
				</div>
				<button
					class="search-btn"
					onclick={handleSearch}
					disabled={!query.trim() || isSearching}
				>
					{#if isSearching}
						<span class="spinner-inline"></span>
						Searching...
					{:else}
						Search
					{/if}
				</button>
			</div>
		</section>

		<!-- Results -->
		<section class="results-section">
			{#if error}
				<div class="status-message error">
					<Icon name="alert-circle" size={18} />
					<span>{error}</span>
				</div>
			{:else if hasSearched && !hasResults && !isSearching}
				<div class="status-message">
					<span>No results found for "{query}"</span>
				</div>
			{:else if hasResults}
				<div class="results-header">
					<span class="results-count">{results.length} result{results.length !== 1 ? 's' : ''}</span>
				</div>
				<ul class="results-list">
					{#each results as result, i}
						{@const isExpanded = expandedIndices.has(i)}
						<li class="result-card" class:expanded={isExpanded}>
							<button class="result-header" onclick={() => toggleExpand(i)}>
								<div class="result-info">
									{#if source === 'osb'}
										{@const osbResult = result as OSBSearchResult}
										{@const ref = formatOsbRef(osbResult)}
										<span class="result-type type-{osbResult.source_type}">{formatSourceType(osbResult.source_type)}</span>
										{#if ref}
											<span class="result-ref">{ref}</span>
										{/if}
									{:else}
										{@const libResult = result as LibrarySearchResult}
										<div class="result-lib-info">
											<div class="result-lib-top">
												<span class="result-type type-library">Library</span>
												{#if libResult.work_title}
													<span class="result-work">{libResult.work_title}</span>
												{/if}
												{#if libResult.author_name}
													<span class="result-author">by {libResult.author_name}</span>
												{/if}
												<span class="result-score">{formatScore(result.score)}</span>
											</div>
											<span class="result-node">{libResult.node_title || libResult.node_id}</span>
										</div>
									{/if}
									{#if source === 'osb'}
										<span class="result-score">{formatScore(result.score)}</span>
									{/if}
								</div>
								<Icon name={isExpanded ? 'chevron-up' : 'chevron-down'} size={16} class="expand-icon" />
							</button>

							{#if isExpanded}
								<div class="result-body">
									<div class="result-text scripture-text">
										{@html processScriptureMarkers(result.text)}
									</div>
									{#if source === 'osb'}
										{@const osbResult = result as OSBSearchResult}
										{#if osbResult.book_id && osbResult.chapter}
											<button class="go-btn" onclick={() => goToOsbResult(osbResult)}>
												Go to passage <Icon name="arrow-right" size={14} />
											</button>
										{/if}
									{:else}
										<button class="go-btn" onclick={() => goToLibraryResult(result as LibrarySearchResult)}>
											Go to section <Icon name="arrow-right" size={14} />
										</button>
									{/if}
								</div>
							{:else}
								<p class="result-preview">{result.text}</p>
							{/if}
						</li>
					{/each}
				</ul>
			{/if}
		</section>
	</div>
</div>

<style>
	.search-surface {
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
	.search-container {
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

	/* Sections */
	.filters-section,
	.search-section {
		background: var(--color-bg-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-lg);
		padding: var(--space-4);
	}

	.section-label {
		font-family: var(--font-ui);
		font-size: var(--font-xs);
		font-weight: var(--font-semibold);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--color-text-muted);
		margin-bottom: var(--space-3);
	}

	/* Filters */
	.filter-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
		gap: var(--space-4);
	}

	.filter-group {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.filter-label {
		font-family: var(--font-ui);
		font-size: var(--font-xs);
		color: var(--color-text-secondary);
	}

	.filter-select,
	.filter-input {
		padding: var(--space-2) var(--space-3);
		background: var(--color-bg-base);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		color: var(--color-text-primary);
		width: 100%;
	}

	.filter-select:focus,
	.filter-input:focus {
		outline: none;
		border-color: var(--color-gold);
	}

	/* Search */
	.search-row {
		display: flex;
		gap: var(--space-2);
	}

	.search-input-wrapper {
		flex: 1;
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-3);
		background: var(--color-bg-base);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		color: var(--color-text-muted);
		transition: border-color var(--transition-fast);
	}

	.search-input-wrapper:focus-within {
		border-color: var(--color-gold);
	}

	.search-input {
		flex: 1;
		min-width: 0;
		background: transparent;
		border: none;
		outline: none;
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		color: var(--color-text-primary);
	}

	.search-input::placeholder {
		color: var(--color-text-muted);
	}

	.clear-input-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 2px;
		color: var(--color-text-muted);
		border-radius: var(--radius-sm);
		transition: color var(--transition-fast);
	}

	.clear-input-btn:hover {
		color: var(--color-text-primary);
	}

	.search-btn {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-4);
		background: var(--color-gold);
		color: var(--color-bg-base);
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		font-weight: var(--font-medium);
		border-radius: var(--radius-md);
		white-space: nowrap;
		transition: background var(--transition-fast), opacity var(--transition-fast);
	}

	.search-btn:hover:not(:disabled) {
		background: var(--color-gold-bright);
	}

	.search-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.spinner-inline {
		width: 14px;
		height: 14px;
		border: 2px solid rgba(0, 0, 0, 0.2);
		border-top-color: currentColor;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	/* Status */
	.status-message {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: var(--space-2);
		padding: var(--space-6);
		color: var(--color-text-muted);
		font-family: var(--font-ui);
		font-size: var(--font-sm);
	}

	.status-message.error {
		color: var(--color-error);
	}

	/* Results */
	.results-section {
		min-height: 100px;
	}

	.results-header {
		margin-bottom: var(--space-3);
	}

	.results-count {
		font-family: var(--font-ui);
		font-size: var(--font-xs);
		color: var(--color-text-muted);
	}

	.results-list {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.result-card {
		background: var(--color-bg-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		overflow: hidden;
		transition: border-color var(--transition-fast);
	}

	.result-card:hover {
		border-color: var(--color-text-muted);
	}

	.result-card.expanded {
		border-color: var(--color-gold-dim);
	}

	.result-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		width: 100%;
		padding: var(--space-3);
		text-align: left;
		color: var(--color-text-muted);
		transition: background var(--transition-fast);
	}

	.result-header:hover {
		background: var(--color-bg-hover);
	}

	.result-info {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		flex-wrap: wrap;
		min-width: 0;
	}

	.result-type {
		padding: 2px var(--space-2);
		border-radius: var(--radius-sm);
		font-family: var(--font-ui);
		font-size: var(--font-xs);
		font-weight: var(--font-medium);
		white-space: nowrap;
	}

	/* Badge color variants */
	.result-type.type-osb_study {
		background: rgba(201, 162, 39, 0.15);
		color: var(--color-gold);
	}

	.result-type.type-osb_article {
		background: rgba(100, 149, 237, 0.15);
		color: #6495ed;
	}

	.result-type.type-osb_chapter {
		background: rgba(144, 238, 144, 0.15);
		color: #7cb87c;
	}

	.result-type.type-library {
		background: rgba(186, 135, 189, 0.15);
		color: #ba87bd;
	}

	.result-lib-info {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		flex: 1;
		min-width: 0;
	}

	.result-lib-top {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		flex-wrap: wrap;
	}

	.result-work {
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		font-weight: var(--font-medium);
		color: var(--color-text-primary);
	}

	.result-author {
		font-family: var(--font-ui);
		font-size: var(--font-xs);
		color: var(--color-text-muted);
		font-style: italic;
	}

	.result-node {
		font-family: var(--font-ui);
		font-size: var(--font-xs);
		color: var(--color-gold);
	}

	.result-ref {
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		font-weight: var(--font-medium);
		color: var(--color-gold);
	}

	.result-score {
		font-family: var(--font-ui);
		font-size: var(--font-xs);
		color: var(--color-text-muted);
	}

	.result-preview {
		padding: 0 var(--space-3) var(--space-3);
		font-family: var(--font-body);
		font-size: var(--text-size, var(--font-sm));
		color: var(--color-text-secondary);
		line-height: var(--leading-normal);
		overflow: hidden;
		display: -webkit-box;
		-webkit-line-clamp: 3;
		line-clamp: 3;
		-webkit-box-orient: vertical;
	}

	.result-body {
		padding: var(--space-3);
		border-top: 1px solid var(--color-border);
		background: var(--color-bg-base);
	}

	.result-text {
		font-family: var(--font-body);
		font-size: var(--text-size, var(--font-sm));
		line-height: var(--leading-relaxed);
		color: var(--color-text-primary);
		white-space: pre-wrap;
	}

	.result-text :global(.scripture-ref) {
		color: var(--color-gold);
		text-decoration: none;
		border-bottom: 1px dotted var(--color-gold-dim);
		cursor: pointer;
	}

	.result-text :global(.scripture-ref:hover) {
		color: var(--color-gold-bright);
		border-bottom-color: var(--color-gold);
	}

	.go-btn {
		display: inline-flex;
		align-items: center;
		gap: var(--space-1);
		margin-top: var(--space-3);
		padding: var(--space-2) var(--space-3);
		background: var(--color-bg-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-sm);
		font-family: var(--font-ui);
		font-size: var(--font-xs);
		font-weight: var(--font-medium);
		color: var(--color-text-secondary);
		transition: color var(--transition-fast), border-color var(--transition-fast);
	}

	.go-btn:hover {
		color: var(--color-gold);
		border-color: var(--color-gold-dim);
	}

	/* Desktop: wider container, more padding */
	@media (min-width: 768px) {
		.search-surface {
			padding: var(--space-8);
		}

		.search-container {
			max-width: 640px;
		}

		.page-header {
			padding-top: var(--space-12);
		}

		.page-title {
			font-size: var(--font-3xl);
		}

		.filters-section,
		.search-section {
			padding: var(--space-5);
		}
	}

	/* Large desktop: even more space */
	@media (min-width: 1024px) {
		.search-container {
			max-width: 720px;
		}

		.page-header {
			padding-top: var(--space-16);
			margin-bottom: var(--space-4);
		}

		.filter-grid {
			grid-template-columns: repeat(3, 1fr);
		}
	}

	/* Mobile adjustments */
	@media (max-width: 480px) {
		.search-surface {
			padding: var(--space-3);
			padding-bottom: var(--space-12);
		}

		.page-header {
			padding-top: var(--space-6);
		}

		.page-title {
			font-size: var(--font-xl);
		}

		.search-row {
			flex-direction: column;
		}

		.search-btn {
			width: 100%;
			justify-content: center;
		}

		.result-info {
			flex-direction: column;
			align-items: flex-start;
			gap: var(--space-1);
		}
	}
</style>
