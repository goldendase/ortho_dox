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
	import { ui, auth, preferences } from '$lib/stores';
	import Sheet from '$lib/components/ui/Sheet.svelte';
	import Header from '$lib/components/navigation/Header.svelte';
	import SidePanel from '$lib/components/SidePanel.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';

	let { children, data } = $props();

	// Track if we're on mobile (for conditional sheet rendering)
	let isMobile = $state(false);

	// Check if we're on the auth page (hide side panel, full-width layout)
	let isAuthPage = $derived($page.url.pathname === '/auth');

	// Check if we're in library reading mode (has its own layout)
	let isLibraryReader = $derived(
		$page.url.pathname.startsWith('/library/') &&
		$page.url.pathname.split('/').length >= 4
	);

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

{#if isLibraryReader}
	<!-- Library reader has its own full-page layout -->
	{@render children()}
{:else}
	<div class="app-layout">
		<Header books={data?.books ?? []} />

		<main class="app-main" class:full-width={isAuthPage} class:collapsed={ui.sidePanelCollapsed}>
			<div class="reader-pane" style="--text-size: {preferences.textSizeCss}">
				{@render children()}
			</div>

			<!-- Desktop: Side panel always visible in sidebar (hidden on auth page) -->
			{#if !isAuthPage}
				<aside class="sidebar-pane desktop-only" class:collapsed={ui.sidePanelCollapsed}>
					{#if ui.sidePanelCollapsed}
						<button
							class="expand-rail"
							onclick={() => ui.expandSidePanel()}
							aria-label="Expand panel"
						>
							<Icon name="chevron-left" size={16} />
						</button>
					{:else}
						<SidePanel />
					{/if}
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
{/if}

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
		grid-template-columns: 3fr 2fr; /* 3:2 reader:panel ratio */
		min-height: 0; /* Allow grid item to shrink */
		overflow: hidden;
		transition: grid-template-columns var(--transition-normal);
	}

	.app-main.full-width {
		grid-template-columns: 1fr;
	}

	.app-main.collapsed {
		grid-template-columns: 1fr 48px;
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
		transition: width var(--transition-normal);
	}

	.sidebar-pane.collapsed {
		display: flex;
		align-items: stretch;
	}

	.expand-rail {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 100%;
		height: 100%;
		color: var(--color-text-muted);
		background: var(--color-bg-elevated);
		cursor: pointer;
		transition: color var(--transition-fast), background var(--transition-fast);
	}

	.expand-rail:hover {
		color: var(--color-text-primary);
		background: var(--color-bg-hover);
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
