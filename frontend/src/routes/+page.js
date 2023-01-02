import { error } from '@sveltejs/kit'

export const load = async () => {
    try {
        const copyleft = await import('../../copy/home-left.md')
        const copyright = await import('../../copy/home-right.md')
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
