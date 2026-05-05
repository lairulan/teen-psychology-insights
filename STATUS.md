# teen-psychology-insights STATUS v5.0 — 2026-05-05

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
