import { MongoClient } from 'mongodb'
import type { PageServerLoad } from './$types';
import { MONGO_URL } from '$env/static/private'
import type { OLACRecord } from '$lib/parser';
import { toObject } from '$lib/util';
import { itemParser } from './itemparser'
import type { PossibleLink } from './itemparser';
import { error } from '@sveltejs/kit';

// Create a new MongoClient
const client = new MongoClient(MONGO_URL);

export const prerender = false;

interface OLACItem {
    status: number
    metadata?: object
    recordvals?: {key: string, value: PossibleLink[]}[]
}

export const load: PageServerLoad  = async ({params}): Promise<OLACItem> => {
    console.time("pageload");
    const database = client.db("olac");
    const record = toObject(await database.collection("records").findOne({identifier: params.slug})) as OLACRecord 
    if (record == null) {
        console.timeEnd("pageload");
        throw error(404, 'Item not found');
    }
    const archive = await database.collection("archives").findOne({identifier: record.identifier})
    const recordvals: {key: string, value: PossibleLink[]}[] = itemParser(record)

    console.timeEnd("pageload");
    if (record == null) return {status: 404}
    return {
        status: 200,
        metadata: record['metadata'],
        recordvals
    }

}