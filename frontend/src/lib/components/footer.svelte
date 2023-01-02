<script>
    import GitHub from '$lib/icons/git-hub.svelte'
    import Twitter from '$lib/icons/twitter.svelte'
    import YouTube from '$lib/icons/you-tube.svelte'
    import { socialLinks } from '$lib/site-config'
</script>

<div class="flex flex-col mb-8 max-w-screen-lg m-auto">
    <div class="divider" />
</div>
<footer class="p-4 footer max-w-screen-lg m-auto">
    <div>
        <p>
            Hosting credit
            <br />.. and link
        </p>
    </div>
    <div>
        <span class="footer-title">Social</span>
        <div class="grid grid-flow-col gap-4">
            <a
                href={socialLinks.find(x => x.title === 'Twitter')
                    .path}
            >
                <Twitter />
            </a>
            <a
                href={socialLinks.find(x => x.title === 'YouTube')
                    .path}
            >
                <YouTube />
            </a>
            <a
                href={socialLinks.find(x => x.title === 'GitHub')
                    .path}
            >
                <GitHub />
            </a>
        </div>
    </div>
</footer>
