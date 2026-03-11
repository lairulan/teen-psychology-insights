#!/usr/bin/env python3
"""
心光馨语自动发布脚本 v2.3
每天自动运行，生成闺蜜聊天式心理学短文并发布到公众号

流程：
1. 选题（4层漏斗：5平台热搜轮换 → Gemini实时搜索 → 日历时令 → 话题池）
2. 用 Gemini 2.5 Flash 生成 800-1200 字闺蜜聊天式文章（豆包兜底）
3. 用 Gemini Imagen 3 生成封面图
4. 转换为微信公众号 HTML（暖橙色调 #FF9F43）
5. 发布到"心光馨语"公众号

版本历史：
v1.0  初始版本
v2.0  全面升级：公众号改"心光馨语"，闺蜜聊天式，grace排版+暖橙色调
v2.1  API升级：Gemini 2.5 Flash + 豆包兜底，修复 GOOGLE_API_KEY 配置
v2.2  排版优化：H2颜色统一(#FF8C42)，列表flex布局，图片占位块
v2.3  选题增强：5平台热搜(微博/抖音/腾讯/百度/全网)每日轮换 + Gemini实时搜索兜底
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
DOUBAO_API_KEY = os.environ.get("DOUBAO_API_KEY")
IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY")
# 天行数据 API Key（用于获取微博热搜）
TIANAPI_KEY = os.environ.get("TIANAPI_KEY", "a0ba59d286ea1b308f5719a4ba28d075")
APPID = "wx5f15d70a0882dc9b"
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


def call_doubao_api(prompt, max_tokens=4000):
    """Call Doubao ARK API as fallback for content generation (OpenAI-compatible)"""
    if not DOUBAO_API_KEY:
        return None
    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    payload = {
        "model": "doubao-1.5-pro-32k",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.85,
    }
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DOUBAO_API_KEY}",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=90) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        log(f"豆包 API 调用失败: {e}")
        return None


def call_gemini_api(prompt, max_tokens=4000):
    """Call Google Gemini API for content generation, fallback to Doubao on failure"""
    if not GOOGLE_API_KEY:
        log("未设置 GOOGLE_API_KEY，尝试豆包 API 兜底")
        return call_doubao_api(prompt, max_tokens)

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash:generateContent?key={GOOGLE_API_KEY}"
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
        log("尝试豆包 API 兜底...")
        return call_doubao_api(prompt, max_tokens)


# 5个平台热搜来源：(接口路径, title字段名, 显示名称)
TIANAPI_SOURCES = [
    ("weibohot",   "hotword", "微博热搜"),
    ("douyinhot",  "word",    "抖音热搜"),
    ("wxhottopic", "word",    "腾讯热搜"),
    ("nethot",     "keyword", "百度热搜"),
    ("networkhot", "title",   "全网热搜"),
]


def _fetch_tianapi(api_path, title_field, source_name, num=30):
    """通用天行热搜抓取器"""
    try:
        url = (
            f"https://apis.tianapi.com/{api_path}/index?"
            f"{urllib.parse.urlencode({'key': TIANAPI_KEY, 'num': num})}"
        )
        req = request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("code") != 200:
            log(f"{source_name} 接口错误: {data.get('msg')}")
            return []
        hot_list = data.get("result", {}).get("list", [])
        topics = [item.get(title_field, "").strip() for item in hot_list if item.get(title_field)]
        log(f"{source_name} 获取到 {len(topics)} 条热搜")
        return topics
    except Exception as e:
        log(f"{source_name} 获取失败: {e}")
        return []


def fetch_hot_topics():
    """每天按日期轮换抓取2个平台的热搜，合并去重后返回"""
    day_num = (datetime.now() - datetime(2026, 1, 1)).days
    idx1 = day_num % len(TIANAPI_SOURCES)
    idx2 = (day_num + 2) % len(TIANAPI_SOURCES)  # +2 保证不同平台
    selected = [TIANAPI_SOURCES[idx1], TIANAPI_SOURCES[idx2]]

    all_topics, source_names = [], []
    for api_path, title_field, source_name in selected:
        topics = _fetch_tianapi(api_path, title_field, source_name)
        all_topics.extend(topics)
        if topics:
            source_names.append(source_name)

    # 去重保序
    seen, unique = set(), []
    for t in all_topics:
        if t not in seen:
            seen.add(t)
            unique.append(t)

    combined = "+".join(source_names) if source_names else "热搜"
    return unique, combined


def fetch_gemini_search_topics():
    """Use Gemini 2.5 Flash + Google Search grounding to get real-time hot topics"""
    if not GOOGLE_API_KEY:
        return []
    today = datetime.now().strftime("%Y年%m月%d日")
    prompt = f"""今天是{today}。请用Google搜索，找出今天中国社交媒体上热议的与以下主题相关的话题：
