import { error } from '@sveltejs/kit'
import type { PageLoad } from './$types';

export const load: PageLoad  = async ({params}) => {
    console.log('params', params)
    try {
        const copy = await import(`../../../../copy/${params.slug}.md`)
        return {
            copy: copy.default,
        }
    } catch (e) {
        throw error(
            404,
            `Uh oh! Sorry, looks like that page doesn't exist`
        )
    }
}

