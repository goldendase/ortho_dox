<!--
  Root Layout

  Desktop: 3:2 split between reader and side panel (tabbed: Notes/Chat)
  Mobile: Full-width reader, side panel as sheet
-->
<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import '$styles/app.css';
	import { ui, auth } from '$lib/stores';
	import Sheet from '$lib/components/ui/Sheet.svelte';
	import Header from '$lib/components/navigation/Header.svelte';
	import SidePanel from '$lib/components/SidePanel.svelte';

	let { children, data } = $props();

	// Track if we're on mobile (for conditional sheet rendering)
	let isMobile = $state(false);

	// Check if we're on the auth page (hide side panel, full-width layout)
	let isAuthPage = $derived($page.url.pathname === '/auth');

	// Check authentication on mount
	onMount(() => {
		// Auth guard: redirect to /auth if not authenticated
		// Skip if already on /auth to avoid redirect loop
		if (!auth.isAuthenticated && $page.url.pathname !== '/auth') {
			goto('/auth', { replaceState: true });
		}

		const mediaQuery = window.matchMedia('(max-width: 768px)');
		isMobile = mediaQuery.matches;

		const handler = (e: MediaQueryListEvent) => {
			isMobile = e.matches;
		};
		mediaQuery.addEventListener('change', handler);

		return () => mediaQuery.removeEventListener('change', handler);
	});
</script>

<div class="app-layout">
	<Header books={data?.books ?? []} />

	<main class="app-main" class:full-width={isAuthPage}>
		<div class="reader-pane">
			{@render children()}
		</div>

		<!-- Desktop: Side panel always visible in sidebar (hidden on auth page) -->
		{#if !isAuthPage}
			<aside class="sidebar-pane desktop-only">
				<SidePanel />
			</aside>
		{/if}
	</main>

	<!-- Side panel sheet (mobile only, hidden on auth page) -->
	{#if isMobile && !isAuthPage}
		<Sheet bind:open={ui.sidePanelOpen}>
			<SidePanel />
		</Sheet>
	{/if}
</div>

<style>
	.app-layout {
		display: grid;
		grid-template-rows: var(--header-height) 1fr;
		height: 100dvh; /* Fixed height, not min-height */
		overflow: hidden;
		background: var(--color-bg-base);
	}

	.app-main {
		display: grid;
		grid-template-columns: 3fr 2fr;
		min-height: 0; /* Allow grid item to shrink */
		overflow: hidden;
	}

	.app-main.full-width {
		grid-template-columns: 1fr;
	}

	.reader-pane {
		overflow-y: auto;
		overflow-x: hidden;
		min-height: 0;
	}

	.sidebar-pane {
		border-left: 1px solid var(--color-border);
		overflow: hidden;
		background: var(--color-bg-surface);
		min-height: 0;
	}

	/* Mobile: single column, full height */
	@media (max-width: 768px) {
		.app-main {
			grid-template-columns: 1fr;
		}

		.sidebar-pane {
			display: none;
		}
	}
</style>
