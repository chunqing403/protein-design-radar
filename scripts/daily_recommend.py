#!/usr/bin/env python3
"""Generate a daily protein-design paper recommendation digest.

The script intentionally uses only the Python standard library so it can run in
GitHub Actions without dependency installation.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "topics.json"
DEFAULT_STATE = ROOT / "data" / "seen.json"
DEFAULT_LIBRARY = ROOT / "data" / "papers.json"
README_START = "<!-- PAPER_RADAR:START -->"
README_END = "<!-- PAPER_RADAR:END -->"


@dataclass
class Paper:
    title: str
    authors: list[str]
    abstract: str
    source: str
    published: str
    url: str
    doi: str = ""
    source_id: str = ""
    score: int = 0
    topics: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    is_new: bool = True

    @property
    def key(self) -> str:
        if self.doi:
            return "doi:" + self.doi.lower()
        if self.source_id:
            return f"{self.source}:{self.source_id}".lower()
        normalized = normalize_text(self.title)
        return "title:" + hashlib.sha1(normalized.encode("utf-8")).hexdigest()


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip().lower()


def clean_text(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def contains_term(haystack: str, term: str) -> bool:
    normalized = normalize_text(term)
    if not normalized:
        return False
    if re.fullmatch(r"[a-z0-9]+", normalized):
        return re.search(rf"(?<![a-z0-9]){re.escape(normalized)}(?![a-z0-9])", haystack) is not None
    return normalized in haystack


def load_json(path: Path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")


def request_text(url: str, timeout: int = 30, retries: int = 2) -> str:
    headers = {
        "User-Agent": "protein-design-paper-radar/0.1 (+https://github.com/)",
        "Accept": "application/json, application/xml, text/xml, */*",
    }
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt >= retries:
                print(f"warning: request failed: {url} ({exc})", file=sys.stderr)
                return ""
            time.sleep(2 * (attempt + 1))
    return ""


def arxiv_query(queries: list[str], max_results: int) -> list[Paper]:
    joined = " OR ".join(f"all:{q}" for q in queries)
    params = urllib.parse.urlencode(
        {
            "search_query": joined,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
    )
    xml_text = request_text(f"https://export.arxiv.org/api/query?{params}")
    if not xml_text:
        return []
    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(xml_text)
    papers: list[Paper] = []
    for entry in root.findall("a:entry", ns):
        source_id = clean_text(entry.findtext("a:id", default="", namespaces=ns)).rsplit("/", 1)[-1]
        authors = [
            clean_text(node.findtext("a:name", default="", namespaces=ns))
            for node in entry.findall("a:author", ns)
        ]
        doi = ""
        for link in entry.findall("a:link", ns):
            if link.attrib.get("title") == "doi":
                doi = link.attrib.get("href", "").replace("http://dx.doi.org/", "")
        papers.append(
            Paper(
                title=clean_text(entry.findtext("a:title", default="", namespaces=ns)),
                authors=[a for a in authors if a],
                abstract=clean_text(entry.findtext("a:summary", default="", namespaces=ns)),
                source="arXiv",
                source_id=source_id,
                doi=doi,
                published=clean_text(entry.findtext("a:published", default="", namespaces=ns))[:10],
                url=clean_text(entry.findtext("a:id", default="", namespaces=ns)),
            )
        )
    return papers


def preprint_query(server: str, start: dt.date, end: dt.date, max_results: int) -> list[Paper]:
    url = f"https://api.biorxiv.org/details/{server}/{start.isoformat()}/{end.isoformat()}/0"
    text = request_text(url)
    if not text:
        return []
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []
    papers: list[Paper] = []
    for item in payload.get("collection", [])[:max_results]:
        doi = clean_text(item.get("doi", ""))
        papers.append(
            Paper(
                title=clean_text(item.get("title", "")),
                authors=[a.strip() for a in clean_text(item.get("authors", "")).split(";") if a.strip()],
                abstract=clean_text(item.get("abstract", "")),
                source=server,
                source_id=doi,
                doi=doi,
                published=clean_text(item.get("date", "")),
                url=f"https://doi.org/{doi}" if doi else clean_text(item.get("link", "")),
            )
        )
    return papers


def pubmed_query(queries: list[str], start: dt.date, end: dt.date, max_results: int) -> list[Paper]:
    term = "(" + ") OR (".join(queries) + ")"
    params = {
        "db": "pubmed",
        "term": term,
        "retmode": "json",
        "retmax": str(max_results),
        "sort": "pub+date",
        "mindate": start.isoformat(),
        "maxdate": end.isoformat(),
        "datetype": "pdat",
    }
    if os.getenv("NCBI_API_KEY"):
        params["api_key"] = os.getenv("NCBI_API_KEY", "")
    if os.getenv("NCBI_EMAIL"):
        params["email"] = os.getenv("NCBI_EMAIL", "")
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urllib.parse.urlencode(params)
    text = request_text(search_url)
    if not text:
        return []
    ids = json.loads(text).get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []
    fetch_params = {
        "db": "pubmed",
        "id": ",".join(ids),
        "retmode": "xml",
    }
    fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?" + urllib.parse.urlencode(fetch_params)
    xml_text = request_text(fetch_url)
    if not xml_text:
        return []
    root = ET.fromstring(xml_text)
    papers: list[Paper] = []
    for article in root.findall(".//PubmedArticle"):
        pmid = clean_text(article.findtext(".//PMID", default=""))
        title = clean_text("".join(article.find(".//ArticleTitle").itertext()) if article.find(".//ArticleTitle") is not None else "")
        abstract_parts = ["".join(node.itertext()) for node in article.findall(".//AbstractText")]
        authors = []
        for author in article.findall(".//Author")[:12]:
            last = clean_text(author.findtext("LastName", default=""))
            initials = clean_text(author.findtext("Initials", default=""))
            if last:
                authors.append(f"{last} {initials}".strip())
        doi = ""
        for aid in article.findall(".//ArticleId"):
            if aid.attrib.get("IdType") == "doi":
                doi = clean_text(aid.text or "")
                break
        date_node = article.find(".//PubDate")
        year = clean_text(date_node.findtext("Year", default="")) if date_node is not None else ""
        month = clean_text(date_node.findtext("Month", default="01")) if date_node is not None else "01"
        day = clean_text(date_node.findtext("Day", default="01")) if date_node is not None else "01"
        published = " ".join(part for part in [year, month, day] if part)
        papers.append(
            Paper(
                title=title,
                authors=authors,
                abstract=clean_text(" ".join(abstract_parts)),
                source="PubMed",
                source_id=pmid,
                doi=doi,
                published=published,
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
            )
        )
    return papers


def score_paper(paper: Paper, config: dict) -> Paper:
    haystack = normalize_text(f"{paper.title} {paper.abstract}")
    required_terms = config.get("required_keywords", [])
    if required_terms and not any(contains_term(haystack, term) for term in required_terms):
        paper.score = -999
        paper.reasons = ["missing required protein-domain term"]
        paper.topics = ["Filtered"]
        return paper
    score = 0
    reasons: list[str] = []
    weights = {"high": 5, "medium": 3, "low": 1}
    for bucket, terms in config["positive_keywords"].items():
        for term in terms:
            if contains_term(haystack, term):
                score += weights.get(bucket, 1)
                if len(reasons) < 6:
                    reasons.append(term)
    for term in config.get("negative_keywords", []):
        if contains_term(haystack, term):
            score -= 4
    topics = []
    for topic, terms in config.get("topic_profiles", {}).items():
        if any(contains_term(haystack, term) for term in terms):
            topics.append(topic)
    if paper.source in {"bioRxiv", "medRxiv", "arXiv"}:
        score += 1
    paper.score = score
    paper.reasons = reasons
    paper.topics = topics or ["General"]
    return paper


def dedupe(papers: Iterable[Paper]) -> list[Paper]:
    best: dict[str, Paper] = {}
    for paper in papers:
        if not paper.title:
            continue
        key = paper.key
        if key not in best or paper.score > best[key].score:
            best[key] = paper
    return list(best.values())


def format_authors(authors: list[str]) -> str:
    if not authors:
        return "Unknown authors"
    if len(authors) <= 3:
        return ", ".join(authors)
    return ", ".join(authors[:3]) + " et al."


def first_sentences(text: str, limit: int = 360) -> str:
    text = clean_text(text)
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "..."


def paper_to_record(paper: Paper, first_seen: str) -> dict:
    return {
        "title": paper.title,
        "authors": paper.authors,
        "abstract": paper.abstract,
        "source": paper.source,
        "published": paper.published,
        "url": paper.url,
        "doi": paper.doi,
        "source_id": paper.source_id,
        "score": paper.score,
        "topics": paper.topics,
        "reasons": paper.reasons,
        "first_seen": first_seen,
    }


def record_to_paper(record: dict) -> Paper:
    return Paper(
        title=record.get("title", ""),
        authors=record.get("authors", []),
        abstract=record.get("abstract", ""),
        source=record.get("source", ""),
        published=record.get("published", ""),
        url=record.get("url", ""),
        doi=record.get("doi", ""),
        source_id=record.get("source_id", ""),
        score=int(record.get("score", 0)),
        topics=record.get("topics", []),
        reasons=record.get("reasons", []),
        is_new=False,
    )


def update_library(library: dict, papers: list[Paper], target_date: dt.date) -> dict:
    records = library.setdefault("papers", {})
    today = target_date.isoformat()
    for paper in papers:
        existing = records.get(paper.key, {})
        first_seen = existing.get("first_seen", today)
        record = paper_to_record(paper, first_seen)
        if existing and existing.get("score", 0) > record["score"]:
            record["score"] = existing["score"]
        records[paper.key] = record
    return library


def library_papers(library: dict) -> list[Paper]:
    papers = []
    for record in library.get("papers", {}).values():
        paper = record_to_paper(record)
        paper.is_new = False
        papers.append(paper)
    return sorted(
        papers,
        key=lambda p: (
            library.get("papers", {}).get(p.key, {}).get("first_seen", ""),
            p.published,
            p.score,
        ),
        reverse=True,
    )


def render_report(date: dt.date, papers: list[Paper], config: dict) -> str:
    lines = [
        f"# {config.get('project_name', 'Paper Radar')} - {date.isoformat()}",
        "",
        f"Generated on {dt.datetime.utcnow().replace(microsecond=0).isoformat()}Z.",
        "",
    ]
    if not papers:
        lines += [
            "No new high-confidence papers were found today.",
            "",
            "Consider lowering `min_score` or adding broader queries in `config/topics.json`.",
            "",
        ]
        return "\n".join(lines)

    lines += [
        f"Found {len(papers)} recommended papers.",
        "",
        "## Highlights",
        "",
    ]
    for idx, paper in enumerate(papers, 1):
        status = "NEW" if paper.is_new else "SEEN"
        lines += [
            f"### {idx}. {paper.title}",
            "",
            f"- **Score:** {paper.score} | **Status:** {status} | **Source:** {paper.source} | **Date:** {paper.published or 'n/a'}",
            f"- **Authors:** {format_authors(paper.authors)}",
            f"- **Topics:** {', '.join(paper.topics)}",
            f"- **Why it matched:** {', '.join(paper.reasons) if paper.reasons else 'query match'}",
            f"- **Link:** {paper.url}",
        ]
        if paper.doi:
            lines.append(f"- **DOI:** {paper.doi}")
        if paper.abstract:
            lines += ["", first_sentences(paper.abstract), ""]
        else:
            lines.append("")
    return "\n".join(lines)


def render_readme_section(date: dt.date, papers: list[Paper], config: dict, library: dict) -> str:
    generated = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    all_papers = library_papers(library)
    lines = [
        README_START,
        "## Latest Recommendations",
        "",
        f"Updated: **{date.isoformat()}** (`{generated}`)",
        "",
    ]
    if not papers:
        lines += [
            "No high-confidence papers were found in the latest search window.",
            "",
            "Tune `config/topics.json` to broaden or narrow the radar.",
            "",
        ]
    else:
        lines += [
            "| # | Paper | Source | Topics | Score |",
            "|---|---|---|---|---:|",
        ]
        for idx, paper in enumerate(papers, 1):
            title = paper.title.replace("|", "\\|")
            source = f"{paper.source}<br>{paper.published or 'n/a'}"
            topics = ", ".join(paper.topics).replace("|", "\\|")
            link = paper.url or (f"https://doi.org/{paper.doi}" if paper.doi else "")
            linked_title = f"[{title}]({link})" if link else title
            lines.append(f"| {idx} | {linked_title}<br><sub>{format_authors(paper.authors)}</sub> | {source} | {topics} | {paper.score} |")

    lines += ["", "### By Topic", ""]
    topic_map: dict[str, list[Paper]] = {}
    for paper in all_papers:
        for topic in paper.topics:
            topic_map.setdefault(topic, []).append(paper)
    for topic in sorted(topic_map):
        lines.append(f"#### {topic}")
        lines.append("")
        for paper in topic_map[topic]:
            link = paper.url or (f"https://doi.org/{paper.doi}" if paper.doi else "")
            title = f"[{paper.title}]({link})" if link else paper.title
            lines.append(f"- {title} ({paper.source}, {paper.published or 'n/a'})")
        lines.append("")

    lines += ["### All Recommended Papers", ""]
    by_seen: dict[str, list[Paper]] = {}
    records = library.get("papers", {})
    for paper in all_papers:
        first_seen = records.get(paper.key, {}).get("first_seen", "unknown")
        by_seen.setdefault(first_seen, []).append(paper)
    for first_seen in sorted(by_seen, reverse=True):
        lines.append(f"#### {first_seen}")
        lines.append("")
        for paper in sorted(by_seen[first_seen], key=lambda p: (p.score, p.published), reverse=True):
            link = paper.url or (f"https://doi.org/{paper.doi}" if paper.doi else "")
            title = f"[{paper.title}]({link})" if link else paper.title
            topics = ", ".join(paper.topics)
            lines.append(f"- {title} ({paper.source}, {paper.published or 'n/a'}; {topics}; score {paper.score})")
        lines.append("")

    lines += [
        "### Archive",
        "",
        f"- [Daily report for {date.isoformat()}](outputs/daily/{date.isoformat()}.md)",
        "- [Latest report](outputs/latest.md)",
        "",
        README_END,
    ]
    return "\n".join(lines)


def update_readme(readme_path: Path, section: str) -> None:
    if readme_path.exists():
        text = readme_path.read_text(encoding="utf-8")
    else:
        text = "# Protein Design Paper Radar\n\n"
    if README_START in text and README_END in text:
        pattern = re.compile(
            rf"{re.escape(README_START)}.*?{re.escape(README_END)}",
            flags=re.DOTALL,
        )
        updated = pattern.sub(section, text)
    else:
        updated = text.rstrip() + "\n\n" + section + "\n"
    readme_path.write_text(updated, encoding="utf-8")


def collect(config: dict, target_date: dt.date, days_back: int) -> list[Paper]:
    start = target_date - dt.timedelta(days=days_back)
    end = target_date
    max_results = int(config.get("max_results_per_source", 80))
    queries = config["queries"]
    papers: list[Paper] = []
    papers.extend(arxiv_query(queries, max_results))
    papers.extend(preprint_query("biorxiv", start, end, max_results))
    papers.extend(preprint_query("medrxiv", start, end, max_results))
    papers.extend(pubmed_query(queries, start, end, max_results))
    return [score_paper(p, config) for p in dedupe(papers)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY)
    parser.add_argument("--out", type=Path, default=ROOT / "outputs" / "daily")
    parser.add_argument("--date", default=dt.date.today().isoformat())
    parser.add_argument("--days-back", type=int, default=2)
    parser.add_argument("--include-seen", action="store_true")
    parser.add_argument("--readme", type=Path, default=ROOT / "README.md")
    parser.add_argument("--skip-readme", action="store_true")
    args = parser.parse_args()

    target_date = dt.date.fromisoformat(args.date)
    config = load_json(args.config, {})
    state = load_json(args.state, {"seen": {}})
    library = load_json(args.library, {"papers": {}})
    seen = state.setdefault("seen", {})

    papers = collect(config, target_date, args.days_back)
    for paper in papers:
        paper.is_new = paper.key not in seen

    min_score = int(config.get("min_score", 6))
    report_limit = int(config.get("report_limit", 25))
    eligible = [p for p in papers if p.score >= min_score]
    ranked = sorted(
        [p for p in eligible if args.include_seen or p.is_new],
        key=lambda p: (p.score, p.published),
        reverse=True,
    )[:report_limit]
    readme_ranked = sorted(
        eligible,
        key=lambda p: (p.score, p.published),
        reverse=True,
    )[:report_limit]
    library = update_library(library, eligible, target_date)

    for paper in ranked:
        seen[paper.key] = {
            "title": paper.title,
            "source": paper.source,
            "url": paper.url,
            "first_seen": target_date.isoformat(),
            "score": paper.score,
        }

    report = render_report(target_date, ranked, config)
    args.out.mkdir(parents=True, exist_ok=True)
    report_path = args.out / f"{target_date.isoformat()}.md"
    report_path.write_text(report, encoding="utf-8")
    latest_path = ROOT / "outputs" / "latest.md"
    latest_path.write_text(report, encoding="utf-8")
    if not args.skip_readme:
        update_readme(args.readme, render_readme_section(target_date, readme_ranked, config, library))
    save_json(args.state, state)
    save_json(args.library, library)
    print(f"wrote {report_path}")
    print(f"wrote {latest_path}")
    if not args.skip_readme:
        print(f"updated {args.readme}")
    print(f"recommended {len(ranked)} papers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
