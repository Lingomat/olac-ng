<script lang="ts">
    import type { PageData } from './$types'
    export let data: PageData
    export const prerender = false

    const metadata = JSON.stringify(data.metadata, null, 2)

    const records = data.recordvals!
    console.log('data', data)
    let showMetadata: boolean = false
</script>

<div class="text-center p-1 text-lg font-bold mt-2 mb-1">
    OLAC item record
</div>

{#if records && records.length > 0}
    <div class="flex flex-col">
        {#each records as record}
            <div class="flex flex-row mb-1">
                <div class="font-medium w-1/4">{record.key}:</div>
                <div class="flex flex-col w-3/4">
                    {#each record.value as value}
                        {#if value.url}
                            <a
                                href={value.url}
                                class="font-medium text-blue-600 dark:text-blue-500 hover:underline"
                            >
                                {value.value}
                            </a>
                        {:else}
                            <div>{value.value}</div>
                        {/if}
                    {/each}
                </div>
            </div>
        {/each}
    </div>

    <button
        class="bg-blue-500 hover:bg-blue-700 text-white mt-2 mb-2 py-2 rounded-lg w-1/6 text-center"
        on:click={() => {
            showMetadata = !showMetadata
        }}
    >
        {showMetadata ? 'Hide raw' : 'Show raw'}
    </button>

    {#if showMetadata}
        <div class="text-sm whitespace-pre-wrap font-mono">
            {metadata}
        </div>
    {/if}
{/if}

<style>
    /* a {
        font-family: 'Segoe Condensed', sans-serif;
        font-weight: 700;
    } */
</style>
