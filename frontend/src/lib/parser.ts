export interface OLACRecord {
    _id: string
    identifier: string
    datestamp: Date
    metadata: any
    id: string
    date?: Date
    page?: number
    languages: string[]
    countries: string[]
}

export interface OLACArchive {
    _id: string
    baseURL: string
    customSchemas: {namespace: string, schema: string}[]
    identify: any
    lastModified: Date
    type: 'static' | 'dynamic'
}

export interface ParsedRecord {
    title: string
    organisation: string | null
    roles: string[]
    date: string | null
    oai: string
    linguistic_type: 'lexicon' | 'primary_text' | 'language_description' | 'other'
}



const parseContributors = (contributors: any[] | any): string[] => {
    const contstrings: string[] = []
    if (Array.isArray(contributors)) {
        for (const contributor of contributors) {
            contstrings.push(...parseContributors(contributor) )
        }
    } else {
        if (typeof contributors == 'string') return [contributors]
        if (contributors !== null && typeof contributors == 'object' && '@olac:code' in contributors) {
            if (!Object.hasOwn(contributors, '#text')) {
                contstrings.push(contributors['@olac:code'])
            } else {
                contstrings.push(contributors['#text'] + ' (' + contributors['@olac:code'] + ')')
            }
            
        }
    }
    return contstrings
}

const parseLinguisticType = (types: any[] | any): 'lexicon' | 'primary_text' | 'language_description' | 'other' => {
    if (Array.isArray(types)) {
        for (const type of types) {
            if (typeof type == 'object' && '@olac:code' in type) {
                return type['@olac:code']
            }
        }
    } else {
        if (typeof types == 'object' && '@olac:code' in types) {
            return types['@olac:code']
        }
    }
    return 'other'
}

const cleanText = (text: string): string => {
    let newtext = text.trim()
    newtext = newtext.replace(/(\r\n|\n|\r)/gm, "");
    return newtext
}

const parseDate = (text: any): string | null => {
    const stripyear = (text: string): string | null => {
        const datenum = Date.parse(text)
        if (isNaN(datenum)) return null
        const realdate = new Date(datenum)
        return realdate.getFullYear().toString()
    }
    if (text == null) return null
    if (typeof text == 'string') {
        return stripyear(text)
    } else if (typeof text == 'object' && Object.hasOwn(text, '#text')) {
        return stripyear(text['#text'])
    }
    return null
}

export const OLACParser = (record: OLACRecord): ParsedRecord | null => {
    if (!Object.hasOwn(record, "metadata")) return null
    let linguistic_type: 'lexicon' | 'primary_text' | 'language_description' | 'other' = 'other' // default
    const roles: string[] = []
    let title: string | null = null
    let date: string | null = null
    let organisation: string | null = null
    for (const [key, value] of Object.entries(record['metadata'])) {
        const anyval = value as any 
        if (anyval == null) continue // believe it or not, null is an object
        if (key === "dc:title") {
            if (typeof anyval == 'string') {
                title = cleanText(anyval) as string
            } else if (typeof anyval == 'object' && Object.hasOwn(anyval, '#text')) {
                title = cleanText(anyval['#text']) as string
            } else if (Array.isArray(anyval)) {
                if (anyval.length > 0 && typeof anyval[0] == 'string') {
                    title = cleanText(anyval[0]) as string
                } else if (anyval.length > 0 && typeof anyval[0] == 'object' && Object.hasOwn(anyval[0], '#text')) {
                    title = cleanText(anyval[0]['#text']) as string
                }
            }
        } else if (key === "dc:date") {
            if (anyval == null || date !== null) continue
            const parsedate = parseDate(anyval)
            if (parsedate != null) {
                date = parsedate
            }
        } else if (key === "dcterms:created") {
            if (anyval == null || date !== null) continue
            const parsedate = parseDate(anyval)
            if (parsedate != null) {
                date = parsedate
            }
        } else if (key === "dc:contributor") {
            roles.push(...parseContributors(value))
        } else if (key === "dc:type") {
            linguistic_type = parseLinguisticType(value)
        } else if (key === "dc:publisher") {
            if (typeof anyval == 'string') {
                organisation = cleanText(anyval) as string
            }

        }
       
    }

    if (title == null) {
        console.log('error: no title found')
        return null
    }

    return {
        title,
        linguistic_type: linguistic_type,
        organisation,
        date,
        oai: record.identifier,
        roles
    }
}
