<!--
  AppShell Component

  Master layout manager that renders different UIs based on app mode:
  - Read mode: Header + Drawer + Content + Study Panel + Action Bar
  - Search mode: Search UI + Action Bar
  - Chat mode: Chat UI + Action Bar
  - Settings mode: Settings UI + Action Bar
-->
<script lang="ts">
	import { page } from '$app/stores';
	import { layout } from '$lib/stores/layout.svelte';
	import { preferences, TEXT_SIZES, TEXT_SIZE_LABELS, type TextSize } from '$lib/stores/preferences.svelte';
	import Header from './Header.svelte';
	import ActionBar from './ActionBar.svelte';
	import NavigationDrawer from './NavigationDrawer.svelte';
	import StudyPanel from './StudyPanel.svelte';
	import AskPanel from './AskPanel.svelte';
	import SearchSurface from './SearchSurface.svelte';
	import Sheet from '$lib/components/ui/Sheet.svelte';
	import type { Book } from '$lib/api';

	interface Props {
		books?: Book[];
		children: import('svelte').Snippet;
	}

	let { books = [], children }: Props = $props();

	// Check if on auth page (special layout)
	let isAuthPage = $derived($page.url.pathname === '/auth');

	// Check if in library mode (for drawer context)
	let isLibraryMode = $derived($page.url.pathname.startsWith('/library/'));

	// Should show study panel (read mode, desktop only, when has content)
	let showStudyPanel = $derived(
		layout.mode === 'read' && !layout.isMobile && layout.hasStudyContent
	);
</script>

