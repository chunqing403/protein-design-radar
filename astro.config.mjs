import { defineConfig } from "astro/config";

export default defineConfig({
  site: "https://www.caom.online",
  base: "/",
  output: "static",
  trailingSlash: "never",
  build: {
    format: "file"
  }
});
