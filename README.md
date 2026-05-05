# 心光心理学公众号自动发布

按新的公众号定位运行：

- 周一、周三、周五：根据微博热搜生成育儿主题文章，风格温馨、亲切，人设是一位温柔亲切的亲子沟通培训师。
- 周二、周四、周六：发布女性自我成长主题文章，人设是一位温暖、专业的心理动力学方向心理咨询师。
- 周日默认不发布。

## 快速开始

```bash
cd ~/.claude/skills/teen-psychology-insights/scripts
python3 auto_publish.py --dry-run
```

手动指定栏目：

```bash
python3 auto_publish.py --theme parenting --topic "孩子写作业拖拉怎么办" --dry-run
python3 auto_publish.py --theme women_growth --topic "为什么总是在关系里先照顾别人" --dry-run
```

## 公众号信息

| 项目 | 值 |
|------|-----|
| 公众号名称 | 心光心理学 |
| AppID | `wx52189e9b012018e1` |
| 自动化入口 | `scripts/auto_publish.py` |
| 调度 | Cloudflare Worker `github-scheduler` 每天 20:00 北京时间触发；脚本内部周日跳过 |

## 环境变量

```bash
export WECHAT_API_KEY='...'
export DEEPSEEK_API_KEY='...'   # 或 ARK_API_KEY
export ARK_API_KEY='...'        # 配图需要
export IMGBB_API_KEY='...'      # 配图托管需要
```

## 文件结构

```text
teen-psychology-insights/
├── SKILL.md
├── README.md
├── STATUS.md
├── scripts/
│   ├── auto_publish.py
│   ├── generate_image.py
│   └── publish.py
└── .github/workflows/daily-publish.yml
```

## 版本

- v5.0：双栏目定位，周一三五育儿亲子，周二四六女性自我成长。
- v4.x：原“心光馨语”青少年心理/亲子关系日更逻辑。
