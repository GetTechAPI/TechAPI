import { defineConfig } from 'astro/config';

// GitHub Pages project site. Data dump (v1/, openapi.json) is copied alongside
// the built site in CI, so internal links use import.meta.env.BASE_URL.
export default defineConfig({
  site: 'https://gettechapi.github.io',
  // Vercel previews serve from the domain root, not the GitHub Pages project path.
  base: process.env.VERCEL ? '/' : '/TechAPI',
});
