#!/usr/bin/env python3
"""
心光馨语 - 配图生成脚本
调用中央 generate-image 技能（AI Gateway + IMGBB）
保留温暖治愈系风格提示词
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime

# 中央生图脚本路径
CENTRAL_SCRIPT = os.path.expanduser("~/.claude/skills/generate-image/scripts/generate_image.py")

# 图片输出目录
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


def call_central_generate(prompt, output=None, retry=3):
    """调用中央生图脚本"""
    cmd = [
        sys.executable, CENTRAL_SCRIPT,
        prompt,
        "--json",
        "--upload-imgbb",
        "--retry", str(retry)
    ]
    if output:
        cmd.extend(["--output", output])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        stdout = result.stdout.strip()
        if not stdout:
            return {"success": False, "error": f"中央脚本无输出. stderr: {result.stderr[:500]}"}

        lines = stdout.split('\n')
        json_lines = []
        for line in reversed(lines):
            json_lines.insert(0, line)
            if line.strip().startswith('{'):
                break

        return json.loads('\n'.join(json_lines))
    except json.JSONDecodeError:
        return {"success": False, "error": "JSON 解析失败"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "生图超时"}
    except Exception as e:
        return {"success": False, "error": str(e)}


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

    result = call_central_generate(prompt, output=output_path, retry=3)
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
        result = call_central_generate(prompt, output=output_path, retry=3)

        if result.get("success"):
            url = result.get("imgbb_url") or result.get("url")
            local = result.get("local_path", output_path)
            generated.append(local)
            # 用 IMGBB URL 替换占位符（公众号可直接引用）
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
    parser = argparse.ArgumentParser(description="心光馨语 配图生成（中央引擎）")
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
