import unittest
from unittest.mock import Mock, patch

import requests

from scripts.discover_wechat import (
    add_links,
    article_identity,
    extract_feed_items,
    extract_feed_links,
    fetch_feed,
    slug_for_url,
)


FULL_URL = (
    "https://mp.weixin.qq.com/s?__biz=Mzk0NDgyNDA0NQ=="
    "&mid=2247485000&idx=1&sn=abc123#wechat_redirect"
)


class WeChatFeedTests(unittest.TestCase):
    def test_extracts_wechat_links_from_rss_and_atom(self):
        rss = f"<rss><channel><item><link>{FULL_URL.replace('&', '&amp;')}</link></item></channel></rss>"
        atom = """<feed xmlns="http://www.w3.org/2005/Atom"><entry>
        <link href="https://mp.weixin.qq.com/s/new-article" />
        </entry></feed>"""
        self.assertEqual([FULL_URL.removesuffix("#wechat_redirect")], extract_feed_links(rss))
        self.assertEqual(["https://mp.weixin.qq.com/s/new-article"], extract_feed_links(atom))

    def test_ignores_non_wechat_links(self):
        rss = "<rss><channel><item><link>https://example.com/post</link></item></channel></rss>"
        self.assertEqual([], extract_feed_links(rss))

    def test_preserves_feed_metadata_for_fetch_fallback(self):
        rss = f"""<rss><channel><title>CAOM</title><item>
        <title>New protein design article</title>
        <link>{FULL_URL.replace('&', '&amp;')}</link>
        <description><![CDATA[<p>Article summary</p>]]></description>
        <pubDate>Thu, 08 Oct 2026 08:00:00 +0800</pubDate>
        </item></channel></rss>"""
        item = extract_feed_items(rss)[0]
        self.assertEqual("CAOM", item["account"])
        self.assertEqual("New protein design article", item["title"])
        self.assertEqual("2026-10-08", item["published"])
        self.assertIn("Article summary", item["description"])

    def test_deduplicates_rotating_query_parameters_by_mid(self):
        first = FULL_URL
        second = FULL_URL.replace("sn=abc123", "sn=changed").replace("#wechat_redirect", "&scene=1")
        self.assertEqual(article_identity(first), article_identity(second))
        sources = [{"url": first, "slug": "caom-2247485000"}]
        self.assertEqual([], add_links(sources, [second], prefix="caom"))

    def test_builds_stable_slug_for_primary_and_secondary_articles(self):
        self.assertEqual("caom-2247485000", slug_for_url(FULL_URL))
        self.assertEqual("caom-2247485000-2", slug_for_url(FULL_URL.replace("idx=1", "idx=2")))

    @patch("scripts.discover_wechat.time.sleep")
    @patch("scripts.discover_wechat.requests.get")
    def test_retries_feed_until_rsshub_is_ready(self, mock_get, mock_sleep):
        failed = Mock()
        failed.raise_for_status.side_effect = requests.HTTPError("starting")
        ready = Mock()
        ready.raise_for_status.return_value = None
        ready.text = "<rss />"
        mock_get.side_effect = [failed, ready]

        self.assertEqual("<rss />", fetch_feed("http://127.0.0.1:1200/feed"))
        mock_sleep.assert_called_once_with(10)


if __name__ == "__main__":
    unittest.main()
