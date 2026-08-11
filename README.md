# 心光心理学公众号自动发布

按新的公众号定位运行：

- 周一、周三、周五：根据微博热搜生成育儿主题文章，风格温馨、亲切，人设是一位温柔亲切的亲子沟通培训师。
- 周二、周四、周六、周日：默认不自动发布。
- 女性自我成长主题保留手动指定能力，不参与自动调度。

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

只生成审稿稿件，不推送公众号草稿箱：

```bash
python3 auto_publish.py --review-only
```

## 公众号信息

| 项目 | 值 |
|------|-----|
| 公众号名称 | 心光心理学 |
| AppID | `wx52189e9b012018e1` |
| 自动化入口 | `scripts/auto_publish.py` |
| 调度 | Cloudflare Worker `github-scheduler` 周一、周三、周五 20:00 北京时间触发；脚本内部对其他日期再次拦截 |

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
│   ├── publish.py
│   └── sync_obsidian.py
└── .github/workflows/daily-publish.yml
```

## Obsidian 本地知识库

GitHub Actions 在云端运行，不能直接写入本机 Obsidian。文章会先提交到 GitHub 仓库，本地再通过同步脚本拉取并复制到 Obsidian；自动同步时间为周一、周三、周五 21:30。

默认目标目录：

```text
~/Documents/Obsidian/02-内容创作/心光心理学/
```

统一附件库：

```text
~/Documents/Obsidian/02-内容创作/心光心理学/附件库/
```

手动同步：

```bash
cd ~/.claude/skills/teen-psychology-insights
python3 scripts/sync_obsidian.py --pull
```

同步后会按栏目分目录，并生成 `心光心理学内容索引.md`。
如果文章里有远程图片、HTML 图片或本地附件链接，同步脚本会复制或下载到 `附件库`，并改写为 Obsidian 内部链接。同一天标题变化时，会自动清理同日期旧文件。

同步脚本会维护本地状态文件 `.xingguang-sync-state.json`。如果某篇文章已经在 Obsidian 里手动修改，后续同步会默认跳过该文件，避免覆盖审稿修改；只有显式加 `--overwrite-local` 才会强制覆盖。

## 版本

- v5.4：自动发布与 Obsidian 同步统一调整为周一、周三、周五。
- v5.3：新增审稿模式、Obsidian 统一附件库和本地修改保护。
- v5.2：增强人设专业框架，并新增本地 Obsidian 同步脚本。
- v5.1：加入硬去重、内容家族冷却、泛标题和质量门禁。
- v5.0：双栏目定位，周一三五育儿亲子，周二四六女性自我成长。
- v4.x：原“心光馨语”青少年心理/亲子关系日更逻辑。