{#if isAuthPage}
	<!-- Auth page - minimal layout -->
	<div class="app-shell auth-layout">
		<main class="app-main">
			<div class="reader-pane">
				{@render children()}
			</div>
		</main>
	</div>
{:else if layout.mode === 'read'}
	<!-- Read Mode -->
	<div
		class="app-shell read-layout"
		class:has-drawer={layout.drawerOpen && !layout.isMobile}
		class:has-study-panel={showStudyPanel}
		style="--text-size: {preferences.textSizeCss}"
	>
		<Header {books} />

		{#if layout.drawerOpen && !layout.isMobile}
			<aside class="nav-drawer">
				<NavigationDrawer {books} {isLibraryMode} />
			</aside>
		{/if}

		<main class="app-main">
			<div class="reader-pane">
				{@render children()}
			</div>
		</main>

		{#if showStudyPanel}
			<aside class="study-panel">
				<StudyPanel />
			</aside>
		{/if}

		<ActionBar />
	</div>

	<!-- Mobile Sheets (Read mode only) -->
	{#if layout.isMobile}
		<Sheet
			open={layout.navSheetState !== 'closed'}
			position="left"
			onclose={() => layout.setNavSheetState('closed')}
		>
			<NavigationDrawer {books} {isLibraryMode} />
		</Sheet>

		<Sheet
			open={layout.studySheetState !== 'closed'}
			onclose={() => layout.setStudySheetState('closed')}
		>
			<StudyPanel />
		</Sheet>
	{/if}
{:else if layout.mode === 'search'}
	<!-- Search Mode -->
	<div class="app-shell simple-layout" style="--text-size: {preferences.textSizeCss}">
		<main class="app-main">
			<SearchSurface />
		</main>
		<ActionBar />
	</div>
{:else if layout.mode === 'ask'}
	<!-- Ask Mode -->
	<div class="app-shell simple-layout" style="--text-size: {preferences.textSizeCss}">
		<main class="app-main">
			<AskPanel />
		</main>
		<ActionBar />
	</div>
{:else if layout.mode === 'settings'}
	<!-- Settings Mode -->
	<div class="app-shell simple-layout">
		<main class="app-main settings-content">
			<div class="settings-panel">
				<h1>Settings</h1>

				<div class="setting-group">
					<label class="setting-label">Font Size</label>
					<div class="font-size-options">
						{#each TEXT_SIZES as size}
							<button
								class="font-size-btn"
								class:active={preferences.textSize === size}
								onclick={() => preferences.setTextSize(size)}
							>
								{TEXT_SIZE_LABELS[size]}
							</button>
						{/each}
					</div>
					<p class="setting-hint">Adjusts text size for scripture and library reading.</p>
				</div>
			</div>
		</main>
		<ActionBar />
	</div>
{/if}

<style>
	/* Base shell */
	.app-shell {
		display: grid;
		height: 100dvh;
		overflow: hidden;
		background: var(--color-bg-base);
	}

	/* Auth layout - just content */
	.auth-layout {
		grid-template-rows: 1fr;
	}

	/* Simple layout - content + action bar */
	.simple-layout {
		grid-template-rows: 1fr var(--action-bar-height, 48px);
	}

	/* Read layout - header + content + action bar */
	.read-layout {
		grid-template-rows: var(--header-height) 1fr var(--action-bar-height, 48px);
		grid-template-columns: 1fr;
	}

	.read-layout.has-drawer {
		grid-template-columns: 280px 1fr;
	}

	.read-layout.has-study-panel {
		grid-template-columns: 1fr 360px;
	}

	.read-layout.has-drawer.has-study-panel {
		grid-template-columns: 280px 1fr 360px;
	}

	/* Header spans full width */
	.read-layout > :global(header) {
		grid-column: 1 / -1;
		grid-row: 1;
	}

	/* Navigation drawer */
	.nav-drawer {
		grid-row: 2;
		grid-column: 1;
		border-right: 1px solid var(--color-border);
		background: var(--color-bg-surface);
		overflow-y: auto;
		overflow-x: hidden;
	}

	/* Main content area */
	.app-main {
		min-height: 0;
		overflow: hidden;
		display: flex;
		flex-direction: column;
	}

	.read-layout .app-main {
		grid-row: 2;
	}

	.reader-pane {
		flex: 1;
		overflow-y: auto;
		overflow-x: hidden;
	}

	/* Study panel */
	.study-panel {
		grid-row: 2;
		grid-column: -2;
		border-left: 1px solid var(--color-border);
		background: var(--color-bg-surface);
		overflow-y: auto;
		overflow-x: hidden;
	}

	/* Action bar spans full width */
	.app-shell > :global(.action-bar) {
		grid-column: 1 / -1;
		grid-row: -1;
	}

	/* Settings content */
	.settings-content {
		display: flex;
		justify-content: center;
		padding: var(--space-8) var(--space-4);
		overflow-y: auto;
	}

	.settings-panel {
		width: 100%;
		max-width: 500px;
	}

	.settings-panel h1 {
		font-size: var(--font-2xl);
		font-weight: var(--font-medium);
		color: var(--color-gold);
		margin-bottom: var(--space-8);
	}

	.setting-group {
		margin-bottom: var(--space-8);
	}

	.setting-label {
		display: block;
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		font-weight: var(--font-semibold);
		color: var(--color-text-secondary);
		margin-bottom: var(--space-3);
		text-transform: uppercase;
		letter-spacing: var(--tracking-wide);
	}

	.font-size-options {
		display: inline-flex;
		gap: var(--space-2);
		background: var(--color-bg-surface);
		padding: var(--space-1);
		border-radius: var(--radius-md);
		border: 1px solid var(--color-border);
	}

	.font-size-btn {
		padding: var(--space-2) var(--space-4);
		border: none;
		border-radius: var(--radius-sm);
		background: transparent;
		color: var(--color-text-secondary);
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.font-size-btn:hover {
		color: var(--color-text-primary);
	}

	.font-size-btn.active {
		background: var(--color-gold);
		color: var(--color-bg-base);
	}

	.setting-hint {
		margin-top: var(--space-3);
		font-family: var(--font-ui);
		font-size: var(--font-xs);
		color: var(--color-text-muted);
	}

	/* Mobile adjustments */
	@media (max-width: 768px) {
		.read-layout {
			grid-template-columns: 1fr !important;
		}

		.nav-drawer,
		.study-panel {
			display: none;
		}

		.simple-layout {
			grid-template-rows: 1fr var(--action-bar-height, 56px);
		}
	}
</style>
