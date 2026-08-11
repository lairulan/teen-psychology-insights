#!/usr/bin/env python3
"""
心光心理学自动发布脚本 v5.2
周一三五生成育儿/亲子沟通文章并发布到公众号，其余日期默认跳过

流程：
1. 按星期选择栏目（周一三五育儿，其余日期跳过；女性成长保留手动运行）
2. 读取微博热搜并提炼符合栏目定位的心理学角度
3. 用 DeepSeek V3 生成温暖、亲切、专业的公众号文章（豆包兜底）
4. 用豆包 Seedream 生成封面图 + 2张正文配图，上传 imgbb 获取 URL
5. 转换为微信公众号 HTML（暖橙色调 #FF9F43），配图替换占位符
6. 发布到"心光心理学"公众号

版本历史：
v1.0  初始版本
v2.0  全面升级：公众号改"心光馨语"，闺蜜聊天式，grace排版+暖橙色调
v2.1  API升级：Gemini 2.5 Flash + 豆包兜底，修复 GOOGLE_API_KEY 配置
v2.2  排版优化：H2颜色统一(#FF8C42)，列表flex布局，图片占位块
v2.3  选题增强：5平台热搜(微博/抖音/腾讯/百度/全网)每日轮换 + Gemini实时搜索兜底
v3.0  投产：修复发布bug，更新凭证，GitHub Actions 北京11:00定时运营
v3.1  配图修复：封面图+正文2张配图，Imagen 4 + imgbb 上传
v3.2  配图双引擎：Imagen 4 失败时自动切豆包 Seedream 兜底
v3.4  选题防重复：修复热搜JSON解析失败（增加截断修复+纯文本兜底），日历选题池扩至每月15个，新增7天去重机制
v4.0  引擎替换：DeepSeek V3 替代 Gemini，豆包 Seedream 为唯一配图引擎，移除 GOOGLE_API_KEY 依赖
v5.0  定位调整：周一三五育儿/亲子沟通，周二四六女性自我成长，按栏目人设生成内容
v5.1  内容质量门禁：硬去重、内容家族冷却、泛标题拦截
v5.2  人设专业度增强：栏目专业框架、练习模板、伪研究拦截、本地 Obsidian 同步脚本
v5.4  自动调度收敛为周一、周三、周五，其余日期默认跳过
"""

import argparse
import base64
import difflib
import json
import os
import random
import re
import sys
import urllib.parse
from datetime import datetime, timedelta
from urllib import request, error

# 配置
WECHAT_API_KEY = os.environ.get("WECHAT_API_KEY")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
ARK_API_KEY = os.environ.get("ARK_API_KEY") or os.environ.get("DOUBAO_API_KEY")
IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY")
# 天行数据 API Key（用于获取微博热搜）
TIANAPI_KEY = os.environ.get("TIANAPI_KEY", "a0ba59d286ea1b308f5719a4ba28d075")
APPID = "wx52189e9b012018e1"
API_BASE = "https://wx.limyai.com/api/openapi"
ACCOUNT_NAME = "心光心理学"
ACCOUNT_TAGLINE = "把心理学说给生活听"

# 工作目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORK_DIR = os.path.dirname(SCRIPT_DIR)
LOG_FILE = os.path.join(WORK_DIR, "logs", "daily-publish.log")

HARD_DUP_LOOKBACK_DAYS = 30
FAMILY_COOLDOWN_DAYS = 10
MAX_TOPIC_SELECTION_ATTEMPTS = 3

GENERIC_TITLE_PATTERNS = [
    "今天微博热搜",
    "那个话题",
    "这件事",
    "看得我心里一紧",
    "刷到一个热搜",
]

UNVERIFIED_AUTHORITY_PATTERNS = [
    r"心理学家做过.*实验",
    r"研究(发现|显示|表明)",
    r"实验(发现|显示|表明)",
    r"数据(发现|显示|表明)",
    r"大脑里.*区域",
    r"脑区.*活跃",
    r"\d+%",
]

CONTENT_FAMILY_RULES = [
    ("school_refusal", "厌学/不想上学", ["厌学", "不想上学", "讨厌上学", "讨厌学习", "逃学", "上学就"]),
    ("homework_learning", "作业/学习压力", ["作业", "写作业", "学习", "成绩", "考试", "期中", "期末", "高考", "中考", "小升初"]),
    ("anxiety_emotion", "焦虑/情绪失控", ["焦虑", "炸毛", "崩溃", "发脾气", "情绪", "喊救命", "累", "心累", "内耗"]),
    ("phone_screen", "手机/屏幕关系", ["手机", "刷屏", "屏幕", "沉迷", "短视频", "游戏"]),
    ("parent_child_comm", "亲子沟通", ["亲子", "沟通", "顶嘴", "唠叨", "说话", "吵架", "不愿意说"]),
    ("boundaries", "边界/讨好", ["边界", "拒绝", "讨好", "照顾别人", "怕让别人失望", "委屈", "过度解释"]),
    ("self_worth", "自我价值", ["自我价值", "自信", "不够好", "普通", "比较", "外表", "体重"]),
    ("intimacy", "亲密关系", ["亲密关系", "伴侣", "争吵", "被忽略", "分手", "恋爱", "婚姻"]),
    ("workplace", "职场情绪", ["职场", "工作", "上班", "同事", "老板", "加班", "职业"]),
]

PUBLISH_PROFILES = {
    "parenting": {
        "key": "parenting",
        "column_name": "育儿与亲子沟通",
        "schedule": "周一、周三、周五",
        "persona": "一位温柔、亲切、很懂家长处境的亲子沟通培训师",
        "tone": "温馨、亲切、具体、有陪伴感；像在陪家长慢慢把话说清楚，不指责、不吓唬、不制造焦虑",
        "target_audience": "正在养育孩子、关心亲子关系和家庭沟通的父母",
        "topic_goal": "从微博热搜中提炼育儿、亲子沟通、孩子情绪、学习压力、家庭关系相关角度",
        "topic_rules": [
            "必须落在育儿、亲子沟通、孩子情绪、家庭教育或家长自我调整上",
            "如果热搜本身不是育儿话题，要提炼它背后的家庭沟通或孩子成长角度",
            "避免娱乐八卦、极端个案、未经证实的传闻和制造家长焦虑的角度",
        ],
        "professional_frame": [
            "先描述孩子的可观察行为，不急着评价孩子对错",
            "把行为翻译成可能的感受和需要，让父母先看见关系层面的信号",
            "区分“接纳感受”和“允许所有行为”：温柔但有边界",
            "落到父母能练习的沟通句式、边界表达和家庭小练习",
        ],
        "practice_requirements": [
            "必须出现一个“先别急着说……”的提醒，帮父母停下自动反应",
            "必须出现一个“可以换成……”的话术替换模板",
            "必须设计一个30秒内能完成的亲子沟通练习",
        ],
        "professional_guardrails": [
            "不要把父母塑造成问题根源，也不要把孩子贴成懒、叛逆、玻璃心",
            "不编心理学实验、百分比、脑区、专家姓名；没有来源时不要写成研究结论",
            "需要提醒风险时，用“如果持续影响睡眠、饮食、上学或安全感，建议寻求专业支持”的温和表达",
        ],
        "categories": ["育儿沟通", "亲子关系", "孩子情绪", "学习陪伴", "家庭教育", "家长成长"],
        "fallback_topics": [
            {"topic": "孩子顶嘴时，父母怎么把话接住", "category": "亲子关系"},
            {"topic": "孩子写作业拖拉，背后可能不是懒", "category": "学习陪伴"},
            {"topic": "孩子发脾气时，先稳住关系再讲道理", "category": "孩子情绪"},
            {"topic": "父母越着急，孩子越不愿意说真话怎么办", "category": "育儿沟通"},
            {"topic": "孩子说不想上学，父母第一句话很重要", "category": "学习陪伴"},
            {"topic": "家庭里的好好说话，是孩子安全感的底色", "category": "家庭教育"},
            {"topic": "孩子沉迷手机时，先看见他的需要", "category": "亲子关系"},
            {"topic": "父母的温柔边界，才是孩子真正的规则感", "category": "家长成长"},
            {"topic": "孩子总在睡前说心事，父母可以怎么接", "category": "育儿沟通"},
            {"topic": "孩子被比较后沉默了，父母要先修复什么", "category": "孩子情绪"},
            {"topic": "父母道歉，不会让孩子没规矩", "category": "家长成长"},
            {"topic": "孩子突然锁房门，可能是在练习长大", "category": "亲子关系"},
            {"topic": "饭桌上的一句话，可能决定孩子愿不愿意聊", "category": "家庭教育"},
            {"topic": "孩子输不起时，先别急着教他大度", "category": "孩子情绪"},
            {"topic": "父母越想控制，孩子越想逃开怎么办", "category": "亲子关系"},
            {"topic": "孩子不敢求助，可能是怕被说没用", "category": "育儿沟通"},
        ],
        "article_structure": [
            "开头从微博热搜或一个家庭生活小场景切入，让家长觉得被理解",
            "中段用大白话解释一个亲子沟通或儿童发展心理学视角",
            "给出3个可直接照着说、照着做的沟通练习或话术",
            "结尾温暖收束，强调关系比输赢更重要",
        ],
        "must_include": [
            "至少给出2句可以直接对孩子说的话",
            "提醒父母先理解感受，再处理行为",
            "避免把孩子标签化为懒、叛逆、不懂事",
        ],
        "forbidden_phrases": ["废掉一个孩子", "毁掉孩子", "再不管就晚了", "家长必须", "孩子没救了"],
        "style_label": "温柔亲切的亲子沟通",
        "default_summary": "亲子沟通的一点温柔提醒",
        "cover_prompt": (
            "Warm healing watercolor illustration, Chinese parent and child in a gentle conversation, "
            "cozy home light, soft orange and light gold tones, caring parenting communication, "
            "emotionally warm, no text, high quality."
        ),
        "body_prompts": [
            "Warm watercolor illustration of a parent listening patiently to a child at home, soft warm orange light, caring communication, no text.",
            "Warm watercolor illustration of a family having a calm conversation, gentle boundaries, cozy home, soft gold tones, no text.",
        ],
    },
    "women_growth": {
        "key": "women_growth",
        "column_name": "女性自我成长",
        "schedule": "仅手动运行（不参与自动调度）",
        "persona": "一位温暖、专业、心理动力学方向的心理咨询师",
        "tone": "温暖、稳稳的、专业但不学术；像咨询室里慢慢陪读者看见自己的感受、关系模式和内在需要",
        "target_audience": "关注自我成长、关系边界、情绪照顾和内在稳定感的女性读者",
        "topic_goal": "围绕女性自我成长，结合微博热搜中可延展的情绪、关系、职场、亲密关系、家庭角色议题",
        "topic_rules": [
            "必须落在女性自我成长、内在关系、情绪照顾、边界感、自我价值或亲密关系上",
            "可以借微博热搜作为引子，但不要写成娱乐八卦或情绪宣泄",
            "保持心理动力学视角：看见关系模式、早年经验影响、重复的内在冲突和真实需要",
        ],
        "professional_frame": [
            "从一个现实事件或情绪反应进入，不急着劝读者变强",
            "看见情绪背后的内在需要、关系模式和旧经验留下的保护方式",
            "用一个心理动力学概念解释，但必须翻译成生活语言，例如防御、投射、依恋、重复性关系模式、内在冲突",
            "把理解落回当下：一个自我觉察问题、一个边界练习、一个现实小行动",
        ],
        "practice_requirements": [
            "至少出现2句以“你可以问自己：”开头的自我觉察问题",
            "必须包含一个不超过5分钟的自我照顾或边界练习",
            "必须把一个心理动力学概念讲成生活语言，不能堆术语",
        ],
        "professional_guardrails": [
            "不诊断读者，不用创伤、抑郁、人格等标签解释一切",
            "不把原生家庭写成宿命，也不把亲密关系写成操控技巧",
            "持续痛苦、失眠、惊恐、关系暴力或自伤风险，要建议寻求专业支持",
        ],
        "categories": ["自我成长", "情绪照顾", "关系边界", "自我价值", "亲密关系", "职场女性"],
        "fallback_topics": [
            {"topic": "为什么你总是在关系里先照顾别人", "category": "关系边界"},
            {"topic": "一个女人真正的稳定感，从允许自己有感受开始", "category": "情绪照顾"},
            {"topic": "停止过度解释，是自我边界开始长出来的信号", "category": "关系边界"},
            {"topic": "总怕让别人失望，可能是在重复旧关系里的自己", "category": "自我成长"},
            {"topic": "亲密关系里最消耗人的，不是争吵，而是长期被忽略", "category": "亲密关系"},
            {"topic": "女性的自我价值，不该只靠有用和懂事来证明", "category": "自我价值"},
            {"topic": "职场里的委屈感，常常也在提醒你看见边界", "category": "职场女性"},
            {"topic": "学会拒绝，不是变冷漠，而是开始尊重自己", "category": "关系边界"},
            {"topic": "你总想把关系解释清楚，可能是在害怕失去", "category": "亲密关系"},
            {"topic": "真正的自我照顾，是允许自己慢一点", "category": "情绪照顾"},
            {"topic": "为什么被冷落时，你会先怀疑自己", "category": "自我价值"},
            {"topic": "职场里不敢表达需求，可能不是你太弱", "category": "职场女性"},
            {"topic": "关系里的安全感，不该只靠猜对方心情维持", "category": "亲密关系"},
            {"topic": "当你开始不讨好，关系才有机会更真实", "category": "关系边界"},
            {"topic": "成年女性的疲惫，有时来自一直扮演没事的人", "category": "情绪照顾"},
            {"topic": "你值得被爱，不需要一直证明自己有用", "category": "自我价值"},
        ],
        "article_structure": [
            "开头用微博热搜或一个女性日常困境切入，不猎奇、不评判",
            "中段用心理动力学视角解释：情绪背后的需要、关系模式、内在冲突",
            "给出3个温和的自我觉察练习或关系边界练习",
            "结尾把读者带回自我照顾和现实行动",
        ],
        "must_include": [
            "至少出现2个自我觉察问题",
            "用通俗语言解释一个心理动力学视角",
            "避免诊断化，不承诺疗效；遇到持续痛苦时建议寻求专业支持",
        ],
        "forbidden_phrases": ["女人一定要", "彻底逆袭", "拿捏男人", "原生家庭毁了你", "治愈所有创伤", "你太敏感了"],
        "style_label": "温暖专业的心理动力学自我成长",
        "default_summary": "陪你看见内在需要与关系边界",
        "cover_prompt": (
            "Warm elegant watercolor illustration of an adult woman sitting by a window with a journal, "
            "soft morning light, calm self-reflection, warm orange and gentle teal accents, psychological growth, "
            "no text, high quality."
        ),
        "body_prompts": [
            "Warm watercolor illustration of an adult woman journaling and reflecting calmly, cozy room, soft light, psychological self-growth, no text.",
            "Warm watercolor illustration of a woman setting a gentle boundary in conversation, respectful relationship, soft orange and teal accents, no text.",
        ],
    },
}

