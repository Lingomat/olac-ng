<script>
    import Footer from '$lib/components/footer.svelte'
    import Nav from '$lib/components/nav.svelte'
    import '../app.css'
    import '../prism.css'
</script>

<Nav />

<main
    class="relative sm:px-6 break-normal text-black max-w-screen-lg m-auto"
>
    <slot />
</main>

<Footer />
