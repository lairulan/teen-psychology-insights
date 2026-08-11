---
name: teen-psychology-insights
version: 5.4.0
description: 心光心理学公众号内容自动生成与发布。仅周一、周三、周五按微博热搜生成并推送育儿/亲子沟通文章；其余日期默认不发，女性自我成长文章保留手动生成能力。触发词："心光心理学"、"心光馨语"、"写心理文章"、"亲子沟通文章"、"女性自我成长文章"。
author: rulanlai
tags: [psychology, parenting, women-growth, wechat]
---

# 心光心理学公众号自动发布 v5.2

定位：把心理学说给生活听。内容分为两条稳定栏目线，自动发布到微信公众号草稿/发布接口，人工可在后台复核。

## 发布节奏

| 星期 | 栏目 | 选题来源 | 人设与风格 |
|------|------|----------|------------|
| 周一、周三、周五 | 育儿与亲子沟通 | 微博热搜优先，兜底用亲子沟通话题池 | 温柔、亲切的亲子沟通培训师；温馨、具体、不指责 |
| 周二、周四、周六、周日 | 不自动发布 | - | 默认跳过 |
| 手动指定 `women_growth` | 女性自我成长 | 微博热搜可延展话题优先，兜底用女性成长话题池 | 温暖、专业的心理动力学方向心理咨询师；稳、深、通俗 |

## 核心规则

- 育儿线必须落在育儿、亲子沟通、孩子情绪、学习陪伴、家庭教育或家长成长。
- 女性成长线必须落在自我成长、情绪照顾、关系边界、自我价值、亲密关系或职场女性。
- 热搜只能作为引子和切口，不能写成娱乐八卦评论。
- 不制造焦虑，不诊断读者，不承诺疗效，不使用极端标题党。
- 文章保持 900-1300 字，短段落，手机阅读友好。
- 配图保持温暖治愈系水彩风格，暖橙浅金为主，女性成长线可加入柔和青绿色点缀。
- 不编造心理学实验、百分比、脑区或专家名字；无可核验来源时，只能用实践观察或生活化解释。
- 育儿线按“行为 -> 感受 -> 需要 -> 边界 -> 话术/练习”的内在框架展开。
- 女性成长线按“事件 -> 情绪 -> 关系模式 -> 防御/内在冲突 -> 觉察练习”的内在框架展开。

## 环境与入口

| 项目 | 值 |
|------|-----|
| 公众号名称 | 心光心理学 |
| AppID | `wx52189e9b012018e1` |
| 发布入口 | `scripts/auto_publish.py` |
| 发布调度 | Cloudflare Worker `github-scheduler` -> GitHub `repository_dispatch: daily-psychology` |

必需环境变量：

- `WECHAT_API_KEY`
- `DEEPSEEK_API_KEY` 或 `ARK_API_KEY`
- `IMGBB_API_KEY` 和 `ARK_API_KEY` 用于配图生成与托管

## 常用命令

按自动发布日运行：

```bash
cd ~/.claude/skills/teen-psychology-insights/scripts
python3 auto_publish.py
```

试运行，不发布到公众号：

```bash
python3 auto_publish.py --dry-run
```

手动指定育儿主题：

```bash
python3 auto_publish.py --theme parenting --topic "孩子顶嘴时父母怎么回应" --dry-run
```

手动指定女性成长主题：

```bash
python3 auto_publish.py --theme women_growth --topic "为什么总是在关系里先照顾别人" --dry-run
```

非自动发布日强制运行：

```bash
python3 auto_publish.py --theme parenting --ignore-schedule
```

同步到本地 Obsidian：

```bash
python3 scripts/sync_obsidian.py --pull
```

只生成审稿稿件，不推送公众号草稿箱：

```bash
python3 scripts/auto_publish.py --review-only
```

## 质量检查

- 标题温暖、有生活感，不使用恐吓式表达。
- 开头能自然承接微博热搜或生活场景。
- 育儿线至少给出 2 句可直接对孩子说的话。
- 女性成长线至少给出 2 个自我觉察问题，并用通俗语言解释心理动力学视角。
- 拦截泛标题、重复主题、伪研究表达、缺少栏目练习模板的文章。
- 文末回到现实行动或温柔提醒，而不是空泛鸡汤。

## Obsidian 知识库

默认本地目录：

```text
~/Documents/Obsidian/02-内容创作/心光心理学/
```

`sync_obsidian.py` 会把仓库里的 `article_*.md` 按栏目复制到 Obsidian，并更新 `心光心理学内容索引.md`。GitHub Actions 只能写远端仓库，本地 Obsidian 需要本机同步任务拉取后复制。

统一附件库：

```text
~/Documents/Obsidian/02-内容创作/心光心理学/附件库/
```

同步脚本会把文章里的远程图片、HTML 图片和本地附件链接统一下载或复制到 `附件库`，再把正文链接改写成 Obsidian 内部链接。同一天如果标题变化，会清理同日期旧文件，避免一篇文章出现多个版本。

同步脚本会维护 `.xingguang-sync-state.json`，默认保护 Obsidian 里已经手动修改过的稿件；需要强制覆盖时再使用 `--overwrite-local`。

## 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 5.4 | 2026-08-11 | 自动发布与 Obsidian 同步统一收敛为周一、周三、周五 |
| 5.3 | 2026-05-05 | 新增审稿模式、Obsidian 统一附件库、同日旧文件清理和本地修改保护 |
| 5.2 | 2026-05-05 | 增强专业人设框架、伪研究拦截和本地 Obsidian 同步 |
| 5.1 | 2026-05-05 | 增加硬去重、内容家族冷却、泛标题和质量门禁 |
| 5.0 | 2026-05-05 | 调整为“心光心理学”双栏目定位：周一三五育儿亲子，周二四六女性自我成长，周日跳过 |
| 4.1 | 2026-04-09 | 垂直热点源升级 |
| 4.0 | 2026-04-08 | DeepSeek V3 + 豆包 Seedream |
