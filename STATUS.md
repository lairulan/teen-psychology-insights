# teen-psychology-insights STATUS v4.0 — 2026-04-08

## 断点
- **本次完成（v4.0）**：引擎全面替换 — DeepSeek V3 替代 Gemini 作文字主力，豆包 Seedream 为唯一配图引擎，移除所有 GOOGLE_API_KEY 依赖，新增 DEEPSEEK_API_KEY + ARK_API_KEY，修复停更 8 天的问题
- **上一版本（v3.4）**：选题防重复修复 — 热搜 JSON 解析截断修复 + 纯文本兜底，日历选题池扩至每月 15 个，7 天去重
- **下一步**：日常运营，GitHub Actions 每天 11:00 自动触发，人工到草稿箱审核后发布

## 环境
- 脚本：`scripts/auto_publish.py`（唯一入口）
- 手动触发：`cd ~/.claude/skills/teen-psychology-insights && DEEPSEEK_API_KEY="..." ARK_API_KEY="..." WECHAT_API_KEY="..." IMGBB_API_KEY="..." python3 scripts/auto_publish.py`
- GitHub Actions cron：`0 3 * * *`（UTC）= 北京时间 11:00
- GitHub Secrets 已配置：WECHAT_API_KEY / DEEPSEEK_API_KEY / ARK_API_KEY / IMGBB_API_KEY

## 关键配置
- 公众号：心光馨语 / AppID：wx52189e9b012018e1
- 文字引擎：DeepSeek V3（deepseek-chat）主力，豆包 doubao-seed-2-0-lite 兜底
- 图片引擎：豆包 Seedream（doubao-seedream-4-5-251128）→ imgbb 永久托管
- 排版：grace 主题，暖橙色调 #FF9F43，封面图 2560×1440，正文配图 1920×1920

## 已知问题
- 无

## 勿碰
- `scripts/auto_publish.py` 中的 AppID，已与 GitHub Secrets 保持一致
- `.github/workflows/daily-publish.yml` cron 配置
- GitHub Secrets：DEEPSEEK_API_KEY / ARK_API_KEY（不可明文写入代码）
