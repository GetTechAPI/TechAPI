import { defineConfig } from 'astro/config';

// GitHub Pages project site. Data dump (v1/, openapi.json) is copied alongside
// the built site in CI, so internal links use import.meta.env.BASE_URL.
export default defineConfig({
  site: 'https://seungpyo1007.github.io',
  base: '/TechAPI',
});
