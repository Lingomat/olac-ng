<script>
    import Head from '$lib/components/head.svelte'
    export let data
    let { leftcopy, rightcopy } = data
</script>

<Head title={`About`} />

<div class="all-prose flex">
    <div class="w-1/2 p-2"><svelte:component this={leftcopy} /></div>
    <div class="w-1/2 p-2"><svelte:component this={rightcopy} /></div>
</div>
