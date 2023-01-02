import { MongoClient } from 'mongodb'
import type { PageServerLoad } from './$types';
import { MONGO_URL } from '$env/static/private'

// Create a new MongoClient
const client = new MongoClient(MONGO_URL);
export const prerender = true;


export const load: PageServerLoad  = async ({fetch, params}) => {
    const database = client.db("olac");
    const records = database.collection("records")
    const area = await database.collection("areas").findOne({area: params.slug}) // an area, with a countries property
    if (!area) return {status: 404}
    const countries = await database.collection("countries").find({code: {$in: area.countries}}).toArray()
    const countrylist: {code: string, name: string, count: number}[] = []
    for (const country of countries) {
        const recordcount = await records.countDocuments({countries: country.code})
        if (recordcount === 0) continue
        countrylist.push({
            code: country.code,
            name: country.name,
            count: recordcount
        })
    }
    return {countries: countrylist} 
}
