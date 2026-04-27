import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  site: 'https://locopuente.org',
  base: '/docs',
  integrations: [
    starlight({
      title: 'LocoPuente',
      description: "Local AI for everyone who can\u2019t \u2014 or won\u2019t \u2014 send their data to the cloud",
      favicon: '/favicon.svg',
      logo: {
        alt: 'LocoPuente',
        src: './src/assets/puente.svg',
        replacesTitle: false,
      },
      social: [
        { icon: 'external', label: 'Home', href: 'https://locopuente.org' },
        { icon: 'external', label: 'LocoLab', href: 'https://locolabo.org' },
      ],
      customCss: ['./src/styles/custom.css'],
      sidebar: [
        {
          label: 'Overview',
          items: [
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
          label: 'LocoLab Projects',
          items: [
            { label: 'LocoLab', link: 'https://locolabo.org' },
            { label: 'LocoBench', link: 'https://locobench.org' },
            { label: 'LocoLLM', link: 'https://locollm.org' },
            { label: 'LocoConvoy', link: 'https://lococonvoy.org' },
            { label: 'LocoAgente', link: 'https://locoagente.org' },
            { label: 'LocoEnsayo', link: 'https://locoensayo.org' },
          ],
        },
      ],
    }),
  ],
});
