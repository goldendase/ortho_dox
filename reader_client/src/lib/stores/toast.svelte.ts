/**
 * Toast Notification Store
 *
 * Simple toast system for user feedback:
 * - Errors (auth failures, API errors)
 * - Warnings (context limit reached)
 * - Info (general feedback)
 */

export type ToastType = 'error' | 'warning' | 'info';

export interface Toast {
	id: string;
	type: ToastType;
	message: string;
	duration: number;
}

const DEFAULT_DURATION = 4000;

class ToastStore {
	toasts = $state<Toast[]>([]);

	/**
	 * Show a toast notification
	 */
	show(message: string, type: ToastType = 'info', duration = DEFAULT_DURATION): void {
		const id = crypto.randomUUID();
		const toast: Toast = { id, type, message, duration };

		this.toasts = [...this.toasts, toast];

		// Auto-remove after duration
		setTimeout(() => {
			this.dismiss(id);
		}, duration);
	}

	/**
	 * Show an error toast
	 */
	error(message: string, duration = DEFAULT_DURATION): void {
		this.show(message, 'error', duration);
	}

	/**
	 * Show a warning toast
	 */
	warning(message: string, duration = DEFAULT_DURATION): void {
		this.show(message, 'warning', duration);
	}

	/**
	 * Show an info toast
	 */
	info(message: string, duration = DEFAULT_DURATION): void {
		this.show(message, 'info', duration);
	}

	/**
	 * Dismiss a specific toast
	 */
	dismiss(id: string): void {
		this.toasts = this.toasts.filter((t) => t.id !== id);
	}

	/**
	 * Clear all toasts
	 */
	clear(): void {
		this.toasts = [];
	}
}

export const toast = new ToastStore();
