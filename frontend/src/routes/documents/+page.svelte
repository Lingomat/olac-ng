<script lang="ts">
    import Head from '$lib/components/head.svelte'
    export let data
</script>

<Head title={`Documents`} />

<div class="all-prose mt-2">
    <svelte:component this={data.copy} />
</div>
