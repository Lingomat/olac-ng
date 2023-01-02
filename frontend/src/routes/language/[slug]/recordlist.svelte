<script lang="ts">
    import type { ParsedRecord } from '$lib/parser'
    export let records: ParsedRecord[]
    export let category: string
    //export let language: any

    const pluralise = (titlestr: string): string => {
        return titlestr + 
            ((records.length > 1) ? 's' : '')
    }

</script>

{#if records && records.length > 0}
    <div class="text-base font-bold mt-4 mb-2">
        {records.length.toLocaleString('en-US')} {pluralise(category)}:
    </div>
    <ol class="list-decimal font-normal">
        {#each records as record}
            <li>
                <span class="font-medium">{record.title}.</span>
                {#if record.roles && record.roles.length > 0}
                    {record.roles.join('; ')}.
                {/if}
                {#if record.date}
                    {record.date}.
                {/if}
                {#if record.organisation}
                    <span class="italic">{record.organisation}.</span>
                {/if}
                <a href="/item/{encodeURIComponent(record.oai)}" class="font-medium text-blue-600 dark:text-blue-500 hover:underline">
                    {record.oai}
                </a>
            </li>
        {/each}
    </ol>
{/if}
