"""Offline checks: no WeChat, AI API, email or push requests."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fetcher
from knowledge_cards import generate_card, write_cards


class KnowledgeCardTests(unittest.TestCase):
    def setUp(self):
        self.article = {"title": "离线测试材料", "url": "https://example.com/article",
                        "account_name": "测试公众号"}
        self.source = "此处是用于离线验证的虚构测试材料，不代表真实裁判规则或法律意见。"
        self.answer = {"eligible": True, "point": "测试知识", "scenario": "测试场景",
                       "conditions": "测试条件", "checklist": "测试核对",
                       "to_verify": "测试材料，无真实法律结论", "evidence": self.source}

    def test_preserves_source_and_warns_about_truncation(self):
        with patch("knowledge_cards._call_ai_raw", return_value=json.dumps(self.answer)) as ai:
            card = generate_card(self.article, self.source + "全文后续内容", {
                "knowledge_cards": {"max_content_length": len(self.source)}})
        self.assertEqual(card["url"], self.article["url"])
        self.assertTrue(card["source_truncated"])
        self.assertEqual(ai.call_args.kwargs["max_tokens"], 1800)
        with tempfile.TemporaryDirectory() as tmp:
            md, data = write_cards([card], Path(tmp))
            self.assertIn("待核实事项", md.read_text())
            self.assertIn("请补读全文", md.read_text())
            self.assertEqual(json.loads(data.read_text())["cards"][0]["url"], self.article["url"])

    def test_rejects_fabricated_evidence_and_invalid_ai_response(self):
        for response in ("", "not json", "[]", '{"eligible": "false"}',
                         json.dumps({**self.answer, "evidence": "伪造依据并不来自文章原文" * 2}),
                         json.dumps({**self.answer, "conditions": ""})):
            with self.subTest(response=response):
                with patch("knowledge_cards._call_ai_raw", return_value=response):
                    with self.assertRaises((ValueError, TypeError)):
                        generate_card(self.article, self.source, {})

    def test_non_knowledge_articles_do_not_become_cards(self):
        with patch("knowledge_cards._call_ai_raw", return_value=json.dumps({
            "eligible": False, "skip_reason": "活动通知"})):
            card = generate_card(self.article, self.source, {})
        with tempfile.TemporaryDirectory() as tmp:
            md, _ = write_cards([card], Path(tmp))
            self.assertIn("本次没有可生成的知识卡", md.read_text())
            self.assertNotIn("**核心知识**", md.read_text())

    def test_does_not_silently_select_a_different_account(self):
        with patch.object(fetcher, "_load_fakeid_cache", return_value={}), \
             patch.object(fetcher, "load_token", return_value={"token": "offline-test"}), \
             patch.object(fetcher, "_get", return_value={"list": [
                 {"nickname": "相似名字", "fakeid": "wrong-account"}]}), \
             patch.object(fetcher, "_save_fakeid_cache") as save:
            self.assertIsNone(fetcher.get_fakeid("指定账号"))
            save.assert_not_called()

    def test_account_name_matching_ignores_case_and_spaces(self):
        with patch.object(fetcher, "_load_fakeid_cache", return_value={}), \
             patch.object(fetcher, "load_token", return_value={"token": "offline-test"}), \
             patch.object(fetcher, "_get", return_value={"list": [
                 {"nickname": "iCourt 法秀", "fakeid": "right-account"}]}), \
             patch.object(fetcher, "_save_fakeid_cache"):
            self.assertEqual(fetcher.get_fakeid("icourt法秀"), "right-account")


if __name__ == "__main__":
    unittest.main()
