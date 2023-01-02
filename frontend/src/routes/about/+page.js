import { error } from '@sveltejs/kit'

export const load = async () => {
    try {
        const copyleft = await import(`../../../copy/about-left.md`)
        const copyright = await import(`../../../copy/about-right.md`)
        return {
            leftcopy: copyleft.default,
            rightcopy: copyright.default,
        }
    } catch (e) {
        throw error(
            404,
            `Uh oh! Sorry, looks like that page doesn't exist`
        )
    }
}
