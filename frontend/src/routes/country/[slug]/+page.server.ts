import { MongoClient } from 'mongodb'
import type { PageServerLoad } from './$types';
import { MONGO_URL } from '$env/static/private'
import { error } from '@sveltejs/kit';

// Create a new MongoClient
const client = new MongoClient(MONGO_URL);
export const prerender = true;

export const load: PageServerLoad  = async ({fetch, params}) => {
    console.time("pageload");
    const database = client.db("olac");
    const country = await database.collection("countries").findOne({code: params.slug})
    if (country == null) {
        console.timeEnd("pageload");
        throw error(404, 'Country not found');
    }
    const languages = await database.collection("languages").find({country: params.slug}).toArray()
    const recordscol = database.collection("records")
    const languagelist: {code: string, name: string, count: number}[] = []
    for (const language of languages) {
        //if (language.code === 'eng') continue

        const recordcount = await recordscol.countDocuments({languages: language.code})
        if (recordcount === 0) continue
        languagelist.push({
            code: language.code,
            name: language.name,
            count: recordcount
        })
    }
    console.timeEnd("pageload");
    return {
        country: country.name,
        languages: languagelist
    } 
}