WEEKDAY_PROFILE = {
    0: "parenting",      # Monday
    2: "parenting",      # Wednesday
    4: "parenting",      # Friday
}

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


def get_publish_profile(now=None):
    """Return today's content profile, or None on non-publishing days."""
    now = now or datetime.now()
    profile_key = WEEKDAY_PROFILE.get(now.weekday())
    if not profile_key:
        return None
    return PUBLISH_PROFILES[profile_key]


def fetch_weibo_hot_topics(num=50):
    """Fetch Weibo hot search topics as the primary editorial source."""
    return _fetch_tianapi("weibohot", "hotword", "微博热搜", num=num)


def choose_fallback_profile_topic(profile, recent_titles=None, recent_history=None):
    """Pick a profile-specific fallback topic when Weibo hot topics are unavailable."""
    candidates = profile["fallback_topics"]
    if not candidates:
        return None

    recent_history = recent_history or get_article_history(days=HARD_DUP_LOOKBACK_DAYS)
    recent_titles = recent_titles or [item["title"] for item in recent_history]
    today = datetime.now()
    base_index = (today - datetime(2026, 1, 1)).days % len(candidates)
    for offset in range(len(candidates)):
        idx = (base_index + offset) % len(candidates)
        topic = candidates[idx]
        reason = _topic_rejection_reason(
            topic["topic"],
            recent_history=recent_history,
            recent_titles=recent_titles,
            profile=profile,
        )
        if reason:
            log(f"{profile['column_name']}兜底选题跳过: {topic['topic']} | {reason}")
            continue
        log(f"{profile['column_name']}兜底选题: {topic['topic']} (分类: {topic['category']})")
        return {**topic, "source": "栏目话题池", "profile": profile}

    # Relax the family cooldown only after all candidates were rejected. Exact/similar
    # title duplication remains blocked.
    for offset in range(len(candidates)):
        idx = (base_index + offset) % len(candidates)
        topic = candidates[idx]
        reason = _topic_rejection_reason(
            topic["topic"],
            recent_history=recent_history,
            recent_titles=recent_titles,
            profile=profile,
            enforce_family=False,
        )
        if not reason:
            log(f"{profile['column_name']}兜底选题（放宽内容家族冷却）: {topic['topic']} (分类: {topic['category']})")
            return {**topic, "source": "栏目话题池", "profile": profile}

    log(f"{profile['column_name']}兜底选题全部与近期标题相似，停止发布以避免重复")
    return None


def get_profile_by_key(profile_key):
    profile = PUBLISH_PROFILES.get(profile_key)
    if not profile:
        valid = ", ".join(PUBLISH_PROFILES.keys())
        raise ValueError(f"未知栏目: {profile_key}，可选: {valid}")
    return profile


def call_deepseek_api(prompt, max_tokens=4000):
    """Call DeepSeek V3 API (primary LLM)"""
    if not DEEPSEEK_API_KEY:
        return None
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.85,
    }
    req = request.Request(
        "https://api.deepseek.com/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=90) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        log(f"DeepSeek API 调用失败: {e}")
        return None


def call_doubao_api(prompt, max_tokens=4000):
    """Call Doubao ARK API as fallback for content generation (OpenAI-compatible)"""
    if not ARK_API_KEY:
        return None
    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    payload = {
        "model": "doubao-seed-2-0-lite-260215",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.85,
    }
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {ARK_API_KEY}",
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
    """统一 LLM 调用：DeepSeek V3 主力，豆包兜底"""
    result = call_deepseek_api(prompt, max_tokens)
    if result:
        return result
    log("DeepSeek 失败，尝试豆包兜底...")
    return call_doubao_api(prompt, max_tokens)

# Bing News RSS 垂直搜索词（精准命中青少年心理/亲子话题）
BING_NEWS_QUERIES = [
    "青少年 心理健康",
    "孩子 情绪 焦虑",
    "亲子关系 沟通",
    "学生 压力 厌学",
    "青春期 叛逆 家长",
]


def fetch_bing_news_topics():
    """用 Bing News RSS 垂直搜索当日青少年心理/亲子热点，每词抓5条，共25条"""
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    all_titles, seen = [], set()
    for q in BING_NEWS_QUERIES:
        url = (
            "https://cn.bing.com/news/search?"
            + urllib.parse.urlencode({"q": q, "format": "rss", "cc": "zh-cn", "setlang": "zh-cn"})
        )
        try:
            req = request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                "Accept-Language": "zh-CN,zh;q=0.9",
            })
            with request.urlopen(req, timeout=10, context=ctx) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")
            # 提取 <item> 内的标题
            items = re.findall(
                r"<item>.*?<title[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>.*?</item>",
                raw, re.DOTALL
            )
            for t in items[:5]:
                t = t.strip()
                # 过滤：去广告/机构推广词、太短的、重复的
                if len(t) > 6 and t not in seen and "广告" not in t and "招生" not in t:
                    seen.add(t)
                    all_titles.append(t)
        except Exception as e:
            log(f"Bing新闻搜索失败 [{q}]: {e}")

    log(f"Bing News 垂直搜索获取到 {len(all_titles)} 条心理/亲子资讯")
    return all_titles


# 天行热搜（作为兜底补充，已知百度/全网频率受限）
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
    """用 DeepSeek 根据当前时令生成实时感话题（替代 Gemini Search）"""
    today = datetime.now().strftime("%Y年%m月%d日")
    month = datetime.now().month
    prompt = f"""今天是{today}。你是一位关注青少年心理健康的编辑。
请根据当前时节（{month}月），列出10个在中国家长和学生群体中近期可能热议的话题，聚焦：
青少年情绪、学业压力、亲子关系、成长烦恼、青春期心理。

要求：每行一个话题，话题具体有代入感，符合当前时令（如月考/开学/放假/节假日等），不超过15字。
不要编号，不要解释，只输出话题列表。"""
    try:
        result = call_deepseek_api(prompt, max_tokens=500)
        if not result:
            return []
        topics = [line.strip().lstrip("0123456789.-、·•* ") for line in result.strip().splitlines() if line.strip() and len(line.strip()) > 3]
        topics = [t for t in topics if t][:15]
        log(f"DeepSeek时令话题生成 {len(topics)} 个")
        return topics
    except Exception as e:
        log(f"DeepSeek时令话题获取失败: {e}")
        return []


