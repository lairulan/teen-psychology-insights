#!/usr/bin/env python3
"""
心光馨语自动发布脚本 V1.1
每天 20:00 自动运行，生成闺蜜聊天式心理学短文并发布到公众号

流程：
1. 从预设话题库按日期轮询选题（避免重复）
2. 用 Google Gemini API 生成 800-1200 字闺蜜聊天式文章
3. 用 Google Gemini Imagen 生成封面图
4. 转换为微信公众号 HTML（grace 主题风格）
5. 发布到"心光馨语"公众号
"""

import argparse
import base64
import json
import os
import random
import re
import sys
import urllib.parse
from datetime import datetime
from urllib import request, error

# 配置
WECHAT_API_KEY = os.environ.get("WECHAT_API_KEY")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY")
# 天行数据 API Key（用于获取微博热搜）
TIANAPI_KEY = os.environ.get("TIANAPI_KEY", "a0ba59d286ea1b308f5719a4ba28d075")
APPID = "wx52189e9b012018e1"
API_BASE = "https://wx.limyai.com/api/openapi"

# 工作目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORK_DIR = os.path.dirname(SCRIPT_DIR)
LOG_FILE = os.path.join(WORK_DIR, "logs", "daily-publish.log")

# 话题库（按天数轮询，覆盖全年不重复）
TOPIC_POOL = [
    # 学业压力
    {"topic": "考试前焦虑怎么办", "category": "学业压力"},
    {"topic": "孩子总是拖延写作业", "category": "学业压力"},
    {"topic": "学习没有动力怎么办", "category": "学业压力"},
    {"topic": "成绩下滑了怎么安慰孩子", "category": "学业压力"},
    {"topic": "孩子说学习太累了", "category": "学业压力"},
    {"topic": "害怕开学怎么办", "category": "学业压力"},
    {"topic": "孩子考试作弊被发现", "category": "学业压力"},
    {"topic": "偏科严重怎么应对", "category": "学业压力"},
    # 人际关系
    {"topic": "孩子在学校没有朋友", "category": "人际关系"},
    {"topic": "孩子被同学排挤了", "category": "人际关系"},
    {"topic": "社恐的孩子怎么引导", "category": "人际关系"},
    {"topic": "孩子和好朋友闹翻了", "category": "人际关系"},
    {"topic": "孩子早恋了怎么办", "category": "人际关系"},
    {"topic": "被同学嘲笑后怎么自处", "category": "人际关系"},
    {"topic": "孩子只喜欢和手机玩", "category": "人际关系"},
    {"topic": "孩子跟风做了不好的事", "category": "人际关系"},
    # 情绪管理
    {"topic": "孩子动不动就发脾气", "category": "情绪管理"},
    {"topic": "青春期情绪起伏大", "category": "情绪管理"},
    {"topic": "孩子说不开心但不说原因", "category": "情绪管理"},
    {"topic": "如何帮孩子缓解焦虑", "category": "情绪管理"},
    {"topic": "孩子说活着没意思怎么办", "category": "情绪管理"},
    {"topic": "孩子一受批评就哭", "category": "情绪管理"},
    {"topic": "孩子特别容易受伤", "category": "情绪管理"},
    {"topic": "孩子突然变得很沉默", "category": "情绪管理"},
    # 亲子沟通
    {"topic": "孩子说烦死了其实在说什么", "category": "亲子沟通"},
    {"topic": "为什么孩子不愿意和我说话", "category": "亲子沟通"},
    {"topic": "怎么和青春期孩子好好说话", "category": "亲子沟通"},
    {"topic": "孩子嫌我唠叨怎么办", "category": "亲子沟通"},
    {"topic": "孩子总说你不理解我", "category": "亲子沟通"},
    {"topic": "孩子不愿分享学校的事", "category": "亲子沟通"},
    {"topic": "和孩子聊天总变成争吵", "category": "亲子沟通"},
    {"topic": "孩子对父母撒谎怎么办", "category": "亲子沟通"},
    # 自我认知
    {"topic": "孩子总觉得自己不够好", "category": "自我认知"},
    {"topic": "青春期孩子特别在意外表", "category": "自我认知"},
    {"topic": "孩子不知道自己想要什么", "category": "自我认知"},
    {"topic": "孩子过于追求完美", "category": "自我认知"},
    {"topic": "孩子特别怕失败", "category": "自我认知"},
    {"topic": "孩子迷上了某个爱好家长不理解", "category": "自我认知"},
    {"topic": "孩子说自己太普通了", "category": "自我认知"},
    {"topic": "孩子总拿自己跟别人比", "category": "自我认知"},
    # 趣味心理
    {"topic": "为什么越禁止越想做", "category": "趣味心理"},
    {"topic": "为什么考试时会突然忘记答案", "category": "趣味心理"},
    {"topic": "为什么排队时总觉得别的队快", "category": "趣味心理"},
    {"topic": "晚上的烦恼为什么早上就消失了", "category": "趣味心理"},
    {"topic": "为什么心情不好的时候想吃甜食", "category": "趣味心理"},
    {"topic": "为什么我们总记得没做完的事", "category": "趣味心理"},
    {"topic": "为什么越说不紧张越紧张", "category": "趣味心理"},
    {"topic": "为什么人在难过时喜欢听悲歌", "category": "趣味心理"},
    # 成长与变化
    {"topic": "孩子突然开窍了是怎么回事", "category": "成长与变化"},
    {"topic": "为什么孩子小时候很开朗长大却内向", "category": "成长与变化"},
    {"topic": "孩子进入叛逆期的信号", "category": "成长与变化"},
    {"topic": "高中生为什么特别需要隐私", "category": "成长与变化"},
    {"topic": "青春期孩子为何喜欢冒险", "category": "成长与变化"},
    {"topic": "孩子突然变得很独立怎么看", "category": "成长与变化"},
]


