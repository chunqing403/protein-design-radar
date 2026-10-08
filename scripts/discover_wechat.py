#!/usr/bin/env python3
"""Discover WeChat article links from RSS/Atom feeds or explicit URLs."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import time
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse, urlunparse
from xml.etree import ElementTree

import requests


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCES = ROOT / "site" / "wechat_sources.json"
DEFAULT_CACHE = ROOT / "work" / "wechat_feed_items.json"
USER_AGENT = "protein-design-radar/1.0 (+https://github.com/chunqing403/protein-design-radar)"


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def normalize_url(value: str) -> str:
    value = (value or "").strip()
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        return ""
    host = (parsed.hostname or "").lower()
    if host != "mp.weixin.qq.com":
        return ""
    return urlunparse(("https", "mp.weixin.qq.com", parsed.path, "", parsed.query, ""))


def article_identity(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    mid = query.get("mid", [""])[0]
    if mid:
        biz = query.get("__biz", [""])[0]
        idx = query.get("idx", ["1"])[0] or "1"
        return f"mid:{biz}:{mid}:{idx}"
    if parsed.path.startswith("/s/"):
        return f"short:{parsed.path.removeprefix('/s/').strip('/')}"
    return "url:" + hashlib.sha256(url.encode("utf-8")).hexdigest()


def slug_for_url(url: str, prefix: str = "caom") -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    mid = query.get("mid", [""])[0]
    idx = query.get("idx", ["1"])[0] or "1"
    if mid.isdigit():
        suffix = mid if idx == "1" else f"{mid}-{idx}"
    else:
        suffix = hashlib.sha256(article_identity(url).encode("utf-8")).hexdigest()[:12]
    clean_prefix = "".join(char for char in prefix.lower() if char.isalnum() or char == "-").strip("-")
    return f"{clean_prefix or 'wechat'}-{suffix}"


def element_value(element) -> str:
    value = element.text or ""
    if list(element):
        value += "".join(ElementTree.tostring(child, encoding="unicode") for child in element)
    return value.strip()


def normalized_date(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    try:
        return parsedate_to_datetime(value).date().isoformat()
    except (TypeError, ValueError):
        pass
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return value[:10] if len(value) >= 10 else ""


def extract_feed_items(xml_text: str) -> list[dict]:
    root = ElementTree.fromstring(xml_text)
    account = ""
    for node in root.iter():
        if local_name(node.tag) in {"channel", "feed"}:
            title = next((element_value(child) for child in node if local_name(child.tag) == "title"), "")
            if title:
                account = title
                break
    items: list[dict] = []
    for entry in root.iter():
        if local_name(entry.tag) not in {"item", "entry"}:
            continue
        candidates: list[str] = []
        fields: dict[str, str] = {}
        for child in entry:
            name = local_name(child.tag)
            if name == "link":
                href = child.attrib.get("href", "").strip()
                rel = child.attrib.get("rel", "alternate")
                if href and rel in {"", "alternate"}:
                    candidates.append(href)
                elif child.text:
                    candidates.append(child.text.strip())
            elif name == "guid" and child.text:
                candidates.append(child.text.strip())
            elif name in {"title", "description", "summary", "content", "encoded", "pubdate", "published", "updated"}:
                fields[name] = element_value(child)
            elif name == "author":
                fields["author"] = next(
                    (element_value(grandchild) for grandchild in child if local_name(grandchild.tag) == "name"),
                    element_value(child),
                )
        for candidate in candidates:
            normalized = normalize_url(candidate)
            if normalized:
                items.append(
                    {
                        "url": normalized,
                        "title": fields.get("title", ""),
                        "description": fields.get("description", "") or fields.get("summary", ""),
                        "content": fields.get("encoded", "") or fields.get("content", ""),
                        "published": normalized_date(
                            fields.get("pubdate", "")
                            or fields.get("published", "")
                            or fields.get("updated", "")
                        ),
                        "author": fields.get("author", ""),
                        "account": account,
                    }
                )
                break
    return list({article_identity(item["url"]): item for item in items}.values())


def extract_feed_links(xml_text: str) -> list[str]:
    return [item["url"] for item in extract_feed_items(xml_text)]


def load_sources(path: Path) -> list[dict]:
    if not path.exists():
        return []
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError(f"expected a JSON list in {path}")
    return value


def fetch_feed(url: str, attempts: int = 4) -> str:
    last_error: requests.RequestException | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=90)
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            last_error = exc
            if attempt == attempts:
                break
            delay = attempt * 10
            print(f"Feed request failed ({attempt}/{attempts}); retrying in {delay}s: {exc}")
            time.sleep(delay)
    assert last_error is not None
    raise last_error


def add_links(
    sources: list[dict],
    links: list[str],
    *,
    prefix: str,
    featured: bool = False,
    topics: list[str] | None = None,
) -> list[dict]:
    existing_identities = {
        article_identity(normalized)
        for source in sources
        if (normalized := normalize_url(source.get("url", "")))
    }
    existing_slugs = {source.get("slug", "") for source in sources}
    added: list[dict] = []
    for value in links:
        url = normalize_url(value)
        if not url or article_identity(url) in existing_identities:
            continue
        slug = slug_for_url(url, prefix)
        if slug in existing_slugs:
            slug = f"{slug}-{hashlib.sha256(url.encode('utf-8')).hexdigest()[:6]}"
        source = {
            "url": url,
            "slug": slug,
            "featured": featured,
            "topics": topics or [],
        }
        sources.append(source)
        added.append(source)
        existing_identities.add(article_identity(url))
        existing_slugs.add(slug)
    return added


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feed-url", default=os.environ.get("WECHAT_FEED_URL", ""))
    parser.add_argument("--article-url", action="append", default=[])
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--slug-prefix", default=os.environ.get("WECHAT_SLUG_PREFIX", "caom"))
    parser.add_argument("--featured", default="false")
    parser.add_argument("--topics", default="")
    args = parser.parse_args()

    links = [url for url in args.article_url if normalize_url(url)]
    feed_items: list[dict] = []
    if args.feed_url:
        feed_items = extract_feed_items(fetch_feed(args.feed_url))
        links.extend(item["url"] for item in feed_items)
    if not links:
        print("No WeChat feed or article URL configured; nothing to discover.")
        return 0

    sources = load_sources(args.sources)
    topics = [topic.strip() for topic in args.topics.split(",") if topic.strip()]
    added = add_links(
        sources,
        list(dict.fromkeys(links)),
        prefix=args.slug_prefix,
        featured=parse_bool(args.featured),
        topics=topics,
    )
    if added:
        args.sources.write_text(
            json.dumps(sources, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    added_by_identity = {article_identity(source["url"]): source for source in added}
    cached_items = []
    for item in feed_items:
        source = added_by_identity.get(article_identity(item["url"]))
        if source:
            cached_items.append({**item, "slug": source["slug"]})
    args.cache.parent.mkdir(parents=True, exist_ok=True)
    args.cache.write_text(
        json.dumps({"items": cached_items}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Discovered {len(added)} new WeChat article(s).")
    for source in added:
        print(f"- {source['slug']}: {source['url']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
