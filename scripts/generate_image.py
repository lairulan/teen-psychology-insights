#!/usr/bin/env python3
"""
心光馨语配图生成脚本
使用 Google Gemini Imagen API 生成温暖治愈系水彩插画
"""

import argparse
import base64
import json
import os
import re
import sys
from datetime import datetime
from urllib import request, error


GOOGLE_API_KEY = os.environ.get(
    "GOOGLE_API_KEY", "AQ.Ab8RN6LKLi1gwnul0aGEdgXzolnfIKYhiovTTsf-yr36z8yDeg"
)
IMAGEN_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"imagen-3.0-generate-002:predict?key={GOOGLE_API_KEY}"
)

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


def call_imagen(prompt, aspect_ratio="1:1"):
    """Call Google Imagen API to generate an image."""
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": aspect_ratio,
            "personGeneration": "allow_all",
        },
    }

    req = request.Request(
        IMAGEN_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"API error {e.code}: {body}", file=sys.stderr)
        return None

    predictions = result.get("predictions", [])
    if not predictions:
        print("No predictions returned", file=sys.stderr)
        return None

    return base64.b64decode(predictions[0]["bytesBase64Encoded"])


def save_image(image_bytes, output_path):
    """Save image bytes to file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(image_bytes)
    print(f"   Saved: {output_path}")
    return output_path


def generate_cover_image(title, style="warm", size="1792x1024"):
    """Generate a cover image for the article."""
    print(f"Generating cover image...")
    print(f"   Title: {title}")
    print(f"   Style: {style}")

    base_style = STYLE_PROMPTS.get(style, STYLE_PROMPTS["warm"])
    prompt = (
        f'Illustration for an article titled "{title}". '
        f"{base_style}. "
        "Include elements related to teenagers, family, growth, and psychology. "
        "Emotionally warm and empathetic. High quality, 4K."
    )

    print(f"   Prompt: {prompt[:100]}...")

    image_bytes = call_imagen(prompt, aspect_ratio="16:9")
    if not image_bytes:
        print("   Failed to generate cover image")
        return None

    today = datetime.now().strftime("%Y-%m-%d")
    output_path = os.path.join(OUTPUT_BASE, f"{today}-cover.png")
    return save_image(image_bytes, output_path)


def extract_image_placeholders(markdown_file):
    """Extract image placeholders from a Markdown file."""
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
                key = key.strip().strip('"').strip()
                value = value.strip().strip('"').strip()
                info[key] = value
        placeholders.append(
            {"position": match.start(), "full_text": match.group(0), "info": info}
        )
    return placeholders


def generate_article_images(markdown_file, max_images=2, size="1024x1024"):
    """Generate inline images for article sections."""
    print(f"Generating article images...")
    print(f"   File: {markdown_file}")

    placeholders = extract_image_placeholders(markdown_file)
    if not placeholders:
        print("   No placeholders found")
        return []

    print(f"   Found {len(placeholders)} placeholder(s)")
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
            "High quality, emotionally warm, suitable for psychology article."
        )

        image_bytes = call_imagen(prompt, aspect_ratio="1:1")
        if not image_bytes:
            print(f"     Failed to generate image {i}")
            continue

        output_path = os.path.join(OUTPUT_BASE, f"{today}-article-{i}.png")
        save_image(image_bytes, output_path)
        generated.append(output_path)

        # Replace placeholder with image markdown
        img_md = f"![配图{i}]({output_path})"
        content = content.replace(ph["full_text"], img_md)

    # Write back with images embedded
    with open(markdown_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\n   Generated {len(generated)} image(s), updated markdown file")
    return generated


def main():
    parser = argparse.ArgumentParser(
        description="Generate images for 心光馨语 articles using Google Imagen",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command")

    cover_p = subparsers.add_parser("cover", help="Generate cover image")
    cover_p.add_argument("--title", required=True, help="Article title")
    cover_p.add_argument(
        "--style",
        default="warm",
        choices=["warm", "modern", "minimalist", "creative"],
    )
    cover_p.add_argument("--size", default="1792x1024")

    article_p = subparsers.add_parser("article", help="Generate article images")
    article_p.add_argument("--file", required=True, help="Markdown file path")
    article_p.add_argument("--max-images", type=int, default=2)
    article_p.add_argument("--size", default="1024x1024")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "cover":
        result = generate_cover_image(args.title, args.style, args.size)
        if result:
            print(f"\nCover image: {result}")
        else:
            sys.exit(1)
    elif args.command == "article":
        if not os.path.exists(args.file):
            print(f"File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        results = generate_article_images(args.file, args.max_images, args.size)
        if not results:
            print("No images generated", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
