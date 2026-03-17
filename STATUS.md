# teen-psychology-insights STATUS v3.4 — 2026-03-14

## 断点
- 本次完成：v3.4 选题防重复修复 — 修复热搜JSON解析失败（截断修复+纯文本兜底），日历选题池扩至每月15个，新增7天去重机制
- 上一版本：v3.3 排版风格升级 — 背景改为奶白#FFFBF5，混合字体（标题宋体+正文黑体），行距2.0，字色#3D3020
- 下一步：日常运营，GitHub Actions 每天 11:00 自动触发，人工到草稿箱审核后发布

## 环境
- 脚本：`scripts/auto_publish.py`（唯一入口）
- 手动触发：`cd ~/.claude/skills/teen-psychology-insights && WECHAT_API_KEY="xhs_a565dc0d2929da8ec203ed7d7b372dbd" python3 scripts/auto_publish.py`
- GitHub Actions cron：`0 3 * * *`（UTC）= 北京时间 11:00
- GitHub Secrets 已配置：WECHAT_API_KEY / GOOGLE_API_KEY / IMGBB_API_KEY / DOUBAO_API_KEY

## 关键配置
- 公众号：心光馨语 / AppID：${WECHAT_APP_ID}
- 排版：grace主题，背景#FFFBF5，标题宋体，正文黑体16px行距2.0，字色#3D3020
- 图片流程：Imagen 4 → 豆包 Seedream 兜底 → imgbb 永久托管

## 已知问题
- 无

## 勿碰
- `scripts/auto_publish.py` 中的 AppID 和 API Key，已与 GitHub Secrets 保持一致
- `.github/workflows/daily-publish.yml` cron 配置
