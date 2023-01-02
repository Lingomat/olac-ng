<script>
    import Head from '$lib/components/head.svelte'

    export let data
    let {
        html,
        meta: { date, title, readingTime },
    } = data
</script>

<Head title={`Post | ${title}`} />

<article class="flex flex-col flex-grow">
    <h2 class="font-bold mb-1 text-2xl">{title}</h2>
    <p>
        {new Date(date).toDateString()}
    </p>
    <article class="all-prose">
        {@html html}
    </article>
</article>
