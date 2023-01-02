import type { OLACRecord } from '$lib/parser';

export interface PossibleLink {
    value: string
    url?: string
}

// : at the start of values means this value can be pluralised with +s
const dckeymap: { [key: string]: string } = {
    'dc:contributor': ':Contributor',
    'dc:coverage': 'Coverage',
    'dc:creator': 'Creator',
    'dc:date': 'Date',
    'dc:description': 'Description',
    'dc:format': ':Format',
    'dc:identifier': ':Identifier',
    'dc:language': ':Language',
    'dc:publisher': ':Publisher',
    'dc:relation': ':Relation',
    'dc:rights': 'Rights',
    'dc:source': ':Source',
    'dc:subject': ':Subject',
    'dc:title': ':Title',
    'dc:type': ':Type',
    'dcterms:abstract': 'Abstract',
    'dcterms:accessRights': 'Access Rights',
    'dcterms:accrualMethod': 'Accrual Method',
    'dcterms:accrualPeriodicity': 'Accrual Periodicity',
    'dcterms:accrualPolicy': 'Accrual Policy',
    'dcterms:alternative': ':Alternative',
    'dcterms:audience': 'Audience',
    'dcterms:available': 'Available',
    'dcterms:bibliographicCitation': ':Bibliographic Citation',
    'dcterms:conformsTo': 'Conforms To',
    'dcterms:contributor': ':Contributor',
    'dcterms:coverage': 'Coverage',
    'dcterms:created': 'Created',
    'dcterms:creator': ':Creator',
    'dcterms:date': 'Date',
    'dcterms:dateAccepted': 'Date Accepted',
    'dcterms:dateAvailable': 'Date Available',
    'dcterms:dateCopyrighted': 'Date Copyrighted',
    'dcterms:dateSubmitted': 'Date Submitted',
    'dcterms:description': ':Description',
    'dcterms:spatial': 'Spatial Coverage',
    'dcterms:extent': 'Extent',
    'dcterms:tableOfContents': 'Table of Contents',
    'dcterms:isRequiredBy': 'Is Required By',
    'dcterms:isPartOf': 'Is Part Of',
    'dcterms:isFormatOf': 'Is Format Of'
}

const olactypesmap: { [key: string]: string } = {
    "language_description": "Language Description",
    "lexicon": "Lexicon",
    "primary_text": "Primary Text"
}

const isHyperlink = (value: string): boolean => {
    let valstr = value.trim()
    return (valstr.startsWith('http://') || valstr.startsWith('https://'))
}

const isOAI = (value: string): boolean => {
    let valstr = value.trim()
    return (valstr.startsWith('oai:'))
}

const isDOI = (value: string): boolean => {
    let valstr = value.trim()
    return (valstr.startsWith('doi:'))
}

const toPossibleLink = (value: string): PossibleLink => {
    if (isHyperlink(value)) {
        return {
            url: value,
            value
        }
    } else if (isOAI(value)) {
        return {
            url: '/item/' + encodeURIComponent(value),
            value
        }
    } else if (isDOI(value)) {
        return {
            url: `https://doi.org/` + encodeURIComponent(value.slice(4)),
            value
        }
    } else {
        return {
            value
        }
    }
}


const xmlValParser = (value: unknown): string[] => {
    if (value == null) return []
    if (typeof value == 'string') {
        return [value]
    }
    if (Array.isArray(value)) {
        const vals: unknown[] = []
        for (const val of value) {
            vals.push(...xmlValParser(val))
        }
        return vals as string[]
    }
    if (typeof value == 'object') {
        //const vals: {key: string, val: string}[] = []
        const valtype = ('@http://www.w3.org/2001/XMLSchema-instance:type' in value) ?
            value['@http://www.w3.org/2001/XMLSchema-instance:type'] as string : null
        const olaccode = ('@olac:code' in value) ?
            value['@olac:code'] as string : null
        console.log(valtype, olaccode)
        if (olaccode && '#text' in value) {
            if (valtype == 'olac:language') {
                // we could do a lookup here
                return [olaccode]
            } else if (valtype == 'olac:linguistic-type') {
                return [mapKeyString(olactypesmap, olaccode)]
            } else if (valtype == 'olac:role') {
                return [(value['#text'] as string) + ' (' + olaccode + ')'] as string[]
            } else {
                return [olaccode]
            }
        } else if ('#text' in value) {
            if (valtype == 'dcterms:W3CDTF') {
                const datenum = Date.parse(value['#text'] as string)
                if (!isNaN(datenum)) {
                    return [new Date(datenum).toISOString().substring(0, 10)]
                } else {
                    return [value['#text']] as string[]
                }
            }
            return [value['#text']] as string[]
        }
    }
    return []
}


const capitalize = (word: string) => {
    const lower = word.toLowerCase();
    return word.charAt(0).toUpperCase() + lower.slice(1);
}

const mapKeyString = (keymap: { [key: string]: string }, key: string, plural: boolean = false): string => {
    if (key in keymap) {
        const keyval = keymap[key]
        if (keyval.startsWith(':') && plural) {
            return keyval.substring(1) + 's'
        } else {
            return keyval.replace(':','')
        }
    }
    if (key.startsWith('dc:')) return capitalize(key.substring(3))
    if (key.startsWith('dcterms:')) return capitalize(key.substring(8))
    return key
}

export const itemParser = (record: OLACRecord): { key: string, value: PossibleLink[] }[] => {
    const keyvals: { key: string, value: PossibleLink[] }[] = []
    if (!Object.hasOwn(record, "metadata")) return []
    for (const [key, value] of Object.entries(record['metadata'])) {
        const xmlval = (xmlValParser(value) as string[]).map(x => toPossibleLink(x))
        const plural = xmlval.length > 1

        if (xmlval.length > 0) {
            keyvals.push({
                key: mapKeyString(dckeymap, key, plural),
                value: xmlval
            })
        }
    }
    return keyvals
}