# 学期日历选题库：按月份自动匹配时令话题，每月15个确保不短期重复
CALENDAR_TOPICS = {
    1: [
        {"topic": "期末考试前的焦虑怎么疏解", "category": "学业压力"},
        {"topic": "孩子成绩出来了，怎么聊", "category": "亲子沟通"},
        {"topic": "寒假第一天，孩子就跟你吵架了", "category": "亲子沟通"},
        {"topic": "期末没考好，孩子哭了怎么安慰", "category": "情绪管理"},
        {"topic": "寒假计划总是泡汤怎么办", "category": "学业压力"},
        {"topic": "过年走亲戚，孩子被比较了怎么办", "category": "自我认知"},
        {"topic": "孩子寒假只想宅家不出门", "category": "人际关系"},
        {"topic": "为什么放假了孩子反而不开心", "category": "情绪管理"},
        {"topic": "考试排名真的重要吗", "category": "学业压力"},
        {"topic": "孩子说不想过年怎么回事", "category": "情绪管理"},
        {"topic": "寒假怎么跟孩子好好相处", "category": "亲子沟通"},
        {"topic": "孩子对压岁钱的态度藏着什么心理", "category": "趣味心理"},
        {"topic": "为什么孩子放假后脾气更大了", "category": "情绪管理"},
        {"topic": "新年目标怎么帮孩子定才不会放弃", "category": "成长与变化"},
        {"topic": "孩子不想见亲戚是社恐吗", "category": "人际关系"},
    ],
    2: [
        {"topic": "开学前的假期综合症怎么破", "category": "学业压力"},
        {"topic": "孩子过完年不想上学怎么办", "category": "情绪管理"},
        {"topic": "开学前一晚孩子焦虑失眠", "category": "学业压力"},
        {"topic": "新学期换了老师孩子不适应", "category": "人际关系"},
        {"topic": "孩子说开学就想哭", "category": "情绪管理"},
        {"topic": "寒假作业没写完孩子慌了", "category": "学业压力"},
        {"topic": "春节后孩子生物钟全乱了", "category": "情绪管理"},
        {"topic": "开学第一周怎么帮孩子调状态", "category": "亲子沟通"},
        {"topic": "孩子开学就说肚子疼是装的吗", "category": "趣味心理"},
        {"topic": "为什么开学后亲子关系反而好了", "category": "亲子沟通"},
        {"topic": "情人节跟孩子聊聊什么是喜欢", "category": "成长与变化"},
        {"topic": "孩子突然换了一个好朋友", "category": "人际关系"},
        {"topic": "开学考试没考好怎么鼓励", "category": "学业压力"},
        {"topic": "孩子说新同桌很讨厌", "category": "人际关系"},
        {"topic": "为什么假期越长越不想开学", "category": "趣味心理"},
    ],
    3: [
        {"topic": "新学期第一个月，孩子为什么容易崩", "category": "学业压力"},
        {"topic": "春天来了，孩子情绪也跟着乱", "category": "情绪管理"},
        {"topic": "三月是孩子最容易厌学的时候", "category": "学业压力"},
        {"topic": "春游前孩子为什么特别兴奋", "category": "趣味心理"},
        {"topic": "孩子说同学都不跟他玩了", "category": "人际关系"},
        {"topic": "女孩子开始在意体重了怎么引导", "category": "自我认知"},
        {"topic": "孩子突然不想上兴趣班了", "category": "亲子沟通"},
        {"topic": "春天犯困不是懒，是身体在说话", "category": "趣味心理"},
        {"topic": "开学一个月，孩子说压力好大", "category": "学业压力"},
        {"topic": "为什么春天更容易发脾气", "category": "情绪管理"},
        {"topic": "孩子开始偷偷写日记了", "category": "成长与变化"},
        {"topic": "怎么在不唠叨的前提下关心孩子", "category": "亲子沟通"},
        {"topic": "植树节聊聊孩子的成长节奏", "category": "成长与变化"},
        {"topic": "孩子说老师不喜欢他", "category": "人际关系"},
        {"topic": "月考没考好，是孩子不努力吗", "category": "学业压力"},
    ],
    4: [
        {"topic": "春季情绪低落是真实存在的", "category": "情绪管理"},
        {"topic": "孩子说活着没意思该怎么接话", "category": "情绪管理"},
        {"topic": "期中考试倒计时孩子开始焦虑了", "category": "学业压力"},
        {"topic": "清明节怎么跟孩子聊生死话题", "category": "亲子沟通"},
        {"topic": "孩子开始跟你顶嘴了，是好事还是坏事", "category": "成长与变化"},
        {"topic": "为什么孩子总觉得别人比自己好", "category": "自我认知"},
        {"topic": "春天孩子特别容易跟同学起冲突", "category": "人际关系"},
        {"topic": "孩子学习上总是三分钟热度", "category": "学业压力"},
        {"topic": "为什么劝孩子别玩手机越劝越玩", "category": "趣味心理"},
        {"topic": "孩子说周末也不想出门", "category": "情绪管理"},
        {"topic": "被老师批评后孩子不想上学了", "category": "学业压力"},
        {"topic": "孩子开始关注异性正常吗", "category": "成长与变化"},
        {"topic": "春天过敏和情绪有什么关系", "category": "趣味心理"},
        {"topic": "孩子考试前总想上厕所是紧张吗", "category": "趣味心理"},
        {"topic": "四月了，帮孩子做个学期中间小复盘", "category": "学业压力"},
    ],
    5: [
        {"topic": "五月病：青少年为什么5月最容易崩溃", "category": "情绪管理"},
        {"topic": "劳动节假期结束孩子状态怎么接回来", "category": "学业压力"},
        {"topic": "母亲节聊聊妈妈的情绪也需要被看见", "category": "亲子沟通"},
        {"topic": "期中考试成绩出来了怎么谈", "category": "亲子沟通"},
        {"topic": "孩子说学这些有什么用", "category": "学业压力"},
        {"topic": "为什么到了学期中间最容易放弃", "category": "趣味心理"},
        {"topic": "初三孩子五月压力到了顶峰", "category": "学业压力"},
        {"topic": "孩子突然不想跟最好的朋友玩了", "category": "人际关系"},
        {"topic": "孩子总在睡前跟你说心里话", "category": "亲子沟通"},
        {"topic": "为什么孩子在家和在外是两个样", "category": "趣味心理"},
        {"topic": "孩子说大家都有手机就我没有", "category": "亲子沟通"},
        {"topic": "小升初的焦虑从五月就开始了", "category": "学业压力"},
        {"topic": "孩子被同学取了外号很难过", "category": "人际关系"},
        {"topic": "夏天来了孩子特别好动坐不住", "category": "情绪管理"},
        {"topic": "孩子开始锁房门了怎么看", "category": "成长与变化"},
    ],
    6: [
        {"topic": "高考季来了陪考家长的情绪怎么管", "category": "亲子沟通"},
        {"topic": "考前焦虑不是坏事心理学怎么说", "category": "学业压力"},
        {"topic": "期末考试周孩子说脑子转不动了", "category": "学业压力"},
        {"topic": "暑假要来了孩子比大人还激动", "category": "趣味心理"},
        {"topic": "父亲节聊聊爸爸在育儿中的角色", "category": "亲子沟通"},
        {"topic": "中考前一周家长比孩子还紧张", "category": "情绪管理"},
        {"topic": "考完试孩子大哭了一场", "category": "情绪管理"},
        {"topic": "孩子说考砸了不想回家", "category": "亲子沟通"},
        {"topic": "毕业季的分离焦虑", "category": "人际关系"},
        {"topic": "成绩单上的评语该怎么看", "category": "学业压力"},
        {"topic": "为什么一到大考就拉肚子", "category": "趣味心理"},
        {"topic": "暑假兴趣班该不该报", "category": "亲子沟通"},
        {"topic": "孩子说终于自由了让人心疼", "category": "情绪管理"},
        {"topic": "考完试后孩子为什么反而更焦虑", "category": "趣味心理"},
        {"topic": "六月的离别和新开始", "category": "成长与变化"},
    ],
    7: [
        {"topic": "暑假第一周孩子为什么会突然变懒", "category": "学业压力"},
        {"topic": "暑假孩子天天玩手机怎么跟他谈", "category": "亲子沟通"},
        {"topic": "暑假里亲子关系反而更紧张了", "category": "亲子沟通"},
        {"topic": "孩子暑假每天睡到中午正常吗", "category": "趣味心理"},
        {"topic": "暑假旅行中的亲子沟通时刻", "category": "亲子沟通"},
        {"topic": "孩子说暑假好无聊没意思", "category": "情绪管理"},
        {"topic": "暑假作业拖到最后一天的心理", "category": "趣味心理"},
        {"topic": "夏令营回来孩子像变了个人", "category": "成长与变化"},
        {"topic": "孩子暑假交了个网友你担心吗", "category": "人际关系"},
        {"topic": "为什么暑假是培养习惯的好时机", "category": "成长与变化"},
        {"topic": "孩子说想学一个你觉得没用的东西", "category": "自我认知"},
        {"topic": "暑假看了一部电影对孩子影响很大", "category": "成长与变化"},
        {"topic": "热到烦躁的时候怎么管理情绪", "category": "情绪管理"},
        {"topic": "孩子暑假只想待在空调房里", "category": "情绪管理"},
        {"topic": "暑假过半怎么帮孩子规划下半场", "category": "学业压力"},
    ],
    8: [
        {"topic": "开学前焦虑：孩子不想回学校怎么办", "category": "学业压力"},
        {"topic": "暑假快结束了收心要怎么收", "category": "学业压力"},
        {"topic": "暑假作业突击赶工的心理状态", "category": "趣味心理"},
        {"topic": "孩子说新学期想重新开始", "category": "成长与变化"},
        {"topic": "开学前帮孩子做个心理准备", "category": "亲子沟通"},
        {"topic": "为什么越临近开学越焦虑", "category": "趣味心理"},
        {"topic": "升学焦虑不只是孩子的事", "category": "亲子沟通"},
        {"topic": "八月的晚上适合跟孩子谈心", "category": "亲子沟通"},
        {"topic": "孩子暑假胖了好几斤在意得不行", "category": "自我认知"},
        {"topic": "军训前孩子有点害怕怎么鼓励", "category": "人际关系"},
        {"topic": "孩子想买新学期的东西是虚荣吗", "category": "自我认知"},
        {"topic": "开学前最后一周的仪式感", "category": "成长与变化"},
        {"topic": "孩子说换学校了一个朋友都没有", "category": "人际关系"},
        {"topic": "暑假结尾的分离焦虑", "category": "情绪管理"},
        {"topic": "为什么快乐的假期总感觉过得特别快", "category": "趣味心理"},
    ],
    9: [
        {"topic": "新学期新班级社恐的孩子如何交到朋友", "category": "人际关系"},
        {"topic": "初一第一个月中学和小学真的不一样", "category": "成长与变化"},
        {"topic": "高一孩子说跟不上节奏", "category": "学业压力"},
        {"topic": "开学典礼后孩子突然很有干劲", "category": "趣味心理"},
        {"topic": "孩子说新老师好凶不想上他的课", "category": "人际关系"},
        {"topic": "教师节聊聊好老师对孩子的影响", "category": "人际关系"},
        {"topic": "中秋节聊聊思念和归属感", "category": "情绪管理"},
        {"topic": "九月是孩子适应力的考验", "category": "成长与变化"},
        {"topic": "孩子说食堂饭不好吃不想住校", "category": "亲子沟通"},
        {"topic": "为什么新学期的前两周最关键", "category": "学业压力"},
        {"topic": "孩子开学就感冒了是心理作用吗", "category": "趣味心理"},
        {"topic": "住校的孩子想家怎么安慰", "category": "情绪管理"},
        {"topic": "新同桌不合拍怎么办", "category": "人际关系"},
        {"topic": "孩子说作业比上学期多了好多", "category": "学业压力"},
        {"topic": "开学一个月后是退步还是适应", "category": "成长与变化"},
    ],
    10: [
        {"topic": "国庆长假结束孩子假期综合症来了", "category": "情绪管理"},
        {"topic": "青春期孩子突然不想和父母说话了", "category": "亲子沟通"},
        {"topic": "十月是孩子开始真正进入学习状态的月份", "category": "学业压力"},
        {"topic": "秋天的情绪低落和夏天不一样", "category": "情绪管理"},
        {"topic": "期中考试要来了怎么减压", "category": "学业压力"},
        {"topic": "孩子说班上有人欺负他", "category": "人际关系"},
        {"topic": "为什么秋天适合跟孩子深聊", "category": "亲子沟通"},
        {"topic": "孩子开始在意班级排名了", "category": "自我认知"},
        {"topic": "换季时节孩子容易烦躁", "category": "情绪管理"},
        {"topic": "孩子不想参加学校运动会", "category": "人际关系"},
        {"topic": "为什么天一凉人就容易伤感", "category": "趣味心理"},
        {"topic": "十月份的亲子冲突高峰期", "category": "亲子沟通"},
        {"topic": "孩子开始有了自己的小秘密", "category": "成长与变化"},
        {"topic": "重阳节聊聊孩子和老人的关系", "category": "人际关系"},
        {"topic": "孩子说选课好纠结帮帮我", "category": "自我认知"},
    ],
    11: [
        {"topic": "期中考试来了孩子压力大到失眠怎么办", "category": "学业压力"},
        {"topic": "孩子说我不如别人自信心怎么建", "category": "自我认知"},
        {"topic": "十一月是最容易厌学的时候", "category": "学业压力"},
        {"topic": "天冷了孩子起不来床怎么办", "category": "趣味心理"},
        {"topic": "期中成绩出来家长会怎么开", "category": "亲子沟通"},
        {"topic": "感恩节聊聊怎么教孩子表达感谢", "category": "亲子沟通"},
        {"topic": "孩子开始讨厌某一科了", "category": "学业压力"},
        {"topic": "青春期孩子为什么变得敏感多疑", "category": "情绪管理"},
        {"topic": "孩子说同学都在补课我也想去", "category": "学业压力"},
        {"topic": "冬天来了孩子情绪也冷了", "category": "情绪管理"},
        {"topic": "孩子开始关注社会新闻了", "category": "成长与变化"},
        {"topic": "为什么有些孩子天一冷就不想动", "category": "趣味心理"},
        {"topic": "孩子说想当网红你怎么看", "category": "自我认知"},
        {"topic": "十一月的亲子关系温度计", "category": "亲子沟通"},
        {"topic": "孩子总是临考前才拼命的心理", "category": "趣味心理"},
    ],
    12: [
        {"topic": "年底了孩子情绪为什么容易低落", "category": "情绪管理"},
        {"topic": "用心理学帮孩子做年度回顾", "category": "自我认知"},
        {"topic": "期末考试倒计时的焦虑怎么缓解", "category": "学业压力"},
        {"topic": "圣诞节聊聊孩子心中的愿望", "category": "亲子沟通"},
        {"topic": "冬天的被窝和上学哪个更重要", "category": "趣味心理"},
        {"topic": "孩子这学期进步了怎么夸", "category": "亲子沟通"},
        {"topic": "孩子这学期退步了怎么聊", "category": "亲子沟通"},
        {"topic": "元旦前后孩子的新年期待", "category": "成长与变化"},
        {"topic": "年末了帮孩子整理情绪账本", "category": "情绪管理"},
        {"topic": "孩子说明年想变得不一样", "category": "自我认知"},
        {"topic": "寒假要来了孩子已经开始规划了", "category": "学业压力"},
        {"topic": "为什么年底特别容易怀旧", "category": "趣味心理"},
        {"topic": "十二月是学期最后的冲刺期", "category": "学业压力"},
        {"topic": "冬至聊聊家的温暖", "category": "亲子沟通"},
        {"topic": "孩子的年度成长你看到了吗", "category": "成长与变化"},
    ],
}


