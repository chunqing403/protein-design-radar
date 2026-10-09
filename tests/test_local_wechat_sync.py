import unittest
from unittest.mock import Mock

import requests

from scripts.local_wechat_sync import feed_title, find_feed_url


def response(status_code: int, text: str = "") -> Mock:
    value = Mock()
    value.status_code = status_code
    value.text = text
    if status_code >= 400:
        value.raise_for_status.side_effect = requests.HTTPError(str(status_code))
    else:
        value.raise_for_status.return_value = None
    return value


class LocalWeChatSyncTests(unittest.TestCase):
    def test_reads_rss_channel_title(self):
        self.assertEqual("CAOM", feed_title("<rss><channel><title>CAOM</title></channel></rss>"))

    def test_finds_matching_feed_after_missing_ids(self):
        session = Mock()
        session.get.side_effect = [
            response(200, '{"ok": true}'),
            response(404),
            response(200, "<rss><channel><title>CAOM</title></channel></rss>"),
        ]
        found = find_feed_url(
            "http://127.0.0.1:8080",
            "CAOM",
            session=session,
            probe_limit=2,
        )
        self.assertEqual("http://127.0.0.1:8080/feeds/2.xml", found)

    def test_accepts_feed_title_containing_account_name(self):
        session = Mock()
        session.get.side_effect = [
            response(200, '{"ok": true}'),
            response(200, "<rss><channel><title>CAOM - WeChat</title></channel></rss>"),
        ]
        found = find_feed_url(
            "http://127.0.0.1:8080",
            "CAOM",
            session=session,
            probe_limit=1,
        )
        self.assertEqual("http://127.0.0.1:8080/feeds/1.xml", found)


if __name__ == "__main__":
    unittest.main()
