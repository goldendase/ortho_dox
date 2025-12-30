<!--
  Root Layout

  Uses AppShell for unified layout management across
  Scripture and Library reading modes.

  Features:
  - Responsive layout with mobile sheets
  - Bottom chat panel (desktop)
  - Navigation drawer
  - Study panel for contextual content
-->
<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import '$styles/app.css';
	import { auth } from '$lib/stores';
	import { layout } from '$lib/stores/layout.svelte';
	import { AppShell } from '$lib/components/layout';
	import Toast from '$lib/components/ui/Toast.svelte';

	let { children, data } = $props();

	// Initialize layout store with mobile detection
	onMount(() => {
		// Auth guard: redirect to /auth if not authenticated
		// Skip if already on /auth to avoid redirect loop
		if (!auth.isAuthenticated && $page.url.pathname !== '/auth') {
			goto('/auth', { replaceState: true });
		}

		// Initialize mobile detection in layout store
		layout.initMobileDetection();
	});
</script>

<AppShell books={data?.books ?? []}>
	{@render children()}
</AppShell>

<Toast />