def _parse_article_file(path):
    """Read one generated article and return metadata used by editorial guards."""
    meta = {
        "file": os.path.basename(path),
        "title": "",
        "date": None,
        "column": "",
        "category": "",
        "source": "",
        "hot_ref": "",
        "topic_family": "",
        "family": None,
    }
    filename_match = re.search(r"article_(\d{8})\.md$", os.path.basename(path))
    if filename_match:
        try:
            meta["date"] = datetime.strptime(filename_match.group(1), "%Y%m%d")
        except ValueError:
            pass

    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return meta

    for line in lines[:40]:
        stripped = line.strip()
        if stripped.startswith("title:"):
            meta["title"] = stripped[6:].strip().strip('"\'')
        elif stripped.startswith("date:"):
            try:
                meta["date"] = datetime.strptime(stripped[5:].strip()[:10], "%Y-%m-%d")
            except ValueError:
                pass
        elif stripped.startswith("column:"):
            meta["column"] = stripped[7:].strip()
        elif stripped.startswith("category:"):
            meta["category"] = stripped[9:].strip()
        elif stripped.startswith("source:"):
            meta["source"] = stripped[7:].strip()
        elif stripped.startswith("hot_ref:"):
            meta["hot_ref"] = stripped[8:].strip()
        elif stripped.startswith("topic_family:"):
            meta["topic_family"] = stripped[13:].strip()
        elif stripped.startswith("# ") and not meta["title"]:
            meta["title"] = stripped[2:].strip()

    detected_family = detect_content_family(" ".join([meta["title"], meta["category"], meta["hot_ref"], meta["topic_family"]]))
    meta["family"] = detected_family
    return meta


def get_article_history(days=None, limit=None):
    """Scan generated article files instead of assuming consecutive daily files."""
    history = []
    today = datetime.now()
    for filename in os.listdir(WORK_DIR):
        if not re.match(r"article_\d{8}\.md$", filename):
            continue
        record = _parse_article_file(os.path.join(WORK_DIR, filename))
        if not record.get("title"):
            continue
        if days is not None and record.get("date"):
            if (today - record["date"]).days > days:
                continue
        history.append(record)

    history.sort(key=lambda item: (item.get("date") or datetime.min, item["file"]), reverse=True)
    if limit:
        history = history[:limit]
    return history


def get_recent_titles(days=HARD_DUP_LOOKBACK_DAYS):
    """读取最近 N 天已发布的文章标题，用于去重"""
    titles = [item["title"] for item in get_article_history(days=days)]
    if titles:
        log(f"近{days}天已发布文章: {titles[:12]}")
    return titles


def _normalize_text(text):
    text = (text or "").lower()
    text = re.sub(r"[\s，。！？、；：,.!?;:\"'“”‘’（）()《》【】\[\]#*_\-—~·|/\\]+", "", text)
    for token in ["孩子", "父母", "家长", "妈妈", "爸爸", "心理学", "真正", "可能", "为什么", "怎么办", "这句话", "背后"]:
        text = text.replace(token, "")
    return text


def _char_ngrams(text, n=2):
    if len(text) <= n:
        return {text} if text else set()
    return {text[i:i + n] for i in range(len(text) - n + 1)}


def _text_similarity(left, right):
    left_norm = _normalize_text(left)
    right_norm = _normalize_text(right)
    if not left_norm or not right_norm:
        return 0.0
    if left_norm in right_norm or right_norm in left_norm:
        return 1.0
    seq_ratio = difflib.SequenceMatcher(None, left_norm, right_norm).ratio()
    left_grams = _char_ngrams(left_norm)
    right_grams = _char_ngrams(right_norm)
    gram_ratio = len(left_grams & right_grams) / len(left_grams | right_grams) if left_grams and right_grams else 0.0
    return max(seq_ratio, gram_ratio)


def _is_similar_topic(topic_text, recent_titles):
    """判断话题是否与近期文章标题相似，避免只靠 LLM 提示自觉去重。"""
    if not recent_titles:
        return False
    for title in recent_titles:
        if _text_similarity(topic_text, title) >= 0.72:
            return True
    return False


def detect_content_family(text):
    """Map titles/topics into coarse content families for cooldown-based diversity."""
    text = (text or "").lower()
    for priority_key in ["school_refusal", "phone_screen"]:
        for family_key, family_label, keywords in CONTENT_FAMILY_RULES:
            if family_key == priority_key and any(keyword.lower() in text for keyword in keywords):
                return (family_key, family_label)

    best_family = None
    best_score = 0
    for family_key, family_label, keywords in CONTENT_FAMILY_RULES:
        score = sum(1 for keyword in keywords if keyword.lower() in text)
        if score > best_score:
            best_family = (family_key, family_label)
            best_score = score
    return best_family


