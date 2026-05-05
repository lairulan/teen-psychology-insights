# teen-psychology-insights STATUS v5.3 — 2026-05-05

## 本次同步与审稿流程优化

- 本地 Obsidian 同步自动化时间改为 21:30（周一至周六）。
- Obsidian 新增统一附件库：`~/Documents/Obsidian/02-内容创作/心光心理学/附件库/`。
- `sync_obsidian.py` 会把文章里的远程图片、HTML 图片、本地附件链接复制或下载到附件库，并改写为 Obsidian 内部链接。
- 同一天如果标题变化，同步时会清理同日期旧文件，避免同一篇文章在 Obsidian 出现多个版本。
- 同步脚本新增本地修改保护：使用 `.xingguang-sync-state.json` 记录上次自动同步内容；如果文章已经在 Obsidian 手动修改，后续同步默认跳过，不覆盖审稿稿件。
- `auto_publish.py` 新增 `--review-only`：生成文章、图片、提交 GitHub，但跳过公众号草稿箱推送。该模式尚未在 GitHub workflow 中启用。

## 本次人设与知识库优化

- 育儿线新增固定专业框架：行为 -> 感受 -> 需要 -> 边界 -> 话术/练习。
- 女性成长线新增固定专业框架：事件 -> 情绪 -> 关系模式 -> 防御/内在冲突 -> 觉察练习。
- 质量门禁新增伪研究拦截：不允许无来源的“研究发现/实验发现/百分比/脑区”表达。
- 育儿线强制检查“可以换成……”话术模板和30秒练习。
- 女性成长线强制检查至少2个“你可以问自己”觉察问题和心理动力学视角。
- 新增 `scripts/sync_obsidian.py`，可把 GitHub 生成的 `article_*.md` 同步到本地 Obsidian 知识库并生成索引。

## 本次内容优化

- 新增程序级硬去重：扫描最近 30 天 `article_*.md`，不再只依赖“提示词里提醒模型别重复”。
- 新增内容家族冷却：厌学/不想上学、作业学习、焦虑情绪、手机屏幕、边界讨好、自我价值、亲密关系、职场情绪等主题 10 天内默认不连写。
- 微博热搜选题最多重试 3 次；如果模型继续选择近期相似角度，会被脚本拦截并换题。
- 成文后增加最终质量门禁：拦截重复标题、泛标题（如“今天微博热搜那个话题”）、禁用表达、字数异常和缺少配图占位符。
- 文章 frontmatter 新增 `topic` 和 `topic_family`，方便后续继续做运营分析和去重。
- 栏目兜底话题池扩充，降低热点不可用时重复写“厌学/焦虑/作业”的概率。

## 本次定位调整

- 公众号定位从原“心光馨语/轻松心理学日更”调整为“心光心理学/双栏目运营”。
- 周一、周三、周五：微博热搜驱动育儿与亲子沟通文章。
- 周二、周四、周六：女性自我成长文章，采用温暖、专业的心理动力学咨询师视角。
- 周日默认跳过，避免继续日更旧定位。

## 关键配置

- 公众号：心光心理学
- AppID：`wx52189e9b012018e1`
- 脚本入口：`scripts/auto_publish.py`
- 手动触发：
  ```bash
  cd ~/.claude/skills/teen-psychology-insights/scripts
  python3 auto_publish.py --dry-run
  ```
- 强制指定栏目：
  ```bash
  python3 auto_publish.py --theme parenting --topic "孩子顶嘴时父母怎么回应" --dry-run
  python3 auto_publish.py --theme women_growth --topic "为什么总是在关系里先照顾别人" --dry-run
  ```
- 本地 Obsidian 同步：
  ```bash
  python3 scripts/sync_obsidian.py --pull
  ```
- 审稿模式：
  ```bash
  python3 scripts/auto_publish.py --review-only
  ```

## 调度

- Cloudflare Worker：`~/cloudflare-workers/github-scheduler/`
- 事件：`repository_dispatch: daily-psychology`
- 时间：每天 20:00 北京时间触发；Worker 限制周一至周六，脚本内部也会在周日跳过。

## 环境

- `WECHAT_API_KEY`
- `DEEPSEEK_API_KEY` 或 `ARK_API_KEY`
- `ARK_API_KEY` + `IMGBB_API_KEY` 用于豆包 Seedream 配图与图片托管

## 注意

- 不要恢复 GitHub Actions 原生 `schedule`，定时任务统一走 Cloudflare Worker。
- 不要把 API Key 写进仓库。
- 发布接口仍使用 AppID，不依赖本地显示名称。
- GitHub Actions 不能直接写本机 Obsidian；本地知识库通过同步脚本或本机定时任务更新。
- Obsidian 审稿修改默认不会被后续同步覆盖；如果确实要用仓库版本覆盖本地审稿稿件，手动运行 `python3 scripts/sync_obsidian.py --pull --overwrite-local`。
- 如果要切换成“GitHub 只生成 -> Obsidian 审稿 -> 手动推送公众号草稿箱”，下一步需要把 workflow 命令改为 `python3 auto_publish.py --review-only`，再补一个从 Obsidian 文件推送草稿箱的本地发布脚本。