def log(message):
    """Record log"""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_msg + "\n")
    except Exception:
        pass


def call_gemini_api(prompt, max_tokens=4000):
    """Call Google Gemini API for content generation"""
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.85,
        },
    }
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=90) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        return result["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        log(f"Gemini API 调用失败: {e}")
        return None


def fetch_weibo_hot():
    """Fetch top Weibo trending topics via Tianapi"""
    try:
        url = (
            f"https://apis.tianapi.com/weibohot/index?"
            f"{urllib.parse.urlencode({'key': TIANAPI_KEY, 'num': 50})}"
        )
        req = request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("code") != 200:
            log(f"Tianapi 返回错误: {data.get('msg')}")
            return []
        hot_list = data.get("result", {}).get("list", [])
        topics = [item.get("hotword", "").strip() for item in hot_list if item.get("hotword")]
        log(f"获取到 {len(topics)} 条微博热搜")
        return topics
    except Exception as e:
        log(f"微博热搜获取失败: {e}")
        return []


def select_topic_from_hot(hot_topics):
    """Use Gemini to pick the best psychology angle from Weibo trending topics"""
    topics_text = "\n".join(f"{i+1}. {t}" for i, t in enumerate(hot_topics[:30]))
    prompt = f"""你是"心光馨语"公众号的编辑，专注青少年心理健康和亲子关系。

以下是今日微博热搜榜（前30条）：
{topics_text}

请从中选一个最适合结合青少年心理学或亲子关系来写文章的热搜话题，或者受热搜启发提炼一个相关话题。

要求：
- 优先选与青少年情绪、学习、亲子关系、成长直接相关的热搜
- 如没有直接相关的，可从社会热点（考试、就业、家庭、情感）中提炼一个心理学角度
- 话题要能引发家长或青少年的共鸣
- 避免选娱乐八卦、政治、灾难类话题

请用 JSON 格式回复（不要有代码块标记）：
{{"topic": "提炼后的话题", "category": "分类（学业压力/人际关系/情绪管理/亲子沟通/自我认知/趣味心理/成长与变化）", "hot_ref": "参考的热搜词"}}"""

    result = call_gemini_api(prompt, max_tokens=200)
    if not result:
        return None
    try:
        # 清理可能的 markdown 代码块
        result = re.sub(r"```(?:json)?|```", "", result).strip()
        data = json.loads(result)
        if data.get("topic"):
            log(f"热搜选题: {data['topic']} (参考热搜: {data.get('hot_ref', '')})")
            return {"topic": data["topic"], "category": data.get("category", "热点"), "hot_ref": data.get("hot_ref", "")}
    except Exception as e:
        log(f"热搜选题解析失败: {e}, 原始返回: {result[:100]}")
    return None


def select_topic():
    """Select today's topic: try Weibo hot topics first, fallback to pool"""
    # 优先尝试热搜选题
    hot_topics = fetch_weibo_hot()
    if hot_topics:
        topic = select_topic_from_hot(hot_topics)
        if topic:
            return topic
        log("热搜选题失败，使用话题池兜底")

    # 兜底：从话题池按天数轮询
    today = datetime.now()
    epoch = datetime(2026, 1, 1)
    day_index = (today - epoch).days % len(TOPIC_POOL)
    topic = TOPIC_POOL[day_index]
    log(f"话题池选题 [第{day_index + 1}/{len(TOPIC_POOL)}个]: {topic['topic']} (分类: {topic['category']})")
    return topic


def generate_article(topic_info):
    """Generate article using Gemini API"""
    log("正在生成文章...")

    prompt = f"""你是"心光馨语"公众号的作者，写作风格是闺蜜聊天式——像朋友分享经验一样讲心理学知识。

请根据以下话题写一篇公众号文章：

话题：{topic_info['topic']}
分类：{topic_info['category']}
{f"热搜背景：今日微博热搜「{topic_info['hot_ref']}」与此话题相关，可在文章中自然呼应这一热点" if topic_info.get('hot_ref') else ""}

严格要求：
1. 字数：800-1200字，绝不超过1500字
2. 语气：像闺蜜聊天，口语化，可以用"哈哈"、"真的"、"你说是不是"
3. 零术语：所有心理学概念都用大白话解释
4. 段落短：每段不超过3-4行，手机阅读友好
5. 温暖不鸡汤，真诚不矫情
6. 多用问句增加互动感："你有没有发现……"、"是不是很像……"

文章结构：
## 开头（150-200字）
用"你有没有过这种时候……"或类似的日常场景开头，引发共鸣

## 中间（300-400字）
用聊天口吻讲1-2个心理学知识点，多用比喻"这就好像……"
可以穿插有趣的心理学实验或数据

## 实用Tips（200-300字）
给出2-3个"马上能用"的小方法
每个方法一句话概括 + 一个具体场景

## 结尾（100-150字）
不说教不总结，用一句温暖的话结束

格式要求：
- 输出纯 Markdown 格式
- 第一行是标题（用 # ）
- 正文不要在开头重复标题
- 不要附参考资料
- 不要用"根据研究表明"之类的学术表达
- 用"心理学家做过一个特别有意思的实验"代替"研究显示"
- 用"下次试试先闭嘴听完，真的有用"代替"建议采取积极倾听策略"

直接输出文章内容，不要输出任何说明。"""

    content = call_gemini_api(prompt, max_tokens=4000)
    if not content:
        log("文章生成失败")
        return None

    # Extract title
    title_match = re.match(r"^#\s*(.+)", content.strip())
    title = title_match.group(1).strip() if title_match else topic_info["topic"]

    # Word count check
    clean_text = re.sub(r"[#*\-\n]", "", content)
    word_count = len(clean_text)
    log(f"文章标题: {title}")
    log(f"文章字数: {word_count}")

    if word_count < 500:
        log("警告: 文章字数不足500")

    return {"title": title, "content": content, "word_count": word_count}


def generate_cover_image(title):
    """Generate cover image using Google Gemini Imagen API, upload to IMGBB"""
    if not GOOGLE_API_KEY:
        log("未设置 GOOGLE_API_KEY，跳过封面图生成")
        return None

    log("正在生成封面图...")

    imagen_url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"imagen-3.0-generate-002:predict?key={GOOGLE_API_KEY}"
    )

    prompt = (
        f'Illustration for an article titled "{title}". '
        "Warm healing watercolor illustration, soft warm orange and light gold tones, "
        "cozy atmosphere, gentle light, heartwarming mood, "
        "elements related to teenagers, family, growth, and psychology. "
        "Emotionally warm and empathetic. High quality, 4K."
    )

    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": "16:9",
            "personGeneration": "allow_all",
        },
    }

    req = request.Request(
        imagen_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        predictions = result.get("predictions", [])
        if not predictions:
            log("Imagen API 未返回结果")
            return None

        image_bytes = base64.b64decode(predictions[0]["bytesBase64Encoded"])
        log(f"封面图生成成功 ({len(image_bytes)} bytes)")

        # Upload to IMGBB if key available
        if IMGBB_API_KEY:
            return upload_to_imgbb(image_bytes)

        return None

    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        log(f"Imagen API 错误 {e.code}: {body[:200]}")
        return None
    except Exception as e:
        log(f"封面图生成异常: {e}")
        return None


def upload_to_imgbb(image_bytes):
    """Upload image to IMGBB and return URL"""
    try:
        data = urllib.parse.urlencode({
            "key": IMGBB_API_KEY,
            "image": base64.b64encode(image_bytes).decode("utf-8"),
        }).encode("utf-8")
        req = request.Request(
            "https://api.imgbb.com/1/upload",
            data=data,
            method="POST",
        )
        with request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        if result.get("success"):
            url = result["data"]["url"]
            log(f"封面图上传成功: {url}")
            return url
    except Exception as e:
        log(f"IMGBB 上传失败: {e}")
    return None


def markdown_to_grace_html(markdown_content):
    """Convert Markdown to WeChat-compatible HTML with grace theme styling"""
    lines = markdown_content.strip().split("\n")
    html_parts = []
    in_list = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append("<p><br/></p>")
            continue

        # H1 title
        if stripped.startswith("# "):
            title_text = stripped[2:].strip()
            html_parts.append(
                f'<h1 style="text-align:center;font-size:22px;font-weight:bold;'
                f"color:#FF9F43;margin:30px 0 20px;padding:15px 20px;"
                f"background:linear-gradient(135deg,#FFF8E7,#FFF3D0);"
                f'border-radius:12px;box-shadow:0 2px 8px rgba(255,159,67,0.15);">'
                f"{title_text}</h1>"
            )
            continue

        # H2 subtitle
        if stripped.startswith("## "):
            subtitle = stripped[3:].strip()
            html_parts.append(
                f'<h2 style="font-size:18px;font-weight:bold;color:#E17055;'
                f"margin:25px 0 12px;padding-left:12px;"
                f'border-left:4px solid #FF9F43;">{subtitle}</h2>'
            )
            continue

        # Blockquote
        if stripped.startswith("> "):
            quote_text = stripped[2:].strip()
            html_parts.append(
                f'<blockquote style="margin:15px 0;padding:12px 18px;'
                f"background:#FFF8E7;border-left:4px solid #FFEAA7;"
                f'border-radius:0 8px 8px 0;color:#666;font-size:15px;line-height:1.8;">'
                f"{quote_text}</blockquote>"
            )
            continue

        # List items
        if stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                html_parts.append(
                    '<ul style="margin:10px 0;padding-left:20px;list-style:none;">'
                )
                in_list = True
            item_text = stripped[2:].strip()
            # Bold processing
            item_text = re.sub(
                r"\*\*(.+?)\*\*",
                r'<strong style="color:#FF9F43;">\1</strong>',
                item_text,
            )
            html_parts.append(
                f'<li style="margin:8px 0;line-height:1.8;font-size:16px;'
                f'color:#333;padding-left:8px;">'
                f'<span style="color:#FF9F43;margin-right:6px;">●</span>'
                f"{item_text}</li>"
            )
            continue

        if in_list:
            html_parts.append("</ul>")
            in_list = False

        # Regular paragraph with bold processing
        text = stripped
        text = re.sub(
            r"\*\*(.+?)\*\*",
            r'<strong style="color:#FF9F43;">\1</strong>',
            text,
        )
        html_parts.append(
            f'<p style="font-size:16px;line-height:1.8;color:#333;'
            f'margin:10px 0;text-align:justify;">{text}</p>'
        )

    if in_list:
        html_parts.append("</ul>")

    # Wrap in container
    body = "\n".join(html_parts)
    html = (
        f'<section style="max-width:600px;margin:0 auto;padding:20px;'
        f'font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;">'
        f"{body}"
        f'<p style="text-align:center;margin-top:30px;padding:15px;'
        f"font-size:13px;color:#999;border-top:1px solid #FFEAA7;\">"
        f"心光馨语 | 像闺蜜一样聊心理</p>"
        f"</section>"
    )

    return html


def publish_to_wechat(title, html_content, cover_url=None):
    """Publish to WeChat Official Account"""
    log("正在发布到公众号...")

    # Generate summary
    summary_prompt = f"""请用一句话（20-30字）概括这篇文章的核心内容，要求温暖有吸引力，适合做公众号文章摘要：
标题：{title}"""
    summary = call_gemini_api(summary_prompt, max_tokens=100)
    if summary:
        summary = summary.strip().strip('"\'')
        log(f"生成摘要: {summary}")

    headers = {
        "X-API-Key": WECHAT_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "wechatAppid": APPID,
        "title": title,
        "content": html_content,
        "contentFormat": "html",
        "summary": summary or "心理学小知识，温暖你的每一天",
        "coverImage": cover_url or "",
        "articleType": "news",
    }

    try:
        req = request.Request(
            f"{API_BASE}/wechat-publish",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        log(f"API 响应: {result}")
        success = result.get("success", False)
        if not success:
            log(f"发布失败: {result.get('error', result)}")
        return success
    except Exception as e:
        log(f"发布异常: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="心光馨语自动发布脚本 V1.0")
    parser.add_argument("--check-env", action="store_true", help="检查环境依赖")
    parser.add_argument("--dry-run", action="store_true", help="试运行（不发布）")
    parser.add_argument("--topic", type=str, help="指定话题")
    args = parser.parse_args()

    # Check environment
    if args.check_env:
        errors = []
        if not WECHAT_API_KEY:
            errors.append("未设置 WECHAT_API_KEY")
        if not GOOGLE_API_KEY:
            errors.append("未设置 GOOGLE_API_KEY")
        if not IMGBB_API_KEY:
            print("⚠️ 未设置 IMGBB_API_KEY（封面图上传将跳过）")
        for e in errors:
            print(f"❌ {e}")
        if errors:
            sys.exit(1)
        print("✅ 环境检查通过")
        sys.exit(0)

    # Validate required env vars
    if not GOOGLE_API_KEY:
        log("❌ 未设置 GOOGLE_API_KEY")
        sys.exit(1)
    if not WECHAT_API_KEY and not args.dry_run:
        log("❌ 未设置 WECHAT_API_KEY")
        sys.exit(1)

    log("=" * 50)
    log("心光馨语自动发布 V1.0 开始执行")
    log(f"日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    if args.dry_run:
        log("⚠️ 试运行模式：不会发布到公众号")

    # 1. Select topic
    if args.topic:
        topic_info = {"topic": args.topic, "category": "自定义", "keywords": args.topic}
    else:
        topic_info = select_topic()

    # 2. Generate article
    article = generate_article(topic_info)
    if not article:
        log("❌ 文章生成失败")
        sys.exit(1)

    # 3. Generate cover image
    cover_url = generate_cover_image(article["title"])

    # 4. Convert to HTML
    log("正在转换 HTML（grace 主题）...")
    html_content = markdown_to_grace_html(article["content"])
    log(f"HTML 内容长度: {len(html_content)} 字符")

    # 5. Save article locally
    today_str = datetime.now().strftime("%Y%m%d")
    md_file = os.path.join(WORK_DIR, f"article_{today_str}.md")
    try:
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(f"---\ntitle: {article['title']}\ndate: {datetime.now().strftime('%Y-%m-%d')}\n"
                    f"category: {topic_info['category']}\nword_count: {article['word_count']}\n"
                    f"style: 闺蜜聊天式\n---\n\n{article['content']}")
        log(f"文章已保存: {md_file}")
    except Exception as e:
        log(f"文件保存失败: {e}")

    # Dry run exit
    if args.dry_run:
        log("=" * 50)
        log("✅ 试运行完成")
        log(f"标题: {article['title']}")
        log(f"字数: {article['word_count']}")
        log(f"封面图: {cover_url or '无'}")
        log("=" * 50)
        sys.exit(0)

    # 6. Publish
    success = publish_to_wechat(article["title"], html_content, cover_url)

    if success:
        log("✅ 发布成功！")

        # Git commit
        try:
            import subprocess
            subprocess.run(["git", "config", "user.name", "GitHub Actions"], check=True, cwd=WORK_DIR)
            subprocess.run(["git", "config", "user.email", "actions@github.com"], check=True, cwd=WORK_DIR)
            subprocess.run(["git", "add", f"article_{today_str}.md"], check=True, cwd=WORK_DIR)
            commit_msg = f"chore: 自动发布心光馨语 {datetime.now().strftime('%Y-%m-%d')} - {article['title']}"
            subprocess.run(["git", "commit", "-m", commit_msg], check=True, cwd=WORK_DIR)
            subprocess.run(["git", "push"], check=True, cwd=WORK_DIR)
            log("✅ 文件已提交到 Git 仓库")
        except Exception as e:
            log(f"⚠️ Git 操作失败（不影响发布）: {e}")

        log("任务完成")
        log("=" * 50)
    else:
        log("❌ 发布失败")
        log("=" * 50)
        sys.exit(1)


if __name__ == "__main__":
    main()
