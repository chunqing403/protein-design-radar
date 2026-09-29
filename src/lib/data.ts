import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const ROOT = process.cwd();

export interface Article {
  account: string;
  author: string;
  body_file: string;
  cover: string;
  description: string;
  featured: boolean;
  published: string;
  slug: string;
  source_url: string;
  title: string;
  topics: string[];
}

export interface NewsItem {
  category?: string;
  first_seen?: string;
  published?: string;
  source?: string;
  summary?: string;
  title: string;
  url?: string;
}

export interface Paper {
  doi?: string;
  first_seen?: string;
  published?: string;
  source?: string;
  title: string;
  topics?: string[];
  url?: string;
}

interface TopicConfig {
  paper_category_order?: string[];
  paper_category_labels?: Record<string, string>;
}

interface NewsConfig {
  category_order?: string[];
}

function readJson<T>(relativePath: string): T {
  return JSON.parse(readFileSync(resolve(ROOT, relativePath), "utf8")) as T;
}

export function getArticles(): Article[] {
  const data = readJson<{ articles: Article[] }>("site/content/articles.json");
  return [...data.articles].sort((a, b) => b.published.localeCompare(a.published));
}

export function getNews(): NewsItem[] {
  const data = readJson<{ items: Record<string, NewsItem> }>("data/news.json");
  return Object.values(data.items).sort((a, b) =>
    `${b.published ?? ""}${b.first_seen ?? ""}${b.title}`.localeCompare(
      `${a.published ?? ""}${a.first_seen ?? ""}${a.title}`
    )
  );
}

export function getPapers(): Paper[] {
  const data = readJson<{ papers: Record<string, Paper> }>("data/papers.json");
  return Object.values(data.papers).sort((a, b) =>
    `${b.first_seen ?? ""}${b.published ?? ""}${b.title}`.localeCompare(
      `${a.first_seen ?? ""}${a.published ?? ""}${a.title}`
    )
  );
}

export function getPaperConfig(): TopicConfig {
  return readJson<TopicConfig>("config/topics.json");
}

export function getNewsConfig(): NewsConfig {
  return readJson<NewsConfig>("config/news_sources.json");
}

export function readArticleBody(article: Article): string {
  return readFileSync(resolve(ROOT, "site", "content", article.body_file), "utf8");
}

export function paperUrl(paper: Paper): string {
  return paper.url || (paper.doi ? `https://doi.org/${paper.doi}` : "");
}

export function groupNews(news: NewsItem[], order: string[] = []): Map<string, NewsItem[]> {
  const grouped = new Map<string, NewsItem[]>(order.map((category) => [category, []]));
  for (const item of news) {
    const category = item.category || "综合资讯";
    grouped.set(category, [...(grouped.get(category) || []), item]);
  }
  return new Map([...grouped].filter(([, items]) => items.length));
}

export function groupPapers(papers: Paper[], order: string[] = []): Map<string, Paper[]> {
  const grouped = new Map<string, Paper[]>(order.map((category) => [category, []]));
  for (const paper of papers) {
    const category = paper.topics?.find((topic) => grouped.has(topic)) || "General";
    grouped.set(category, [...(grouped.get(category) || []), paper]);
  }
  return new Map([...grouped].filter(([, items]) => items.length));
}
