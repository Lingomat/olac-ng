<script>
    import { onMount } from 'svelte'

    let posts = []

    onMount(async () => {
        const res = await fetch(`/posts.json`)
        if (res.ok) {
            posts = (await res.json()).posts
            console.log('posts', posts)
        }
    })
</script>

<ul class="prose">
    {#each posts as post}
        {#if post.published}
            <a data-sveltekit:prefetch href={`/posts/${post.slug}`}>
                <li class="font-normal">
                    <span class="text-black">{post.title}</span>
                    <!-- <div class="text-sm mb-4 uppercase">
          <time>{new Date(post.date).toDateString()}</time>
        </div> -->
                </li>
            </a>
        {/if}
    {/each}
</ul>
