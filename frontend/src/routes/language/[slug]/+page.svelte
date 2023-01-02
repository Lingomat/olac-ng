<script lang="ts">
    import type { PageData } from './$types'
    import Recordlist from './recordlist.svelte'
    import type { ParsedRecord } from '$lib/parser'
    import Head from '$lib/components/head.svelte'
    export let data: PageData
    export const prerender = true

    const catlist: { name: string; records: ParsedRecord[] }[] = []
    const searchterms: string[] = ['dialect', 'vernacular'] // taken from original PHP logic
    if (data.lexicons && data.lexicons.length > 0)
        catlist.push({ name: 'lexicon', records: data.lexicons })
    searchterms.push(
        ...[
            'lexicon',
            'dictionary',
            'vocabulary',
            'wordlist',
            'phrase book',
        ]
    )
    if (data.primary_texts && data.primary_texts.length > 0)
        catlist.push({
            name: 'primary text',
            records: data.primary_texts,
        })
    searchterms.push(
        ...[
            'discourse',
            'stories',
            'conversation',
            'dialogue',
            'documentation',
        ]
    )
    if (
        data.language_descriptions &&
        data.language_descriptions.length > 0
    )
        catlist.push({
            name: 'language description',
            records: data.language_descriptions,
        })
    searchterms.push(
        ...[
            'grammar',
            'syntax',
            'morphology',
            'phonology',
            'orthography',
        ]
    )
    if (data.others && data.others.length > 0)
        catlist.push({
            name: 'other language resource',
            records: data.others,
        })
    const language = data.language!

    let description =
        'OLAC language resources for ' + language['name']
    if (language.altNames && language.altNames.length > 0)
        description +=
            ' also known as ' + language.altNames.join(', ') + '. '
    if (language.dialects && language.dialects.length > 0)
        description +=
            'Including dialects: ' +
            language.dialects.join(', ') +
            '. '
    description += 'Resources include ' + searchterms.join(', ') + '.'
</script>

<Head title="OLAC resources for {language['name']}" {description} />

<div class="all-prose">
    {#if data}
    <h2 class="text-center">
        OLAC resources for {language['name']}
    </h2>
    {#if language.altNames && language.altNames.length > 0}
        <div class="">
            <span class="font-medium">Language also known as:</span>
            <span class="italic">{language.altNames.join(', ')}.</span
            >
        </div>
    {/if}
    {#if language.dialects && language.dialects.length > 0}
        <div class="">
            <span class="font-medium">Including dialects:</span>
            <span class="italic">{language.dialects.join(', ')}.</span
            >
        </div>
    {/if}

    {#each catlist as thiscat}
        <Recordlist
            records={thiscat.records}
            category={thiscat.name}
        />
    {/each}

    <div class="mt-2">
        <span class="font-medium">Other search terms:</span>
        <span class="italic">{searchterms.join(', ')}.</span>
    </div>
{/if}

</div>
