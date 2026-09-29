import { cpSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const publicDir = resolve(root, "public");

mkdirSync(resolve(publicDir, "assets"), { recursive: true });
cpSync(resolve(root, "site", "content", "assets", "wechat"), resolve(publicDir, "assets", "wechat"), {
  recursive: true,
  force: true
});
cpSync(resolve(root, "site", "static", "favicon.svg"), resolve(publicDir, "favicon.svg"), { force: true });

console.log("Prepared WeChat images and favicon for Astro.");
