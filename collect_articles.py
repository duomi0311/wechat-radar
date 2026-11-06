"""Collect article sources for ChatGPT/Codex; no AI key or push channel needed."""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

import auth
import fetcher

ROOT = Path(__file__).resolve().parent
logger = logging.getLogger(__name__)


def collect(config: dict, *, smoke: bool = False) -> dict:
    """Smoke checks metadata only; full collection includes article bodies."""
    if not auth.is_token_valid(auth.load_token()):
        raise ValueError("微信登录缺失或过期，请先运行 python collect_articles.py --login")
    accounts = config.get("accounts") or []
    if not accounts:
        raise ValueError("config.yaml 未设置公众号名单")
    fetcher.API_INTERVAL = config.get("fetch", {}).get("request_interval", 1.5)
    hours = 24 * 14 if smoke else config.get("fetch", {}).get("hours", 24)
    now = datetime.now(timezone(timedelta(hours=8)))
    payload = {"collected_at": now.isoformat(), "hours": hours,
               "mode": "smoke" if smoke else "collect", "accounts": [], "articles": []}
    seen = set()
    for name in accounts:
        fakeid = fetcher.get_fakeid(name)
        if not fakeid:
            raise ValueError(f"无法确认公众号：{name}；请核对公众号名称或原文链接")
        # 先用较长窗口确认接口可读，避免把网络/会话错误返回的空列表当成“今天无更新”。
        articles = fetcher.get_recent_articles(fakeid, name, hours=max(hours, 24 * 14))
        if not articles:
            raise ValueError(f"{name} 在检查窗口内无文章，尚不能确认元数据读取正常")
        if not smoke:
            cutoff = now - timedelta(hours=hours)
            articles = [a for a in articles
                        if datetime.fromisoformat(a["publish_time"]) >= cutoff]
        payload["accounts"].append({"name": name, "articles_found": len(articles)})
        logger.info("%s：读取到 %s 篇文章元数据", name, len(articles))
        if smoke:
            continue
        for article in articles:
            url = article.get("url", "")
            if not url:
                raise ValueError(f"{name} 文章缺少原文链接")
            if url in seen:
                continue
            data = fetcher.get_article_content(url)
            text = data.get("text", "").strip()
            if not text:
                raise ValueError(f"正文未获取成功：{article.get('title', '')}")
            payload["articles"].append({**article, "account_name": name, "text": text})
            seen.add(url)
    return payload


def save_sources(payload: dict, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d-%H%M%S-%f")
    target = destination / f"articles-{timestamp}.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="只获取公众号文章，供 ChatGPT/Codex 整理，无需AI密钥")
    parser.add_argument("--login", action="store_true", help="扫码登录，不采集文章")
    parser.add_argument("--smoke", action="store_true", help="逐号检查元数据，不抓正文、不调用AI、不推送")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    if args.login:
        # QR临时文件也放在项目中，Windows用户可将整个项目放在D盘。
        temporary = ROOT / "login_temp"
        temporary.mkdir(exist_ok=True)
        os.environ["TMPDIR"] = os.environ["TEMP"] = os.environ["TMP"] = str(temporary)
        tempfile.tempdir = str(temporary)
        return 0 if auth.login() else 1
    try:
        config_path = ROOT / "config.yaml.local"
        if not config_path.exists():
            config_path = ROOT / "config.yaml"
        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        payload = collect(config, smoke=args.smoke)
        if args.smoke:
            print("六个来源检查完成（仅元数据）；尚未调用AI或推送。" if len(payload["accounts"]) == 6
                  else "来源检查完成（仅元数据）；尚未调用AI或推送。")
        else:
            target = save_sources(payload, ROOT / "collected_articles")
            print(f"已保存 {len(payload['articles'])} 篇原文：{target}")
            print("可将此JSON文件交给ChatGPT或Codex整理知识卡。")
        return 0
    except Exception as exc:
        logger.error("采集未完成：%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
