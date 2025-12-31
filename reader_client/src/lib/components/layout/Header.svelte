<!--
  Header Component

  Minimal header with:
  - Hamburger menu (opens navigation drawer)
  - Mode navigation (Scripture, Library)
  - Prev/Next navigation arrows
  - Settings dropdown (font size)
-->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { layout } from '$lib/stores/layout.svelte';
	import { studyContext } from '$lib/stores/studyContext.svelte';
	import { preferences, TEXT_SIZES, TEXT_SIZE_LABELS, type TextSize } from '$lib/stores/preferences.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';

	// Settings dropdown state
	let settingsOpen = $state(false);

	// Navigation handlers
	function handlePrev() {
		if (studyContext.prevLink) {
			goto(studyContext.prevLink);
		}
	}

	function handleNext() {
		if (studyContext.nextLink) {
			goto(studyContext.nextLink);
		}
	}

	// Mode navigation handlers
	function goToScripture() {
		layout.openDrawer('scripture');
	}

	function goToLibrary() {
		goto('/library');
		layout.closeDrawer();
	}

	function toggleSettings() {
		settingsOpen = !settingsOpen;
	}

	function closeSettings() {
		settingsOpen = false;
	}

	function selectFontSize(size: TextSize) {
		preferences.setTextSize(size);
	}
</script>

<header class="header">
	<div class="header-left">
		<!-- Hamburger menu -->
		<button
			class="icon-btn touch-target"
			onclick={() => layout.toggleDrawer()}
			aria-label="Toggle navigation"
		>
			<Icon name="menu" size={20} />
		</button>

		<!-- Mode navigation buttons -->
		<div class="nav-buttons">
			<button
				class="nav-btn"
				onclick={goToScripture}
				aria-label="Scripture"
			>
				<Icon name="book-open" size={16} />
				<span class="nav-label">Scripture</span>
			</button>
			<button
				class="nav-btn"
				onclick={goToLibrary}
				aria-label="Library"
			>
				<Icon name="library" size={16} />
				<span class="nav-label">Library</span>
			</button>
		</div>
	</div>

	<div class="header-right">
		<!-- Prev/Next navigation -->
		<button
			class="icon-btn touch-target"
			onclick={handlePrev}
			disabled={!studyContext.canGoPrev}
			aria-label="Previous"
		>
			<Icon name="chevron-left" size={20} />
		</button>
		<button
			class="icon-btn touch-target"
			onclick={handleNext}
			disabled={!studyContext.canGoNext}
			aria-label="Next"
		>
			<Icon name="chevron-right" size={20} />
		</button>

		<!-- Settings dropdown -->
		<div class="settings-wrapper">
			<button
				class="icon-btn touch-target"
				class:active={settingsOpen}
				onclick={toggleSettings}
				aria-label="Settings"
				aria-expanded={settingsOpen}
			>
				<Icon name="settings" size={20} />
			</button>

			{#if settingsOpen}
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<!-- svelte-ignore a11y_click_events_have_key_events -->
				<div class="settings-backdrop" onclick={closeSettings}></div>
				<div class="settings-dropdown">
					<div class="dropdown-header">
						<span class="dropdown-title">Font Size</span>
					</div>
					<div class="font-size-options">
						{#each TEXT_SIZES as size}
							<button
								class="font-size-btn"
								class:active={preferences.textSize === size}
								onclick={() => selectFontSize(size)}
							>
								{TEXT_SIZE_LABELS[size]}
							</button>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	</div>
</header>

<style>
	.header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 var(--space-2);
		background: var(--color-bg-surface);
		border-bottom: 1px solid var(--color-border);
		height: var(--header-height);
		gap: var(--space-2);
	}

	.header-left,
	.header-right {
		display: flex;
		align-items: center;
		gap: var(--space-1);
	}

	.nav-buttons {
		display: flex;
		align-items: center;
		gap: var(--space-1);
		margin-left: var(--space-2);
		padding-left: var(--space-2);
		border-left: 1px solid var(--color-border);
	}

	.nav-btn {
		display: flex;
		align-items: center;
		gap: var(--space-1);
		padding: var(--space-1) var(--space-2);
		border-radius: var(--radius-sm);
		color: var(--color-text-secondary);
		font-family: var(--font-ui);
		font-size: var(--font-xs);
		font-weight: var(--font-medium);
		transition: background var(--transition-fast), color var(--transition-fast);
		white-space: nowrap;
	}

	.nav-btn:hover {
		background: var(--color-bg-hover);
		color: var(--color-text-primary);
	}

	.icon-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 40px;
		height: 40px;
		border-radius: var(--radius-md);
		color: var(--color-text-secondary);
		transition: background var(--transition-fast), color var(--transition-fast);
	}

	.icon-btn:hover:not(:disabled) {
		background: var(--color-bg-hover);
		color: var(--color-text-primary);
	}

	.icon-btn:disabled {
		opacity: 0.3;
		cursor: not-allowed;
	}

	.icon-btn.active {
		color: var(--color-gold);
		background: var(--color-gold-dim-bg);
	}

	/* Settings dropdown */
	.settings-wrapper {
		position: relative;
	}

	.settings-backdrop {
		position: fixed;
		inset: 0;
		z-index: 40;
	}

	.settings-dropdown {
		position: absolute;
		top: calc(100% + var(--space-2));
		right: 0;
		min-width: 180px;
		background: var(--color-bg-elevated);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-lg);
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
		z-index: 50;
		overflow: hidden;
	}

	.dropdown-header {
		padding: var(--space-3) var(--space-4);
		border-bottom: 1px solid var(--color-border);
	}

	.dropdown-title {
		font-family: var(--font-ui);
		font-size: var(--font-xs);
		font-weight: var(--font-semibold);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--color-text-muted);
	}

	.font-size-options {
		display: flex;
		padding: var(--space-2);
		gap: var(--space-1);
	}

	.font-size-btn {
		flex: 1;
		padding: var(--space-2) var(--space-3);
		border-radius: var(--radius-sm);
		background: transparent;
		color: var(--color-text-secondary);
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		font-weight: var(--font-medium);
		transition: all var(--transition-fast);
	}

	.font-size-btn:hover {
		background: var(--color-bg-hover);
		color: var(--color-text-primary);
	}

	.font-size-btn.active {
		background: var(--color-gold);
		color: var(--color-bg-base);
	}

	@media (max-width: 768px) {
		.header {
			padding: 0 var(--space-2);
		}

		.nav-buttons {
			margin-left: var(--space-1);
			padding-left: var(--space-1);
		}

		.nav-btn {
			padding: var(--space-1) var(--space-2);
		}
	}
</style>
