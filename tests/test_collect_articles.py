import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import collect_articles as collector


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.config = {"accounts": ["山东高法", "上海一中法院"], "fetch": {"hours": 24}}
        self.article = {"title": "离线测试文章", "url": "https://example.com/test",
                        "publish_time": datetime.now(timezone.utc).isoformat()}

    def test_smoke_checks_every_account_without_reading_bodies(self):
        with patch.object(collector.auth, "load_token", return_value={}), \
             patch.object(collector.auth, "is_token_valid", return_value=True), \
             patch.object(collector.fetcher, "get_fakeid", return_value="offline-id"), \
             patch.object(collector.fetcher, "get_recent_articles", return_value=[self.article]) as metadata, \
             patch.object(collector.fetcher, "get_article_content") as body:
            payload = collector.collect(self.config, smoke=True)
        self.assertEqual(metadata.call_count, 2)
        self.assertEqual(len(payload["accounts"]), 2)
        self.assertEqual(payload["articles"], [])
        body.assert_not_called()

    def test_full_collection_preserves_sources_and_removes_duplicates(self):
        with patch.object(collector.auth, "load_token", return_value={}), \
             patch.object(collector.auth, "is_token_valid", return_value=True), \
             patch.object(collector.fetcher, "get_fakeid", return_value="offline-id"), \
             patch.object(collector.fetcher, "get_recent_articles", return_value=[self.article]), \
             patch.object(collector.fetcher, "get_article_content", return_value={"text": "虚构测试正文"}) as body:
            payload = collector.collect(self.config)
        body.assert_called_once()
        self.assertEqual(payload["articles"][0]["text"], "虚构测试正文")
        self.assertEqual(payload["articles"][0]["url"], self.article["url"])
        with tempfile.TemporaryDirectory() as folder:
            output = collector.save_sources(payload, Path(folder))
            self.assertEqual(json.loads(output.read_text()), payload)

    def test_old_metadata_verifies_access_but_does_not_become_todays_article(self):
        old = {**self.article, "publish_time": (datetime.now(timezone.utc)-timedelta(days=3)).isoformat()}
        with patch.object(collector.auth, "load_token", return_value={}), \
             patch.object(collector.auth, "is_token_valid", return_value=True), \
             patch.object(collector.fetcher, "get_fakeid", return_value="offline-id"), \
             patch.object(collector.fetcher, "get_recent_articles", return_value=[old]), \
             patch.object(collector.fetcher, "get_article_content") as body:
            self.assertEqual(collector.collect(self.config)["articles"], [])
        body.assert_not_called()

    def test_invalid_token_and_unverified_empty_metadata_fail(self):
        with patch.object(collector.auth, "load_token", return_value=None):
            with self.assertRaisesRegex(ValueError, "登录"):
                collector.collect(self.config)
        with patch.object(collector.auth, "load_token", return_value={}), \
             patch.object(collector.auth, "is_token_valid", return_value=True), \
             patch.object(collector.fetcher, "get_fakeid", return_value="offline-id"), \
             patch.object(collector.fetcher, "get_recent_articles", return_value=[]):
            with self.assertRaisesRegex(ValueError, "尚不能确认"):
                collector.collect(self.config)


if __name__ == "__main__":
    unittest.main()