def _recent_family_records(family_key, history, days=FAMILY_COOLDOWN_DAYS):
    today = datetime.now()
    records = []
    for item in history or []:
        if not item.get("family") or item["family"][0] != family_key:
            continue
        item_date = item.get("date")
        if item_date and (today - item_date).days <= days:
            records.append(item)
    return records


def _topic_rejection_reason(topic_text, recent_history=None, recent_titles=None, profile=None, enforce_family=True):
    """Return a concrete reason when a candidate should not be used."""
    if not topic_text or len(topic_text.strip()) < 4:
        return "话题过短"

    recent_history = recent_history or []
    recent_titles = recent_titles or [item["title"] for item in recent_history]
    if _is_similar_topic(topic_text, recent_titles):
        return "与近30天标题过于相似"

    family = detect_content_family(topic_text)
    cooldown_families = {
        "school_refusal",
        "homework_learning",
        "anxiety_emotion",
        "phone_screen",
        "boundaries",
        "self_worth",
        "intimacy",
        "workplace",
    }
    if enforce_family and family and family[0] in cooldown_families:
        family_records = _recent_family_records(family[0], recent_history, days=FAMILY_COOLDOWN_DAYS)
        if family_records:
            recent_titles_text = "、".join(item["title"] for item in family_records[:3])
            return f"内容家族「{family[1]}」{FAMILY_COOLDOWN_DAYS}天内已写过：{recent_titles_text}"

    if profile and topic_text.strip() in [item["topic"] for item in profile.get("fallback_topics", [])]:
        return None
    return None


def _title_quality_issue(title, recent_history=None):
    if not title or len(_normalize_text(title)) < 6:
        return "标题过短或无有效信息"
    if any(pattern in title for pattern in GENERIC_TITLE_PATTERNS):
        return "标题过泛，像临时热搜占位标题"
    if _is_similar_topic(title, [item["title"] for item in recent_history or []]):
        return "最终标题与近30天标题过于相似"
    return None


def validate_article_output(article, topic_info, recent_history=None):
    """Final publish gate for title/content quality before images and WeChat upload."""
    if not article:
        return ["文章为空"]
    issues = []
    profile = topic_info.get("profile") or PUBLISH_PROFILES["parenting"]
    content = article.get("content", "")
    title_issue = _title_quality_issue(article.get("title", ""), recent_history=recent_history)
    if title_issue:
        issues.append(title_issue)
    forbidden_hits = [
        phrase for phrase in profile.get("forbidden_phrases", [])
        if phrase and phrase in (article.get("title", "") + content)
    ]
    if forbidden_hits:
        issues.append("出现禁用表达：" + "、".join(forbidden_hits[:3]))
    unverifiable_hits = [
        pattern for pattern in UNVERIFIED_AUTHORITY_PATTERNS
        if re.search(pattern, content)
    ]
    if unverifiable_hits:
        issues.append("出现未核验的研究/实验/数据表达，需改为实践观察或生活化解释")
    if article.get("word_count", 0) > 1500:
        issues.append("文章超过1500字")
    if article.get("word_count", 0) < 700:
        issues.append("文章低于700字，信息量不足")
    for placeholder in ["<!-- IMG_PLACEHOLDER_1 -->", "<!-- IMG_PLACEHOLDER_2 -->"]:
        if placeholder not in content:
            issues.append(f"缺少配图占位符 {placeholder}")
    if profile.get("key") == "parenting":
        if "可以换成" not in content:
            issues.append("育儿线缺少“可以换成……”的话术替换模板")
        if "30秒" not in content and "30 秒" not in content:
            issues.append("育儿线缺少30秒亲子沟通练习")
    if profile.get("key") == "women_growth":
        if content.count("你可以问自己") < 2:
            issues.append("女性成长线缺少至少2个“你可以问自己”觉察问题")
        psychodynamic_markers = ["心理动力学", "关系模式", "防御", "投射", "依恋", "重复性关系", "内在冲突"]
        if not any(marker in content for marker in psychodynamic_markers):
            issues.append("女性成长线缺少清晰的心理动力学视角")
    return issues


def _format_recent_history_for_prompt(history, limit=10):
    lines = []
    for item in (history or [])[:limit]:
        family_label = item["family"][1] if item.get("family") else "其他"
        lines.append(f"- {item['title']}（{item.get('category', '')} / {family_label}）")
    return "\n".join(lines)


def fetch_calendar_topic(recent_titles=None):
    """Pick a time-sensitive topic based on current month, skip recently used topics"""
    month = datetime.now().month
    candidates = CALENDAR_TOPICS.get(month, [])
    if not candidates:
        return None
    day = datetime.now().day
    # 从 day % len 开始，依次尝试每个候选，跳过已用的
    for offset in range(len(candidates)):
        idx = (day + offset) % len(candidates)
        topic = candidates[idx]
        if not _is_similar_topic(topic["topic"], recent_titles):
            log(f"日历选题 [{month}月]: {topic['topic']} (分类: {topic['category']})")
            return topic
        log(f"日历选题跳过（与近期文章相似）: {topic['topic']}")
    # 全部重复，返回第一个（极端情况）
    topic = candidates[day % len(candidates)]
    log(f"日历选题（全部相似，强制使用）: {topic['topic']}")
    return topic


def _repair_json(text):
    """尝试修复不完整的 JSON 字符串"""
    text = text.strip()
    # 清理 markdown 代码块
    text = re.sub(r"```(?:json)?\s*|```", "", text).strip()
    # 去掉 JSON 前后多余的文字，只保留 { ... } 部分
    start = text.find("{")
    if start == -1:
        return None
    text = text[start:]

    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 修复截断的 JSON：补全缺失的引号和花括号
    fixed = text
    # 如果最后一个引号没闭合，补上
    if fixed.count('"') % 2 != 0:
        fixed += '"'
    # 如果花括号没闭合，补上
    if fixed.count("{") > fixed.count("}"):
        fixed += "}" * (fixed.count("{") - fixed.count("}"))

    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # 用正则提取已有的字段值
    topic_m = re.search(r'"topic"\s*:\s*"([^"]*)', text)
    cat_m = re.search(r'"category"\s*:\s*"([^"]*)', text)
    ref_m = re.search(r'"hot_ref"\s*:\s*"([^"]*)', text)
    if topic_m and topic_m.group(1):
        return {
            "topic": topic_m.group(1),
            "category": cat_m.group(1) if cat_m else "热点",
            "hot_ref": ref_m.group(1) if ref_m else "",
        }
    return None


def select_topic_from_hot(hot_topics, source="热搜", recent_titles=None, profile=None, recent_history=None):
    """Use LLM to pick the best profile-matched psychology angle from trending topics."""
    topics_text = "\n".join(f"{i+1}. {t}" for i, t in enumerate(hot_topics[:30]))
    recent_history = recent_history or get_article_history(days=HARD_DUP_LOOKBACK_DAYS)
    recent_titles = recent_titles or [item["title"] for item in recent_history]

    # 构建去重提示
    dedup_hint = ""
    recent_history_text = _format_recent_history_for_prompt(recent_history)
    if recent_history_text:
        dedup_hint = f"""

重要：最近已发布过以下文章，请避开相同标题、相同问题场景、相同心理解释路径：
{recent_history_text}

硬性避让：
- 近{FAMILY_COOLDOWN_DAYS}天写过的内容家族不要再写，例如厌学/不想上学、作业学习、焦虑情绪、手机屏幕、边界讨好等。
- 不要把不同热搜都改写成同一个“孩子不想上学/焦虑/作业大战”角度。
- 标题不能使用“今天微博热搜那个话题”这类泛泛占位表达。"""

    blocked_candidates = []

    def build_prompt(extra_blocked=None):
        blocked_hint = ""
        if extra_blocked:
            blocked_hint = "\n\n本轮已被系统判定重复，请不要再选：\n" + "\n".join(f"- {item}" for item in extra_blocked)

        if profile:
            category_list = "/".join(profile["categories"])
            rules = "\n".join(f"- {rule}" for rule in profile["topic_rules"])
            return f"""你是"{ACCOUNT_NAME}"公众号的选题编辑。

今日栏目：{profile['column_name']}
账号定位：{profile['topic_goal']}
作者人设：{profile['persona']}

以下是今日{source}热点话题（前30条）：
{topics_text}
{dedup_hint}
{blocked_hint}

请从中选择一个最适合今日栏目的话题，或受热搜启发提炼一个更适合公众号的心理学角度。

要求：
{rules}
- 话题要具体、有生活感，不要太大太虚
- 如果热搜词可用，请在 hot_ref 中保留原始热搜词

严格按以下格式回复，只输出一行 JSON，不要有其他任何文字：
{{"topic": "话题", "category": "分类", "hot_ref": "热点词"}}

分类只能是：{category_list}"""
        return f"""你是"心光心理学"公众号的编辑，专注心理健康和亲密关系。

以下是今日{source}热点话题（前30条）：
{topics_text}
{dedup_hint}
{blocked_hint}

请从中选一个最适合结合心理学来写文章的话题，或者受热点启发提炼一个相关话题。

要求：
- 优先选与情绪、关系、成长、家庭、教育直接相关的话题
- 如没有直接相关的，可从社会热点中提炼一个心理学角度
- 避免选娱乐八卦、政治、灾难类话题

严格按以下格式回复，只输出一行 JSON，不要有其他任何文字：
{{"topic": "话题", "category": "分类", "hot_ref": "热点词"}}"""

    def build_candidate(data):
        return {
            "topic": data["topic"],
            "category": data.get("category", profile["categories"][0] if profile else "热点"),
            "hot_ref": data.get("hot_ref", ""),
            "source": source,
            "profile": profile,
        }

    for attempt in range(1, MAX_TOPIC_SELECTION_ATTEMPTS + 1):
        result = call_gemini_api(build_prompt(blocked_candidates), max_tokens=1000)
        if not result:
            return None

        data = _repair_json(result)
        if data and data.get("topic"):
            candidate = build_candidate(data)
            reason = _topic_rejection_reason(
                " ".join([candidate["topic"], candidate.get("hot_ref", "")]),
                recent_history=recent_history,
                recent_titles=recent_titles,
                profile=profile,
            )
            if reason:
                log(f"热搜选题跳过（第{attempt}次）: {candidate['topic']} | {reason}")
                blocked_candidates.append(f"{candidate['topic']}（{reason}）")
                continue
            log(f"热搜选题: {candidate['topic']} (参考热搜: {candidate.get('hot_ref', '')})")
            return candidate

        # JSON 解析失败时只做一次纯文本兜底，仍然走硬去重。
        log(f"热搜JSON解析失败，尝试纯文本选题。原始返回: {result[:150]}")
        if profile:
            fallback_prompt = f"""从以下热搜话题中，选一个最适合"{profile['column_name']}"栏目写成心理学文章的话题。
作者人设：{profile['persona']}
选题目标：{profile['topic_goal']}
近期文章必须避开：
{recent_history_text}
只输出话题名称，不要输出其他任何内容：
{topics_text}"""
        else:
            fallback_prompt = f"""从以下热搜话题中，选一个最适合写心理学文章的话题，只输出话题名称，不要输出其他任何内容：
{topics_text}"""
        fallback_result = call_gemini_api(fallback_prompt, max_tokens=200)
        if fallback_result:
            topic_name = fallback_result.strip().strip('"\'').split('\n')[0].strip()
            if len(topic_name) > 3:
                candidate = {
                    "topic": topic_name,
                    "category": profile["categories"][0] if profile else "热点",
                    "hot_ref": "",
                    "source": source,
                    "profile": profile,
                }
                reason = _topic_rejection_reason(
                    candidate["topic"],
                    recent_history=recent_history,
                    recent_titles=recent_titles,
                    profile=profile,
                )
                if reason:
                    log(f"纯文本兜底选题跳过: {topic_name} | {reason}")
                    blocked_candidates.append(f"{topic_name}（{reason}）")
                    continue
                log(f"纯文本兜底选题: {topic_name}")
                return candidate

    log("热搜选题彻底失败或全部被去重规则拦截")
    return None


