<script lang="ts">
    import Head from '$lib/components/head.svelte'
    export let data
    let { leftcopy, rightcopy } = data
</script>

<Head
    title="OLAC Home"
    description="OLAC: Open Language Archives Community"
/>

<div class="all-prose flex">
    <div class="w-1/2 p-2"><svelte:component this={leftcopy} /></div>
    <div class="w-1/2 p-2"><svelte:component this={rightcopy} /></div>
</div>
