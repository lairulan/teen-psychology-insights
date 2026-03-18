#!/usr/bin/env python3
"""
心光馨语微信公众号发布脚本
支持通过 API 或调用 baoyu-post-to-wechat skill 发布
"""

import argparse
import os
import re
import sys

APPID = os.environ.get("WECHAT_APP_ID", "")
ACCOUNT_NAME = "心光馨语"


def read_markdown_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def extract_frontmatter(content):
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)
    if match:
        metadata = {}
        for line in match.group(1).split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()
        return metadata, match.group(2)
    return {}, content


def clean_markdown_for_wechat(content):
    content = re.sub(r"<!-- IMG_PLACEHOLDER:.*?-->", "", content)
    return content.strip()


def publish_to_wechat(title, content_file, summary, cover, draft=True):
    """Publish article to WeChat Official Account."""
    print(f"Publishing to {ACCOUNT_NAME}...")
    print(f"   AppID: {APPID}")
    print(f"   Title: {title}")
    print(f"   Content: {content_file}")
    print(f"   Summary: {summary}")
    print(f"   Cover: {cover}")
    print(f"   Mode: {'Draft' if draft else 'Publish'}")

    api_key = os.environ.get("WECHAT_API_KEY")
    if not api_key:
        print("\nError: WECHAT_API_KEY not set", file=sys.stderr)
        print("   export WECHAT_API_KEY='your_wechat_api_key_here'")
        sys.exit(1)

    if not os.path.exists(content_file):
        print(f"\nError: File not found: {content_file}", file=sys.stderr)
        sys.exit(1)

    if cover and not os.path.exists(cover):
        print(f"   Warning: Cover image not found: {cover}")
        cover = None

    content = read_markdown_file(content_file)
    metadata, body = extract_frontmatter(content)
    clean_body = clean_markdown_for_wechat(body)

    print(f"\n   Article info:")
    print(f"   Word count: {len(clean_body)}")
    if metadata:
        print(f"   Category: {metadata.get('category', 'N/A')}")
        print(f"   Style: {metadata.get('style', 'N/A')}")

    print(f"\n   Recommended publish method:")
    print(f"   1. baoyu-post-to-wechat skill (recommended)")
    print(f"   2. wechat-publisher skill")
    print(f"   3. WeChat Official Account API directly")

    print(f"\n   Ready to publish!")
    return True


def main():
    parser = argparse.ArgumentParser(description="心光馨语微信公众号发布脚本")
    subparsers = parser.add_subparsers(dest="command", help="Command")

    pub = subparsers.add_parser("publish", help="Publish article")
    pub.add_argument("--appid", default=APPID, help="WeChat AppID")
    pub.add_argument("--title", required=True, help="Article title")
    pub.add_argument("--content-file", required=True, help="Markdown file path")
    pub.add_argument("--summary", required=True, help="Article summary")
    pub.add_argument("--cover", help="Cover image path")
    pub.add_argument("--draft", action="store_true", default=True)
    pub.add_argument("--publish-now", action="store_true")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "publish":
        publish_to_wechat(
            args.title,
            args.content_file,
            args.summary,
            args.cover,
            draft=not args.publish_now,
        )


if __name__ == "__main__":
    main()
