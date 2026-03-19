#!/usr/bin/env python3
"""
心光馨语 - 配图生成脚本
直接调用 AI Gateway（https://ai-gateway.happycapy.ai）+ IMGBB 上传
无本地路径依赖，可在 GitHub Actions 中正常运行
"""

import argparse
import base64
import json
import os
import re
import sys
import time
from datetime import datetime
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

API_BASE = "https://ai-gateway.happycapy.ai/api/v1"
DEFAULT_MODEL = "google/gemini-3.1-flash-image-preview"

OUTPUT_BASE = os.path.expanduser("~/Documents/Obsidian/心光馨语/images")

STYLE_PROMPTS = {
    "warm": (
        "Warm healing watercolor illustration, soft warm orange and light gold tones, "
        "cozy family atmosphere, gentle light, heartwarming mood, "
        "suitable for psychology and parenting content"
    ),
    "modern": (
        "Modern minimalist flat illustration, fresh color palette, clean lines, "
        "warm orange accents, professional and approachable"
    ),
    "minimalist": (
        "Minimalist line art illustration, warm orange and cream palette, "
        "generous white space, elegant and soothing"
    ),
    "creative": (
        "Playful colorful illustration, warm and vibrant, cartoon style, "
        "youthful energy, fun and engaging"
    ),
}


