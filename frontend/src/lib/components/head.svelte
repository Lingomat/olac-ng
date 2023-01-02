<script>
    import { authorName, website } from '$lib/site-config'
    import { page } from '$app/stores'
    export let title = 'OLAC'
    export let description = 'OLAC: Open Language Archives Community'
    export let image = '/nolac.webp'
    export let url = $page.url.pathname
</script>

<svelte:head>
    <link rel="canonical" href={url} />
    <!-- Meta Tags Generated via https://heymeta.com -->

    <!-- HTML Meta Tags -->
    <title>{title}</title>
    <meta name="description" content={description} />
    <meta name="author" content={authorName} />

    <!-- Google / Search Engine Tags -->
    <meta itemprop="name" content={title} />
    <meta itemprop="description" content={description} />
    <meta itemprop="image" content={image} />

    <!-- Facebook Meta Tags -->
    <meta property="og:url" content={url} />
    <meta property="og:type" content="website" />
    <meta property="og:title" content={title} />
    <meta property="og:description" content={description} />
    <meta property="og:image" content={image} />

    <!-- Twitter Meta Tags -->
    <meta name="twitter:card" content="summary_large_image" />
    <meta property="twitter:domain" content={website} />
    <meta property="twitter:url" content={url} />
    <meta name="twitter:title" content={title} />
    <meta name="twitter:description" content={description} />
    <meta name="twitter:image" content={image} />
</svelte:head>
