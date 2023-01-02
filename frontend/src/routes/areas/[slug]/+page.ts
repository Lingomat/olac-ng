import { error } from '@sveltejs/kit'
import type { PageLoad } from './$types';

export const load: PageLoad = ({ params, data }) => {
    //console.log('shared page data', data)
    const areas = ['americas', 'africa', 'asia', 'europe', 'pacific']

    if (areas.findIndex(x => x === params.slug) === -1) {
        throw error(404, 'Not Found')
    }
    return {
        countries: data.countries,
        slug: params.slug
    }
}
export const prerender = true;

