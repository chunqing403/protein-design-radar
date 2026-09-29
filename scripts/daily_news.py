#!/usr/bin/env python3
"""Collect protein-design news from RSS, aggregators, and GitHub releases."""

from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import hashlib
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "news_sources.json"
DEFAULT_OUTPUT = ROOT / "data" / "news.json"


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip().lower()


def clean_text(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def trim(value: str, limit: int = 240) -> str:
    value = clean_text(value)
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def request_text(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "protein-design-news-radar/1.0 (+https://github.com/chunqing403/protein-design-radar)",
            "Accept": "application/rss+xml, application/atom+xml, application/json, text/xml, */*",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"warning: news source failed: {url} ({exc})", file=sys.stderr)
        return ""


def parse_date(value: str) -> str:
    value = clean_text(value)
    if not value:
        return ""
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        return parsed.date().isoformat()
    except (TypeError, ValueError, OverflowError):
        pass
    match = re.search(r"\d{4}-\d{2}-\d{2}", value)
    return match.group(0) if match else ""


def item_key(title: str, url: str = "") -> str:
    identity = normalize_text(title)
    if not identity:
        identity = normalize_text(url)
    return hashlib.sha1(identity.encode("utf-8")).hexdigest()


def relevant(title: str, summary: str, config: dict) -> bool:
    text = f" {normalize_text(title)} {normalize_text(summary)} "
    if any(term.lower() in text for term in config.get("negative_terms", [])):
        return False
    if any(term.lower() in text for term in config.get("high_relevance_terms", [])):
        return True
    has_domain = any(term.lower() in text for term in config.get("domain_terms", []))
    has_ai = any(term.lower() in text for term in config.get("ai_terms", []))
    return has_domain and has_ai


def child_text(node: ET.Element, names: tuple[str, ...]) -> str:
    for child in node.iter():
        local = child.tag.rsplit("}", 1)[-1].lower()
        if local in names and child.text:
            return child.text
    return ""


def feed_link(node: ET.Element) -> str:
    for child in node:
        if child.tag.rsplit("}", 1)[-1].lower() != "link":
            continue
        href = child.attrib.get("href", "")
        rel = child.attrib.get("rel", "alternate")
        if href and rel in {"alternate", ""}:
            return href
        if child.text:
            return child.text.strip()
    return ""


def parse_feed(xml_text: str, source: dict, config: dict) -> list[dict]:
    if not xml_text:
        return []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        print(f"warning: invalid feed from {source.get('name')}: {exc}", file=sys.stderr)
        return []
    nodes = root.findall(".//item") or root.findall(".//{*}entry")
    records = []
    for node in nodes[: int(source.get("limit", 30))]:
        title = clean_text(child_text(node, ("title",)))
        summary = trim(child_text(node, ("description", "summary", "content")))
        url = clean_text(feed_link(node))
        published = parse_date(child_text(node, ("pubdate", "published", "updated", "date")))
        source_name = source.get("name", "RSS")
        embedded_source = clean_text(child_text(node, ("source",)))
        if source.get("use_embedded_source") and embedded_source:
            source_name = embedded_source
            suffix = f" - {source_name}"
            if title.lower().endswith(suffix.lower()):
                title = title[: -len(suffix)].rstrip()
        blocked = {normalize_text(name) for name in config.get("blocked_sources", [])}
        if normalize_text(source_name) in blocked:
            continue
        if not title or not url:
            continue
        if not source.get("trusted") and not relevant(title, summary, config):
            continue
        records.append(
            {
                "title": title,
                "summary": summary,
                "url": url,
                "published": published,
                "source": source_name,
                "category": source.get("category", "综合资讯"),
            }
        )
    return records


def collect_google_news(config: dict) -> list[dict]:
    records = []
    for query in config.get("google_news_queries", []):
        params = urllib.parse.urlencode({"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"})
        source = {
            "name": "Google News",
            "category": "产业动态",
            "limit": 40,
            "use_embedded_source": True,
        }
        records.extend(parse_feed(request_text(f"https://news.google.com/rss/search?{params}"), source, config))
    return records


def collect_ai_hot(config: dict) -> list[dict]:
    source = config.get("ai_hot", {})
    if not source.get("enabled"):
        return []
    text = request_text(source.get("url", ""))
    if not text:
        return []
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []
    records = []
    for item in payload.get("items", []):
        title = clean_text(item.get("title", ""))
        summary = trim(item.get("summary", ""))
        if not relevant(title, summary, config):
            continue
        links = item.get("links") or {}
        source_data = item.get("source") or {}
        records.append(
            {
                "title": title,
                "summary": summary,
                "url": links.get("original") or links.get("aihot") or "https://aihot.virxact.com",
                "published": parse_date(item.get("publishedAt") or item.get("discoveredAt") or ""),
                "source": source_data.get("name") or "AI HOT",
                "category": source.get("category", "综合资讯"),
            }
        )
    return records


def collect_github_releases(config: dict) -> list[dict]:
    records = []
    for repo in config.get("github_releases", []):
        records.extend(collect_github_release(repo, config))
    return records


def collect_github_release(repo: str, config: dict) -> list[dict]:
    source = {
        "name": f"GitHub · {repo}",
        "category": "模型与工具",
        "trusted": True,
        "limit": int(config.get("github_release_limit", 5)),
    }
    feed = request_text(f"https://github.com/{repo}/releases.atom")
    records = parse_feed(feed, source, config)
    for record in records:
        record["title"] = f"{repo.split('/')[-1]} · {record['title']}"
    return records


def merge_records(existing: dict, collected: list[dict], config: dict, today: str) -> dict:
    items = dict(existing.get("items", {}))
    for record in collected:
        key = item_key(record.get("title", ""), record.get("url", ""))
        if not key:
            continue
        previous = items.get(key, {})
        merged = {**previous, **record}
        merged["first_seen"] = previous.get("first_seen") or today
        items[key] = merged
    limit = int(config.get("history_limit", 400))
    ordered = sorted(
        items.items(),
        key=lambda pair: (
            pair[1].get("published", ""),
            pair[1].get("first_seen", ""),
            pair[1].get("title", ""),
        ),
        reverse=True,
    )[:limit]
    return {
        "updated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "items": dict(ordered),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    config = load_json(args.config, {})
    jobs = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        for source in config.get("feeds", []):
            jobs.append(executor.submit(lambda item=source: parse_feed(request_text(item["url"]), item, config)))
        for query in config.get("google_news_queries", []):
            jobs.append(
                executor.submit(
                    lambda value=query: parse_feed(
                        request_text(
                            "https://news.google.com/rss/search?"
                            + urllib.parse.urlencode({"q": value, "hl": "en-US", "gl": "US", "ceid": "US:en"})
                        ),
                        {
                            "name": "Google News",
                            "category": "产业动态",
                            "limit": 40,
                            "use_embedded_source": True,
                        },
                        config,
                    )
                )
            )
        jobs.append(executor.submit(collect_ai_hot, config))
        for repo in config.get("github_releases", []):
            jobs.append(executor.submit(collect_github_release, repo, config))
        collected = []
        for job in as_completed(jobs):
            try:
                collected.extend(job.result())
            except Exception as exc:  # Keep one flaky source from aborting the daily run.
                print(f"warning: news collection task failed: {exc}", file=sys.stderr)

    payload = merge_records(load_json(args.output, {"items": {}}), collected, config, dt.date.today().isoformat())
    save_json(args.output, payload)
    print(f"collected {len(collected)} relevant news items; library now has {len(payload['items'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
