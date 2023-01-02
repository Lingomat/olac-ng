<script>
  import Head from '$lib/components/head.svelte'
  import PostCard from '$lib/components/post-card.svelte'

  export let data
  let { posts } = data
</script>

<Head title={'OLAC News'} />

## News

{#each posts as post} {#if post.published} <PostCard {post} /> {/if}
{/each}
