<script lang="ts">
    import { page } from '$app/stores';
    console.log(page);
    export let data
    export let form
    console.log(data, form)
</script>

<div class="text-center p-1 text-lg font-bold mt-2 mb-1">
    Oops, something went wrong!
</div>


{#if $page && $page.error}
    <div class="font-medium">
        {$page.error.message}
    </div>
{/if}
