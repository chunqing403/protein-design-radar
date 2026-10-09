import tempfile
import unittest
from pathlib import Path

import requests

from scripts.sync_wechat import import_feed_article


class WeChatImportTests(unittest.TestCase):
    def test_creates_retryable_placeholder_when_feed_has_no_body(self):
        source = {
            "url": "https://mp.weixin.qq.com/s/example-token",
            "slug": "caom-example",
            "featured": False,
            "topics": [],
        }
        feed_item = {
            "title": "Example article",
            "published": "2026-10-09",
            "account": "CAOM",
        }
        with tempfile.TemporaryDirectory() as directory:
            content_root = Path(directory)
            article = import_feed_article(requests.Session(), source, content_root, feed_item)
            body = (content_root / article["body_file"]).read_text(encoding="utf-8")

        self.assertTrue(article["incomplete"])
        self.assertEqual("Example article", article["description"])
        self.assertIn("阅读微信公众号原文", body)
        self.assertIn(source["url"], body)


if __name__ == "__main__":
    unittest.main()
