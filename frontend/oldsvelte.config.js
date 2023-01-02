//import adapter from '@sveltejs/adapter-vercel'
import adapter from '@sveltejs/adapter-node';
import { mdsvex } from 'mdsvex'
import { resolve } from 'path'
import preprocess from 'svelte-preprocess'
import mdsvexConfig from './mdsvex.config.js'

/** @type {import('@sveltejs/kit').Config} */
const config = {
    extensions: ['.svelte', ...mdsvexConfig.extensions],

    kit: {
        adapter: adapter(),
        alias: {
            $lib: resolve('./src/lib'),
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
    preprocess: [preprocess({postcss: true}), mdsvex({ extensions: ['.svelte.md', '.md', '.svx'] })],
    // preprocess: [
    //     mdsvex(mdsvexConfig),
    //     [
    //         preprocess({
    //             postcss: true,
    //         }),
    //     ],
    // ],
}

export default config
