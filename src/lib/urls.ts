const configuredBase = import.meta.env.BASE_URL;
const base = configuredBase.endsWith("/") ? configuredBase : `${configuredBase}/`;

export function withBase(path = ""): string {
  return `${base}${path.replace(/^\/+/, "")}`;
}

export function articleHref(slug: string): string {
  return withBase(`articles/${slug}.html`);
}

export function assetHref(path: string): string {
  return withBase(path);
}

export function rewriteArticleHtml(body: string): string {
  const assets = withBase("assets/");
  return body
    .replaceAll('src="../assets/', `src="${assets}`)
    .replaceAll("src='../assets/", `src='${assets}`)
    .replaceAll('src="assets/', `src="${assets}`)
    .replaceAll("src='assets/", `src='${assets}`);
}
