import adapter from '@sveltejs/adapter-node';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	preprocess: vitePreprocess(),
	kit: {
		adapter: adapter({
			// Use PORT env var from Railway
			envPrefix: ''
		}),
		alias: {
			$styles: 'src/styles'
		}
	}
};

export default config;
