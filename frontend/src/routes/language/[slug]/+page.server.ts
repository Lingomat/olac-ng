import { MongoClient } from 'mongodb'
import type { PageServerLoad } from './$types';
import { MONGO_URL } from '$env/static/private'
import { OLACParser } from '$lib/parser';
import type { ParsedRecord, OLACRecord } from '$lib/parser';
import { toObject } from '$lib/util';
import { error } from '@sveltejs/kit';

interface OLACLanguage {
    _id: string
    code: string
    name: string
    country: string
    area: string
    altNames: string[]
    dialects: string[]
}

interface ParsedOutput {
    status: number
    language?: OLACLanguage
    lexicons?: ParsedRecord[]
    primary_texts?: ParsedRecord[]
    language_descriptions?: ParsedRecord[]
    others?: ParsedRecord[]
}

// Create a new MongoClient
const client = new MongoClient(MONGO_URL);
export const prerender = true;


export const load: PageServerLoad  = async ({fetch, params}): Promise<ParsedOutput> => {
    console.time("pageload");
    const database = client.db("olac");
    const language = toObject(await database.collection("languages").findOne({code: params.slug})) as OLACLanguage
    if (language == null) {
        console.timeEnd("pageload");
        throw error(404, 'Language not found');
    } 
    const recordscol = database.collection("records")
    const records = await recordscol.find({languages: params.slug}).toArray()
    const lexicons: ParsedRecord[] = []
    const primary_texts: ParsedRecord[] = []
    const language_descriptions: ParsedRecord[] = []
    const others: ParsedRecord[] = []
    for (const record of records) {
        //console.log('record', record)
        const cleanrecord = toObject(record)
        if (cleanrecord == null) {continue}
        const parsedrecord = OLACParser(cleanrecord as OLACRecord)
        //console.log('parsedrecord', parsedrecord)
        if (parsedrecord == null) {continue}
        switch(parsedrecord.linguistic_type) {
            case "lexicon":
                lexicons.push(parsedrecord)
                break
            case "primary_text":
                primary_texts.push(parsedrecord)
                break
            case "language_description":
                language_descriptions.push(parsedrecord)
                break
            case "other":
                others.push(parsedrecord)
        }       
    }
    console.timeEnd("pageload");
    return {
        status: 200,
        language,
        lexicons,
        primary_texts,
        language_descriptions,
        others       
    } 
}
