import type { PageServerLoad } from './$types';
import fs from 'fs/promises'
import { MongoClient } from 'mongodb'
import { MONGO_URL } from '$env/static/private'
import type { OLACArchive, OLACRecord } from '$lib/parser';
import { toObject } from '$lib/util';
import * as path from 'path';
import { error } from '@sveltejs/kit';
import { homedir } from 'os'

// Create a new MongoClient
const client = new MongoClient(MONGO_URL);

export const load: PageServerLoad = async ({params}) => {
    const database = client.db("olac");
    const record = toObject(await database.collection("records").findOne({identifier: params.slug})) as OLACRecord
    if (record == null) {
        throw error(404, 'No record found')
    } 
    const archive = toObject(await database.collection("archives").findOne({id: record.id})) as OLACArchive
    let xmlfilepath: string = ''
    if (archive.type === 'static') {
        const filename = archive.baseURL.split('/').pop()
        path.join(homedir(), 'olac-ng/backend/filestore', record.id, filename+'.xml')
    } else if (archive.type === 'dynamic') {
        if (record.page == null) {
            throw error(500, 'No page number for dynamic record')
        }
        xmlfilepath = path.join(homedir(), 'olac-ng/backend/filestore', record.id, 'listrecords' + record.page.toString() + '.xml')
    }
    console.log('xml filepath', xmlfilepath)
    try {
        const xmldata = await fs.readFile(xmlfilepath, { encoding: 'utf8' });
        return {
            xml: xmldata
        }
    } catch (e) {
        console.log('error',e)
        throw error(500, 'Could not read XML file')
    }
}
