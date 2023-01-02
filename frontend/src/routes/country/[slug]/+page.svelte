<script lang="ts">
    import type { PageData } from "./$types"

    export let data: PageData
    export const prerender = true;
    const name = data.country
</script>

<div class="all-prose">
    <h2 class="text-center">
        OLAC resources for languages in {name}
    </h2>
</div>

{#if data.languages}
<div class="grid grid-cols-4 gap-1 font-medium">
    {#each data.languages as language}
        <div>
            <a href="/language/{language.code}">
                {language.name}&nbsp;({language.count})
            </a>
        </div>
    {/each}
</div>
{/if}