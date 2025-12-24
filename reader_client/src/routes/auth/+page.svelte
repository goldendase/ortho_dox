<!--
  Authentication Page

  Simple form to enter the parish secret.
  Redirects to home/last position after successful entry.
-->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { auth, reader, positionToPath } from '$lib/stores';

	let secret = $state('');
	let error = $state<string | null>(null);

	function handleSubmit(e: Event) {
		e.preventDefault();

		if (!secret.trim()) {
			error = 'Please enter the access code';
			return;
		}

		// Save the secret
		auth.setSecret(secret.trim());

		// Redirect to last reading position or home
		const destination = reader.position ? positionToPath(reader.position) : '/';
		goto(destination, { replaceState: true });
	}
</script>

<div class="auth-page">
	<div class="auth-card">
		<h1 class="auth-title">Holy Mother of God</h1>
		<p class="auth-subtitle text-secondary">
			Glory to God. Enter the parish access code to continue.
		</p>

		<form class="auth-form" onsubmit={handleSubmit}>
			<div class="form-group">
				<input
					type="password"
					class="auth-input"
					bind:value={secret}
					placeholder="Access code"
					autocomplete="off"
					autocapitalize="off"
				/>
			</div>

			{#if error}
				<p class="auth-error">{error}</p>
			{/if}

			<button type="submit" class="auth-button">
				Continue
			</button>
		</form>
	</div>
</div>

<style>
	.auth-page {
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 100%;
		padding: var(--space-8);
	}

	.auth-card {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-4);
		width: 100%;
		max-width: 320px;
		text-align: center;
	}

	.auth-title {
		font-size: var(--font-2xl);
		font-weight: var(--font-medium);
		color: var(--color-gold);
		letter-spacing: var(--tracking-tight);
	}

	.auth-subtitle {
		font-size: var(--font-base);
		margin-bottom: var(--space-2);
	}

	.auth-form {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
		width: 100%;
	}

	.form-group {
		width: 100%;
	}

	.auth-input {
		width: 100%;
		padding: var(--space-3) var(--space-4);
		font-family: var(--font-ui);
		font-size: var(--font-base);
		color: var(--color-text-primary);
		background: var(--color-bg-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		text-align: center;
		letter-spacing: 0.1em;
	}

	.auth-input:focus {
		outline: none;
		border-color: var(--color-gold);
	}

	.auth-input::placeholder {
		color: var(--color-text-muted);
		letter-spacing: normal;
	}

	.auth-error {
		font-family: var(--font-ui);
		font-size: var(--font-sm);
		color: var(--color-accent-red);
	}

	.auth-button {
		padding: var(--space-3) var(--space-6);
		font-family: var(--font-ui);
		font-size: var(--font-base);
		font-weight: var(--font-medium);
		color: var(--color-bg-base);
		background: var(--color-gold);
		border-radius: var(--radius-md);
		transition: background var(--transition-fast);
	}

	.auth-button:hover {
		background: var(--color-gold-bright);
	}
</style>
