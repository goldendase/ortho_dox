<!--
  Root Layout

  Desktop: 3:2 split between reader and side panel (tabbed: Notes/Chat)
  Mobile: Full-width reader, side panel as sheet
-->
<script lang="ts">
	import { onMount } from 'svelte';
	import '$styles/app.css';
	import { ui } from '$lib/stores';
	import Sheet from '$lib/components/ui/Sheet.svelte';
	import Header from '$lib/components/navigation/Header.svelte';
	import SidePanel from '$lib/components/SidePanel.svelte';

	let { children, data } = $props();

	// Track if we're on mobile (for conditional sheet rendering)
	let isMobile = $state(false);

	onMount(() => {
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

	<main class="app-main">
		<div class="reader-pane">
			{@render children()}
		</div>

		<!-- Desktop: Side panel always visible in sidebar -->
		<aside class="sidebar-pane desktop-only">
			<SidePanel />
		</aside>
	</main>

	<!-- Side panel sheet (mobile only) -->
	{#if isMobile}
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
