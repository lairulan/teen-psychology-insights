#!/usr/bin/env python3
"""Publish an already-rendered HTML article to the WeChat draft box."""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib import error, request


API_BASE = "https://wx.limyai.com/api/openapi"
DEFAULT_APPID = "wx52189e9b012018e1"


def read_html(path):
    html = Path(path).read_text(encoding="utf-8")
    body_match = re.search(r"<body[^>]*>(.*?)</body>", html, flags=re.I | re.S)
    return body_match.group(1).strip() if body_match else html.strip()


def extract_title(path, fallback):
    if fallback:
        return fallback[:64]
    html = Path(path).read_text(encoding="utf-8")
    title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, flags=re.I)
    if title_match:
        return title_match.group(1).strip()[:64]
    h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", html, flags=re.I | re.S)
    if h1_match:
        title = re.sub(r"<[^>]+>", "", h1_match.group(1)).strip()
        return title[:64]
    return "心光心理学"[:64]


def publish(args):
    api_key = os.environ.get("WECHAT_API_KEY")
    if not api_key:
        raise RuntimeError("WECHAT_API_KEY is not set")

    appid = args.appid or os.environ.get("WECHAT_APP_ID") or DEFAULT_APPID
    html_content = read_html(args.html)
    title = extract_title(args.html, args.title)

    payload = {
        "wechatAppid": appid,
        "title": title,
        "content": html_content,
        "contentFormat": "html",
        "summary": args.summary,
        "articleType": "news",
    }
    if args.cover:
        payload["coverImage"] = args.cover
    if args.author:
        payload["author"] = args.author

    req = request.Request(
        f"{API_BASE}/wechat-publish",
        data=json.dumps(payload).encode("utf-8"),
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=180) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(body, file=sys.stderr)
        raise

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get("success"):
        raise RuntimeError(result.get("error") or "WeChat publish failed")


def main():
    parser = argparse.ArgumentParser(description="Publish rendered HTML to WeChat drafts")
    parser.add_argument("--html", required=True, help="Rendered HTML file")
    parser.add_argument("--title", help="Article title")
    parser.add_argument("--summary", required=True, help="Article summary")
    parser.add_argument("--cover", help="Cover image URL")
    parser.add_argument("--author", default="心光心理学", help="Author name")
    parser.add_argument("--appid", help="WeChat AppID; defaults to WECHAT_APP_ID or 心光心理学 AppID")
    args = parser.parse_args()
    publish(args)


if __name__ == "__main__":
    main()
