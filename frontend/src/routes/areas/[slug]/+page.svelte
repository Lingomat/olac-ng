<script lang="ts">
    import type { PageData } from './$types'

    export let data: PageData
    export const prerender = true
    //console.log('data', data)
    const name =
        data.slug.charAt(0).toUpperCase() + data.slug.slice(1)
</script>

<div class="all-prose">
    <h2 class="text-center">
        OLAC Resources for Countries in {name}
    </h2>
</div>

{#if data.countries}
    <div class="grid grid-cols-4 gap-1 font-medium">
        {#each data.countries as country}
            <div>
                <a href="/country/{country.code}">
                    {country.name}&nbsp;({country.count})
                </a>
            </div>
        {/each}
    </div>
{/if}
