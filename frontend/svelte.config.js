//import adapter from '@sveltejs/adapter-vercel'
import adapter from '@sveltejs/adapter-node';
import { vitePreprocess } from '@sveltejs/kit/vite';
import { mdsvex } from 'mdsvex'
import { resolve } from 'path'
import mdsvexConfig from './mdsvex.config.js'

/** @type {import('@sveltejs/kit').Config} */
const config = {
    extensions: ['.svelte', ...mdsvexConfig.extensions],

    kit: {
        adapter: adapter(),
        alias: {
            $lib: resolve('./src/lib')
        },
        prerender: {
            entries: [
                '/areas/asia',
                '/areas/americas',
                '/areas/europe',
                '/areas/africa',
                '/areas/pacific'
            ]
        }
    },
    preprocess: [
        vitePreprocess({postcss: true}),
        mdsvex({ extensions: ['.svelte.md', '.md', '.svx'] })
    ]
}

export default config
