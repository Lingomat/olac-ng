<script>
    import Fa from 'svelte-fa'
    import { faSearch } from '@fortawesome/free-solid-svg-icons'
    import { page } from '$app/stores'
    const navpages = [
        { n: 'Home', p: '/' },
        { n: 'Documents', p: '/documents' },
        { n: 'About', p: '/about' },
        { n: 'Archives', p: '/archives' },
        { n: 'News', p: '/posts' },
        { n: 'Organization', p: '/organization' },
        { n: 'Tools', p: '/tools' },
        { n: 'Services', p: '/services' },
    ]
</script>

<div class="flex flex-wrapfont-sans bg-blue-900">
    <div class="max-w-screen-lg m-auto flex flex-grow">
        <div
            class="w-24 relative ml-2"
            style="background-image: url('/images/nolac.webp');background-size: contain;background-position:center;background-repeat: no-repeat;filter: drop-shadow(0px 0px 4px #3b82f6);"
        >
            <div class="text-white tcenter text-3xl font-bold">
                OLAC
            </div>
        </div>
        <div class="flex text-white flex-auto justify-center">
            <div class="flex flex-col w-2/3 max-w-md">
                <div class="text-center p-1 text-lg font-bold">
                    Open Language Archives Community
                </div>
                <div class="grid grid-cols-4 gap-2 mb-2">
                    {#each navpages as thispage, i}
                        <a href={thispage.p}
                            ><div
                                class="rounded-lg text-center text-ellipsis overflow-hidden {$page
                                    .url.pathname === thispage.p
                                    ? 'bg-blue-400 text-black font-bold'
                                    : 'bg-blue-700'}"
                            >
                                {thispage.n}
                            </div></a
                        >
                    {/each}
                </div>
            </div>
        </div>
        <div class="text-white w-36 flex flex-col justify-end p-1">
            <div class="flex items-center mb-1">
                <Fa icon={faSearch} class="text-lg mr-2" />
                <input
                    type="text"
                    class="bg-blue-500 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-1"
                />
            </div>
        </div>
    </div>
</div>

<style>
    .tcenter {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        filter: drop-shadow(-1px -1px 2px #000000);
    }
</style>
