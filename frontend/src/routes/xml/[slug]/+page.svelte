<script lang="ts">
    import type { PageData } from './$types'
    import Highlight from "svelte-highlight";
    import xml from "svelte-highlight/languages/xml";
    import onedark from "svelte-highlight/styles/onedark";
    export let data: PageData
    export const prerender = false
    const code = data.xml
</script>

<svelte:head>
  {@html onedark}
</svelte:head>

<div class="text-center p-1 text-lg font-bold mt-2 mb-1">
    XML
</div>

<Highlight class="text-xs whitespace-pre-wrap" language={xml} {code} />
