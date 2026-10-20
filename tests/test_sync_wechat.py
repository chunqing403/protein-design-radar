import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from scripts.sync_wechat import import_article, import_feed_article


class WeChatImportTests(unittest.TestCase):
    @patch("scripts.sync_wechat.download_image")
    @patch("scripts.sync_wechat.fetch")
    def test_uses_first_body_image_when_cover_download_fails(self, mock_fetch, mock_download):
        html = """
        <html><head>
          <meta property="og:title" content="Example article">
          <meta property="og:image" content="https://mmbiz.qpic.cn/cover.jpg">
        </head><body>
          <div id="js_content"><p>Body</p><img data-src="https://mmbiz.qpic.cn/body.png"></div>
          <strong id="js_name">CAOM</strong><span id="js_author_name">ZCQ</span>
          <script>var ori_create_time = "1792368000";</script>
        </body></html>
        """
        mock_fetch.return_value.content = html.encode("utf-8")

        def download(_session, _url, destination):
            if destination.name == "cover":
                raise requests.RequestException("cover unavailable")
            image_path = destination.with_suffix(".png")
            image_path.write_bytes(b"image")
            return image_path

        mock_download.side_effect = download
        source = {
            "url": "https://mp.weixin.qq.com/s/example-token",
            "slug": "caom-example",
            "featured": True,
            "topics": ["蛋白设计"],
        }

        with tempfile.TemporaryDirectory() as directory:
            article = import_article(requests.Session(), source, Path(directory))

        self.assertEqual("assets/wechat/caom-example/image-01.png", article["cover"])

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
