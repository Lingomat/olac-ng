<script>
    export let size = 400
    let imagesrc = '/images/world-color.png'
    const areas = [
        {
            name: 'africa',
            coords: '136,45,127,60,127,71,136,78,149,77,159,118,171,116,179,103,186,109,192,94,188,92,183,96,182,88,193,69,184,70,173,49,163,47,161,49,154,46,153,43,139,44',
        },
        {
            name: 'americas',
            coords: '11,25,22,22,34,10,62,12,77,5,83,6,102,1,142,3,131,13,109,21,103,33,73,50,91,66,90,72,116,88,91,125,100,134,91,139,80,129,77,100,65,85,69,75,57,66,46,65,35,40,40,31,41,23,37,21,16,28',
        },
        {
            name: 'asia',
            coords: '207,57,218,77,220,65,226,61,239,89,262,92,261,84,268,86,266,90,269,90,272,87,275,91,275,82,264,77,258,59,271,43,268,38,283,14,233,4,196,2,200,7,191,9,193,29,181,30,185,34,185,38,165,39,168,45,176,45,175,50,184,68,197,63,199,56"',
        },
        {
            name: 'europe',
            coords: '135,42,142,45,148,37,152,37,152,40,157,40,157,43,161,40,165,44,165,38,169,37,172,35,176,34,178,37,184,36,184,33,180,30,192,28,192,12,184,13,191,8,183,1,154,3,148,19,131,14,129,17,141,21,135,29,143,35,136,35',
        },
        {
            name: 'pacific',
            coords: '265,93,245,104,246,119,262,116,269,128,284,127,286,132,304,119,299,115,284,126,274,125,285,108,320,96,319,92,303,97,286,83,283,86,275,82,275,98"',
        },
    ]
    function mouseover(area) {
        imagesrc = '/images/world-color-' + area + '.png'
    }
    function mouseout() {
        imagesrc = '/images/world-color.png'
    }
    function scalepoly(polystring) {
        const vals = polystring.split(',')
        const scaledvals = vals.map(x => {
            return parseInt(x) * (size / 320)
        })
        return scaledvals.join(',')
    }
</script>

<img
    id="world-map"
    src={imagesrc}
    alt="World Map"
    usemap="#areas"
    width={size}
    style="width: {size + 'px'};min-width: {size + 'px'};"
/>
<map name="areas">
    {#each areas as area}
        <area
            alt={area.name}
            shape="poly"
            coords={scalepoly(area.coords)}
            href={'/areas/' + area.name}
            on:mouseover={() => {
                mouseover(area.name)
            }}
            on:focus={() => {
                mouseover(area.name)
            }}
            on:mouseout={mouseout}
            on:blur={mouseout}
        />
    {/each}
</map>