def select_topic(profile=None):
    """Select today's topic with profile-aware Weibo hot-search priority."""
    # 读取近期文章标题用于去重
    recent_history = get_article_history(days=HARD_DUP_LOOKBACK_DAYS)
    recent_titles = [item["title"] for item in recent_history]
    if recent_titles:
        log(f"近{HARD_DUP_LOOKBACK_DAYS}天已发布文章: {recent_titles[:12]}")

    if profile:
        weibo_topics = fetch_weibo_hot_topics()
        if weibo_topics:
            topic = select_topic_from_hot(
                weibo_topics,
                source="微博热搜",
                recent_titles=recent_titles,
                recent_history=recent_history,
                profile=profile,
            )
            if topic:
                return topic
            log("微博热搜选题失败，尝试栏目话题池")
        else:
            log("微博热搜为空，尝试栏目话题池")

        fallback_topic = choose_fallback_profile_topic(
            profile,
            recent_titles=recent_titles,
            recent_history=recent_history,
        )
        if fallback_topic:
            return fallback_topic

    # Legacy fallback for manual/old invocations without a profile.
    # 1. Bing News RSS 垂直搜索（5个精准关键词，25条高相关度资讯）
    # 2. 天行多平台热搜（每天轮换，作为补充兜底）
    # 3. 学期日历时令话题
    # 4. 话题池轮询兜底

    # 第1层：Bing News 垂直搜索（精准命中心理/亲子话题）
    bing_topics = fetch_bing_news_topics()
    if bing_topics:
        topic = select_topic_from_hot(
            bing_topics,
            source="Bing新闻垂直搜索",
            recent_titles=recent_titles,
            recent_history=recent_history,
        )
        if topic:
            return topic
        log("Bing新闻选题失败，尝试天行热搜")

    # 第2层：天行多平台热搜（轮换，已知部分接口频率受限）
    hot_topics, source_name = fetch_hot_topics()
    if hot_topics:
        topic = select_topic_from_hot(
            hot_topics,
            source=source_name,
            recent_titles=recent_titles,
            recent_history=recent_history,
        )
        if topic:
            return topic
        log("热搜选题失败，尝试日历选题")

    # 第3层：学期日历时令话题（带去重）
    calendar_topic = fetch_calendar_topic(recent_titles=recent_titles)
    if calendar_topic:
        return calendar_topic

    # 第4层：话题池轮询兜底（带去重）
    today = datetime.now()
    epoch = datetime(2026, 1, 1)
    base_index = (today - epoch).days % len(TOPIC_POOL)
    for offset in range(len(TOPIC_POOL)):
        day_index = (base_index + offset) % len(TOPIC_POOL)
        topic = TOPIC_POOL[day_index]
        if not _is_similar_topic(topic["topic"], recent_titles):
            log(f"话题池选题 [第{day_index + 1}/{len(TOPIC_POOL)}个]: {topic['topic']} (分类: {topic['category']})")
            return topic
    # 极端情况：所有话题都用过
    topic = TOPIC_POOL[base_index]
    log(f"话题池选题（全部相似，强制使用）: {topic['topic']}")
    return topic


