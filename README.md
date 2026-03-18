# 心光馨语 - 轻松心理学公众号

像闺蜜聊天一样讲心理学。每日一篇 800-1200 字轻松短文，配温暖治愈系插画，发布到"心光馨语"微信公众号。

## 特性

- **闺蜜聊天式**：口语化表达，零术语，像朋友分享经验
- **热点驱动选题**：基于知乎、微博、小红书热搜自动选题
- **轻松短文**：800-1200 字，手机阅读友好
- **温暖配图**：Google Gemini Imagen 生成暖橙水彩插画
- **优雅排版**：grace 主题，暖橙浅金色调
- **一键发布**：支持发布到微信公众号

## 快速开始

```bash
# 默认：基于热搜自动选题
claude "心光馨语"

# 指定主题
claude "心光馨语 主题:考试焦虑"

# 生成并发布
claude "心光馨语 发布:是"
```

## 公众号信息

| 项目 | 值 |
|------|-----|
| 公众号名称 | 心光馨语 |
| AppID | ${WECHAT_APP_ID} |

## 配置

### 环境变量

```bash
# 配图生成（Google Gemini Imagen）
export GOOGLE_API_KEY='your_google_api_key_here'

# 微信公众号发布
export WECHAT_API_KEY='your_wechat_api_key_here'
```

### 输出目录

文章保存到：`~/Documents/Obsidian/心光馨语/`

## 文件结构

```
teen-psychology-insights/
├── SKILL.md                     # 核心技能定义 (v2.0)
├── README.md                    # 本文档
├── QUICKSTART.md                # 快速开始指南
└── scripts/
    ├── generate_image.py       # Google Gemini Imagen 配图脚本
    ├── publish.py              # 微信公众号发布脚本
    └── test_image_generation.py # 配图测试脚本
```

## 排版方案

- **主题**：baoyu-markdown-to-html grace 主题
- **配色**：暖橙 #FF9F43 + 浅金 #FFEAA7
- **风格**：圆角卡片、柔和阴影、暖色引用块
- **正文**：16px，行距 1.8

## 覆盖领域

1. 学业压力：考试焦虑、学习动力、拖延症
2. 人际关系：同伴交往、社交恐惧、校园冲突
3. 情绪管理：情绪失控、挫折应对、焦虑缓解
4. 自我认知：自我价值、青春期困惑
5. 亲子沟通：叛逆期、沟通技巧
6. 趣味心理：心理实验、冷知识、性格测试

## 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 2.0 | 2026-03-10 | 公众号改为"心光馨语"，闺蜜聊天式短文，grace 排版，Google Gemini 配图 |
| 1.0 | 2026-02-02 | 初始版本 |