def _generate_image_b64(prompt, model=DEFAULT_MODEL, retry=3):
    """直接调用 AI Gateway 生成图片，返回 base64 数据"""
    api_key = os.environ.get("AI_GATEWAY_API_KEY")
    if not api_key:
        return {"success": False, "error": "未设置 AI_GATEWAY_API_KEY"}

    payload = {
        "model": model,
        "prompt": prompt,
        "response_format": "b64_json",
        "n": 1,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "Origin": "https://trickle.so",
        "User-Agent": "Mozilla/5.0 (compatible; AI-Gateway-Client/1.0)",
    }

    for attempt in range(retry):
        try:
            req = urllib_request.Request(
                f"{API_BASE}/images/generations",
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib_request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            if "data" in data and data["data"]:
                b64 = data["data"][0].get("b64_json")
                if b64:
                    return {"success": True, "b64_json": b64}
            return {"success": False, "error": "API 响应无图片数据"}

        except HTTPError as e:
            err = e.read().decode("utf-8")
            if attempt < retry - 1:
                time.sleep(5)
                continue
            return {"success": False, "error": f"HTTP {e.code}: {err[:300]}"}
        except Exception as e:
            if attempt < retry - 1:
                time.sleep(5)
                continue
            return {"success": False, "error": str(e)}

    return {"success": False, "error": "超过重试次数"}


def _upload_imgbb(b64_data):
    """上传 base64 图片到 IMGBB，返回 URL"""
    api_key = os.environ.get("IMGBB_API_KEY")
    if not api_key:
        return None

    try:
        body = urlencode({"key": api_key, "image": b64_data})
        req = urllib_request.Request(
            "https://api.imgbb.com/1/upload",
            data=body.encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib_request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        if result.get("success"):
            return result["data"]["url"]
    except Exception:
        pass
    return None


def generate_and_upload(prompt, retry=3, output=None):
    """生成图片并上传到 IMGBB，返回统一格式结果"""
    result = _generate_image_b64(prompt, retry=retry)
    if not result.get("success"):
        return result

    b64 = result["b64_json"]

    # 保存本地文件（如果指定了路径）
    local_path = None
    if output:
        try:
            os.makedirs(os.path.dirname(output), exist_ok=True)
            with open(output, "wb") as f:
                f.write(base64.b64decode(b64))
            local_path = output
        except Exception:
            pass

    imgbb_url = _upload_imgbb(b64)

    return {
        "success": True,
        "imgbb_url": imgbb_url,
        "url": imgbb_url,
        "local_path": local_path,
        "source": "ai-gateway",
    }


def generate_cover_image(title, style="warm", size="1792x1024"):
    """生成封面图"""
    print(f"Generating cover image...")
    print(f"   Title: {title}")
    print(f"   Style: {style}")

    base_style = STYLE_PROMPTS.get(style, STYLE_PROMPTS["warm"])
    prompt = (
        f'Illustration for an article titled "{title}". '
        f"{base_style}. "
        "Include elements related to teenagers, family, growth, and psychology. "
        "Emotionally warm and empathetic. High quality, 4K. "
        "NO text, NO Chinese characters, NO typography."
    )

    today = datetime.now().strftime("%Y-%m-%d")
    output_path = os.path.join(OUTPUT_BASE, f"{today}-cover.png")

    result = generate_and_upload(prompt, retry=3, output=output_path)
    if result.get("success"):
        url = result.get("imgbb_url") or result.get("url")
        local = result.get("local_path", output_path)
        print(f"   Cover URL: {url}")
        print(f"   Local: {local}")
        return local
    else:
        print(f"   Failed: {result.get('error')}")
        return None


def extract_image_placeholders(markdown_file):
    """从 Markdown 文件提取图片占位符"""
    with open(markdown_file, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r"<!-- IMG_PLACEHOLDER: \{([^}]+)\} -->"
    matches = list(re.finditer(pattern, content))

    placeholders = []
    for match in matches:
        info = {}
        for item in match.group(1).split(","):
            if ":" in item:
                key, value = item.split(":", 1)
                info[key.strip().strip('"')] = value.strip().strip('"')
        placeholders.append({"position": match.start(), "full_text": match.group(0), "info": info})
    return placeholders


def generate_article_images(markdown_file, max_images=2, size="1024x1024"):
    """为文章生成配图"""
    print(f"Generating article images...")

    placeholders = extract_image_placeholders(markdown_file)
    if not placeholders:
        print("   No placeholders found")
        return []

    placeholders = placeholders[:max_images]
    today = datetime.now().strftime("%Y-%m-%d")
    generated = []

    with open(markdown_file, "r", encoding="utf-8") as f:
        content = f.read()

    for i, ph in enumerate(placeholders, 1):
        info = ph["info"]
        print(f"\n   Generating image {i}/{len(placeholders)}:")
        print(f"     Subject: {info.get('主体', 'N/A')}")

        prompt = (
            f"{info.get('主体', '')}, "
            f"{info.get('动作/状态', '')}, "
            f"{info.get('场景/环境', '')}, "
            f"{info.get('风格', 'Warm healing watercolor illustration, soft warm orange and light gold tones')}. "
            "High quality, emotionally warm, suitable for psychology article. "
            "NO text, NO Chinese characters."
        )

        output_path = os.path.join(OUTPUT_BASE, f"{today}-article-{i}.png")
        result = generate_and_upload(prompt, retry=3, output=output_path)

        if result.get("success"):
            url = result.get("imgbb_url") or result.get("url")
            local = result.get("local_path", output_path)
            generated.append(local)
            img_md = f"![配图{i}]({url})"
            content = content.replace(ph["full_text"], img_md)
            print(f"     URL: {url}")
        else:
            print(f"     Failed: {result.get('error')}")

    with open(markdown_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\n   Generated {len(generated)} image(s)")
    return generated


def main():
    parser = argparse.ArgumentParser(description="心光馨语 配图生成（AI Gateway 直连）")
    subparsers = parser.add_subparsers(dest="command")

    cover_p = subparsers.add_parser("cover")
    cover_p.add_argument("--title", required=True)
    cover_p.add_argument("--style", default="warm", choices=["warm", "modern", "minimalist", "creative"])
    cover_p.add_argument("--size", default="1792x1024")

    article_p = subparsers.add_parser("article")
    article_p.add_argument("--file", required=True)
    article_p.add_argument("--max-images", type=int, default=2)
    article_p.add_argument("--size", default="1024x1024")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "cover":
        generate_cover_image(args.title, args.style, args.size)
    elif args.command == "article":
        if not os.path.exists(args.file):
            print(f"File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        generate_article_images(args.file, args.max_images, args.size)


if __name__ == "__main__":
    main()