青少年心理健康、亲子关系、学业压力、情绪管理、教育焦虑、青春期成长。

请列出10-15个具体的热议话题或社会现象，每行一个，不需要解释，直接列话题名称。
排除娱乐八卦、政治、自然灾害类话题。"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GOOGLE_API_KEY}"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}],
            "generationConfig": {"maxOutputTokens": 600}
        }
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with request.urlopen(req, timeout=20) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        text = result["candidates"][0]["content"]["parts"][0]["text"]
        topics = [line.strip().lstrip("0123456789.-、 ") for line in text.strip().splitlines() if line.strip() and len(line.strip()) > 3]
        topics = [t for t in topics if t][:15]
        log(f"Gemini搜索获取到 {len(topics)} 个实时热点话题")
        return topics
    except Exception as e:
        log(f"Gemini搜索话题获取失败: {e}")
        return []


# 学期日历选题库：按月份 + 特殊节点自动匹配时令话题
CALENDAR_TOPICS = {
    # 月份通用话题 (key: month 1-12)
    1:  [{"topic": "期末考试前的焦虑怎么疏解", "category": "学业压力"},
         {"topic": "孩子成绩出来了，怎么聊", "category": "亲子沟通"}],
    2:  [{"topic": "开学前的「假期综合症」怎么破", "category": "学业压力"},
         {"topic": "孩子过完年不想上学怎么办", "category": "情绪管理"}],
    3:  [{"topic": "新学期第一个月，孩子为什么容易崩", "category": "学业压力"},
         {"topic": "春天来了，孩子情绪也跟着乱", "category": "情绪管理"}],
    4:  [{"topic": "春季抑郁是真实存在的，家长要知道", "category": "情绪管理"},
         {"topic": "孩子说「活着没意思」，该怎么接这句话", "category": "情绪管理"}],
    5:  [{"topic": "五月病：青少年为什么5月最容易崩溃", "category": "情绪管理"},
         {"topic": "劳动节假期结束，孩子状态怎么接回来", "category": "学业压力"}],
    6:  [{"topic": "高考季来了，陪考家长的情绪怎么管", "category": "亲子沟通"},
         {"topic": "考前焦虑不是坏事，心理学怎么说", "category": "学业压力"}],
    7:  [{"topic": "暑假第一周，孩子为什么会突然变懒", "category": "学业压力"},
         {"topic": "暑假孩子天天玩手机，怎么跟他谈", "category": "亲子沟通"}],
    8:  [{"topic": "开学前焦虑：孩子不想回学校怎么办", "category": "学业压力"},
         {"topic": "暑假快结束了，收心要怎么收", "category": "学业压力"}],
    9:  [{"topic": "新学期新班级，社恐的孩子如何交到朋友", "category": "人际关系"},
         {"topic": "初一第一个月：中学和小学真的不一样", "category": "成长与变化"}],
    10: [{"topic": "国庆长假结束，孩子假期综合症来了", "category": "情绪管理"},
         {"topic": "青春期孩子突然不想和父母说话了", "category": "亲子沟通"}],
    11: [{"topic": "期中考试来了，孩子压力大到失眠怎么办", "category": "学业压力"},
         {"topic": "孩子说「我不如别人」，自信心怎么建", "category": "自我认知"}],
    12: [{"topic": "年底了，孩子情绪为什么容易低落", "category": "情绪管理"},
         {"topic": "元旦前后，用心理学帮孩子做年度回顾", "category": "自我认知"}],
}


