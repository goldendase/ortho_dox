<!--
  AppShell Component

  Master layout manager that renders different UIs based on app mode:
  - Read mode: Header + Drawer + Content + Study Panel + Action Bar
  - Search mode: Search UI + Action Bar
  - Shelf mode: Reading history UI + Action Bar
  - Ask mode: AI chat UI + Action Bar
-->
<script lang="ts">
	import { page } from '$app/stores';
	import { layout } from '$lib/stores/layout.svelte';
	import { preferences } from '$lib/stores/preferences.svelte';
	import Header from './Header.svelte';
	import ActionBar from './ActionBar.svelte';
	import NavigationDrawer from './NavigationDrawer.svelte';
	import StudyPanel from './StudyPanel.svelte';
	import AskPanel from './AskPanel.svelte';
	import SearchSurface from './SearchSurface.svelte';
	import ShelfSurface from './ShelfSurface.svelte';
	import Sheet from '$lib/components/ui/Sheet.svelte';
	import type { Book } from '$lib/api';

	interface Props {
		books?: Book[];
		children: import('svelte').Snippet;
	}

	let { books = [], children }: Props = $props();

	// Check if on auth page (special layout)
	let isAuthPage = $derived($page.url.pathname === '/auth');

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
		<Header />

		{#if layout.drawerOpen && !layout.isMobile}
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<div class="drawer-backdrop" onclick={() => layout.closeDrawer()}></div>
			<aside class="nav-drawer">
				<NavigationDrawer {books} />
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
			<NavigationDrawer {books} />
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
{:else if layout.mode === 'shelf'}
	<!-- Shelf Mode -->
	<div class="app-shell simple-layout" style="--text-size: {preferences.textSizeCss}">
		<main class="app-main">
			<ShelfSurface />
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
		z-index: 20;
	}

	/* Backdrop for closing drawer when clicking outside */
	.drawer-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.3);
		z-index: 10;
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
		grid-row: -2 / -1;
	}

	/* Mobile adjustments */
	@media (max-width: 768px) {
		.read-layout {
			grid-template-columns: 1fr !important;
			grid-template-rows: var(--header-height) 1fr var(--action-bar-height, 56px);
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
