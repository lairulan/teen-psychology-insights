# teen-psychology-insights STATUS v3.3 — 2026-03-12

## 断点
- 本次完成：v3.3 排版风格升级 — 背景改为奶白#FFFBF5，混合字体（标题宋体+正文黑体），行距2.0，字色#3D3020；语气词克制（全篇≤2处）；配图布局改为开头1张+中间1-2张
- 下一步：日常运营，GitHub Actions 每天 11:00 自动触发，人工到草稿箱审核后发布

## 环境
- 脚本：`scripts/auto_publish.py`（唯一入口）
- 手动触发：`cd ~/.claude/skills/teen-psychology-insights && WECHAT_API_KEY="xhs_a565dc0d2929da8ec203ed7d7b372dbd" python3 scripts/auto_publish.py`
- GitHub Actions cron：`0 3 * * *`（UTC）= 北京时间 11:00
- GitHub Secrets 已配置：WECHAT_API_KEY / GOOGLE_API_KEY / IMGBB_API_KEY / DOUBAO_API_KEY

## 关键配置
- 公众号：心光馨语 / AppID：wx52189e9b012018e1
- 排版：grace主题，背景#FFFBF5，标题宋体，正文黑体16px行距2.0，字色#3D3020
- 图片流程：Imagen 4 → 豆包 Seedream 兜底 → imgbb 永久托管

## 已知问题
- 无

## 勿碰
- `scripts/auto_publish.py` 中的 AppID 和 API Key，已与 GitHub Secrets 保持一致
- `.github/workflows/daily-publish.yml` cron 配置