def fetch_calendar_topic():
    """Pick a time-sensitive topic based on current month (school calendar logic)"""
    month = datetime.now().month
    candidates = CALENDAR_TOPICS.get(month, [])
    if not candidates:
        return None
    # 按月内天数轮换，同月不重复
    day = datetime.now().day
    topic = candidates[day % len(candidates)]
    log(f"日历选题 [{month}月]: {topic['topic']} (分类: {topic['category']})")
    return topic


def select_topic_from_hot(hot_topics, source="热搜"):
    """Use Gemini to pick the best psychology angle from trending topics"""
    topics_text = "\n".join(f"{i+1}. {t}" for i, t in enumerate(hot_topics[:30]))
    prompt = f"""你是"心光馨语"公众号的编辑，专注青少年心理健康和亲子关系。

以下是今日{source}热点话题（前30条）：
{topics_text}

请从中选一个最适合结合青少年心理学或亲子关系来写文章的话题，或者受热点启发提炼一个相关话题。

要求：
- 优先选与青少年情绪、学习、亲子关系、成长直接相关的话题
- 如没有直接相关的，可从社会热点（考试、就业、家庭、情感）中提炼一个心理学角度
- 话题要能引发家长或青少年的共鸣
- 避免选娱乐八卦、政治、灾难类话题

请用 JSON 格式回复（不要有代码块标记）：
{{"topic": "提炼后的话题", "category": "分类（学业压力/人际关系/情绪管理/亲子沟通/自我认知/趣味心理/成长与变化）", "hot_ref": "参考的热点词"}}"""

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
    """Select today's topic: 4-tier funnel
    1. 多平台热搜（每天轮换2个平台，5个平台循环覆盖）
    2. Gemini + Google Search 实时热点
    3. 学期日历时令话题
    4. 话题池轮询兜底
    """
    # 第1层：多平台热搜（轮换）
    hot_topics, source_name = fetch_hot_topics()
    if hot_topics:
        topic = select_topic_from_hot(hot_topics, source=source_name)
        if topic:
            return topic
        log("热搜选题失败，尝试 Gemini 搜索")

    # 第2层：Gemini + Google Search 实时热点
    gemini_topics = fetch_gemini_search_topics()
    if gemini_topics:
        topic = select_topic_from_hot(gemini_topics, source="Google实时搜索")
        if topic:
            return topic
        log("Gemini搜索选题失败，尝试日历选题")

    # 第3层：学期日历时令话题
    calendar_topic = fetch_calendar_topic()
    if calendar_topic:
        return calendar_topic

    # 第4层：话题池轮询兜底
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
        f"imagen-3.0-fast-generate-001:predict?key={GOOGLE_API_KEY}"
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

        # Image placeholder — render as warm-toned placeholder block (replaced when image URL available)
        if stripped.startswith("<!-- IMG_PLACEHOLDER"):
            html_parts.append(
                '<div style="width:100%;min-height:160px;margin:20px 0;'
                "background:linear-gradient(135deg,#FFF8E7,#FFEAA7);"
                "border-radius:12px;display:flex;align-items:center;"
                'justify-content:center;">'
                '<span style="color:#FF9F43;font-size:14px;">✦ 配图加载中 ✦</span></div>'
            )
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
                f'<h2 style="font-size:18px;font-weight:bold;color:#FF8C42;'
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
                    '<ul style="margin:12px 0;padding-left:0;list-style:none;">'
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
                f'<li style="margin:10px 0;line-height:1.8;font-size:16px;'
                f'color:#333;display:flex;align-items:flex-start;">'
                f'<span style="color:#FF9F43;margin-right:10px;flex-shrink:0;'
                f'font-size:18px;line-height:1.5;">●</span>'
                f'<span>{item_text}</span></li>'
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
    summary_prompt = f"""请用一句话（20-30字）概括这篇文章的核心内容，要求温暖有吸引力，适合做公众号文章摘要。
标题：{title}
注意：只输出摘要正文，不要加引号或任何前缀，不少于15字。"""
    summary = call_gemini_api(summary_prompt, max_tokens=150)
    if summary:
        summary = summary.strip().strip('"\'').split('\n')[0].strip()
        # 如果摘要太短，用默认值
        if len(summary) < 10:
            summary = f"新学期的孩子为什么容易情绪崩溃？心理学角度给家长一个温暖的解释"
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
        "articleType": "news",
    }
    if cover_url:
        payload["coverImage"] = cover_url

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
