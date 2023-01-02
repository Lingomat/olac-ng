const config = {
    mode: 'jit',
    purge: ['./src/**/*.{html,js,svelte,ts}'],
    theme: {
        extend: {
            typography: {
                DEFAULT: {
                    css: {
                        color: 'black',
                        maxWidth: null,
                        li: {
                            'margin-bottom': '0px',
                            'margin-top': '0px',
                        },
                        a: {
                            'text-decoration': 'inherit',
                        },
                        h2: {
                            'margin-top': '.5em',
                            'margin-bottom': '.5em',
                        },
                        img: {
                            'margin-top': '0',
                        },
                        '.all-prose': {
                            '--tw-prose-headings': 'brown'
                        }
                        
                    },
                },
            },
        },
    },
    plugins: [require('@tailwindcss/typography'), require('daisyui')],
}


// const config = {
//     mode: 'jit',
//     purge: ['./src/**/*.{html,js,svelte,ts}'],
//     theme: {
//         extend: {
//             typography: ({ theme }) => ({
//                 DEFAULT: {
//                     css: {
//                         color: 'black',
//                         maxWidth: null,
//                         li: {
//                             'margin-bottom': '0px',
//                             'margin-top': '0px',
//                         },
//                         a: {
//                             'text-decoration': 'inherit',
//                         },
//                         h2: {
//                             'margin-top': '.5em',
//                             'margin-bottom': '.5em',
//                         },
//                         img: {
//                             'margin-top': '0',
//                         },
//                         '--tw-prose-headings': theme('colors.pink[900]'),
//                     },
//                 },
//             }),
//         },
//     },
//     plugins: [require('@tailwindcss/typography'), require('daisyui')],
// }


module.exports = config
