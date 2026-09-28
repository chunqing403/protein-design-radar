#!/usr/bin/env python3
"""Import selected WeChat articles into local, portable site content."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Comment


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCES = ROOT / "site" / "wechat_sources.json"
DEFAULT_CONTENT = ROOT / "site" / "content"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
ALLOWED_TAGS = {
    "a",
    "b",
    "blockquote",
    "br",
    "code",
    "div",
    "em",
    "figcaption",
    "figure",
    "h1",
    "h2",
    "h3",
    "h4",
    "hr",
    "i",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "section",
    "span",
    "strong",
    "u",
    "ul",
}


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_text_if_changed(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == value:
        return
    path.write_text(value, encoding="utf-8")


def write_bytes_if_changed(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == value:
        return
    path.write_bytes(value)


def fetch(session: requests.Session, url: str) -> requests.Response:
    response = session.get(url, timeout=60)
    response.raise_for_status()
    return response


def meta_content(soup: BeautifulSoup, key: str) -> str:
    node = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
    return node.get("content", "").strip() if node else ""


def canonical_image_url(value: str) -> str:
    value = (value or "").strip()
    if value.startswith("//"):
        return "https:" + value
    return value


def image_extension(response: requests.Response, source_url: str) -> str:
    content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
    by_type = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/svg+xml": ".svg",
    }
    if content_type in by_type:
        return by_type[content_type]
    match = re.search(r"[?&]wx_fmt=([a-zA-Z0-9]+)", source_url)
    if match:
        fmt = match.group(1).lower().replace("jpeg", "jpg")
        if fmt in {"jpg", "png", "gif", "webp"}:
            return "." + fmt
    suffix = Path(urlparse(source_url).path).suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"} else ".jpg"


def download_image(
    session: requests.Session,
    source_url: str,
    destination_without_suffix: Path,
) -> Path:
    response = fetch(session, canonical_image_url(source_url))
    extension = image_extension(response, source_url)
    destination = destination_without_suffix.with_suffix(extension)
    write_bytes_if_changed(destination, response.content)
    return destination


def publication_date(page_html: str) -> str:
    match = re.search(r"ori_create_time\s*[:=]\s*[\"']?(\d+)", page_html)
    if not match:
        return ""
    timestamp = int(match.group(1))
    timezone = dt.timezone(dt.timedelta(hours=8))
    return dt.datetime.fromtimestamp(timestamp, timezone).date().isoformat()


def sanitize_content(
    content,
    session: requests.Session,
    article_assets: Path,
    public_asset_prefix: str,
) -> str:
    for comment in content.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    for node in content.find_all(["script", "style", "noscript", "iframe", "audio", "video", "form"]):
        node.decompose()

    image_index = 0
    for image in content.find_all("img"):
        source_url = image.get("data-src") or image.get("data-original") or image.get("src") or ""
        source_url = canonical_image_url(source_url)
        if not source_url.startswith("http"):
            image.decompose()
            continue
        image_index += 1
        try:
            local_path = download_image(
                session,
                source_url,
                article_assets / f"image-{image_index:02d}",
            )
        except requests.RequestException as exc:
            print(f"warning: failed to download image {source_url}: {exc}")
            image.decompose()
            continue
        image.attrs = {
            "src": f"{public_asset_prefix}/{local_path.name}",
            "alt": image.get("alt", "文章配图"),
            "loading": "lazy",
        }

    for link in content.find_all("a"):
        href = canonical_image_url(link.get("href", ""))
        link.attrs = {"href": href} if href.startswith(("http://", "https://")) else {}
        if link.attrs:
            link.attrs.update({"target": "_blank", "rel": "noopener noreferrer"})

    for tag in list(content.find_all(True)):
        if tag.name not in ALLOWED_TAGS:
            tag.unwrap()
            continue
        if tag.name not in {"a", "img"}:
            tag.attrs = {}

    return content.decode_contents().strip()


def import_article(session: requests.Session, source: dict, content_root: Path) -> dict:
    url = source["url"]
    slug = source["slug"]
    response = fetch(session, url)
    page_html = response.content.decode("utf-8", errors="replace")
    soup = BeautifulSoup(page_html, "html.parser")
    content = soup.select_one("#js_content")
    if content is None:
        raise RuntimeError(f"article body not found: {url}")

    assets = content_root / "assets" / "wechat" / slug
    assets.mkdir(parents=True, exist_ok=True)
    cover_url = canonical_image_url(meta_content(soup, "og:image"))
    cover_path = ""
    if cover_url:
        try:
            downloaded_cover = download_image(session, cover_url, assets / "cover")
            cover_path = f"assets/wechat/{slug}/{downloaded_cover.name}"
        except requests.RequestException as exc:
            print(f"warning: failed to download cover {cover_url}: {exc}")

    body_html = sanitize_content(
        content,
        session,
        assets,
        f"../assets/wechat/{slug}",
    )
    article_path = content_root / "articles" / f"{slug}.html"
    write_text_if_changed(article_path, body_html + "\n")

    account_node = soup.select_one("#js_name")
    author_node = soup.select_one("#js_author_name")
    return {
        "slug": slug,
        "title": meta_content(soup, "og:title") or soup.title.get_text(strip=True),
        "description": meta_content(soup, "og:description"),
        "account": account_node.get_text(" ", strip=True) if account_node else "",
        "author": author_node.get_text(" ", strip=True) if author_node else "",
        "published": publication_date(page_html),
        "source_url": url,
        "cover": cover_path,
        "featured": bool(source.get("featured", False)),
        "topics": source.get("topics", []),
        "body_file": f"articles/{slug}.html",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--content", type=Path, default=DEFAULT_CONTENT)
    args = parser.parse_args()

    sources = load_json(args.sources, [])
    args.content.mkdir(parents=True, exist_ok=True)
    existing_manifest = load_json(args.content / "articles.json", {"articles": []})
    existing_by_slug = {
        article["slug"]: article
        for article in existing_manifest.get("articles", [])
        if article.get("slug")
    }
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Referer": "https://mp.weixin.qq.com/"})

    articles = []
    for source in sources:
        print(f"importing {source['url']}")
        try:
            articles.append(import_article(session, source, args.content))
        except (requests.RequestException, RuntimeError) as exc:
            existing = existing_by_slug.get(source.get("slug"))
            if existing:
                print(f"warning: keeping previously imported article: {exc}")
                articles.append(existing)
                continue
            raise
    articles.sort(key=lambda article: article.get("published", ""), reverse=True)
    manifest = {"articles": articles}
    write_text_if_changed(
        args.content / "articles.json",
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    print(f"imported {len(articles)} WeChat articles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
