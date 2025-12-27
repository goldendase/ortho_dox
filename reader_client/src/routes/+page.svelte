<!--
  Home Page

  Redirects to last reading position or shows welcome screen.
-->
<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { reader, positionToPath, ui } from '$lib/stores';

	onMount(() => {
		// If we have a saved position, redirect there
		if (reader.position) {
			goto(positionToPath(reader.position), { replaceState: true });
		}
	});
</script>

<div class="welcome">
	<div class="welcome-content">
		<h1 class="welcome-title">Orthodox Study Bible</h1>
		<p class="welcome-subtitle text-secondary">
			Scripture with patristic commentary
		</p>

		<p class="welcome-hint text-muted">
			Glory to God for all things
		</p>

		<div class="button-group">
			<button class="start-button" onclick={() => ui.openBookPicker()}>
				Orthodox Study Bible
			</button>
			<a href="/library" class="library-button">
				Library
			</a>
		</div>
	</div>
</div>

<style>
	.welcome {
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 100%;
		padding: var(--space-8);
		text-align: center;
	}

	.welcome-content {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-4);
	}

	.welcome-title {
		font-size: var(--font-3xl);
		font-weight: var(--font-medium);
		color: var(--color-gold);
		letter-spacing: var(--tracking-tight);
	}

	.welcome-subtitle {
		font-size: var(--font-lg);
		margin-bottom: var(--space-4);
	}

	.button-group {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		align-items: center;
	}

	.start-button {
		padding: var(--space-4) var(--space-8);
		font-family: var(--font-ui);
		font-size: var(--font-base);
		font-weight: var(--font-medium);
		color: var(--color-bg-base);
		background: var(--color-gold);
		border-radius: var(--radius-md);
		transition: background var(--transition-fast);
	}

	.start-button:hover {
		background: var(--color-gold-bright);
	}

	.library-button {
		padding: var(--space-3) var(--space-6);
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		font-weight: var(--font-medium);
		color: var(--color-gold);
		background: transparent;
		border: 1px solid var(--color-gold);
		border-radius: var(--radius-md);
		text-decoration: none;
		transition: background var(--transition-fast), color var(--transition-fast);
	}

	.library-button:hover {
		background: var(--color-gold);
		color: var(--color-bg-base);
	}

	.welcome-hint {
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		font-style: italic;
		margin-bottom: var(--space-2);
	}
</style>
