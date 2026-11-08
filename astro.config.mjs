import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import { loco } from '@locolabo/theme';

export default defineConfig({
  site: 'https://locopuente.org',
  integrations: [
    starlight(
      loco({
        project: 'loco-puente',
        title: 'LocoPuente',
        description: 'Local AI for everyone who can’t — or won’t — send their data to the cloud',
        home: 'https://locopuente.org',
        github: 'loco-puente',
        accent: { low: '#4c0519', main: '#f43f5e', high: '#fecdd3' },
        logo: {
          alt: 'LocoPuente',
          src: './src/assets/art/icon.png',
          replacesTitle: false,
        },
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
        ],
      })
    ),
  ],
});
