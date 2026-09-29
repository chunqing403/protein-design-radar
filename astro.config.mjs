import { defineConfig } from "astro/config";

export default defineConfig({
  site: "https://chunqing403.github.io",
  base: "/protein-design-radar",
  output: "static",
  trailingSlash: "never",
  build: {
    format: "file"
  }
});
