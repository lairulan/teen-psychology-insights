# teen-psychology-insights STATUS v3.2 — 2026-03-12

## 断点
- 本次完成：v3.2 双引擎配图上线（Imagen 4 → 豆包 Seedream 兜底 + imgbb 永久存储），今日文章《新学期第一个月，孩子为什么这么容易"崩"？》发布成功，封面+2张正文配图全部正常
- 下一步：日常运营，GitHub Actions 每天 11:00 自动触发，人工到草稿箱审核后发布

## 环境
- 脚本：`scripts/auto_publish.py`（唯一入口）
- 手动触发：`cd ~/.claude/skills/teen-psychology-insights && WECHAT_API_KEY="xhs_a565dc0d2929da8ec203ed7d7b372dbd" python3 scripts/auto_publish.py`
- GitHub Actions cron：`0 3 * * *`（UTC）= 北京时间 11:00
- GitHub Secrets 已配置：WECHAT_API_KEY / GOOGLE_API_KEY / IMGBB_API_KEY / DOUBAO_API_KEY

## 关键配置
- 公众号：心光馨语
- AppID：`wx52189e9b012018e1`
- WECHAT_API_KEY：`xhs_a565dc0d2929da8ec203ed7d7b372dbd`
- 图片流程：Imagen 4 → 豆包 Seedream 兜底 → imgbb 永久托管

## 已知问题
- 无

## 勿碰
- `scripts/auto_publish.py` 中的 AppID 和 API Key，已与 GitHub Secrets 保持一致
- `.github/workflows/daily-publish.yml` cron 配置