def generate_article(topic_info, avoid_titles=None, quality_notes=None):
    """Generate article using profile-specific editorial positioning."""
    log("正在生成文章...")
    profile = topic_info.get("profile") or PUBLISH_PROFILES["parenting"]
    structure = "\n".join(f"- {item}" for item in profile["article_structure"])
    must_include = "\n".join(f"- {item}" for item in profile["must_include"])
    professional_frame = "\n".join(f"- {item}" for item in profile.get("professional_frame", []))
    practice_requirements = "\n".join(f"- {item}" for item in profile.get("practice_requirements", []))
    professional_guardrails = "\n".join(f"- {item}" for item in profile.get("professional_guardrails", []))
    forbidden = "、".join(profile["forbidden_phrases"])
    avoid_titles = avoid_titles or []
    avoid_hint = ""
    if avoid_titles:
        avoid_hint = "\n近期标题不能复用，也不要换汤不换药：\n" + "\n".join(f"- {title}" for title in avoid_titles[:12])
    quality_hint = ""
    if quality_notes:
        quality_hint = "\n本次重写必须修正这些问题：\n" + "\n".join(f"- {note}" for note in quality_notes)

    prompt = f"""你是"{ACCOUNT_NAME}"公众号的作者。

今日栏目：{profile['column_name']}（{profile['schedule']}）
作者人设：{profile['persona']}
目标读者：{profile['target_audience']}
整体语气：{profile['tone']}

专业判断框架（文章必须按这个内在逻辑展开，不一定逐字作为小标题）：
{professional_frame}

专业边界：
{professional_guardrails}

请根据以下话题写一篇公众号文章：

话题：{topic_info['topic']}
分类：{topic_info['category']}
{f"热搜背景：今日微博热搜「{topic_info['hot_ref']}」与此话题相关。文章可以自然借这个热搜作为引子，但不要写成八卦评论。" if topic_info.get('hot_ref') else ""}
{avoid_hint}
{quality_hint}

严格要求：
1. 字数：900-1300字，绝不超过1500字
2. 语气必须符合人设：温暖、亲切、专业、具体，不居高临下
3. 心理学观点要用大白话讲清楚，允许少量专业概念，但必须解释成生活语言
4. 段落短：每段不超过3-4行，手机阅读友好
5. 温暖不鸡汤，专业不吓人，避免制造焦虑
6. 禁止使用这些表达：{forbidden}
7. 不要编造心理学实验、百分比、脑区、专家名字或“研究发现”；没有可核验来源时，用“在亲子沟通训练/咨询实践中常见的是……”或“从这个视角看……”来表达

文章结构：
{structure}

必须包含：
{must_include}

练习与落地要求：
{practice_requirements}

格式要求：
- 输出纯 Markdown 格式
- 第一行是标题（用 # ）
- 标题必须具体，不要写“今天微博热搜那个话题”“这件事看得我心里一紧”这类占位标题
- 正文不要在开头重复标题
- 不要附参考资料
- 不要用"根据研究表明"之类的生硬表达
- 在"中间"部分末尾插入一行：<!-- IMG_PLACEHOLDER_1 -->
- 在"实用Tips"部分末尾插入一行：<!-- IMG_PLACEHOLDER_2 -->
- 实用Tips或练习部分的每个方法必须用这个格式：**编号. 方法名：** 具体说明（例如：**1. 先接住感受：** 当对方说……）
- 每个方法下面如果有具体场景，用缩进列表：  * **具体场景：** xxxxxx
- 可以在文章中任意位置用 > 引用一句温暖的话作为金句高亮（可选，不强制）
- 结尾前可以用一句 > ✦ 温暖收尾语 作为点睛句（可选）

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


def generate_cover_image(title, profile=None):
    """Generate cover image using Doubao Seedream, upload to IMGBB"""
    if not ARK_API_KEY or not IMGBB_API_KEY:
        log("跳过封面图生成（需要 ARK_API_KEY 和 IMGBB_API_KEY）")
        return None

    log("正在生成封面图...")
    profile = profile or PUBLISH_PROFILES["parenting"]
    prompt = f'Cover illustration for article "{title}". {profile["cover_prompt"]}'
    return generate_image_doubao(prompt, size="2560x1440", label="封面图")


def upload_to_imgbb(image_bytes, label="图片"):
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
            log(f"{label}上传成功: {url}")
            return url
    except Exception as e:
        log(f"IMGBB 上传失败 ({label}): {e}")
    return None


def generate_image_doubao(prompt, size="1920x1920", label="图片"):
    """Generate image via Doubao Seedream, download temp URL and upload to imgbb"""
    if not ARK_API_KEY or not IMGBB_API_KEY:
        return None
    payload = {
        "model": "doubao-seedream-4-5-251128",
        "prompt": prompt,
        "size": size,
        "response_format": "url",
        "watermark": False,
    }
    req = request.Request(
        "https://ark.cn-beijing.volces.com/api/v3/images/generations",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {ARK_API_KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=90) as resp:
            result = json.loads(resp.read().decode())
        temp_url = (result.get("data") or [{}])[0].get("url", "")
        if not temp_url:
            log(f"豆包未返回图片URL ({label})")
            return None
        dl_req = request.Request(temp_url, headers={"User-Agent": "Mozilla/5.0"})
        with request.urlopen(dl_req, timeout=30) as resp:
            image_bytes = resp.read()
        return upload_to_imgbb(image_bytes, label=f"{label}(豆包)")
    except Exception as e:
        log(f"豆包图片生成失败 ({label}): {e}")
        return None


def generate_body_images(topic_info, title):
    """Generate 2 body images using Doubao Seedream, upload to imgbb"""
    if not ARK_API_KEY or not IMGBB_API_KEY:
        log("跳过正文配图（需要 ARK_API_KEY 和 IMGBB_API_KEY）")
        return []

    log("正在生成正文配图...")
    profile = topic_info.get("profile") or PUBLISH_PROFILES["parenting"]
    prompts = [
        f"Article body illustration for '{title}', topic '{topic_info['topic']}'. {prompt}"
        for prompt in profile["body_prompts"]
    ]

    urls = []
    for i, prompt in enumerate(prompts):
        url = generate_image_doubao(prompt, size="1920x1920", label=f"正文配图{i+1}")
        if url:
            urls.append(url)

    log(f"正文配图完成: {len(urls)}/2 张")
    return urls


def inject_markdown_images(markdown_content, body_images=None):
    """Replace generated image placeholders with Markdown images for Obsidian review."""
    content = markdown_content
    for idx, url in enumerate(body_images or [], start=1):
        placeholder = f"<!-- IMG_PLACEHOLDER_{idx} -->"
        markdown_image = f"![正文配图{idx}]({url})"
        content = content.replace(placeholder, markdown_image, 1)
    return content


def markdown_to_grace_html(markdown_content, body_images=None, profile=None):
    """Convert Markdown to WeChat-compatible HTML with grace theme styling (v2)"""
    profile = profile or PUBLISH_PROFILES["parenting"]
    lines = markdown_content.strip().split("\n")
    html_parts = []
    in_list = False
    in_tip_card = False  # track numbered tip card state
    placeholder_index = [0]
    h2_count = [0]  # track H2 occurrences for decorative dividers

    def _bold(text):
        """Process **bold** markers in text"""
        return re.sub(
            r"\*\*(.+?)\*\*",
            r'<strong style="color:#FF9F43;font-weight:bold;">\1</strong>',
            text,
        )

    def _italic(text):
        """Process *italic* markers in text (single asterisk only)"""
        return re.sub(
            r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)",
            r'<em style="color:#888;">\1</em>',
            text,
        )

    def _inline_format(text):
        """Apply all inline formatting: bold then italic"""
        return _italic(_bold(text))

    def _close_tip_card():
        """Close an open tip card"""
        nonlocal in_tip_card
        if in_tip_card:
            html_parts.append("</div>")
            in_tip_card = False

    def _close_list():
        """Close an open list"""
        nonlocal in_list
        if in_list:
            html_parts.append("</ul>")
            in_list = False

    for line in lines:
        stripped = line.strip()
        raw_indent = len(line) - len(line.lstrip())

        if not stripped:
            _close_list()
            _close_tip_card()
            # Compact spacer instead of <br/>
            html_parts.append(
                '<div style="margin:8px 0;"></div>'
            )
            continue

        # --- separator → decorative divider
        if stripped in ("---", "***", "___"):
            _close_list()
            _close_tip_card()
            html_parts.append(
                '<div style="text-align:center;margin:28px 0 8px;">'
                '<span style="color:#FFEAA7;font-size:18px;letter-spacing:14px;">'
                '\u00b7 \u00b7 \u00b7</span></div>'
            )
            continue

        # Image placeholder
        if stripped.startswith("<!-- IMG_PLACEHOLDER"):
            _close_list()
            _close_tip_card()
            idx = placeholder_index[0]
            placeholder_index[0] += 1
            url = (body_images or [])[idx] if body_images and idx < len(body_images) else None
            if url:
                html_parts.append(
                    f'<div style="margin:24px 0;text-align:center;">'
                    f'<img src="{url}" style="width:100%;border-radius:12px;'
                    f'display:block;" /></div>'
                )
            else:
                html_parts.append(
                    '<div style="width:100%;min-height:160px;margin:24px 0;'
                    "background:linear-gradient(135deg,#FFF8E7,#FFEAA7);"
                    "border-radius:12px;display:flex;align-items:center;"
                    'justify-content:center;">'
                    '<span style="color:#FF9F43;font-size:14px;">✦ 配图 ✦</span></div>'
                )
            continue

        # H1 title
        if stripped.startswith("# ") and not stripped.startswith("## "):
            _close_list()
            _close_tip_card()
            title_text = stripped[2:].strip()
            html_parts.append(
                f'<h1 style="text-align:center;font-size:22px;font-weight:bold;'
                f"color:#FF9F43;margin:30px 0 24px;padding:16px 20px;"
                f"background:linear-gradient(135deg,#FFF8E7,#FFF3D0);"
                f"border-radius:12px;box-shadow:0 2px 8px rgba(255,159,67,0.15);"
                f'letter-spacing:1px;">'
                f"{title_text}</h1>"
            )
            continue

        # H2 subtitle — with decorative divider before it (except first H2)
        if stripped.startswith("## "):
            _close_list()
            _close_tip_card()
            subtitle = stripped[3:].strip()
            h2_count[0] += 1
            if h2_count[0] > 1:
                html_parts.append(
                    '<div style="text-align:center;margin:32px 0 8px;">'
                    '<span style="color:#FFEAA7;font-size:18px;letter-spacing:14px;">'
                    '\u00b7 \u00b7 \u00b7</span></div>'
                )
            html_parts.append(
                f'<h2 style="font-size:18px;font-weight:bold;color:#FF8C42;'
                f"margin:20px 0 14px;padding:8px 0 8px 14px;"
                f"border-left:4px solid #FF9F43;"
                f'letter-spacing:0.5px;">{subtitle}</h2>'
            )
            continue

        # Blockquote — distinguish highlight quotes vs normal quotes
        if stripped.startswith("> "):
            _close_list()
            _close_tip_card()
            quote_text = stripped[2:].strip()
            # Highlight quote: > ✦ ... or > ** ...
            if quote_text.startswith("\u2726") or quote_text.startswith("**"):
                quote_text = quote_text.lstrip("\u2726 ")
                quote_text = _inline_format(quote_text)
                html_parts.append(
                    f'<div style="margin:22px 0;padding:18px 24px;text-align:center;'
                    f"background:linear-gradient(135deg,#FFF8E7,#FFF3D0);"
                    f"border-radius:12px;box-shadow:0 2px 8px rgba(255,159,67,0.1);"
                    f'font-size:16px;line-height:2.0;color:#E8852E;font-weight:500;'
                    f'letter-spacing:0.5px;">'
                    f'<span style="color:#FFEAA7;margin-right:6px;">✦</span>'
                    f"{quote_text}"
                    f'<span style="color:#FFEAA7;margin-left:6px;">✦</span>'
                    f"</div>"
                )
            else:
                quote_text = _inline_format(quote_text)
                html_parts.append(
                    f'<blockquote style="margin:16px 0;padding:14px 18px;'
                    f"background:#FFF8E7;border-left:4px solid #FFEAA7;"
                    f"border-radius:0 8px 8px 0;color:#666;font-size:15px;"
                    f'line-height:2.0;letter-spacing:0.5px;">'
                    f"{quote_text}</blockquote>"
                )
            continue

        # Numbered tip pattern: **1. Title：** or **1. Title:**
        tip_match = re.match(
            r"\*\*(\d+)\.\s*(.+?)[：:]\*\*\s*(.*)", stripped
        )
        if tip_match:
            _close_list()
            _close_tip_card()
            tip_num = tip_match.group(1)
            tip_title = tip_match.group(2)
            tip_rest = tip_match.group(3).strip()
            # Open tip card
            in_tip_card = True
            html_parts.append(
                f'<div style="margin:16px 0;padding:16px 18px;'
                f"background:linear-gradient(135deg,#FFFAF0,#FFF8E7);"
                f"border-left:4px solid #FF9F43;border-radius:0 10px 10px 0;"
                f'box-shadow:0 1px 4px rgba(255,159,67,0.08);">'
                f'<div style="font-size:16px;font-weight:bold;color:#FF8C42;'
                f'margin-bottom:8px;line-height:1.6;">'
                f'<span style="display:inline-block;width:24px;height:24px;'
                f"background:#FF9F43;color:#fff;border-radius:50%;text-align:center;"
                f'line-height:24px;font-size:13px;margin-right:8px;">'
                f"{tip_num}</span>{tip_title}</div>"
            )
            if tip_rest:
                tip_rest = _inline_format(tip_rest)
                html_parts.append(
                    f'<p style="font-size:15px;line-height:2.0;color:#555;'
                    f'margin:4px 0 0;text-align:justify;letter-spacing:0.5px;">'
                    f"{tip_rest}</p>"
                )
            continue

        # Sub-item inside tip card: indented * or - with **具体场景：**
        if in_tip_card and (stripped.startswith("* ") or stripped.startswith("- ")):
            item_text = stripped[2:].strip()
            item_text = _inline_format(item_text)
            html_parts.append(
                f'<p style="font-size:15px;line-height:2.0;color:#666;'
                f"margin:6px 0 0;padding-left:32px;"
                f'text-align:justify;letter-spacing:0.5px;">'
                f"{item_text}</p>"
            )
            continue

        # Scene description item (e.g. *   **具体场景：** ...) — render as indented block
        # Works both inside and outside tip cards, handles old article format
        scene_match = re.match(r'^[-*]\s+\*\*具体场景[：:]\*\*\s*(.*)', stripped)
        if scene_match:
            _close_list()
            scene_text = _inline_format(scene_match.group(1).strip())
            html_parts.append(
                f'<p style="font-size:15px;line-height:2.0;color:#666;'
                f"margin:6px 0 0;padding-left:32px;"
                f'text-align:justify;letter-spacing:0.5px;">'
                f'<strong style="color:#FF9F43;">具体场景：</strong>'
                f"{scene_text}</p>"
            )
            continue

        # Regular list items (outside tip cards)
        if stripped.startswith("- ") or stripped.startswith("* "):
            _close_tip_card()
            is_sub = raw_indent >= 2 or stripped.startswith("  ")
            if not in_list:
                html_parts.append(
                    '<ul style="margin:14px 0;padding-left:0;list-style:none;">'
                )
                in_list = True
            # Extract text after list marker (- or *) safely
            item_text = re.sub(r'^[-*]\s+', '', stripped)
            item_text = _inline_format(item_text)
            if is_sub:
                # Nested sub-item: smaller, indented
                html_parts.append(
                    f'<li style="margin:6px 0;line-height:2.0;font-size:15px;'
                    f'color:#666;padding-left:28px;display:flex;align-items:flex-start;">'
                    f'<span style="color:#FFEAA7;margin-right:8px;flex-shrink:0;'
                    f'font-size:14px;line-height:1.8;">◦</span>'
                    f'<span>{item_text}</span></li>'
                )
            else:
                html_parts.append(
                    f'<li style="margin:10px 0;line-height:2.0;font-size:16px;'
                    f'color:#3D3020;display:flex;align-items:flex-start;'
                    f'letter-spacing:0.5px;">'
                    f'<span style="color:#FF9F43;margin-right:10px;flex-shrink:0;'
                    f'font-size:16px;line-height:1.8;">\u25cf</span>'
                    f'<span>{item_text}</span></li>'
                )
            continue

        _close_list()
        _close_tip_card()

        # Regular paragraph — justified, no indent, warm brown text
        text = _inline_format(stripped)
        html_parts.append(
            f'<p style="font-size:16px;line-height:2.0;color:#3D3020;'
            f'margin:14px 0;text-align:justify;letter-spacing:0.5px;">'
            f"{text}</p>"
        )

    _close_list()
    _close_tip_card()

    # Wrap in container with enhanced footer
    body = "\n".join(html_parts)
    html = (
        f'<section style="max-width:600px;margin:0 auto;padding:20px 24px;'
        f'font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;">'
        f"{body}"
        # Enhanced footer
        f'<div style="margin-top:36px;padding-top:20px;text-align:center;'
        f'border-top:1px solid #FFEAA7;">'
        f'<div style="margin-bottom:6px;">'
        f'<span style="color:#FFEAA7;font-size:14px;letter-spacing:6px;">'
        f'\u2500\u2500 \u2726 \u2500\u2500</span></div>'
        f'<p style="font-size:15px;color:#FF9F43;font-weight:bold;'
        f'margin:4px 0 2px;letter-spacing:1px;">{ACCOUNT_NAME}</p>'
        f'<p style="font-size:12px;color:#bbb;margin:0;letter-spacing:0.5px;">'
        f"{ACCOUNT_TAGLINE} · {profile['column_name']}</p>"
        f"</div>"
        f"</section>"
    )

    return html


def publish_to_wechat(title, html_content, cover_url=None, article_text="", profile=None):
    """Publish to WeChat Official Account"""
    log("正在发布到公众号...")
    profile = profile or PUBLISH_PROFILES["parenting"]

    # Generate summary — 传入文章正文前200字作为上下文
    text_snippet = article_text[:200] if article_text else ""
    summary_prompt = f"""请为这篇公众号文章写一句摘要（20-30字），要求温暖有吸引力。
