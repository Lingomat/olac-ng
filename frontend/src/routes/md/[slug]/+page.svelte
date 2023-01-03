<script lang="ts">
    import Head from '$lib/components/head.svelte'
    export let data

</script>

<Head title={`Documents`} />

<div class="all-prose">
    <svelte:component this={data.copy} />

</div>
