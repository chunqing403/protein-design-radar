#!/usr/bin/env python3
"""Build the CAOM editorial site and paper library as static HTML."""

from __future__ import annotations

import argparse
import html
import json
import shutil
from collections import OrderedDict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTENT = ROOT / "site" / "content"
DEFAULT_OUTPUT = ROOT / "docs"
DEFAULT_PAPERS = ROOT / "data" / "papers.json"
DEFAULT_NEWS = ROOT / "data" / "news.json"
DEFAULT_CONFIG = ROOT / "config" / "topics.json"
DEFAULT_NEWS_CONFIG = ROOT / "config" / "news_sources.json"


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def page_shell(title: str, description: str, body: str, prefix: str = "", active: str = "", body_class: str = "") -> str:
    nav_items = [
        ("首页", f"{prefix}index.html", "home"),
        ("文章", f"{prefix}articles.html", "articles"),
        ("资讯", f"{prefix}news.html", "news"),
        ("每日论文", f"{prefix}papers.html", "papers"),
        ("关于", f"{prefix}index.html#about", "about"),
    ]
    nav = "".join(
        f'<a href="{href}" class="{"active" if key == active else ""}">{label}</a>'
        for label, href, key in nav_items
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{esc(description)}">
  <title>{esc(title)}</title>
  <link rel="icon" type="image/svg+xml" href="{prefix}assets/favicon.svg">
  <link rel="stylesheet" href="{prefix}assets/styles.css">
</head>
<body class="{esc(body_class)}">
  <header class="site-header">
    <a class="brand" href="{prefix}index.html" aria-label="CAOM 首页">
      <span class="brand-mark">C</span>
      <span><strong>CAOM</strong><small>AI × Protein Design Notes</small></span>
    </a>
    <nav aria-label="主导航">{nav}</nav>
  </header>
  <main>{body}</main>
  <footer class="site-footer">
    <strong>CAOM</strong>
    <span>公众号文章、行业资讯与蛋白设计前沿论文的独立归档。</span>
  </footer>
</body>
</html>
"""


def article_href(article: dict, prefix: str = "") -> str:
    return f"{prefix}articles/{esc(article['slug'])}.html"


def topic_tags(topics: list[str]) -> str:
    return "".join(f'<span class="tag">{esc(topic)}</span>' for topic in topics)


def article_row(article: dict, prefix: str = "") -> str:
    return f"""
<article class="story-row">
  <div class="story-meta"><span>{esc(article.get('published'))}</span><span>{esc(article.get('author'))}</span></div>
  <div>
    <div class="tag-row">{topic_tags(article.get('topics', []))}</div>
    <h3><a href="{article_href(article, prefix)}">{esc(article.get('title'))}</a></h3>
    <p>{esc(article.get('description'))}</p>
  </div>
  <a class="arrow-link" href="{article_href(article, prefix)}" aria-label="阅读文章">↗</a>
</article>"""


def paper_link(record: dict) -> str:
    return record.get("url") or (f"https://doi.org/{record['doi']}" if record.get("doi") else "")


def paper_row(record: dict) -> str:
    link = paper_link(record)
    title = esc(record.get("title"))
    linked_title = f'<a href="{esc(link)}" target="_blank" rel="noopener noreferrer">{title}</a>' if link else title
    topics = topic_tags(record.get("topics", []))
    return f"""
<article class="paper-row">
  <div class="paper-date">{esc(record.get('first_seen'))}</div>
  <div>
    <h3>{linked_title}</h3>
    <p>{esc(record.get('source'))} · {esc(record.get('published') or '日期未知')}</p>
    <div class="tag-row">{topics}</div>
  </div>
</article>"""


def news_row(record: dict) -> str:
    title = esc(record.get("title"))
    link = esc(record.get("url"))
    linked_title = f'<a href="{link}" target="_blank" rel="noopener noreferrer">{title}</a>' if link else title
    return f"""
<article class="news-row">
  <div class="news-date">{esc(record.get('published') or record.get('first_seen'))}</div>
  <div>
    <div class="news-source"><span>{esc(record.get('category'))}</span>{esc(record.get('source'))}</div>
    <h3>{linked_title}</h3>
    <p>{esc(record.get('summary'))}</p>
  </div>
  <a class="arrow-link" href="{link}" target="_blank" rel="noopener noreferrer" aria-label="查看资讯原文">↗</a>
</article>"""


def news_brief(record: dict) -> str:
    return f"""
<article class="brief-row">
  <div><span>{esc(record.get('source'))}</span><time>{esc(record.get('published') or record.get('first_seen'))}</time></div>
  <h3><a href="{esc(record.get('url'))}" target="_blank" rel="noopener noreferrer">{esc(record.get('title'))}</a></h3>
</article>"""


def home_article_card(article: dict) -> str:
    return f"""
<article class="magazine-story">
  <div><time>{esc(article.get('published'))}</time><span>{esc((article.get('topics') or ['CAOM'])[0])}</span></div>
  <h3><a href="{article_href(article)}">{esc(article.get('title'))}</a></h3>
  <p>{esc(article.get('description'))}</p>
</article>"""


def sorted_papers(library: dict) -> list[dict]:
    return sorted(
        library.get("papers", {}).values(),
        key=lambda record: (record.get("first_seen", ""), record.get("published", ""), record.get("title", "")),
        reverse=True,
    )


def sorted_news(library: dict) -> list[dict]:
    return sorted(
        library.get("items", {}).values(),
        key=lambda record: (record.get("published", ""), record.get("first_seen", ""), record.get("title", "")),
        reverse=True,
    )


def build_home(articles: list[dict], news: list[dict], papers: list[dict], news_config: dict) -> str:
    featured = next((article for article in articles if article.get("featured")), articles[0])
    cover = featured.get("cover", "")
    hero_style = f' style="background-image: url(\'{esc(cover)}\')"' if cover else ""
    latest_articles = [item for item in articles if item.get("slug") != featured.get("slug")][:6]
    latest_stories = "".join(home_article_card(article) for article in latest_articles)
    latest_news = "".join(news_brief(item) for item in news[:8])
    latest_papers = "".join(paper_row(paper) for paper in papers[:6])
    return f"""
<div class="magazine-home">
<section class="magazine-hero"{hero_style}>
  <div class="magazine-hero-shade"></div>
  <div class="magazine-hero-copy">
    <span class="magazine-kicker">Independent notes on AI and protein design</span>
    <h1>CAOM</h1>
    <p>追踪生成式生物学、蛋白质设计模型与实验验证。</p>
    <a href="{article_href(featured)}"><small>本期头条</small><strong>{esc(featured.get('title'))}</strong><span>阅读全文 →</span></a>
  </div>
</section>
<section class="edition-strip">
  <div><span>ESSAYS</span><strong>{len(articles)}</strong><small>公众号文章</small></div>
  <div><span>SIGNALS</span><strong>{len(news)}</strong><small>行业资讯</small></div>
  <div><span>RESEARCH</span><strong>{len(papers)}</strong><small>精选论文</small></div>
  <p>每日 08:20 更新</p>
</section>
<section class="magazine-feature">
  <div class="magazine-section-head"><span>Featured</span><a href="articles.html">全部文章 →</a></div>
  <div class="feature-layout">
    <a class="feature-image" href="{article_href(featured)}"{hero_style} aria-label="阅读本期精选文章"></a>
    <article>
      <div class="feature-meta">{esc((featured.get('topics') or ['CAOM'])[0])} · {esc(featured.get('published'))}</div>
      <h2><a href="{article_href(featured)}">{esc(featured.get('title'))}</a></h2>
      <p>{esc(featured.get('description'))}</p>
      <a class="editorial-link" href="{article_href(featured)}">继续阅读 →</a>
    </article>
  </div>
</section>
<section class="magazine-columns">
  <section class="writing-column">
    <div class="magazine-section-head"><span>Latest writing</span><a href="articles.html">文章归档 →</a></div>
    <div class="magazine-story-list">{latest_stories}</div>
  </section>
  <aside class="signal-column">
    <div class="magazine-section-head"><span>Signals now</span><a href="news.html">全部资讯 →</a></div>
    <div class="brief-list">{latest_news}</div>
    <p class="signal-attribution">来源包括研究机构、产业媒体与 GitHub Releases</p>
  </aside>
</section>
<section class="research-section">
  <div class="magazine-section-head"><span>Paper radar</span><a href="papers.html">完整文献库 →</a></div>
  <div class="paper-list">{latest_papers}</div>
</section>
<section class="magazine-about" id="about">
  <div><span>Editorial scope</span><h2>我们在追踪什么</h2></div>
  <p>从模型发布到湿实验结果，记录蛋白设计领域真正值得继续关注的论文、工具和产业变化。</p>
  <a href="articles.html">阅读中文解读 →</a>
</section>
</div>"""


def build_news_page(news: list[dict], config: dict) -> str:
    order = config.get("category_order", [])
    grouped: OrderedDict[str, list[dict]] = OrderedDict((category, []) for category in order)
    for item in news:
        grouped.setdefault(item.get("category") or "综合资讯", []).append(item)
    directory = "".join(
        f'<a href="#{esc(category)}"><span>{esc(category)}</span><strong>{len(items)}</strong></a>'
        for category, items in grouped.items()
        if items
    )
    sections = "".join(
        f'<section class="news-category" id="{esc(category)}"><div class="category-heading"><h2>{esc(category)}</h2><span>{len(items)} 条</span></div><div class="news-list">{"".join(news_row(item) for item in items)}</div></section>'
        for category, items in grouped.items()
        if items
    )
    return f"""
<section class="archive-header">
  <div><span class="eyebrow dark">Industry Radar</span><h1>行业资讯</h1></div>
  <p>来自蛋白设计实验室、模型工具、产业媒体和开源项目的每日信号。保留来源，直达原文。</p>
</section>
<div class="news-browser">
  <aside class="news-sidebar"><div><span class="sidebar-label">浏览目录</span><nav aria-label="资讯分类目录">{directory}</nav><p>共 {len(news)} 条，经领域与来源质量过滤。</p></div></aside>
  <div class="news-categories">{sections}</div>
</div>"""


def build_articles_page(articles: list[dict]) -> str:
    rows = "".join(article_row(article) for article in articles)
    return f"""
<section class="page-intro"><span class="eyebrow dark">Archive</span><h1>公众号文章</h1><p>CAOM 的独立网页归档。正文和图片保存在本站，同时保留微信原文入口。</p></section>
<section class="section-band compact"><div class="story-list">{rows}</div></section>"""


def build_papers_page(papers: list[dict], config: dict) -> str:
    order = config.get("paper_category_order", [])
    labels = config.get("paper_category_labels", {})
    grouped: OrderedDict[str, list[dict]] = OrderedDict((category, []) for category in order)
    for paper in papers:
        category = next((topic for topic in paper.get("topics", []) if topic in grouped), "General")
        grouped.setdefault(category, []).append(paper)
    directory = "".join(
        f'<a href="#{esc(category.lower().replace(" ", "-"))}"><span>{esc(labels.get(category, category))}</span><strong>{len(items)}</strong></a>'
        for category, items in grouped.items()
        if items
    )
    sections = "".join(
        f'<section class="paper-category" id="{esc(category.lower().replace(" ", "-"))}"><div class="category-heading"><h2>{esc(labels.get(category, category))}</h2><span>{len(items)} 篇</span></div><div class="paper-list">{"".join(paper_row(item) for item in items)}</div></section>'
        for category, items in grouped.items()
        if items
    )
    return f"""
<section class="page-intro"><span class="eyebrow dark">Research Library</span><h1>每日论文</h1><p>自动收集并按研究方向归档的 AI 蛋白设计文献。站内不公开相关性评分。</p></section>
<nav class="paper-directory" aria-label="文献分类目录">{directory}</nav>
<div class="paper-categories">{sections}</div>"""


def build_article_page(article: dict, body_html: str) -> str:
    cover = f'<img class="article-cover" src="../{esc(article.get("cover"))}" alt="{esc(article.get("title"))}">' if article.get("cover") else ""
    return f"""
<article class="article-page">
  <header class="article-header">
    <div class="tag-row">{topic_tags(article.get('topics', []))}</div>
    <h1>{esc(article.get('title'))}</h1>
    <p class="article-deck">{esc(article.get('description'))}</p>
    <div class="article-meta">{esc(article.get('account'))} · {esc(article.get('author'))} · {esc(article.get('published'))}</div>
  </header>
  {cover}
  <div class="article-layout">
    <aside><span>来源</span><a href="{esc(article.get('source_url'))}" target="_blank" rel="noopener noreferrer">微信原文 ↗</a></aside>
    <div class="article-body">{body_html}</div>
  </div>
</article>"""


def copy_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    if source.exists():
        shutil.copytree(source, destination)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--content", type=Path, default=DEFAULT_CONTENT)
    parser.add_argument("--papers", type=Path, default=DEFAULT_PAPERS)
    parser.add_argument("--news", type=Path, default=DEFAULT_NEWS)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--news-config", type=Path, default=DEFAULT_NEWS_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    manifest = load_json(args.content / "articles.json", {"articles": []})
    articles = manifest.get("articles", [])
    if not articles:
        raise RuntimeError("no imported WeChat articles; run scripts/sync_wechat.py first")
    papers = sorted_papers(load_json(args.papers, {"papers": {}}))
    news = sorted_news(load_json(args.news, {"items": {}}))
    config = load_json(args.config, {})
    news_config = load_json(args.news_config, {})

    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "articles").mkdir(parents=True, exist_ok=True)
    (args.output / "assets").mkdir(parents=True, exist_ok=True)
    copy_tree(args.content / "assets" / "wechat", args.output / "assets" / "wechat")
    shutil.copy2(ROOT / "site" / "static" / "styles.css", args.output / "assets" / "styles.css")
    shutil.copy2(ROOT / "site" / "static" / "favicon.svg", args.output / "assets" / "favicon.svg")

    (args.output / "index.html").write_text(
        page_shell("CAOM · AI × Protein Design Notes", "CAOM 公众号文章、行业资讯与蛋白设计论文索引。", build_home(articles, news, papers, news_config), active="home", body_class="home-shell"),
        encoding="utf-8",
    )
    (args.output / "articles.html").write_text(
        page_shell("公众号文章 · CAOM", "CAOM 公众号文章归档。", build_articles_page(articles), active="articles"),
        encoding="utf-8",
    )
    (args.output / "news.html").write_text(
        page_shell("行业资讯 · CAOM", "AI 蛋白设计行业资讯与工具动态。", build_news_page(news, news_config), active="news"),
        encoding="utf-8",
    )
    (args.output / "papers.html").write_text(
        page_shell("每日论文 · CAOM", "AI 蛋白设计每日论文与分类索引。", build_papers_page(papers, config), active="papers"),
        encoding="utf-8",
    )
    for article in articles:
        body_html = (args.content / article["body_file"]).read_text(encoding="utf-8")
        page = page_shell(
            f"{article['title']} · CAOM",
            article.get("description", ""),
            build_article_page(article, body_html),
            prefix="../",
            active="articles",
        )
        (args.output / "articles" / f"{article['slug']}.html").write_text(page, encoding="utf-8")

    (args.output / ".nojekyll").write_text("", encoding="utf-8")
    print(f"built site with {len(articles)} articles, {len(news)} news items, and {len(papers)} papers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