栏目：{profile['column_name']}
人设：{profile['persona']}
标题：{title}
正文摘录：{text_snippet}
要求：只输出摘要正文，不要加引号或前缀。摘要必须与文章主题相关，15-30字。"""
    summary = call_gemini_api(summary_prompt, max_tokens=150)
    if summary:
        summary = summary.strip().strip('"\'').split('\n')[0].strip()
    # fallback: 从标题提取摘要
    if not summary or len(summary) < 10:
        summary = title[:30] if len(title) > 15 else f"{profile['column_name']} | {title}"
        log(f"摘要回退到标题: {summary}")
    else:
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
        "summary": summary or profile["default_summary"],
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
        with request.urlopen(req, timeout=180) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        log(f"API 响应: {result}")
        success = result.get("success", False)
        if not success:
            log(f"发布失败: {result.get('error', result)}")
        return success
    except error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        log(f"发布异常: {e} | 响应体: {body[:500]}")
        return False
    except Exception as e:
        log(f"发布异常: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="心光心理学自动发布脚本 V5.2")
    parser.add_argument("--check-env", action="store_true", help="检查环境依赖")
    parser.add_argument("--dry-run", action="store_true", help="试运行（不发布）")
    parser.add_argument("--review-only", action="store_true", help="只生成并提交文章，不推送公众号草稿箱")
    parser.add_argument("--topic", type=str, help="指定话题")
    parser.add_argument(
        "--theme",
        choices=sorted(PUBLISH_PROFILES.keys()),
        help="手动指定栏目：parenting=育儿亲子，women_growth=女性自我成长",
    )
    parser.add_argument("--ignore-schedule", action="store_true", help="忽略周一三五发布日限制")
    args = parser.parse_args()

    # Check environment
    if args.check_env:
        errors = []
        if not WECHAT_API_KEY:
            errors.append("未设置 WECHAT_API_KEY")
        if not DEEPSEEK_API_KEY and not ARK_API_KEY:
            errors.append("未设置 DEEPSEEK_API_KEY 或 ARK_API_KEY")
        if not IMGBB_API_KEY:
            print("⚠️ 未设置 IMGBB_API_KEY（封面图上传将跳过）")
        for e in errors:
            print(f"❌ {e}")
        if errors:
            sys.exit(1)
        print("✅ 环境检查通过")
        sys.exit(0)

    # Validate required env vars
    if not DEEPSEEK_API_KEY and not ARK_API_KEY:
        log("❌ 未设置 DEEPSEEK_API_KEY 或 ARK_API_KEY，至少需要一个文本生成 API")
        sys.exit(1)
    if not WECHAT_API_KEY and not args.dry_run and not args.review_only:
        log("❌ 未设置 WECHAT_API_KEY")
        sys.exit(1)

    if args.theme:
        profile = get_profile_by_key(args.theme)
    else:
        profile = get_publish_profile()

    if not profile:
        message = "今天不是心光心理学公众号的自动发布日（仅周一三五自动发布育儿与亲子沟通文章）"
        if not args.ignore_schedule:
            log(message)
            log("如需手动运行，请加 --theme parenting 或 --theme women_growth，并加 --ignore-schedule")
            sys.exit(0)
        profile = PUBLISH_PROFILES["parenting"]
        log(f"{message}；已因 --ignore-schedule 使用默认育儿栏目")

    log("=" * 50)
    log("心光心理学自动发布 V5.2 开始执行")
    log(f"日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log(f"今日栏目: {profile['column_name']} | 人设: {profile['persona']}")
    if args.dry_run:
        log("⚠️ 试运行模式：不会发布到公众号")
    if args.review_only:
        log("📝 审稿模式：会生成并提交文章，但不会推送公众号草稿箱")

    # 1. Select topic
    if args.topic:
        topic_info = {
            "topic": args.topic,
            "category": profile["categories"][0],
            "keywords": args.topic,
            "source": "手动指定",
            "profile": profile,
        }
    else:
        topic_info = select_topic(profile=profile)
    if not topic_info:
        log("❌ 选题失败")
        sys.exit(1)

    # 2. Generate article
    recent_history = get_article_history(days=HARD_DUP_LOOKBACK_DAYS)
    avoid_titles = [item["title"] for item in recent_history]
    article = None
    quality_issues = []
    for attempt in range(1, 3):
        article = generate_article(
            topic_info,
            avoid_titles=avoid_titles,
            quality_notes=quality_issues,
        )
        if not article:
            log("❌ 文章生成失败")
            sys.exit(1)
        quality_issues = validate_article_output(article, topic_info, recent_history=recent_history)
        if not quality_issues:
            break
        log(f"文章质量门禁未通过（第{attempt}次）: {'；'.join(quality_issues)}")

    if quality_issues:
        log("❌ 文章质量门禁连续未通过，停止发布以避免重复或低质内容")
        sys.exit(1)

    # 3. Generate cover image
    cover_url = generate_cover_image(article["title"], profile=profile)

    # 3.5 Generate body images
    body_images = generate_body_images(topic_info, article["title"])

    # 4. Convert to HTML
    log("正在转换 HTML（grace 主题）...")
    html_content = markdown_to_grace_html(article["content"], body_images=body_images, profile=profile)
    log(f"HTML 内容长度: {len(html_content)} 字符")

    # 5. Save article locally
    today_str = datetime.now().strftime("%Y%m%d")
    md_file = os.path.join(WORK_DIR, f"article_{today_str}.md")
    family = detect_content_family(" ".join([article["title"], topic_info.get("topic", ""), topic_info.get("hot_ref", "")]))
    family_label = family[1] if family else ""
    try:
        saved_content = inject_markdown_images(article["content"], body_images=body_images)
        cover_line = f"cover_image_url: {cover_url or ''}\n"
        body_images_line = f"body_image_urls: {' | '.join(body_images)}\n"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(f"---\ntitle: {article['title']}\ndate: {datetime.now().strftime('%Y-%m-%d')}\n"
                    f"column: {profile['column_name']}\ncategory: {topic_info['category']}\n"
                    f"topic: {topic_info.get('topic', '')}\n"
                    f"source: {topic_info.get('source', '')}\n"
                    f"hot_ref: {topic_info.get('hot_ref', '')}\n"
                    f"topic_family: {family_label}\n"
                    f"{cover_line}"
                    f"{body_images_line}"
                    f"persona: {profile['persona']}\nword_count: {article['word_count']}\n"
                    f"style: {profile['style_label']}\n---\n\n{saved_content}")
        log(f"文章已保存: {md_file}")
    except Exception as e:
        log(f"文件保存失败: {e}")

    # Dry run exit
    if args.dry_run:
        log("=" * 50)
        log("✅ 试运行完成")
        log(f"栏目: {profile['column_name']}")
        log(f"标题: {article['title']}")
        log(f"字数: {article['word_count']}")
        log(f"封面图: {cover_url or '无'}")
        log("=" * 50)
        sys.exit(0)

    # 6. Publish, or keep for Obsidian review only.
    if args.review_only:
        success = True
        log("📝 审稿模式：已跳过公众号草稿箱推送")
    else:
        success = publish_to_wechat(article["title"], html_content, cover_url,
                                   article_text=article["content"], profile=profile)

    if success:
        if args.review_only:
            log("✅ 审稿稿件已生成并准备提交")
        else:
            log("✅ 发布成功！")

        # Git commit
        try:
            import subprocess
            subprocess.run(["git", "config", "user.name", "GitHub Actions"], check=True, cwd=WORK_DIR)
            subprocess.run(["git", "config", "user.email", "actions@github.com"], check=True, cwd=WORK_DIR)
            subprocess.run(["git", "add", f"article_{today_str}.md"], check=True, cwd=WORK_DIR)
            commit_msg = f"chore: 自动发布心光心理学 {datetime.now().strftime('%Y-%m-%d')} - {article['title']}"
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
