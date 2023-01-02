import type { WithId, Document } from 'mongodb'

export const toObject = (document: WithId<Document> | null): object | null => {
    if (document == null) return null
    const clone = {...document} as any
    clone._id = document._id.toString();
    return clone
}