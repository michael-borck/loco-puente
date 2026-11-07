import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  site: 'https://locopuente.org',
  integrations: [
    starlight({
      title: 'LocoPuente',
      description: "Local AI for everyone who can\u2019t \u2014 or won\u2019t \u2014 send their data to the cloud",
      favicon: '/favicon.svg',
      disable404Route: true,
      logo: {
        alt: 'LocoPuente',
        src: './src/assets/puente.svg',
        replacesTitle: false,
      },
      social: [
        { icon: 'external', label: 'Home', href: 'https://locopuente.org' },
        { icon: 'external', label: 'LocoLabo', href: 'https://locolabo.org' },
      ],
      customCss: ['./src/styles/custom.css'],
      sidebar: [
        {
          label: 'Overview',
          items: [
            { label: 'Home', link: '/' },
            { label: 'Why LocoPuente', slug: 'about' },
            { label: 'Student Services', slug: 'services' },
            { label: 'Architecture', slug: 'architecture' },
            { label: 'Philosophy', slug: 'philosophy' },
          ],
        },
        {
          label: 'Infrastructure',
          items: [
            { label: 'Proof of Concept', slug: 'poc' },
            { label: 'Software Stack', slug: 'stack' },
            { label: 'Roadmap', slug: 'roadmap' },
            { label: 'Choosing Your Stack', slug: 'choosing' },
            { label: 'Hardware Selection', slug: 'hardware' },
          ],
        },
        {
          label: 'LocoLabo Projects',
          items: [
            { label: 'All Projects', link: 'https://locolabo.org/projects/' },
            { label: 'LocoLabo', link: 'https://locolabo.org' },
            { label: 'LocoLLM', link: 'https://locollm.org' },
            { label: 'LocoBanco', link: 'https://locobanco.org' },
            { label: 'LocoBench Picker', link: 'https://picker.locobanco.org' },
            { label: 'LocoFósil', link: 'https://locofosil.org' },
            { label: 'LocoMusa', link: 'https://locomusa.org' },
            { label: 'LocoConvoy', link: 'https://lococonvoy.org' },
            { label: 'LocoAgente', link: 'https://locoagente.org' },
            { label: 'LocoEnsayo', link: 'https://locoensayo.org' },
            { label: 'LocoNotas', link: 'https://loconotas.org' },
            { label: 'LocoBase', link: 'https://github.com/michael-borck/loco-base' },
          ],
        },
      ],
    }),
  ],
});
