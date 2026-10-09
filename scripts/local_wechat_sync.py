#!/usr/bin/env python3
"""Sync a local WechRss feed into the repository and push new articles."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from urllib.parse import urljoin
from xml.etree import ElementTree

import requests


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "http://127.0.0.1:8080"
TRACKED_PATHS = ("site/wechat_sources.json", "site/content")


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def feed_title(xml_text: str) -> str:
    root = ElementTree.fromstring(xml_text)
    for node in root.iter():
        if local_name(node.tag) not in {"channel", "feed"}:
            continue
        for child in node:
            if local_name(child.tag) == "title" and child.text:
                return child.text.strip()
    return ""


def find_feed_url(
    base_url: str,
    account_name: str,
    *,
    session: requests.Session | None = None,
    probe_limit: int = 20,
) -> str:
    session = session or requests.Session()
    base_url = base_url.rstrip("/") + "/"
    health = session.get(urljoin(base_url, "api/health"), timeout=10)
    health.raise_for_status()

    candidates: list[tuple[str, str]] = []
    for source_id in range(1, probe_limit + 1):
        url = urljoin(base_url, f"feeds/{source_id}.xml")
        response = session.get(url, timeout=15)
        if response.status_code == 404:
            continue
        response.raise_for_status()
        try:
            title = feed_title(response.text)
        except ElementTree.ParseError:
            continue
        candidates.append((title, url))
        if title.casefold() == account_name.casefold():
            return url

    for title, url in candidates:
        if account_name.casefold() in title.casefold():
            return url
    available = ", ".join(title or "(untitled)" for title, _ in candidates) or "none"
    raise RuntimeError(
        f"No local feed matched account '{account_name}'. Available feeds: {available}. "
        "Open WechRss and add the account first."
    )


def run(command: list[str], *, cwd: Path = ROOT, capture: bool = False) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(command))
    return subprocess.run(
        command,
        cwd=cwd,
        check=True,
        text=True,
        capture_output=capture,
    )


def git_output(*args: str) -> str:
    result = run(["git", *args], capture=True)
    return result.stdout.strip()


def content_changes() -> str:
    return git_output("status", "--porcelain", "--", *TRACKED_PATHS)


def sync(feed_url: str, *, pull: bool = True, push: bool = True) -> bool:
    if pull and not content_changes():
        run(["git", "pull", "--rebase"])

    run([sys.executable, "scripts/discover_wechat.py", "--feed-url", feed_url])
    if not content_changes():
        print("No new WeChat articles.")
        return False

    run([sys.executable, "scripts/sync_wechat.py"])
    run(["git", "add", *TRACKED_PATHS])
    if not git_output("diff", "--cached", "--name-only"):
        print("No publishable WeChat changes.")
        return False

    run(["git", "config", "user.name", "paper-radar-local-bot"])
    run(["git", "config", "user.email", "paper-radar-bot@users.noreply.github.com"])
    run(["git", "commit", "-m", "Update WeChat articles"])
    if push:
        run(["git", "pull", "--rebase"])
        run(["git", "push"])
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--account", default="CAOM")
    parser.add_argument("--feed-url", default="")
    parser.add_argument("--probe-limit", type=int, default=20)
    parser.add_argument("--no-pull", action="store_true")
    parser.add_argument("--no-push", action="store_true")
    args = parser.parse_args()

    try:
        feed_url = args.feed_url or find_feed_url(
            args.base_url,
            args.account,
            probe_limit=args.probe_limit,
        )
        print(f"Using local feed: {feed_url}")
        changed = sync(feed_url, pull=not args.no_pull, push=not args.no_push)
        print("WeChat sync completed with new content." if changed else "WeChat sync is already current.")
        return 0
    except (requests.RequestException, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Local WeChat sync failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
