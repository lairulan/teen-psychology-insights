#!/usr/bin/env python3
import unittest
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import auto_publish as ap


def record(title, family_text=None, days_ago=1, category=""):
    family = ap.detect_content_family(family_text or title)
    return {
        "file": "article_test.md",
        "title": title,
        "date": datetime.now() - timedelta(days=days_ago),
        "column": "",
        "category": category,
        "source": "",
        "hot_ref": "",
        "topic_family": family[1] if family else "",
        "family": family,
    }


class ContentGuardTests(unittest.TestCase):
    def test_exact_duplicate_title_is_rejected(self):
        history = [record("当孩子说“我讨厌学习”时，他真正想说的是什么？")]
        reason = ap._topic_rejection_reason(
            "当孩子说我讨厌学习时，他真正想说的是什么",
            recent_history=history,
        )
        self.assertIn("近30天标题", reason)

    def test_school_refusal_family_cooldown_is_rejected(self):
        history = [record("“不想上学”这句话背后，可能藏着一个在保护自己的孩子")]
        reason = ap._topic_rejection_reason(
            "孩子说不想上学，父母第一句话很重要",
            recent_history=history,
        )
        self.assertIn("厌学/不想上学", reason)

    def test_generic_title_is_blocked(self):
        issue = ap._title_quality_issue("今天微博热搜那个话题，看得我心里一紧", recent_history=[])
        self.assertIn("标题过泛", issue)

    def test_unverified_research_language_is_blocked(self):
        profile = ap.PUBLISH_PROFILES["women_growth"]
        article = {
            "title": "关系里总是先道歉的人，心里可能藏着害怕",
            "content": "# 关系里总是先道歉的人，心里可能藏着害怕\n\n研究发现，80%的人都会这样。\n\n<!-- IMG_PLACEHOLDER_1 -->\n\n你可以问自己：我在害怕什么？\n\n你可以问自己：我真正想保护什么？\n\n**1. 小练习：** 先写下来。\n\n<!-- IMG_PLACEHOLDER_2 -->",
            "word_count": 900,
        }
        issues = ap.validate_article_output(
            article,
            {"profile": profile},
            recent_history=[],
        )
        self.assertTrue(any("未核验" in issue for issue in issues))

    def test_parenting_article_requires_practice_template(self):
        profile = ap.PUBLISH_PROFILES["parenting"]
        article = {
            "title": "孩子顶嘴时，父母先稳住关系",
            "content": "# 孩子顶嘴时，父母先稳住关系\n\n这是一篇文章。\n\n<!-- IMG_PLACEHOLDER_1 -->\n\n**1. 先接住感受：** 我理解你现在很烦。\n\n<!-- IMG_PLACEHOLDER_2 -->",
            "word_count": 900,
        }
        issues = ap.validate_article_output(
            article,
            {"profile": profile},
            recent_history=[],
        )
        self.assertTrue(any("可以换成" in issue for issue in issues))
        self.assertTrue(any("30秒" in issue for issue in issues))

    def test_fallback_topic_skips_recent_family(self):
        profile = ap.PUBLISH_PROFILES["parenting"]
        history = [
            record("孩子焦虑时，家长的稳是最好的解药"),
            record("孩子说不想上学时，可能是在偷偷保护自己"),
        ]
        topic = ap.choose_fallback_profile_topic(
            profile,
            recent_titles=[item["title"] for item in history],
            recent_history=history,
        )
        self.assertIsNotNone(topic)
        self.assertNotIn("不想上学", topic["topic"])


if __name__ == "__main__":
    unittest.main()
