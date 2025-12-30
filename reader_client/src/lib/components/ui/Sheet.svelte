<!--
  Sheet Component

  A sheet that slides in from the bottom or left.
  Supports swipe-to-dismiss gesture.
-->
<script lang="ts">
	import { onMount } from 'svelte';

	interface Props {
		open: boolean;
		position?: 'bottom' | 'left';
		onclose?: () => void;
		children: import('svelte').Snippet;
	}

	let { open = $bindable(), position = 'bottom', onclose, children }: Props = $props();

	// Helper to close the sheet
	function closeSheet() {
		open = false;
		onclose?.();
	}

	let sheetEl = $state<HTMLElement | undefined>(undefined);
	let startPos = 0;
	let currentPos = 0;
	let isDragging = false;

	function handleTouchStart(e: TouchEvent) {
		// Only start drag from the handle area
		const target = e.target as HTMLElement;
		if (!target.closest('.sheet-handle')) return;

		startPos = position === 'left' ? e.touches[0].clientX : e.touches[0].clientY;
		isDragging = true;
	}

	function handleTouchMove(e: TouchEvent) {
		if (!isDragging || !sheetEl) return;

		currentPos = position === 'left' ? e.touches[0].clientX : e.touches[0].clientY;
		const delta = currentPos - startPos;

		if (position === 'left') {
			// Only allow dragging left (negative delta)
			if (delta < 0) {
				sheetEl.style.transform = `translateX(${delta}px)`;
			}
		} else {
			// Only allow dragging down (positive delta)
			if (delta > 0) {
				sheetEl.style.transform = `translateY(${delta}px)`;
			}
		}
	}

	function handleTouchEnd() {
		if (!isDragging || !sheetEl) return;

		const delta = currentPos - startPos;
		isDragging = false;

		// If dragged more than 100px in dismiss direction, close
		const shouldClose = position === 'left' ? delta < -100 : delta > 100;
		if (shouldClose) {
			closeSheet();
		}

		// Reset transform
		sheetEl.style.transform = '';
	}

	function handleOverlayClick() {
		closeSheet();
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			closeSheet();
		}
	}

	// Prevent body scroll when sheet is open
	$effect(() => {
		if (typeof document !== 'undefined') {
			if (open) {
				document.body.style.overflow = 'hidden';
			} else {
				document.body.style.overflow = '';
			}
		}
	});
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
	<div class="sheet-container" class:position-left={position === 'left'}>
		<!-- Overlay -->
		<button
			class="sheet-overlay"
			onclick={handleOverlayClick}
			aria-label="Close"
			tabindex="-1"
		></button>

		<!-- Sheet -->
		<div
			class="sheet"
			class:sheet-left={position === 'left'}
			bind:this={sheetEl}
			ontouchstart={handleTouchStart}
			ontouchmove={handleTouchMove}
			ontouchend={handleTouchEnd}
			role="dialog"
			aria-modal="true"
		>
			{#if position === 'left'}
				<div class="sheet-content">
					{@render children()}
				</div>
				<div class="sheet-handle sheet-handle-vertical">
					<div class="sheet-handle-bar"></div>
				</div>
			{:else}
				<div class="sheet-handle">
					<div class="sheet-handle-bar"></div>
				</div>
				<div class="sheet-content">
					{@render children()}
				</div>
			{/if}
		</div>
	</div>
{/if}

<style>
	.sheet-container {
		position: fixed;
		inset: 0;
		z-index: 100;
		display: flex;
		flex-direction: column;
		justify-content: flex-end;
	}

	.sheet-container.position-left {
		flex-direction: row;
		justify-content: flex-start;
	}

	.sheet-overlay {
		position: absolute;
		inset: 0;
		background: rgba(0, 0, 0, 0.6);
		border: none;
		cursor: pointer;
		animation: fadeIn 200ms ease-out;
	}

	.sheet {
		position: relative;
		background: var(--color-bg-surface);
		border-radius: var(--radius-lg) var(--radius-lg) 0 0;
		max-height: 85dvh;
		display: flex;
		flex-direction: column;
		animation: slideUp 250ms ease-out;
		will-change: transform;
	}

	/* Left position styles */
	.sheet.sheet-left {
		flex-direction: row;
		border-radius: 0 var(--radius-lg) var(--radius-lg) 0;
		max-height: 100dvh;
		height: 100dvh;
		width: min(85vw, 400px);
		max-width: 400px;
		animation: slideInLeft 250ms ease-out;
	}

	.sheet-handle {
		padding: var(--space-3) var(--space-4);
		cursor: grab;
		display: flex;
		justify-content: center;
		flex-shrink: 0;
	}

	.sheet-handle:active {
		cursor: grabbing;
	}

	.sheet-handle-bar {
		width: 2.5rem;
		height: 0.25rem;
		background: var(--color-text-muted);
		border-radius: var(--radius-full);
	}

	/* Vertical handle for left sheet */
	.sheet-handle-vertical {
		padding: var(--space-4) var(--space-3);
		flex-direction: column;
		align-items: center;
		justify-content: center;
	}

	.sheet-handle-vertical .sheet-handle-bar {
		width: 0.25rem;
		height: 2.5rem;
	}

	.sheet-content {
		flex: 1;
		overflow-y: auto;
		overflow-x: hidden;
	}

	@keyframes fadeIn {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}

	@keyframes slideUp {
		from {
			transform: translateY(100%);
		}
		to {
			transform: translateY(0);
		}
	}

	@keyframes slideInLeft {
		from {
			transform: translateX(-100%);
		}
		to {
			transform: translateX(0);
		}
	}
</style>
