import unittest

from scripts.daily_news import merge_records, parse_feed, relevant


CONFIG = {
    "history_limit": 20,
    "high_relevance_terms": ["protein design", "alphafold"],
    "domain_terms": ["protein", "enzyme"],
    "ai_terms": ["machine learning", " ai "],
    "negative_terms": ["food protein"],
    "blocked_sources": ["Spam News"],
}


class NewsRelevanceTests(unittest.TestCase):
    def test_accepts_high_signal_title(self):
        self.assertTrue(relevant("A new AlphaFold model", "", CONFIG))

    def test_requires_domain_and_ai_for_generic_terms(self):
        self.assertTrue(relevant("Machine learning for enzyme discovery", "", CONFIG))
        self.assertFalse(relevant("Machine learning infrastructure", "", CONFIG))

    def test_rejects_negative_topic(self):
        self.assertFalse(relevant("AI forecasts the food protein market", "", CONFIG))


class FeedParsingTests(unittest.TestCase):
    def test_parses_rss_and_uses_embedded_source(self):
        xml = """<rss><channel><item><title>AI protein design milestone</title>
        <link>https://example.com/story</link><description>Machine learning for proteins.</description>
        <pubDate>Mon, 28 Sep 2026 10:00:00 GMT</pubDate><source>Example News</source>
        </item></channel></rss>"""
        source = {"name": "Google News", "category": "产业动态", "use_embedded_source": True}
        records = parse_feed(xml, source, CONFIG)
        self.assertEqual(1, len(records))
        self.assertEqual("Example News", records[0]["source"])
        self.assertEqual("2026-09-28", records[0]["published"])

    def test_trusted_feed_does_not_require_keywords(self):
        xml = """<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Lab update</title>
        <link href="https://example.com/update"/><updated>2026-09-28T10:00:00Z</updated>
        </entry></feed>"""
        records = parse_feed(xml, {"name": "IPD", "category": "研究机构", "trusted": True}, CONFIG)
        self.assertEqual(1, len(records))

    def test_blocks_low_quality_embedded_source(self):
        xml = """<rss><channel><item><title>AlphaFold market update - Spam News</title>
        <link>https://example.com/spam</link><source>Spam News</source></item></channel></rss>"""
        source = {"name": "Google News", "category": "产业动态", "use_embedded_source": True}
        self.assertEqual([], parse_feed(xml, source, CONFIG))


class NewsMergeTests(unittest.TestCase):
    def test_deduplicates_same_title_across_sources(self):
        collected = [
            {"title": "AlphaFold release", "url": "https://one.example", "source": "One"},
            {"title": "AlphaFold release", "url": "https://two.example", "source": "Two"},
        ]
        merged = merge_records({"items": {}}, collected, CONFIG, "2026-09-29")
        self.assertEqual(1, len(merged["items"]))


if __name__ == "__main__":
    unittest.main()
