import { error } from '@sveltejs/kit'
import type { PageLoad } from './$types';

export const load: PageLoad  = async () => {
    try {
        const copy = await import(`../../../copy/documents.md`)
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

